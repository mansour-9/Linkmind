import json
from datetime import timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import HTTPException

from app import connectors, main, processing, retrieval, providers
from app.connector_providers import ConnectionSpec, Provider
from app.connector_transport import SourceFailure, ReadClient, ReadLimits, AtlassianMCP
from app.db import sql
from test_search_readiness import workspace, viewer, OMAR
HTTPClient = httpx.Client


def ready_source():
    id=connectors.create(viewer(),spec())['id']
    connectors.authenticate_connection(viewer(),id)
    connectors.test_connection(viewer(),id)
    return id


def spec(kind='jira', **changes):
    values = dict(kind=kind,name='Fictional '+kind,scope_id='RF' if kind=='jira' else '42',
        site_url='https://fixture.atlassian.net' if kind in {'jira','confluence'} else '',
        drive_id='drive' if kind in {'onedrive','sharepoint'} else '',credential_ref='RF4_FIXTURE')
    return ConnectionSpec(**{**values,**changes})


@pytest.fixture
def wire(monkeypatch):
    monkeypatch.setenv('LINKMIND_CONNECTOR_NETWORK','1')
    monkeypatch.setenv('RF4_FIXTURE',json.dumps({'authorization':'Bearer fictional-secret'}))
    client = httpx.Client
    state = dict(status='Open',updated='2026-11-15T00:00:00Z',denied=False,requests=[])
    def issue():
        return dict(id='1',key='RF-1',fields=dict(project={'key':'RF'},summary='Fictional release',
            description={'type':'doc','content':[{'type':'text','text':'SourceOnlyConnectorsMarker'}]},
            status={'name':state['status']},assignee={'displayName':'Leila'},updated=state['updated']))
    state['issue']=issue
    def handle(request):
        state['requests'].append(request)
        if state['denied']: return httpx.Response(403,json={'error':'private source error text'})
        path=request.url.path
        if path.endswith('/search/jql'): return httpx.Response(200,json={'issues':[issue()],'isLast':True})
        if '/issue/' in path: return httpx.Response(200,json=issue())
        if '/pages' in path:
            item=dict(id='8',spaceId='42',version={'number':1,'createdAt':state['updated']},body={'storage':{'value':'<p>Readable Confluence policy.</p>'}})
            return httpx.Response(200,json={'results':[item]} if path.endswith('/pages') else item)
        if path.endswith('/children'):
            return httpx.Response(200,json={'value':[graph_item()]})
        if request.url.host=='fixture.sharepoint.com':
            assert 'authorization' not in request.headers
            return httpx.Response(200,content=b'Readable Graph source text.')
        if '/items/' in path: return httpx.Response(200,json=graph_item())
        raise AssertionError('Unexpected source request: '+str(request.url))
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:client(transport=httpx.MockTransport(handle),**kwargs))
    return state


def graph_item():
    return {'id':'file1','name':'policy.md','file':{},'parentReference':{'id':'42','driveId':'drive'},
        'eTag':'revision-1','lastModifiedDateTime':'2026-11-15T00:00:00Z',
        'webUrl':'https://fixture.sharepoint.com/sites/test/policy.md',
        '@microsoft.graph.downloadUrl':'https://fixture.sharepoint.com/download?opaque=temporary'}


@pytest.fixture
def local(workspace, monkeypatch):
    monkeypatch.setattr(connectors,'engine',main.engine)
    monkeypatch.setattr(providers,'engine',main.engine)
    return workspace


@pytest.mark.parametrize('kind',['jira','confluence','onedrive','sharepoint'])
def test_four_provider_scopes_return_original_records_with_bounded_reads(wire,kind):
    provider=Provider(spec(kind))
    records,cursor,complete=provider.page({})
    assert len(records)==1 and complete and cursor=={}
    record=records[0]
    assert record.content and record.updated.tzinfo and record.original_url.startswith('https://')
    if kind in {'onedrive','sharepoint'}:
        assert '@microsoft.graph.downloadUrl' not in record.payload
        assert not any('authorization' in r.headers for r in wire['requests'] if r.url.host.endswith('sharepoint.com'))
    else: assert all(r.method=='GET' for r in wire['requests'])


@pytest.mark.parametrize('mode',['live','sync'])
def test_live_only_does_not_persist_and_never_exposes_secrets(local,wire,mode):
    id=ready_source()
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode=mode,expected_generation=0))
    before=sql(local,'SELECT count(*) FROM documents').scalar()
    result=connectors.live(viewer(),id,connectors.LiveRead(native_id='RF-1',question='What is the status?'))
    assert result['retained'] is False and result['evidence']['fields']
    assert result['answer']['statements'] and result['provider']=='mock-extractive'
    assert sql(local,'SELECT count(*) FROM documents').scalar()==before
    assert 'fictional-secret' not in json.dumps(connectors.list_connections(viewer()),default=str)
    with pytest.raises(HTTPException) as exc: connectors.live(viewer(OMAR),id,connectors.LiveRead(native_id='RF-1'))
    assert exc.value.status_code==404


