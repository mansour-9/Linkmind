from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from starlette.responses import Response

from app import chat_agent, connectors, graph_explorer, knowledge_records, knowledge_sync, main, processing, providers, retrieval, source_answers
from app.connector_demo import DemoProvider
from app.connector_providers import ConnectionSpec, Provider, Record
from app.connector_transport import SourceFailure
from app.db import sql
from test_search_readiness import AMAL, OMAR, viewer, workspace


@pytest.fixture
def company(workspace,monkeypatch):
    monkeypatch.delenv('LINKMIND_LEGACY_CORPUS_TESTS',raising=False)
    for module in (connectors,knowledge_sync,knowledge_records,source_answers):monkeypatch.setattr(module,'engine',main.engine)
    monkeypatch.setattr(providers,'configured',lambda:False)
    monkeypatch.setattr(processing,'embed',lambda *a,**k:pytest.fail('Knowledge Sync uses lexical indexing.'))
    return workspace


def connect(scope,mode='sync',kind='jira'):
    user=viewer()
    id=connectors.create(user,ConnectionSpec(kind=kind,name=scope,scope_id=scope,execution='mock'))['id']
    connectors.authenticate_connection(user,id)
    connectors.test_connection(user,id)
    with main.engine.connect() as conn:generation=connectors.owned(conn,user,id).generation
    connectors.change_mode(user,id,connectors.ModeChange(mode=mode,expected_generation=generation))
    return id


def finish():
    for _ in range(30):
        if not (processing.process_one() or knowledge_sync.process_one()):return
    pytest.fail('Sync did not finish within the expected number of worker iterations.')


def install_records(monkeypatch):
    revision=['1','Dina Sample']
    def record(self):
        return Record('17',revision[0],datetime(2026,11,18,int(revision[0]),tzinfo=timezone.utc),
            'https://example.atlassian.net/browse/HARBOR-7','HARBOR-7.md',
            f'key: "HARBOR-7"\nassignee: "{revision[1]}"\nproject: {{"key": "HARBOR", "name": "Harbor Integration"}}\nSyncedZebra establishes an unrelated marker.'.encode(),{},
            [{'field':'key','value':'HARBOR-7'},{'field':'assignee','value':revision[1]},
             {'field':'project','value':{'key':'HARBOR','name':'Harbor Integration'}}])
    def page(self,cursor):
        if self.spec.scope_id=='FAILED':raise SourceFailure('authentication_expired')
        return [record(self)],{},True
    monkeypatch.setattr(DemoProvider,'page',page)
    monkeypatch.setattr(DemoProvider,'get',lambda self,id,**kwargs:record(self))
    return revision


def test_unified_sync_reuses_run_updates_and_isolates_corpora(company,monkeypatch):
    harbor=connect('HARBOR'); failed=connect('FAILED'); connect('LIVE',mode='live')
    revisions=install_records(monkeypatch)
    first=knowledge_sync.start(viewer())
    assert knowledge_sync.start(viewer())['id']==first['id']
    finish()
    assert sql(company,'SELECT status FROM knowledge_sync_runs WHERE id=:run',run=first['id']).scalar_one()=='partial'
    tasks={r.connection_id:r for r in sql(company,'SELECT * FROM knowledge_sync_tasks WHERE run_id=:run',run=first['id']).mappings()}
    assert set(tasks)=={harbor,failed}
    assert tasks[harbor].imported==1 and tasks[harbor].status=='completed'
    assert tasks[failed].failed==1 and tasks[failed].error_code=='authentication_expired'
    assert not main.repository_resources(viewer(),q='SyncedZebra',source_instance_id=None,format=None,project_id=None,team_id=None,
        after=None,before=None,limit=20,offset=0)['items']
    results=main.enterprise_search(viewer(),Response(),q='SyncedZebra',limit=20,offset=0)
    assert results and {row['document_id'] for row in results}=={sql(company,'SELECT document_id FROM connected_resources WHERE connection_id=:id',id=harbor).scalar_one()}
    assert not retrieval.search_manual(viewer(),'SyncedZebra')
    synchronized_id=results[0]['document_id']
    with pytest.raises(HTTPException) as exc:
        main.create_conversation(main.NewConversation(document_ids=[synchronized_id]),viewer())
    assert exc.value.status_code==404
    with pytest.raises(HTTPException) as exc:
        source_answers.ask(viewer(),source_answers.SourceQuestion(question='SyncedZebra?',document_ids=[synchronized_id]))
    assert exc.value.status_code==404
    with monkeypatch.context() as offline:
        offline.setattr(chat_agent,'connections',lambda *a:[])
        conversation=main.create_conversation(main.NewConversation(),viewer())['id']
        answer=main.ask(conversation,main.Question(question='What is SyncedZebra?'),viewer())
        assert not answer['evidence'] and answer['insufficient_evidence']
    assert not main.wiki(viewer(OMAR))
    assert {'Dina Sample','Harbor Integration'}<={r['name'] for r in main.wiki(viewer())}

    next_run=knowledge_sync.start(viewer())
    finish()
    assert sql(company,'SELECT skipped FROM knowledge_sync_tasks WHERE run_id=:run AND connection_id=:source',run=next_run['id'],source=harbor).scalar_one()==1
    revisions[:]=['2','Priya Sample']
    latest=knowledge_sync.start(viewer())
    finish()
    assert sql(company,'SELECT updated FROM knowledge_sync_tasks WHERE run_id=:run AND connection_id=:source',run=latest['id'],source=harbor).scalar_one()==1
    names={r['name'] for r in main.wiki(viewer())}
    assert 'Priya Sample' in names and 'Dina Sample' not in names


