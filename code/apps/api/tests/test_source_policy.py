import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app import main,source_policy,chat_agent,retrieval,providers,structured_chat,conversation_routing,source_answers,processing
from app.db import sql
from app.source_intent import project_request
from app.source_answer_contracts import SourceAnswer
from test_search_readiness import workspace,source,viewer
from test_main_chat_agent import connection
from test_chat_polish import row,record

@pytest.mark.parametrize('question',[
    'how many porject are they','no u shoude be use jira and see how may project ?',
    'How many projects do I have?','show project','what Jira projects do I have?',
    'كم عدد المشاريع في جيرا؟','قصدي المشاريع',
])
def test_project_requests_execute_sources_before_help(monkeypatch,question):
    calls=[]
    monkeypatch.setattr(structured_chat.connectors,'Provider',lambda config,*a:SimpleNamespace(project_snapshot=lambda:calls.append(config['scope_id']) or record(config['scope_id'])))
    result,deps=structured_chat.answer(question,[row('ONE'),row('TWO')],[])
    assert set(calls)=={'ONE','TWO'} and not deps
    assert result['project_coverage']['verified_count']==2 and not result['insufficient_evidence']
    assert all(p.get('live') for p in result['evidence'])
    monkeypatch.setattr(providers,'structured',lambda *a,**k:pytest.fail('Source corrections must not be answered as help.'))
    assert conversation_routing.plan(question,[],{},lambda:None)['route']=='answer'

def test_duplicate_project_and_unavailable_scope_do_not_inflate_count(monkeypatch):
    def provider(config,*a):
        return SimpleNamespace(project_snapshot=lambda:None if config['scope_id']=='EMPTY' else record('SAME'))
    monkeypatch.setattr(structured_chat.connectors,'Provider',provider)
    result,_=structured_chat.answer('count projects',[row('SAME'),row('SAME'),row('EMPTY')],[])
    assert result['project_coverage']['verified_count']==1
    assert result['insufficient_evidence'] and not result['project_coverage']['complete']

def test_product_help_and_named_project_overview_are_not_project_enumerations():
    assert not project_request('What is project Atlas?')
    assert not project_request('Why is the project delayed?')
    assert conversation_routing.plan('hi',[],{},lambda:None)['route']=='greeting'

def test_live_only_never_calls_stored_search_and_cannot_deliver_stored_citations(workspace,monkeypatch):
    monkeypatch.setenv('LINKMIND_CHAT_AGENT','1');monkeypatch.setenv('LINKMIND_CHAT_POLISH','1')
    monkeypatch.setattr(chat_agent,'connections',lambda *a:[])
    monkeypatch.setattr(chat_agent,'plan',lambda *a,**k:dict(route='answer',query='unknown',use_previous=False))
    monkeypatch.setattr(main,'search',lambda *a,**k:pytest.fail('Live Only must never read the stored index.'))
    cid=main.create_conversation(main.NewConversation(source_policy='live'),viewer())['id']
    result=main.ask(cid,main.Question(question='Where is the launch evidence?'),viewer())
    assert not result['evidence'] and result['source_policy']=='live'
    assert not any(a['mode']=='stored' for a in result['retrieval_activity'])
    with pytest.raises(HTTPException):source_policy.enforce('live',{'evidence':[{'id':'stored'}]},['stored'])
    with source_policy.scope('live'):
        with pytest.raises(HTTPException):retrieval.search(viewer(),'anything')

def test_stored_uploads_work_but_known_demo_is_opt_in(workspace,monkeypatch):
    monkeypatch.setenv('LINKMIND_CHAT_AGENT','1');monkeypatch.setenv('LINKMIND_CHAT_POLISH','0')
    for module in (source_answers,):monkeypatch.setattr(module,'engine',main.engine)
    good=source(workspace,b'QuartzProject is owned by the real uploaded knowledge contact.',enrichment_requested=False)
    demo=source(workspace,b'QuartzProject has an unrelated synthetic owner.',enrichment_requested=False)
    while processing.process_one():pass
    sql(workspace,"UPDATE document_versions SET dataset_id='test-demo' WHERE id=:id",id=demo.version_id)
    with source_policy.scope('stored'):
        found=retrieval.search(viewer(),'QuartzProject',semantic=False)
    assert good.document_id in {p['document_id'] for p in found} and demo.document_id not in {p['document_id'] for p in found}
    monkeypatch.setattr(chat_agent,'connections',lambda *a:pytest.fail('Stored knowledge cannot query MCP.'))
    cid=main.create_conversation(main.NewConversation(source_policy='stored',document_ids=[demo.document_id]),viewer())['id']
    result=main.ask(cid,main.Question(question='QuartzProject'),viewer())
    assert result['evidence'] and all(p['synthetic'] for p in result['evidence'])
    assert result['source_policy']=='stored' and not result['live_dependencies']

