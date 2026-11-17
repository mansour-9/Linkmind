import json
from dataclasses import replace
from uuid import uuid4
import pytest
from app import main,connectors,source_answers,providers,chat_agent,source_answer_provider,processing
from app.db import sql
from app.connector_providers import ConnectionSpec,Provider
from app.connector_demo import DemoProvider
from app.connector_transport import SourceFailure
from app.source_answer_contracts import PointerAnswer
from app.contracts import AnswerSupportVerdict
from test_search_readiness import workspace,source,viewer,OMAR


@pytest.fixture
def agent(workspace,monkeypatch):
    for module in (connectors,source_answers,providers):monkeypatch.setattr(module,'engine',main.engine)
    monkeypatch.setenv('LINKMIND_CHAT_AGENT','1')
    monkeypatch.delenv('LINKMIND_CHAT_POLISH',raising=False)
    monkeypatch.delenv('LINKMIND_CONNECTOR_NETWORK',raising=False)
    monkeypatch.delenv('LINKMIND_MCP_DISCOVERY_CACHE',raising=False)
    _real_connections=chat_agent.connections
    monkeypatch.setattr(chat_agent,'connections',lambda viewer,db:[r for r in _real_connections(viewer,db) if r['config'].get('execution')=='mock'])
    monkeypatch.setattr(providers,'configured',lambda:False)
    monkeypatch.setattr(chat_agent,'plan',lambda q,prev,*a,**k:dict(route='answer',query=q,use_previous=bool(prev)))
    monkeypatch.setattr(providers,'embed',lambda *a,**k:pytest.fail('No paid embedding for agent tests.'))
    return workspace


def connection(kind='jira',scope='HARBOR'):
    id=connectors.create(viewer(),ConnectionSpec(kind=kind,execution='mock',name='Test '+scope,scope_id=scope))['id']
    connectors.authenticate_connection(viewer(),id);connectors.test_connection(viewer(),id)
    with main.engine.connect() as conn:generation=connectors.owned(conn,viewer(),id).generation
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='live',expected_generation=generation))
    return id


def ask(text,conversation=None,user=None,documents=None):
    user=user or viewer()
    conversation=conversation or main.create_conversation(main.NewConversation(document_ids=documents or []),user)['id']
    return conversation,main.ask(conversation,main.Question(question=text),user)


def test_main_chat_discovers_live_resources_without_ids_and_keeps_followup_topic(agent,monkeypatch):
    id=connection();requests=[]
    monkeypatch.setattr(DemoProvider,'search',lambda self,q,limit=4:requests.append((self.spec.scope_id,q)) or [dict(native_id='demo-1',title='HARBOR')])
    cid,result=ask('What is HARBOR?')
    assert result['statements'] and result['live_dependencies'][0]['connection_id']==str(id)
    _,follow=ask('Who owns it?',cid)
    assert follow['statements'] and 'harbor' in requests[-1][1].casefold()
    assert follow['live_dependencies']
    saved=sql(agent,'SELECT response FROM conversation_turns WHERE conversation_id=:id ORDER BY created_at DESC',id=cid).scalar()
    assert all(p['text']=='' for p in saved['evidence'] if p.get('live'))
    assert saved['statements'] # derived answer and cited excerpts remain in conversation


def test_main_chat_does_not_search_unrelated_jira_project_or_inherit_owner_access(agent,monkeypatch):
    connection();connection(scope='ATLAS');calls=[]
    monkeypatch.setattr(DemoProvider,'search',lambda self,q,limit=4:calls.append(self.spec.scope_id) or [dict(native_id='demo-1',title='HARBOR')])
    ask('What is HARBOR?')
    assert calls==['HARBOR']
    calls.clear();_,result=ask('What is HARBOR?',user=viewer(OMAR))
    assert calls==[] and not result['live_dependencies']


def test_live_revision_change_and_local_disconnect_hide_saved_answer(agent,monkeypatch):
    id=connection();cid,result=ask('What is HARBOR?')
    assert not main.history(cid,viewer())['turns'][0]['suppressed']
    original=DemoProvider.record
    monkeypatch.setattr(DemoProvider,'record',lambda self:replace(original(self),revision='new-revision'))
    assert main.history(cid,viewer())['turns'][0]['suppressed']
    monkeypatch.setattr(DemoProvider,'record',original)
    with main.engine.connect() as conn:generation=connectors.owned(conn,viewer(),id).generation
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='disconnected',expected_generation=generation))
    assert main.history(cid,viewer())['turns'][0]['suppressed']


def test_company_information_works_without_graph_and_survives_other_source_outage(agent,monkeypatch):
    job=source(agent,b'AsterBridge is a fictional SaaS company. Its onboarding contact is Maya Chen.',enrichment_requested=False)
    assert processing.process_one()
    connection()
    def outage(*a,**k):raise SourceFailure('source_outage')
    monkeypatch.setattr(DemoProvider,'search',outage)
    _,result=ask('What is AsterBridge company?')
    assert result['statements'] and any('AsterBridge' in s['text'] for s in result['statements'])
    assert result['insufficient_evidence'] and result['source_outcomes'][0]['code']=='source_outage'
    assert not sql(agent,'SELECT 1 FROM entities WHERE version_id=:id',id=job.version_id).first()