def test_manual_file_is_available_to_chat_and_attachments_are_rejected(company,monkeypatch):
    user=viewer()
    document=main.upload(user,UploadFile(file=BytesIO(b'ManualZebra is the recorded warranty codename.'),filename='warranty.txt'),'team')
    finish()
    assert retrieval.search_manual(user,'ManualZebra')[0]['document_id']==document['document_id']
    assert not main.enterprise_search(user,Response(),q='ManualZebra',limit=20,offset=0)
    conversation=main.create_conversation(main.NewConversation(),user)['id']
    response=main.ask(conversation,main.Question(question='What is ManualZebra?'),user)
    assert any(str(item['document_id'])==str(document['document_id']) for item in response['evidence'])
    with pytest.raises(HTTPException) as exc:
        main.ask(conversation,main.Question(question='ManualZebra?',attachment_document_ids=[document['document_id']]),user)
    assert exc.value.status_code==422
    with pytest.raises(HTTPException) as exc:
        main.upload(viewer(OMAR),UploadFile(file=BytesIO(b'Employee upload'),filename='blocked.txt'),'team')
    assert exc.value.status_code==403

    assert not knowledge_records.catalog(user,'ManualZebra',None,0,6)['items']
    with pytest.raises(HTTPException) as exc:
        knowledge_records.read(user,document['document_id'])
    assert exc.value.status_code==404


def test_full_record_is_independent_of_passages_and_claims(company,monkeypatch):
    connect('HARBOR')
    description='First paragraph.\n\n' + 'Keep the whole description beyond the cited key. ' * 30 + '\n\nFinal acceptance checkpoint.'
    payload={'key':'HARBOR-7','id':'17','fields':{
        'summary':'Partner delivery','description':description,'status':{'name':'In Progress'},
        'project':{'key':'HARBOR','name':'Harbor Integration'},'assignee':{'displayName':'Dina Sample'},
        'updated':'2026-11-18T01:00:00Z'}}
    provider=Provider(ConnectionSpec(kind='jira',name='Example',scope_id='HARBOR',execution='mock'))
    native=provider.jira(payload)
    monkeypatch.setattr(DemoProvider,'page',lambda *args:([native],{},True))
    monkeypatch.setattr(DemoProvider,'get',lambda *args,**kwargs:native)
    knowledge_sync.start(viewer())
    finish()

    item,=knowledge_records.catalog(viewer(),'HARBOR-7',None,0,6)['items']
    body=knowledge_records.read(viewer(),item['id'])
    assert body['current'] and body['body']==description
    assert body['issue_key']=='HARBOR-7' and body['metadata']['status']=='In Progress'
    assert {r['predicate'] for r in body['relationships']}=={'assigned_to','belongs_to_project'}
    assert body['original_url']==native.original_url
    assert main.entity_detail(company,viewer(),body['entity_id'])['claims']==[]
    assert graph_explorer.overview(company,viewer(),'Partner delivery')['entity']['id']==body['entity_id']
    passage=sql(company,"SELECT id FROM chunks WHERE version_id=:id AND line_number=1",id=item['version_id']).scalar_one()
    evidence=main.evidence(passage,viewer())
    assert evidence['quote']=='key: "HARBOR-7"' and evidence['record_id']==item['id']
    assert knowledge_records.read(viewer(),evidence['record_id'],evidence['version_id'])['body']==description
    assert not knowledge_records.catalog(viewer(OMAR),'HARBOR-7',None,0,6)['items']
    with pytest.raises(HTTPException) as exc:
        knowledge_records.read(viewer(OMAR),item['id'],item['version_id'])
    assert exc.value.status_code==404


