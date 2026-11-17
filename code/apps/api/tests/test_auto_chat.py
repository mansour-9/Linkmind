"""Automatic retrieval is tested against disposable mock data, never a live preview."""
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app import main, auto_agent, chat_agent, processing, providers, source_answers, connectors
from app.db import sql
from app.query_limits import question_limits, QueryLimits
from app.connector_demo import DemoProvider
from app.connector_transport import SourceFailure
from pydantic import ValidationError
from test_search_readiness import workspace, source, viewer, OMAR
from test_main_chat_agent import connection


@pytest.fixture
def automatic(workspace,monkeypatch):
    monkeypatch.setenv('LINKMIND_AUTO_CHAT','1')
    for module in (connectors,source_answers,providers):monkeypatch.setattr(module,'engine',main.engine)
    monkeypatch.setattr(providers,'configured',lambda:False)
    monkeypatch.setattr(main,'configured',lambda:False)
    monkeypatch.setattr(providers,'embed',lambda *a,**k:pytest.fail('Automatic chat must not start embeddings.'))
    return workspace


def ask(question,attachments=(),cid=None,user=None,documents=()):
    user=user or viewer()
    cid=cid or main.create_conversation(main.NewConversation(document_ids=list(documents)),user)['id']
    return cid,main.ask(cid,main.Question(question=question,attachment_document_ids=list(attachments)),user)


def test_auto_default_and_real_uploaded_text_without_graph(automatic):
    job=source(automatic,b'Quartz launch onboarding contact is Maya Chen.',enrichment_requested=False)
    while processing.process_one():pass
    cid,result=ask('Quartz onboarding')
    assert result['source_policy']=='auto' and result['statements']
    assert any(p['document_id']==job.document_id for p in result['evidence'])
    assert sql(automatic,'SELECT count(*) FROM entities WHERE version_id=:v',v=job.version_id).scalar()==0


def test_attachments_persist_and_are_reauthorized(automatic):
    job=source(automatic,b'Quartz delivery is owned by Priya.',visibility='private',enrichment_requested=False)
    while processing.process_one():pass
    cid,result=ask('Summarize this file',attachments=[job.document_id])
    assert result['statements']
    assert main.history(cid,viewer())['attachments'][0]['document_id']==str(job.document_id)
    main.delete(job.document_id,viewer())
    assert not main.history(cid,viewer())['attachments']
    assert main.history(cid,viewer())['turns'][0]['suppressed']


def test_private_and_unknown_attachments_fail_before_model(automatic,monkeypatch):
    job=source(automatic,visibility='private',enrichment_requested=False)
    monkeypatch.setattr(providers,'structured',lambda *a,**k:pytest.fail('No model may see an inaccessible attachment.'))
    for doc in (job.document_id,uuid4()):
        with pytest.raises(HTTPException) as exc:ask('Read this file',attachments=[doc],user=viewer(OMAR))
        assert exc.value.status_code==404


def test_not_ready_attachment_is_an_explicit_wait(automatic):
    job=source(automatic,enrichment_requested=False)
    with pytest.raises(HTTPException) as exc:ask('Explain this',attachments=[job.document_id])
    assert exc.value.status_code==409 and exc.value.detail['code']=='attachment_not_ready'


def test_auto_combines_live_and_file_while_one_source_fails(automatic,monkeypatch):
    job=source(automatic,b'Quartz launch feedback comes from Customer Success.',enrichment_requested=False)
    while processing.process_one():pass
    connection('confluence','DOCS');connection('confluence','OUTAGE');connection('jira','QUARTZ')
    original=DemoProvider.search
    def search(self,*a,**k):
        if self.spec.scope_id=='OUTAGE':raise SourceFailure('source_outage')
        return original(self,*a,**k)
    monkeypatch.setattr(DemoProvider,'search',search)
    _,result=ask('Quartz launch',attachments=[job.document_id])
    assert any(p.get('live') for p in result['evidence'])
    assert any(not p.get('live') for p in result['evidence'])
    assert any(o['code']=='source_outage' for o in result['source_outcomes'])