def test_combined_preserves_legitimate_uploads_and_live_evidence(workspace,monkeypatch):
    monkeypatch.setenv('LINKMIND_CHAT_AGENT','1');monkeypatch.setenv('LINKMIND_CHAT_POLISH','0')
    for module in (source_answers,):monkeypatch.setattr(module,'engine',main.engine)
    job=source(workspace,b'QuartzProject has useful uploaded project knowledge.',enrichment_requested=False)
    while processing.process_one():pass
    monkeypatch.setattr(chat_agent,'connections',lambda *a:[])
    cid=main.create_conversation(main.NewConversation(source_policy='combined'),viewer())['id']
    result=main.ask(cid,main.Question(question='QuartzProject'),viewer())
    assert any(p['document_id']==job.document_id for p in result['evidence'])
    source_policy.enforce('combined',{'evidence':[{'id':'upload'},{'id':'native','live':{'connection_id':'x'}}]},['upload'])

def test_greetings_are_not_reused_as_factual_retrieval_topics():
    previous=[dict(question='hi',response={'message':'Hello'})]
    assert conversation_routing.plan('how many porject are they',previous,{},lambda:None)['query']=='how many porject are they'

def test_legacy_history_is_preserved_but_cannot_continue_as_live(workspace):
    cid=main.create_conversation(main.NewConversation(source_policy='combined'),viewer())['id']
    sql(workspace,"UPDATE conversations SET source_policy='legacy' WHERE id=:id",id=cid)
    with pytest.raises(HTTPException) as exc:main.ask(cid,main.Question(question='hi'),viewer())
    assert exc.value.status_code==409
    assert main.history(cid,viewer())['source_policy']=='legacy'

def test_live_cannot_accept_explicit_stored_scope(workspace):
    job=source(workspace)
    with pytest.raises(HTTPException):main.create_conversation(main.NewConversation(source_policy='live',document_ids=[job.document_id]),viewer())

def test_real_connected_scope_defaults_new_chat_to_live(workspace,monkeypatch):
    from app import connectors
    from app.connector_providers import ConnectionSpec
    monkeypatch.setattr(connectors,'engine',main.engine)
    cid=connectors.create(viewer(),ConnectionSpec(kind='jira',execution='mock',name='Scope metadata',scope_id='TEST'))['id']
    sql(workspace,"UPDATE source_connections SET mode='live',config=jsonb_set(config,'{execution}','\"real\"') WHERE id=:id",id=cid)
    assert main.create_conversation(main.NewConversation(),viewer())['source_policy']=='live'
    assert main.chat_source_options(viewer())['default_policy']=='live'

def test_live_expired_auth_does_not_fall_back_to_stored_knowledge(workspace,monkeypatch):
    from app.connector_transport import SourceFailure
    from app import connectors
    monkeypatch.setenv('LINKMIND_CHAT_AGENT','1');monkeypatch.setenv('LINKMIND_CHAT_POLISH','1')
    monkeypatch.setattr(chat_agent,'connections',lambda *a:[row('TEST')])
    monkeypatch.setattr(main,'search',lambda *a,**k:pytest.fail('An outage must not widen Live Only.'))
    def expired(*a,**k):raise SourceFailure('authentication_expired')
    monkeypatch.setattr(connectors,'Provider',lambda *a,**k:SimpleNamespace(search=expired))
    cid=main.create_conversation(main.NewConversation(source_policy='live'),viewer())['id']
    result=main.ask(cid,main.Question(question='Why is TEST delayed?'),viewer())
    assert not result['evidence'] and not result['statements']
    assert result['source_outcomes'][0]['code']=='authentication_expired'
    assert all(a['mode']!='stored' for a in result['retrieval_activity'])

def test_demo_loader_refuses_real_runtime_before_mutation(workspace,monkeypatch):
    before=sql(workspace,'SELECT count(*) FROM documents').scalar()
    monkeypatch.setenv('LINKMIND_CONNECTOR_NETWORK','1')
    with pytest.raises(HTTPException) as exc:main.load_company_dataset(viewer())
    assert exc.value.status_code==403 and sql(workspace,'SELECT count(*) FROM documents').scalar()==before
