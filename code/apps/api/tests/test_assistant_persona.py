import pytest
from app import providers
from app.assistant_persona import CONVERSATION_SYSTEM,local_reply
from app.conversation_routing import ConversationVerdict,QueryPlan,plan
from app.question_intent import intent
from test_search_readiness import workspace,viewer
from test_conversational import chat,ask


@pytest.mark.parametrize('question',['who are you?','can you help me?','what is u can do form me ?','مين انت؟','وش تقدر تسوي'])
def test_persona_identity_and_help_are_brief_without_source_claims(workspace,monkeypatch,question):
    monkeypatch.setattr(providers,'structured',lambda *a,**k:pytest.fail('Simple greetings/help need no model call'))
    result=ask(chat(),question)
    assert result['provider']=='system' and result['evidence']==[] and not result['insufficient_evidence']
    assert len(result['message'])<250
    assert 'Supported files' not in result['message'] and 'Admin Console' not in result['message']


def test_greeting_does_not_repeat_introduction_on_followup(workspace):
    id=chat()
    first=ask(id,'hi')
    second=ask(id,'hi')
    assert 'Link9' in first['message'] and '👋' in first['message']
    assert 'Link9' not in second['message']
    thanks=ask(id,'thanks')
    assert thanks['message']=="You're welcome 🙂"
    assert thanks['evidence']==[]


@pytest.mark.parametrize('question',['hi, who owns NS-ATLAS?','thanks, when is the deadline?','who are you working with on Project Alpha?'])
def test_mixed_greeting_and_organization_questions_do_not_use_local_social_route(question):
    assert intent(question) not in {'greeting','help','social'}


def test_nontrivial_social_reply_is_personalized_and_checked(monkeypatch):
    monkeypatch.setenv('BEDROCK_ANSWER_MODEL','test/no-network')
    monkeypatch.setattr(providers,'configured',lambda:True)
    calls=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        calls.append(operation)
        kwargs['authorize']()
        if operation=='query_understanding':
            assert 'You are Link9' in system and 'TRUTH AND ACTION BOUNDARIES' in system
            return QueryPlan(route='social',query='',use_previous=False,reply="I'm Link9 🙂 Tell me what you're working on.")
        assert operation=='conversation_verification'
        assert 'passages' not in payload and payload['reply'].startswith("I'm Link9")
        return ConversationVerdict(allowed=True,requires_sources=False)
    monkeypatch.setattr(providers,'structured',structured)
    result=plan('Introduce yourself like a colleague would.',[],{},lambda:None)
    assert result['reply'].startswith("I'm Link9")
    assert calls==['query_understanding','conversation_verification']


@pytest.mark.parametrize('requires_sources',[False,True])
def test_social_verifier_blocks_unsupported_capabilities_or_company_facts(monkeypatch,requires_sources):
    monkeypatch.setenv('BEDROCK_ANSWER_MODEL','test/no-network')
    monkeypatch.setattr(providers,'configured',lambda:True)
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        if operation=='query_understanding':
            return QueryPlan(route='help',query='',use_previous=False,reply='Invented company fact or unavailable email action.')
        return ConversationVerdict(allowed=False,requires_sources=requires_sources)
    monkeypatch.setattr(providers,'structured',structured)
    result=plan('Explain how you can help with my work.',[],{},lambda:None)
    assert 'Invented' not in result['reply']
    assert result['route']==('answer' if requires_sources else 'help')


def test_user_language_and_upload_help_are_respected():
    assert local_reply('مين انت','help').startswith('أنا Link9')
    assert 'Add documents' in local_reply('how do I upload a file?','help')
    assert len(local_reply('what can you do?','help'))<200


def test_personality_does_not_replace_answer_grounding_prompt(monkeypatch):
    from app.contracts import GroundedAnswer,AnswerVerdict
    monkeypatch.setattr(providers,'configured',lambda:True)
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        if operation=='answer':
            assert CONVERSATION_SYSTEM in system
            assert 'MANDATORY GROUNDING' in system and 'Every factual statement needs exact supporting quotations.' in system
            return GroundedAnswer(statements=[dict(text='Amal owns Project Alpha.',evidence=[dict(passage_id='source',quote='Amal owns Project Alpha.')])],insufficient_evidence=False)
        return AnswerVerdict(supported=[False])
    monkeypatch.setattr(providers,'structured',structured)
    result=providers.answer('Who owns Project Alpha?',[dict(id='source',text='Amal owns Project Alpha.')],{})
    assert result.insufficient_evidence and not result.statements