def test_file_only_never_widens_to_connected_sources(automatic,monkeypatch):
    job=source(automatic,b'Quartz project source evidence.',enrichment_requested=False)
    while processing.process_one():pass
    connection('confluence','DOCS')
    monkeypatch.setattr(DemoProvider,'search',lambda *a,**k:pytest.fail('File-only scope cannot contact MCP.'))
    _,result=ask('Use only this file to explain Quartz',attachments=[job.document_id])
    assert result['statements'] and not result['live_dependencies']


def test_archived_chat_is_unavailable_and_not_in_sidebar(automatic):
    cid,_=ask('hi')
    sql(automatic,'UPDATE conversations SET archived_at=now() WHERE id=:id',id=cid)
    assert cid not in {c['id'] for c in main.conversations(viewer())}
    with pytest.raises(HTTPException):main.history(cid,viewer())
    with pytest.raises(HTTPException):ask('Who owns it?',cid=cid)


def test_one_targeted_followup_can_search_a_missing_part(automatic,monkeypatch):
    from dataclasses import replace
    connection('confluence','DOCS');queries=[];answers=[]
    original=DemoProvider.record
    monkeypatch.setattr(DemoProvider,'get',lambda self,native_id,**kw:replace(original(self),native_id=native_id))
    def search(self,q,limit=4):
        queries.append(q);return [dict(native_id='demo-1' if len(queries)==1 else 'demo-2',title='Responsibility')]
    monkeypatch.setattr(DemoProvider,'search',search)
    def answer(question,sources,*a,**kw):
        answers.append(sources)
        return dict(statements=[dict(text='Available source context.',evidence=[dict(passage_id=sources[0]['reference_id'],quote='')])],provider='bedrock',
            insufficient_evidence=len(answers)==1,followup_query='technical responsibilities' if len(answers)==1 else '',validation_summary={})
    monkeypatch.setattr(auto_agent.source_answer_provider,'linked_answer',answer)
    _,result=ask('Who has technical responsibility?')
    assert len(answers)==2 and queries[-1]=='technical responsibilities'
    assert len(result['live_dependencies'])==2


def test_model_cannot_request_an_undiscovered_issue_key(automatic,monkeypatch):
    connection('confluence','DOCS');connection('jira','QUARTZ');reads=[]
    original=connectors.live
    def live(user,cid,body):
        reads.append(body.native_id)
        assert body.native_id!='QUARTZ-999'
        return original(user,cid,body)
    monkeypatch.setattr(connectors,'live',live)
    monkeypatch.setattr(auto_agent.source_answer_provider,'linked_answer',lambda *a,**kw:dict(statements=[],provider='bedrock',
        insufficient_evidence=True,followup_query='QUARTZ-999',validation_summary={}))
    ask('Find the responsibility overview')
    assert reads==['demo-1']


def test_attachment_only_natural_request_cannot_search_live(automatic,monkeypatch):
    job=source(automatic,b'The accepted file code is AMBER-12.',enrichment_requested=False)
    while processing.process_one():pass
    connection('confluence','DOCS')
    monkeypatch.setattr(DemoProvider,'search',lambda *a,**k:pytest.fail('A file-only request must stay file-only.'))
    _,result=ask('What is the code in the uploaded file only?',attachments=[job.document_id])
    assert result['statements'] and not result['live_dependencies']


def test_model_failure_never_saves_a_draft_or_retries(automatic,monkeypatch):
    job=source(automatic,b'The accepted file code is AMBER-12.',enrichment_requested=False)
    while processing.process_one():pass
    calls=[]
    def blocked(*a,**k):
        calls.append(True);raise providers.ModelResponseError('content_filtered')
    monkeypatch.setattr(auto_agent.source_answer_provider,'linked_answer',blocked)
    with pytest.raises(HTTPException):ask('What is the accepted code?',attachments=[job.document_id])
    assert len(calls)==1