def test_sync_resume_revisions_unchanged_content_access_and_history(local,wire):
    id=ready_source()
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='sync',expected_generation=0))
    assert connectors.process_one() and processing.process_one()
    row=sql(local,'SELECT * FROM connected_resources WHERE connection_id=:id',id=id).mappings().one()
    hits=retrieval.search(viewer(),'SourceOnlyConnectorsMarker',[row.document_id],semantic=False)
    assert hits and main.evidence(UUID(hits[0]['id']),viewer())['provenance']['fields']
    from app.source_evidence import SourceEvidence
    assert SourceEvidence.model_validate(main.evidence(UUID(hits[0]['id']),viewer())['provenance']).identity.resource_type=='issue'
    assert not retrieval.search(viewer(OMAR),'SourceOnlyConnectorsMarker',[row.document_id],semantic=False)
    assert sql(local,'SELECT count(*) FROM entities WHERE version_id=:id',id=hits[0]['version_id']).scalar()==0
    conversation=main.create_conversation(main.NewConversation(document_ids=[row.document_id]),viewer())
    main.ask(conversation['id'],main.Question(question='What is the status?'),viewer())
    def collect():
        sql(local,'UPDATE source_connections SET sync_requested=true WHERE id=:id',id=id)
        assert connectors.process_one()
    collect()
    assert sql(local,'SELECT count(*) FROM document_versions WHERE document_id=:id',id=row.document_id).scalar()==1
    wire.update(status='Done',updated='2026-11-15T01:00:00Z')
    collect(); assert processing.process_one()
    assert sql(local,'SELECT count(*) FROM document_versions WHERE document_id=:id',id=row.document_id).scalar()==2
    assert main.history(conversation['id'],viewer())['turns'][0]['suppressed']
    wire['denied']=True
    with pytest.raises(HTTPException): main.evidence(UUID(hits[0]['id']),viewer())
    assert not retrieval.search(viewer(),'SourceOnlyConnectorsMarker',[row.document_id],semantic=False)
    assert sql(local,'SELECT count(*) FROM connected_revisions WHERE connection_id=:id',id=id).scalar()==2


def test_mode_removal_revokes_all_retained_surfaces_and_reconnect_keeps_identity(local,wire):
    id=ready_source()
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='sync',expected_generation=0))
    connectors.process_one();processing.process_one()
    resource=sql(local,'SELECT * FROM connected_resources WHERE connection_id=:id',id=id).mappings().one()
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='disconnected',expected_generation=1))
    assert not retrieval.search(viewer(),'SourceOnlyConnectorsMarker',[resource.document_id],semantic=False)
    assert ready_source()==id
    assert next(r for r in connectors.list_connections(viewer()) if r['id']==id)['name']==spec().name
    assert sql(local,'SELECT count(*) FROM connected_resources WHERE connection_id=:id',id=id).scalar()==1
    with pytest.raises(HTTPException) as exc:
        connectors.change_mode(viewer(),id,connectors.ModeChange(mode='sync',expected_generation=1))
    assert exc.value.status_code==409


def test_page_failure_keeps_checkpoint_and_records_for_resume(local,wire,monkeypatch):
    id=ready_source()
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='sync',expected_generation=0))
    original=Provider.page
    monkeypatch.setattr(Provider,'page',lambda self,cursor:([self.jira(wire['issue']())],{'token':'page-two'},False))
    connectors.process_one()
    sql(local,'UPDATE source_connections SET sync_requested=true WHERE id=:id',id=id)
    monkeypatch.setattr(Provider,'page',lambda *args:(_ for _ in ()).throw(SourceFailure('source_outage')))
    connectors.process_one()
    row=sql(local,'SELECT * FROM source_connections WHERE id=:id',id=id).mappings().one()
    assert row.cursor=={'token':'page-two'} and row.error_code=='source_outage'
    assert sql(local,'SELECT count(*) FROM connected_resources WHERE connection_id=:id',id=id).scalar()==1
    monkeypatch.setattr(Provider,'page',original)
    sql(local,'UPDATE source_connections SET sync_requested=true WHERE id=:id',id=id)
    connectors.process_one()
    assert sql(local,'SELECT cursor FROM source_connections WHERE id=:id',id=id).scalar()=={}


