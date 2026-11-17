from types import SimpleNamespace
from uuid import uuid4
from datetime import datetime, timezone

import pytest

from app import providers, model_limits
from app.contracts import AnswerVerdict
from app.query_limits import QueryLimits, QueryLimitReached, question_limits, active
from app.retrieval_coordinator import SourceAdapter, choose_adapters, retrieve_adapters
from app.source_evidence import ResourceIdentity, SourceEvidence, FieldEvidence, EvidenceCoverage


def test_request_budget_is_scoped_and_independent_for_each_question():
    assert active() is None
    with question_limits(QueryLimits(max_retrievals=1)) as first:
        first.retrieve()
        with pytest.raises(QueryLimitReached, match='retrieval_limit'):
            first.retrieve()
        with question_limits() as second:
            assert second is not first and second.retrievals == 0
        assert active() is first
    assert active() is None


def test_context_limits_keep_whole_passages_and_source_diversity():
    passages = [dict(id=str(i), document_id='a', text='x' * 10) for i in range(5)] + [dict(id='b', document_id='b', text='y' * 10)]
    limits = QueryLimits(max_passages=3, max_context_characters=30)
    result = limits.context(passages)
    assert len(result) == 3 and {p['document_id'] for p in result} == {'a', 'b'}
    assert all(len(p['text']) == 10 for p in result)


@pytest.mark.parametrize('kind', ['time', 'calls', 'payload', 'planner'])
def test_budget_denial_precedes_any_pacing_reservation_or_sdk(monkeypatch, kind):
    monkeypatch.setenv('AI_PROVIDER', 'bedrock')
    monkeypatch.setenv('BEDROCK_EXTRACTION_MODEL', 'test/no-network')
    monkeypatch.setattr(model_limits, 'pace', lambda *a: pytest.fail('No pacing after rejection'))
    monkeypatch.setattr(providers, 'reserve', lambda *a: pytest.fail('No dollar reservation after rejection'))
    monkeypatch.setattr(providers, 'runtime', lambda: pytest.fail('No SDK after rejection'))
    limits = QueryLimits(seconds=-1 if kind == 'time' else 90, max_model_calls=0 if kind == 'calls' else 7,
        max_request_bytes=1 if kind == 'payload' else 180000, max_planner_calls=0 if kind == 'planner' else 1)
    with question_limits(limits), pytest.raises(QueryLimitReached):
        providers.structured(AnswerVerdict, 'System', {}, {}, 'query_understanding' if kind == 'planner' else 'test')


def test_query_sdk_timeouts_and_retries_are_bounded_without_changing_background_defaults(monkeypatch):
    configs = []
    monkeypatch.setattr(providers.boto3, 'Session', lambda: SimpleNamespace(client=lambda service, **kw: configs.append(kw['config']) or object()))
    monkeypatch.delenv('BEDROCK_BUDGET_RUN', raising=False)
    providers.runtime.cache_clear()
    try:
        with question_limits(QueryLimits(seconds=20)):
            first = providers.runtime()
            assert providers.runtime() is first
        providers.runtime()
        assert configs[0].read_timeout <= 15 and configs[0].retries['total_max_attempts'] == 1
        assert configs[1].read_timeout == 180
    finally:
        providers.runtime.cache_clear()


def test_adapter_routing_does_not_fan_out_and_expands_only_after_empty_result():
    org, live_id, stored_id, irrelevant_id = uuid4(), str(uuid4()), str(uuid4()), str(uuid4())
    calls = []
    def adapter(id, mode, keys, empty=False):
        def fetch(question):
            calls.append(id)
            if empty:
                return []
            identity = ResourceIdentity(organization_id=org, source_instance_id=id, resource_type='issue', native_id='HB-42')
            return [SourceEvidence(reference_id='observation', identity=identity, origin='live' if mode=='live' else 'stored', source_revision='fixture-revision' if mode!='live' else None, observed_at=datetime.now(timezone.utc),
                fields=[FieldEvidence(field='status', value='In progress')], access_dependencies=[identity],
                coverage=EvidenceCoverage(complete=False, description='Offline current-status fixture.'))]
        return SourceAdapter(id, mode, keys, fetch)
    adapters = [adapter(live_id, 'live', ('HB-42',), True), adapter(irrelevant_id, 'live', ('OtherProject',)), adapter(stored_id, 'stored', ())]
    assert [a.id for a in choose_adapters('Latest HB-42 status', adapters)] == [live_id, stored_id]
    authorize_calls = []
    result = retrieve_adapters('Latest HB-42 status', adapters, authorize_calls.append, org)
    assert len(result) == 1 and calls == [live_id, stored_id]
    assert authorize_calls == [live_id, live_id, stored_id, stored_id]
    calls.clear()
    assert not retrieve_adapters('Latest HB-42 status', adapters, lambda id: None, org, selected=[live_id])
    assert calls == [live_id]


def test_adapter_denial_is_not_empty_search_and_cannot_fall_back():
    org = uuid4()
    live = SourceAdapter(str(uuid4()), 'live', ('HB-42',), lambda q: pytest.fail('Denied source must not execute'))
    fallback = SourceAdapter(str(uuid4()), 'stored', (), lambda q: pytest.fail('No cached fallback after denied access'))
    def deny(id):
        raise PermissionError('Source denied')
    with pytest.raises(PermissionError):
        retrieve_adapters('Latest HB-42 status', [live, fallback], deny, org)


def test_adapter_cannot_return_evidence_from_another_tenant_or_source():
    org, source = uuid4(), uuid4()
    identity = ResourceIdentity(organization_id=uuid4(), source_instance_id=source, resource_type='issue', native_id='HB-42')
    evidence = SourceEvidence(reference_id='foreign', identity=identity, origin='live', observed_at=datetime.now(timezone.utc),
        fields=[FieldEvidence(field='status', value='Open')], access_dependencies=[identity],
        coverage=EvidenceCoverage(complete=False, description='Invalid-tenant fixture.'))
    adapter = SourceAdapter(str(source), 'live', ('HB-42',), lambda q: [evidence])
    with pytest.raises(ValueError, match='authorized source identity'):
        retrieve_adapters('Latest HB-42 status', [adapter], lambda id: None, org)
