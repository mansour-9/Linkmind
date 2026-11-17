"""Company presentation, conversation intent and compound source investigation."""
import json
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app import main,auto_agent,providers,source_answer_provider,structured_chat
from app.assistant_persona import local_reply,PRODUCT_FACTS
from app.question_intent import intent
from test_auto_chat import automatic,ask
from test_search_readiness import workspace,viewer


@pytest.mark.parametrize('question',['مين انت؟','من أنت؟','who are you?','كيفك','كيفيك','هلا'])
def test_identity_and_small_talk_do_not_search_company_sources(automatic,monkeypatch,question):
    monkeypatch.setattr(providers,'structured',lambda *a,**k:pytest.fail('Pure identity/social messages do not need inference.'))
    _,result=ask(question)
    assert result['provider']=='system' and result['message'] and not result['evidence']


def test_mixed_greeting_and_company_request_is_still_factual():
    assert intent('ارحب كيفيك ابيك تقولي عن عدد مشاريع الموجوده و من الاونير لهم')=='search'
    assert intent('hi who owns these projects?')=='search'


def test_upload_help_points_to_documents_popup():
    reply=local_reply('كيف أرفع ملف؟','help')
    assert 'Documents' in reply and 'Add document' in reply
    assert 'Attach files' not in PRODUCT_FACTS and 'organization by default' in PRODUCT_FACTS


def test_project_enumeration_does_not_end_compound_question(automatic,monkeypatch):
    from test_main_chat_agent import connection
    cid=connection('jira','ATLAS')
    monkeypatch.setattr(main,'configured',lambda:True)
    from app import connectors
    with main.engine.connect() as conn:row=connectors.owned(conn,viewer(),cid)
    dependency=dict(connection_id=str(cid),native_id='demo-1',generation=row.generation,revision='1')
    evidence=dict(id='enum-ref',filename='ATLAS gate',text='',version_id='',document_id='live:atlas',locator={},live=dependency,original_url='https://fixture.test/ATLAS-1',source_application='Jira',observed_at='2026-11-17T00:00:00Z')
    direct=dict(statements=[dict(text='ATLAS',evidence=[dict(passage_id='enum-ref',quote='project: '+json.dumps(dict(key='ATLAS',name='Customer Portal')))])],evidence=[evidence],insufficient_evidence=False,
        project_coverage=dict(verified_count=1,configured_scopes=1,complete=True,scope='enabled_connections'),retrieval_activity=[])
    monkeypatch.setattr(structured_chat,'answer',lambda *a,**k:(direct,[]))
    monkeypatch.setattr(auto_agent,'assert_live',lambda *a,**k:None)
    calls=[]
    def synthesize(question,sources,scope,authorize,context=None):
        calls.append(dict(question=question,sources=sources,context=context))
        return dict(statements=[],provider='bedrock',insufficient_evidence=True,followup_query='',validation_summary={})
    monkeypatch.setattr(source_answer_provider,'linked_answer',synthesize)
    _,result=ask('كم مشروع ومين مالك كل مشروع؟')
    assert len(calls)==1 and calls[0]['question']=='كم مشروع ومين مالك كل مشروع؟'
    assert calls[0]['sources'][0]['fields'][0]['value']['key']=='ATLAS'
    assert calls[0]['context']['project_coverage']['verified_count']==1
    assert result['project_coverage']['verified_count']==1


def test_source_failures_keep_distinct_limit_code():
    from app.connector_transport import SourceFailure
    assert auto_agent.failure_code(SourceFailure('source_limit'))=='source_limit'