def test_native_read_rejects_cross_scope_and_stale_source_update(local,wire):
    provider=Provider(spec())
    malformed=wire['issue']();malformed['fields']['project']['key']='OTHER'
    with pytest.raises(SourceFailure,match='outside_scope'): provider.jira(malformed)
    id=ready_source()
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='sync',expected_generation=0))
    connectors.process_one();processing.process_one()
    wire.update(updated='2026-11-14T00:00:00Z',status='Obsolete')
    sql(local,'UPDATE source_connections SET sync_requested=true WHERE id=:id',id=id)
    connectors.process_one()
    assert sql(local,'SELECT source_updated_at FROM connected_resources WHERE connection_id=:id',id=id).scalar().day==15
    assert sql(local,'SELECT count(*) FROM connected_revisions WHERE connection_id=:id',id=id).scalar()==1


@pytest.mark.parametrize('status,code',[(401,'authentication_expired'),(403,'access_denied'),(404,'resource_missing'),(410,'checkpoint_expired'),(429,'rate_limited'),(503,'source_outage'),(302,'source_response_rejected')])
def test_transport_classifies_source_errors_without_returning_body(monkeypatch,status,code):
    monkeypatch.setenv('LINKMIND_CONNECTOR_NETWORK','1');monkeypatch.setenv('RF4_FIXTURE','{"authorization":"Bearer test"}')
    client=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda **kw:client(transport=httpx.MockTransport(lambda r:httpx.Response(status,json={'private':'secret error'})),**kw))
    with pytest.raises(SourceFailure,match=code): ReadClient('RF4_FIXTURE','graph.microsoft.com').get('https://graph.microsoft.com/v1.0/me')


def test_transport_fails_closed_without_network_and_bounds_size_and_calls(wire,monkeypatch):
    monkeypatch.delenv('LINKMIND_CONNECTOR_NETWORK')
    with pytest.raises(SourceFailure,match='network_not_enabled'): ReadClient('RF4_FIXTURE','graph.microsoft.com').get('https://graph.microsoft.com/v1.0/me')
    monkeypatch.setenv('LINKMIND_CONNECTOR_NETWORK','1')
    with pytest.raises(SourceFailure,match='source_limit'): ReadClient('RF4_FIXTURE','graph.microsoft.com',ReadLimits(max_calls=0)).get('https://graph.microsoft.com/v1.0/me')
    with pytest.raises(SourceFailure,match='source_size_limit'): ReadClient('RF4_FIXTURE','fixture.atlassian.net',ReadLimits(max_bytes=1)).get('https://fixture.atlassian.net/rest/api/3/issue/1')
    with pytest.raises(SourceFailure,match='unsafe_source_url'): ReadClient('RF4_FIXTURE','graph.microsoft.com').get('https://evil.invalid/token')


def test_mcp_negotiates_discovery_and_rejects_writes(wire,monkeypatch):
    client=HTTPClient; requests=[]
    def server(request):
        body=json.loads(request.content);requests.append(body)
        method=body['method']
        if method=='notifications/initialized':return httpx.Response(202)
        result={'protocolVersion':'2025-11-25'} if method=='initialize' else {'tools':[{'name':'getJiraIssue','inputSchema':{'required':['cloudId','issueIdOrKey']}}]} if method=='tools/list' else {'structuredContent':wire['issue']()}
        return httpx.Response(200,json={'jsonrpc':'2.0','id':body['id'],'result':result},headers={'Mcp-Session-Id':'fixture-session'})
    monkeypatch.setattr(httpx,'Client',lambda **kw:client(transport=httpx.MockTransport(server),**kw))
    mcp=AtlassianMCP('RF4_FIXTURE')
    assert mcp.call('getJiraIssue',{'cloudId':'fixture','issueIdOrKey':'RF-1'})['key']=='RF-1'
    count=len(requests)
    with pytest.raises(SourceFailure):mcp.call('createJiraIssue',{})
    assert len(requests)==count