def test_focused_documents_never_query_external_sources(agent,monkeypatch):
    job=source(agent,b'HARBOR stored scope is a partner integration.',enrichment_requested=False);assert processing.process_one()
    connection()
    monkeypatch.setattr(DemoProvider,'search',lambda *a,**k:pytest.fail('Explicit document scope must not widen.'))
    _,result=ask('What is HARBOR?',documents=[job.document_id])
    assert result['statements'] and not result.get('live_dependencies')


def test_past_only_main_chat_does_not_use_today_live_state(agent,monkeypatch):
    connection()
    monkeypatch.setattr(main,'search',lambda *a,**k:[])
    monkeypatch.setattr(DemoProvider,'search',lambda *a,**k:pytest.fail('Current live state cannot prove yesterday.'))
    _,result=ask('What was HARBOR status yesterday?')
    assert not result['live_dependencies'] and not result['statements']


def supported(statements):
    return AnswerSupportVerdict(reviews=[dict(statement=s['text'],supported=True,unsupported_fragments=[],temporal_scope_supported=True,authority_scope_supported=True,freshness_supported=True,reason='Synthetic original supports this point.') for s in statements])


def test_ambiguous_identity_still_clarifies_before_source_synthesis(agent,monkeypatch):
    from app import source_discovery
    jobs=[source(agent,text,enrichment_requested=False) for text in (b'Samir in engineering.',b'Samir in customer support.')]
    while processing.process_one():pass
    choices=[dict(document_id=str(j.document_id),version_id=str(j.version_id),filename='readiness.md',search_ready=True,match='entity_name') for j in jobs]
    monkeypatch.setattr(source_discovery,'identity_choices',lambda *a:choices)
    monkeypatch.setattr(source_answer_provider,'answer',lambda *a,**k:pytest.fail('Do not combine ambiguous identities.'))
    _,result=ask('Who is Samir?')
    assert result['clarification'] and len(result['source_matches'])==2 and not result['statements']


def test_server_resolves_typed_fields_and_one_bad_citation_does_not_erase_good_points(monkeypatch):
    monkeypatch.setattr(providers,'configured',lambda:True);calls=[]
    def structured(contract,system,payload,scope,operation,*a,**k):
        calls.append(operation)
        if operation=='answer':return PointerAnswer(statements=[
            dict(text='Native status is In Progress.',evidence=[dict(reference_id='issue',field='status',quote=None)]),
            dict(text='An ungrounded extra fact.',evidence=[dict(reference_id='missing',field=None,quote='invented')])],insufficient_evidence=False)
        assert len(payload['statements'])==1
        return supported(payload['statements'])
    monkeypatch.setattr(providers,'structured',structured)
    result,state=source_answer_provider.answer('Status?', [dict(reference_id='issue',kind='fields',text=None,fields=[dict(field='status',value='In Progress')])],{},lambda:None)
    assert len(result.statements)==1 and result.statements[0].evidence[0].value=='In Progress'
    assert result.insufficient_evidence and state=='partial' and calls==['answer','answer_verification']


def test_one_unsupported_semantic_statement_is_removed_without_losing_supported_answer(monkeypatch):
    monkeypatch.setattr(providers,'configured',lambda:True)
    def structured(contract,system,payload,scope,operation,*a,**k):
        if operation=='answer':return PointerAnswer(statements=[
            dict(text='The status is Blocked.',evidence=[dict(reference_id='issue',field='status',quote=None)]),
            dict(text='The company is cancelled.',evidence=[dict(reference_id='issue',field='status',quote=None)])],insufficient_evidence=False)
        verdict=supported(payload['statements']);verdict.reviews[1].supported=False;verdict.reviews[1].unsupported_fragments=['cancelled'];return verdict
    monkeypatch.setattr(providers,'structured',structured)
    result,state=source_answer_provider.answer('Status?', [dict(reference_id='issue',kind='fields',text=None,fields=[dict(field='status',value='Blocked')])],{},lambda:None)
    assert [s.text for s in result.statements]==['The status is Blocked.'] and state=='partial'


def test_search_scopes_are_built_by_server_and_search_hits_cannot_escape_project():
    spec=ConnectionSpec(kind='jira',name='Scoped Jira',site_url='https://example.atlassian.net',scope_id='HARBOR',transport='atlassian_mcp',cloud_id='cloud',mcp_credential_ref='RF4_TEST')
    calls=[]
    class Client:
        def call(self,tool,args):
            calls.append((tool,args));return {'data':{'issues':[{'key':'ATLAS-1','fields':{'summary':'Wrong project'}}]}}
    provider=Provider(spec);provider.mcp_client=lambda:Client()
    with pytest.raises(SourceFailure) as exc:provider.search('HARBOR OR project = ATLAS')
    assert exc.value.code=='outside_scope'
    assert calls[0][1]['jql'].startswith('project = "HARBOR" AND text ~ ')
    spec=ConnectionSpec(kind='confluence',name='Scoped Confluence',site_url='https://example.atlassian.net',scope_id='123',space_key='TEAM',transport='atlassian_mcp',cloud_id='cloud',mcp_credential_ref='RF4_TEST')
    class Pages:
        tools={'searchConfluence':{}}
        def call(self,tool,args):calls.append((tool,args));return {'data':{'results':[{'content':{'id':'7','title':'A page'}}]}}
    provider=Provider(spec);provider.mcp_client=lambda:Pages()
    assert provider.search('onboarding')[0]['native_id']=='7'
    page_calls=[args for _,args in calls if 'cql' in args]
    assert all(args['cql'].startswith('space = "TEAM" AND type = page AND ') for args in page_calls)
    assert any('text ~ ' in args['cql'] for args in page_calls)
