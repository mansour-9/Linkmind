"""Demo chat keeps basic grounding/permissions without model verification loops."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app import auto_agent,providers,main,chat_agent,source_answer_provider,connectors
from app.source_answer_contracts import LinkedAnswer
from app.db import sql
from test_auto_chat import automatic,ask
from test_search_readiness import workspace,viewer
from test_main_chat_agent import connection


def test_one_answer_call_and_followup_use_fresh_sources_not_previous_answer_bodies(automatic,monkeypatch):
    from app.connector_demo import DemoProvider
    connection('jira','QUARTZ');connection('confluence','DOCS')
    queries=[];calls=[];original=DemoProvider.search
    monkeypatch.setattr(DemoProvider,'search',lambda self,q,limit=4:queries.append(q) or original(self,q,limit))
    monkeypatch.setattr(providers,'configured',lambda:True);monkeypatch.setattr(main,'configured',lambda:True)
    monkeypatch.setattr(chat_agent,'allowed',lambda *a,**kw:pytest.fail('Previous answer bodies are not used for topic resolution.'))
    def generate(contract,system,payload,scope,operation,*a,**kw):
        assert contract is LinkedAnswer and operation=='answer'
        calls.append(payload)
        assert 'recent_context' not in payload and payload['sources']
        return LinkedAnswer(statements=[dict(text='Supported source context is available.',source_ids=[payload['sources'][0]['reference_id']])],
            insufficient_evidence=False,followup_query='')
    monkeypatch.setattr(providers,'structured',generate)
    cid,_=ask('What is QUARTZ?')
    _,result=ask('Who owns it?',cid=cid)
    assert len(calls)==2 and all('QUARTZ' in q for q in queries)
    assert result['topic']['project_keys']==['QUARTZ']
    assert result['validation_summary']['independent_verification'] is False


def test_unknown_links_and_fabricated_native_completion_are_removed(monkeypatch):
    monkeypatch.setattr(providers,'configured',lambda:True);calls=[]
    def generate(*a,**kw):
        calls.append(True)
        return LinkedAnswer(statements=[
            dict(text='QUARTZ-7 is Done in Jira.',source_ids=['issue']),
            dict(text='A fabricated source fact.',source_ids=['invented']),
            dict(text='QUARTZ-7 is In Progress in Jira.',source_ids=['issue'])],
            insufficient_evidence=False,followup_query='')
    monkeypatch.setattr(providers,'structured',generate)
    result=source_answer_provider.linked_answer('What is QUARTZ-7 status?',
        [dict(reference_id='issue',text='',fields=[dict(field='key',value='QUARTZ-7'),dict(field='status',value='In Progress')])],{},lambda:None)
    assert len(calls)==1 and [p['text'] for p in result['statements']]==['QUARTZ-7 is In Progress in Jira.']
    assert result['validation_summary']['status_claims_rejected']==1
    assert result['validation_summary']['unknown_source_ids']==1


def test_plain_status_label_uses_native_value_without_overwriting_business_state(monkeypatch):
    monkeypatch.setattr(providers,'configured',lambda:True)
    monkeypatch.setattr(providers,'structured',lambda *a,**kw:LinkedAnswer(statements=[
        dict(text='QUARTZ-7 (status: Blocked, owner: Leena) is blocked by an upstream dependency.',source_ids=['issue'])],
        insufficient_evidence=False,followup_query=''))
    result=source_answer_provider.linked_answer('Which issues block release?',
        [dict(reference_id='issue',text='Business state: Blocked.',fields=[dict(field='key',value='QUARTZ-7'),dict(field='status',value='In Progress')])],{},lambda:None)
    assert 'status: In Progress' in result['statements'][0]['text']
    assert 'blocked by an upstream dependency' in result['statements'][0]['text']


def test_connection_change_during_generation_still_blocks_delivery(automatic,monkeypatch):
    cid=connection('confluence','DOCS')
    def generate(question,sources,*a,**kw):
        with main.engine.begin() as conn:sql(conn,'UPDATE source_connections SET generation=generation+1 WHERE id=:id',id=cid)
        return dict(statements=[dict(text='A source fact.',evidence=[dict(passage_id=sources[0]['reference_id'],quote='')])],
            insufficient_evidence=False,followup_query='',provider='bedrock')
    monkeypatch.setattr(source_answer_provider,'linked_answer',generate)
    with pytest.raises(HTTPException) as error:ask('Explain the project overview')
    assert error.value.status_code==409