@pytest.mark.parametrize('kind',['jira','confluence','onedrive','sharepoint','custom_mcp'])
def test_mock_management_is_functional_without_external_auth_or_network(local,monkeypatch,kind):
    monkeypatch.delenv('LINKMIND_CONNECTOR_NETWORK',raising=False)
    monkeypatch.setattr(ReadClient,'request',lambda *a,**k:pytest.fail('Demo must never contact a source'))
    config=ConnectionSpec(kind=kind,execution='mock',name='Demo '+kind,scope_id='unit-'+uuid4().hex)
    id=connectors.create(viewer(),config)['id']
    with pytest.raises(HTTPException):connectors.change_mode(viewer(),id,connectors.ModeChange(mode='live',expected_generation=0))
    assert connectors.authenticate_connection(viewer(),id)['synthetic']
    assert connectors.test_connection(viewer(),id)['retained'] is False
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='live',expected_generation=0))
    result=connectors.live(viewer(),id,connectors.LiveRead(native_id='demo-1'))
    assert result['synthetic'] and result['evidence']['synthetic']
    assert sql(local,'SELECT count(*) FROM connected_resources WHERE connection_id=:id',id=id).scalar()==0
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='sync',expected_generation=1))
    connectors.process_one();assert processing.process_one()
    assert sql(local,'SELECT count(*) FROM connected_resources WHERE connection_id=:id',id=id).scalar()==1
    assert sql(local,'SELECT count(*) FROM entities e JOIN document_versions v ON v.id=e.version_id WHERE v.document_id IN (SELECT document_id FROM connected_resources WHERE connection_id=:id)',id=id).scalar()==0
    config.name='Updated demo'
    connectors.edit(viewer(),id,connectors.ConfigurationEdit(expected_generation=2,configuration=config))
    row=next(r for r in connectors.list_connections(viewer()) if r['id']==id)
    assert row['mode']=='disconnected' and row['auth_state']=='unconfigured' and row['retained_resources']==0
    connectors.remove(viewer(),id,3)
    assert all(r['id']!=id for r in connectors.list_connections(viewer()))
    assert sql(local,'SELECT count(*) FROM connected_revisions WHERE connection_id=:id',id=id).scalar()==1


def test_configuration_secrets_and_member_writes_are_rejected(local):
    with pytest.raises(Exception):ConnectionSpec(kind='jira',execution='mock',name='URL credentials',scope_id='demo',site_url='https://user:secret@example.com')
    with pytest.raises(Exception):ConnectionSpec(kind='jira',execution='mock',name='Token',scope_id='demo',access_token='secret')
    id=connectors.create(viewer(),ConnectionSpec(kind='jira',execution='mock',name='Private config',scope_id='demo'))['id']
    with pytest.raises(HTTPException) as exc:connectors.list_connections(viewer(OMAR))
    assert exc.value.status_code==403
    for action in [lambda:connectors.authenticate_connection(viewer(OMAR),id),lambda:connectors.remove(viewer(OMAR),id,0),lambda:connectors.test_connection(viewer(OMAR),id)]:
        with pytest.raises(HTTPException) as exc:action()
        assert exc.value.status_code==403


def test_stale_worker_failure_cannot_cancel_a_new_collection_lease(local,wire):
    from uuid import uuid4
    id=ready_source();new_lease=uuid4()
    sql(local,"UPDATE source_connections SET lease_token=:lease,lease_until=now()+interval '1 minute' WHERE id=:id",id=id,lease=new_lease)
    connectors.failure(id,0,'source_outage',uuid4())
    assert sql(local,'SELECT lease_token FROM source_connections WHERE id=:id',id=id).scalar()==new_lease


def test_custom_mcp_checks_read_contract_scope_and_credential_audience(wire,monkeypatch):
    import socket
    client=HTTPClient
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))])
    monkeypatch.setenv('RF4_FIXTURE',json.dumps({'authorization':'Bearer fictional-custom','audience_host':'read.example'}))
    item={'resource_id':'r1','scope_id':'scope','revision':'1','updated_at':'2026-11-15T00:00:00Z','url':'https://read.example/page','text':'Original custom MCP evidence.'}
    def server(request):
        body=json.loads(request.content);method=body['method']
        if method=='notifications/initialized':return httpx.Response(202)
        result={'protocolVersion':'2025-11-25'} if method=='initialize' else {'tools':[{'name':'fetch_resource','annotations':{'readOnlyHint':True},'inputSchema':{'required':['resource_id','scope_id']}}]} if method=='tools/list' else {'structuredContent':item}
        return httpx.Response(200,json={'jsonrpc':'2.0','id':body['id'],'result':result})
    monkeypatch.setattr(httpx,'Client',lambda **kw:client(transport=httpx.MockTransport(server),**kw))
    config=ConnectionSpec(kind='custom_mcp',name='Custom read',scope_id='scope',mcp_url='https://read.example/mcp',credential_ref='RF4_FIXTURE')
    provider=connectors.Provider(config)
    assert provider.get('r1').content==b'Original custom MCP evidence.'
    item['scope_id']='other'
    with pytest.raises(SourceFailure,match='outside_scope'):provider.get('r1')
    monkeypatch.setenv('RF4_FIXTURE',json.dumps({'authorization':'Bearer fictional-custom','audience_host':'other.example'}))
    with pytest.raises(SourceFailure,match='credential_audience_mismatch'):provider.get('r1')


def test_connection_validation_does_not_echo_accidentally_submitted_secrets(local):
    from fastapi.testclient import TestClient
    result=TestClient(main.app).post('/api/v1/connections',headers={'Authorization':'Bearer demo-amal'},json={
        'kind':'jira','execution':'mock','name':'Invalid secret','scope_id':'demo','access_token':'NeverEchoThisSecret'})
    assert result.status_code==422 and 'NeverEchoThisSecret' not in result.text