def test_scheduled_run_discovers_connections_added_after_previous_run(company,monkeypatch):
    connect('HARBOR'); install_records(monkeypatch)
    first=knowledge_sync.start(viewer())
    finish()
    new=connect('NOTION',kind='notion')
    sql(company,"""INSERT INTO knowledge_sync_schedules(organization_id,owner_id,enabled,next_run_at)
        VALUES(:org,:owner,true,now()-interval '1 second')""",org=viewer().organization_id,owner=AMAL)
    finish()
    scheduled=sql(company,"SELECT id FROM knowledge_sync_runs WHERE trigger='scheduled'").scalar_one()
    assert scheduled!=first['id']
    assert new in sql(company,'SELECT connection_id FROM knowledge_sync_tasks WHERE run_id=:id',id=scheduled).scalars().all()


def test_stale_worker_cannot_publish_after_connection_changes(company,monkeypatch):
    harbor=connect('HARBOR')
    install_records(monkeypatch)
    original=DemoProvider.page

    def page(self,cursor):
        rows=original(self,cursor)
        sql(company,"UPDATE source_connections SET mode='disconnected',generation=generation+1 WHERE id=:id",id=harbor)
        return rows

    monkeypatch.setattr(DemoProvider,'page',page)
    run=knowledge_sync.start(viewer())
    finish()
    assert sql(company,'SELECT error_code FROM knowledge_sync_tasks WHERE run_id=:id',id=run['id']).scalar_one()=='connection_changed'
    assert not sql(company,'SELECT 1 FROM connected_resources WHERE connection_id=:id',id=harbor).first()


def test_confluence_sync_replays_opaque_cursor_in_the_same_scoped_tool(monkeypatch):
    provider=Provider(ConnectionSpec(kind='confluence',name='Company wiki',scope_id='42',space_key='ABL',
        site_url='https://example.atlassian.net',transport='atlassian_mcp',cloud_id='cloud',mcp_credential_ref='RF4_FIXTURE'))
    calls=[]

    def call(name,args):
        calls.append((name,args))
        if 'cursor' not in args:
            return {'results':[{'content':{'id':'101'}}], 'totalSize':2,
                '_links':{'next':'/wiki/rest/api/search?cursor=opaque%2Bvalue&limit=8'}}
        return {'results':[{'content':{'id':'102'}}], 'totalSize':2, '_links':{}}

    monkeypatch.setattr(provider,'mcp_client',lambda:SimpleNamespace(
        tools={'searchConfluence':{'properties':{'cursor':{}}}},call=call))
    monkeypatch.setattr(provider,'get',lambda native,**_:native)
    first,checkpoint,done=provider.sync_page({},None)
    assert first==['101'] and not done
    assert provider.sync_page(checkpoint,None)==(['102'],{},True)
    assert calls[1][1]['cursor']=='opaque+value'
    assert calls[0][1]['cql']==calls[1][1]['cql'] and 'space = "ABL"' in calls[1][1]['cql']


def test_confluence_sync_rejects_truncated_results_without_a_cursor(monkeypatch):
    provider=Provider(ConnectionSpec(kind='confluence',name='Company wiki',scope_id='42',space_key='ABL',
        site_url='https://example.atlassian.net',transport='atlassian_mcp',cloud_id='cloud',mcp_credential_ref='RF4_FIXTURE'))
    monkeypatch.setattr(provider,'mcp_client',lambda:SimpleNamespace(
        tools={'searchConfluence':{'properties':{'cursor':{}}}},
        call=lambda *_:{'results':[{'content':{'id':'101'}}],'totalSize':2,'_links':{}}))
    with pytest.raises(SourceFailure) as exc:
        provider.sync_page({},None)
    assert exc.value.code=='incomplete_page'


def test_bounded_knowledge_reads_reuse_fresh_access_and_leave_leases_on_read_limit(company,monkeypatch):
    harbor=connect('HARBOR'); install_records(monkeypatch)
    knowledge_sync.start(viewer()); finish()
    calls=[]

    def limit(*args):
        calls.append(True)
        raise SourceFailure('source_limit')

    monkeypatch.setattr(DemoProvider,'authorize',limit)
    connectors.refresh_access(viewer(),query='SyncedZebra',reuse_recent=True)
    assert not calls
    sql(company,"UPDATE connected_resources SET access_until=clock_timestamp()-interval '1 second' WHERE connection_id=:id",id=harbor)
    connectors.refresh_access(viewer(),query='SyncedZebra',reuse_recent=True)
    assert calls==[True]
    row=sql(company,'SELECT c.health,c.error_code,r.access_until FROM source_connections c JOIN connected_resources r ON c.id=r.connection_id WHERE c.id=:id',id=harbor).mappings().one()
    assert row.health=='ready' and row.error_code is None and row.access_until is not None
