"""Offline regressions for the response and authorization shapes observed live."""
import json
import httpx
import pytest
from app import connectors
from app.connector_providers import Provider
from app.connector_transport import SourceFailure, ReadLimits
from test_connectors import spec, HTTPClient, local
from test_search_readiness import viewer, workspace

@pytest.fixture
def rovo(monkeypatch):
    from app.connector_transport import _protocol_cache
    _protocol_cache.clear()
    monkeypatch.delenv('LINKMIND_MCP_DISCOVERY_CACHE',raising=False)
    monkeypatch.setenv('LINKMIND_CONNECTOR_NETWORK','1')
    monkeypatch.setenv('RF4_FIXTURE',json.dumps({'authorization':'Bearer test-mcp-only'}))
    monkeypatch.delenv('RF4_UNUSED_NATIVE',raising=False)
    state=dict(requests=[],denied=False,legacy=False)
    issue=dict(id='1',key='RF-1',fields=dict(project={'key':'RF'},summary='Release',description='Original issue body',status={'name':'In Progress'},assignee=None,updated='2026-11-16T00:00:00Z'))
    page=dict(id='8',spaceId='42',body={'format':'html','value':'<p>Original approved page.</p>'},metadata={'version':{'number':3,'createdAt':'2026-11-16T00:00:00Z'}})
    state.update(issue=issue,page=page)
    def server(request):
        assert request.url.host=='mcp.atlassian.com', 'MCP credentials must not be sent to a native API'
        assert request.headers['authorization']=='Bearer test-mcp-only'
        body=json.loads(request.content);state['requests'].append(body)
        if state['denied']:return httpx.Response(403,json={'error':'denied'})
        method=body['method']
        if method=='notifications/initialized':return httpx.Response(202)
        if method=='initialize':result={'protocolVersion':'2025-11-25'}
        elif method=='tools/list':
            result={'tools':[{'name':name,'inputSchema':{'required':['cloudId'],'additionalProperties':False,'properties':{key:{} for key in keys}}} for name,keys in [
                ('getJiraIssue',['cloudId','issueIdOrKey','view']),
                ('getConfluencePage' if state['legacy'] else 'getConfluenceContent', ['cloudId','pageId','contentFormat'] if state['legacy'] else ['cloudId','content_id','detail','content_format'])]]+[
                {'name':'executeWrite','inputSchema':{}},{'name':'executeRead','inputSchema':{}}]}
        else:
            name=body['params']['name'];args=body['params']['arguments']
            if name=='getJiraIssue':
                assert args['view']=='full';value=issue
            else:
                if state['legacy']:
                    assert args['contentFormat']=='html'
                    value=dict(id='8',spaceId='42',body={'storage':{'value':'<p>Legacy original page.</p>'}},version={'number':2,'createdAt':'2026-11-16T00:00:00Z'})
                else:
                    assert args['detail']=='full' and args['content_format']=='html';value=page
            result={'structuredContent':value if state['legacy'] else {'data':value}}
        return httpx.Response(200,json={'jsonrpc':'2.0','id':body['id'],'result':result})
    monkeypatch.setattr(httpx,'Client',lambda **kw:HTTPClient(transport=httpx.MockTransport(server),**kw))
    return state

def config(kind='jira'):
    return spec(kind,transport='atlassian_mcp',cloud_id='test-cloud',credential_ref='RF4_UNUSED_NATIVE',mcp_credential_ref='RF4_FIXTURE')

@pytest.mark.parametrize('kind',['jira','confluence'])
def test_wrapped_originals_and_mcp_reauthorization(rovo,kind):
    limits=ReadLimits();p=Provider(config(kind),limits)
    record=p.get('RF-1' if kind=='jira' else '8',mcp=True)
    assert record.native_id==('1' if kind=='jira' else '8') and record.content and record.updated.tzinfo
    assert 'data' in record.payload
    if kind=='confluence':assert record.revision=='3' and record.content==b'Original approved page.'
    again=Provider(config(kind),limits).authorize(record.native_id)
    assert again.revision==record.revision
    assert sum(r['method']=='initialize' for r in rovo['requests'])==1
    assert sum(r['method']=='tools/call' for r in rovo['requests'])==2
    rovo['denied']=True
    with pytest.raises(SourceFailure,match='access_denied'):p.authorize(record.native_id)

@pytest.mark.parametrize('kind',['jira','confluence'])
def test_actual_scope_and_native_id_stay_enforced(rovo,kind):
    if kind=='jira':rovo['issue']['fields']['project']['key']='OTHER'
    else:rovo['page']['spaceId']='OTHER'
    with pytest.raises(SourceFailure,match='outside_scope'):Provider(config(kind)).get('RF-1' if kind=='jira' else '8',mcp=True)

@pytest.mark.parametrize('kind',['jira','confluence'])
def test_legacy_flat_records_remain_compatible(rovo,kind):
    rovo['legacy']=True
    record=Provider(config(kind)).get('RF-1' if kind=='jira' else '8',mcp=True)
    assert record.content
    if kind=='confluence':assert record.revision=='2'

def test_mcp_authentication_does_not_require_native_token(local,rovo):
    id=connectors.create(viewer(),config())['id']
    assert connectors.authenticate_connection(viewer(),id)['auth_state']=='server_credential'
    assert rovo['requests']==[]

def test_session_is_request_bounded_and_generic_tools_remain_unavailable(rovo):
    for _ in range(2):
        client=Provider(config()).mcp_client()
        for tool in ['executeRead','executeWrite','createJiraIssue']:
            with pytest.raises(SourceFailure,match='mcp_tool_unavailable'):client.call(tool,{})
    assert sum(r['method']=='initialize' for r in rovo['requests'])==2
    assert not any(r['method']=='tools/call' for r in rovo['requests'])
