import pytest
from app import providers
from app.contracts import AnswerSupportVerdict, GroundedAnswer


@pytest.mark.parametrize('change', [
    {'statement': 'Only the supported prefix.'},
    {'unsupported_fragments': ['(before the requested day)']},
    {'temporal_scope_supported': False},
    {'authority_scope_supported': False},
    {'freshness_supported': False},
    {'supported': False},
])
def test_whole_statement_audit_fails_closed_even_when_other_checks_pass(monkeypatch, change):
    text='Submit before Thursday (before the requested day).'
    source='Submit before Thursday.'
    monkeypatch.setattr(providers, 'configured', lambda: True)
    monkeypatch.setattr(providers, 'record', lambda *a, **k: None)
    def structured(contract, system, payload, scope, operation, *a, **k):
        if operation == 'answer':
            return GroundedAnswer(statements=[dict(text=text, evidence=[dict(passage_id='p', quote=source)])], insufficient_evidence=False)
        assert contract is AnswerSupportVerdict
        assert payload['evidence_mode'] == 'saved_or_mixed'
        return contract(reviews=[dict(statement=text, supported=True, unsupported_fragments=[],
            temporal_scope_supported=True, authority_scope_supported=True, freshness_supported=True,
            reason='Synthetic audit.', **{}) | change])
    monkeypatch.setattr(providers, 'structured', structured)
    result=providers.answer('When?', [dict(id='p', text=source)], {})
    assert not result.statements and result._failure_reason == 'verification_failed'


def test_live_observation_is_explicit_and_cannot_be_inferred_from_a_source_url():
    assert providers.evidence_mode([dict(original_url='https://source.example')]) == 'saved_or_mixed'
    assert providers.evidence_mode([dict(observation_kind='live')]) == 'live'
    assert providers.evidence_mode([dict(observation_kind='live'), {}]) == 'saved_or_mixed'


def test_missing_or_duplicate_review_cannot_certify_an_answer():
    statement=GroundedAnswer(statements=[dict(text='Recorded date: Friday.', evidence=[])], insufficient_evidence=False).statements
    assert not AnswerSupportVerdict(reviews=[]).accepts(statement)


@pytest.mark.parametrize('question,expected',[
    ('Who currently owns the project?',True),('What is the current owner?',True),
    ('ما أحدث موعد؟',True),('مين المسؤول حاليًا؟',True),('وش آخر تحديث؟',True),
    ('Who leads the project?',False),('Translate the policy deadline.',False),
])
def test_freshness_requirement_distinguishes_operational_requests(question,expected):
    from app.query_language import operational_question
    assert operational_question(question) is expected