def test_linked_answer_has_no_tool_execution_or_quote_repair_contract():
    from app.source_answer_contracts import LinkedAnswer
    schema=LinkedAnswer.model_json_schema()
    assert set(schema['properties'])=={'statements','insufficient_evidence','followup_query'}
    with pytest.raises(ValidationError):LinkedAnswer(statements=[],insufficient_evidence=True,followup_query='',actions=[dict(tool='read')])


def test_source_read_limit_is_not_reported_as_access_revocation(automatic,monkeypatch):
    cid=connection('confluence','DOCS')
    def limited(*a,**k):raise SourceFailure('source_limit')
    monkeypatch.setattr(connectors,'Provider',lambda *a,**k:SimpleNamespace(authorize=limited))
    with pytest.raises(HTTPException) as exc:
        auto_agent.assert_live(viewer(),[dict(connection_id=str(cid),native_id='demo-1',generation=0,revision='1')],main.engine)
    # Read the actual configured generation rather than assuming the seed's value.
    if exc.value.status_code==409:
        with main.engine.connect() as conn:generation=connectors.owned(conn,viewer(),cid).generation
        with pytest.raises(HTTPException) as exc:
            auto_agent.assert_live(viewer(),[dict(connection_id=str(cid),native_id='demo-1',generation=generation,revision='1')],main.engine)
    assert exc.value.status_code==503 and exc.value.detail['code']=='source_limit'


def test_broad_discovery_reserves_room_for_fresh_access_checks(automatic,monkeypatch):
    for scope in ['ONE','TWO','THREE']:connection('confluence',scope)
    calls=[]
    def search(*a,**k):return [dict(native_id=str(i),title='Role page '+str(i)) for i in range(1,7)]
    monkeypatch.setattr(connectors,'Provider',lambda *a,**k:SimpleNamespace(search=search,authorize=lambda *a:SimpleNamespace(revision='1')))
    def live(user,cid,body):
        calls.append((str(cid),body.native_id));ref=str(cid)+'-'+body.native_id
        return dict(evidence=dict(original_url='https://fixture.test/'+ref,source_revision='1',source_updated_at='2026-11-17T00:00:00Z',observed_at='2026-11-17T00:00:00Z',synthetic=True,fields=[]),
            passages=[dict(id=ref,text='The responsibility belongs to the named delivery team in this fictional source.',locator={})])
    monkeypatch.setattr(connectors,'live',live)
    _,result=ask('Explain delivery responsibilities')
    assert len(calls)==4 and len(result['live_dependencies'])==4
    assert all(o['code']=='observed' for o in result['source_outcomes'])


@pytest.mark.parametrize('kind',['onedrive','sharepoint'])
def test_microsoft_search_stays_in_configured_folder_and_skips_remote_items(monkeypatch,kind):
    from app.connector_providers import Provider
    from test_connectors import spec
    provider=Provider(spec(kind))
    calls=[]
    def get(url,params=None):
        calls.append(url)
        return {'value':[
            {'id':'visible','name':'Brief.docx','file':{},'parentReference':{'driveId':'drive','id':'42'}},
            {'id':'remote','name':'Remote.docx','remoteItem':{},'parentReference':{'driveId':'other','id':'42'}},
            {'id':'sheet','name':'Data.xlsx','file':{},'parentReference':{'driveId':'drive','id':'42'}}]}
    provider.client=SimpleNamespace(get=get)
    assert provider.search('customer brief')==[dict(native_id='visible',title='Brief.docx')]
    assert '/drives/drive/items/42/search(' in calls[0]


def test_workspace_reset_clears_content_and_preserves_connections_and_usage(automatic):
    from scripts.clean_workspace import purge
    job=source(automatic,enrichment_requested=False)
    while processing.process_one():pass
    connection('confluence','DOCS')
    cid,_=ask('hi')
    result=purge(automatic,viewer().organization_id)
    assert result['before']['counts']['documents']>0
    assert not any(result['after']['counts'].values())
    assert result['before']['connections']==result['after']['connections']
    assert sql(automatic,'SELECT archived_at IS NOT NULL FROM conversations WHERE id=:id',id=cid).scalar()
