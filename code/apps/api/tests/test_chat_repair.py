"""Routing, coverage, diagnostic and amendment regressions without external calls."""
import time
from decimal import Decimal
from types import SimpleNamespace
import pytest
from app import auto_agent,providers,connectors,main,chat_trace,inference_budget
from app.chat_retrieval import rank_hits,select_passages,pack_passages
from app.parsers import Passage
from test_auto_chat import automatic,ask
from test_search_readiness import workspace,viewer
from test_inference_budget import budget_environment


def test_relevance_prefers_project_scope_over_incidental_department_mentions():
    hits=[dict(native_id='1',title='Engineering department responsibilities and collaboration'),
          dict(native_id='2',title='QUARTZ customer portal scope and ownership')]
    assert rank_hits('What is QUARTZ? Explain purpose, features and customer.',hits)[0]['native_id']=='2'


def test_directory_and_approved_policy_rankings_are_generic():
    assert rank_hits('List operating departments',[dict(native_id='1',title='Security department responsibilities'),
        dict(native_id='2',title='Company and teams')])[0]['native_id']=='2'
    assert rank_hits('approved retention policy',[dict(native_id='1',title='retention draft proposal'),
        dict(native_id='2',title='Approved analytics retention policy')])[0]['native_id']=='2'


def test_relevant_late_passage_survives_character_and_count_limits():
    passages=[Passage('Unrelated paragraph '+str(i),{'line':i}) for i in range(40)]
    passages.append(Passage('Approved signal retention is 17 days.',{'line':41}))
    selected,complete=select_passages(passages,'signal retention',max_passages=2,max_characters=100)
    assert not complete and selected[-1]==(40,passages[40])
    assert all(p.text==passages[i].text for i,p in selected)


def test_short_directory_lines_do_not_consume_the_entire_context_allowance():
    original=[Passage('Department member '+str(i),{'line':i}) for i in range(60)]
    packed=pack_passages(original)
    selected,complete=select_passages(packed,'all departments')
    assert complete and 'Department member 59' in selected[-1][1].text
    assert [part for p in packed for part in p.locator['parts']]==[p.locator for p in original]


def test_first_output_is_once_per_request_and_each_operation_is_timed():
    with chat_trace.session() as trace:
        chat_trace.first_output(time.monotonic(),'planning')
        first=trace.counters['model_first_output_ms']
        time.sleep(.002)
        chat_trace.first_output(time.monotonic(),'answer')
        assert trace.counters['model_first_output_ms']==first<=trace.summary()['total_ms']
        assert len(trace.events)==2


def test_positive_review_prose_cannot_override_rejecting_flags():
    from app.contracts import AnswerSupportVerdict
    review=AnswerSupportVerdict(reviews=[dict(statement='The source-supported fact.',reason='The cited sources fully support this statement.',
        unsupported_fragments=[],temporal_scope_supported=True,authority_scope_supported=True,freshness_supported=True,supported=False)])
    assert not review.accepts([SimpleNamespace(text='The source-supported fact.')])


def test_read_retry_is_bounded_and_never_retries_access_denial(monkeypatch):
    from app.connector_transport import ReadClient,ReadLimits,SourceFailure
    client=ReadClient('RF4_TEST','example.test',ReadLimits());calls=[]
    def transient(*a,**kw):
        calls.append(True)
        if len(calls)==1:raise SourceFailure('source_timeout')
        return {'ok':True}
    monkeypatch.setattr(client,'_request',transient)
    with chat_trace.session() as trace:
        assert client.request('GET','https://example.test')=={'ok':True}
        assert len(calls)==2 and trace.counters['source_calls']==2
        assert trace.events[-1]['retries']==1
    calls.clear()
    def denied(*a,**kw):calls.append(True);raise SourceFailure('access_denied')
    monkeypatch.setattr(client,'_request',denied)
    with pytest.raises(SourceFailure,match='access_denied'):client.request('GET','https://example.test')
    assert len(calls)==1


def test_explicit_issue_key_reads_actual_issue_without_search(automatic,monkeypatch):
    from test_main_chat_agent import connection
    cid=connection('jira','QUARTZ');reads=[]
    def live(user,id,body):
        reads.append(body.native_id)
        return dict(evidence=dict(reference_id='actual-issue',display_title='Actual delivery task',original_url='https://fixture.test/QUARTZ-7',
            source_revision='1',source_updated_at='2026-11-17T00:00:00Z',observed_at='2026-11-17T00:00:00Z',
            synthetic=True,fields=[dict(field='key',value='QUARTZ-7'),dict(field='status',value='Open')]),passages=[])
    monkeypatch.setattr(connectors,'live',live)
    monkeypatch.setattr(connectors,'Provider',lambda *a,**k:SimpleNamespace(authorize=lambda *a:SimpleNamespace(revision='1'),
        search=lambda *a,**k:pytest.fail('Exact keys do not require discovery.')))
    _,result=ask('Read QUARTZ-7 and explain its acceptance criteria')
    assert reads==['QUARTZ-7'] and result['evidence'][0]['filename']=='QUARTZ-7 — Actual delivery task'
    assert result['live_dependencies'][0]['connection_id']==str(cid)


def test_compound_question_keeps_literal_status_when_synthesis_cannot_verify_other_parts(automatic,monkeypatch):
    from test_main_chat_agent import connection
    connection('jira','QUARTZ')
    def live(user,id,body):
        return dict(evidence=dict(reference_id='issue',display_title='Original issue',original_url='https://fixture.test/QUARTZ-7',
            source_revision='1',source_updated_at='2026-11-17T00:00:00Z',observed_at='2026-11-17T00:00:00Z',synthetic=True,
            fields=[dict(field='key',value='QUARTZ-7'),dict(field='status',value='Waiting for review')]),passages=[])
    monkeypatch.setattr(connectors,'live',live)
    monkeypatch.setattr(connectors,'Provider',lambda *a,**k:SimpleNamespace(authorize=lambda *a:SimpleNamespace(revision='1')))
    def unavailable(*a,**kw):raise providers.ModelResponseError('verification_unavailable')
    monkeypatch.setattr(auto_agent.source_answer_provider,'linked_answer',unavailable)
    _,result=ask('Read QUARTZ-7: what is its status, owner and acceptance criteria?')
    assert 'Waiting for review' in result['statements'][0]['text']
    assert result['statements'][0]['evidence'][0]['quote']=='status: "Waiting for review"'
    assert result['insufficient_evidence'] and result['provider']=='structured'


def test_explicit_issue_key_does_not_widen_file_only_scope(automatic,monkeypatch):
    from test_main_chat_agent import connection
    connection('jira','QUARTZ')
    monkeypatch.setattr(connectors,'live',lambda *a,**k:pytest.fail('File-only scope must not read Jira.'))
    _,result=ask('Use only uploaded files to explain QUARTZ-7')
    assert not result['live_dependencies']






def test_resolved_question_reports_exact_native_status_without_model(automatic,monkeypatch):
    from test_main_chat_agent import connection
    from test_chat_polish import record
    from dataclasses import replace
    connection('jira','QUARTZ')
    original=record('QUARTZ');fields=[dict(f,value='Done') if f['field']=='status' else f for f in original.fields]
    monkeypatch.setattr(connectors,'Provider',lambda *a,**k:SimpleNamespace(get=lambda *a,**k:replace(original,fields=fields,content=b'Synthetic original issue body.'),authorize=lambda *a:original))
    monkeypatch.setattr(providers,'structured',lambda *a,**k:pytest.fail('A native status needs no model.'))
    _,result=ask('Is QUARTZ-1 resolved?')
    assert result['provider']=='structured' and 'Done' in result['statements'][0]['text']








def test_retained_diagnostics_do_not_expose_revoked_discovery_metadata():
    from app.chat_agent import retained_response
    response=dict(evidence=[],diagnostics=dict(events=[dict(kind='discovery',connection_id='private-id',candidates=[dict(title='Private title')]),
        dict(kind='resource_read',title='Private title',native_id='private-native',ms=42)]))
    result=retained_response(response)
    assert 'Private title' not in str(result) and 'private-native' not in str(result)
    assert response['diagnostics']['events'][1]['title']=='Private title'


def test_amendment_preserves_unknown_reservations_and_pause(budget_environment,tmp_path):
    call=inference_budget.reserve('test/model','answer',{},100)
    inference_budget.settle(call,{},'TimeoutError')
    before=inference_budget.status()
    receipt=inference_budget.amend_limit('.1','17','User approved additional seven dollars',tmp_path/'approval.json')
    after=inference_budget.status()
    assert after['limit_usd']==Decimal('17') and after['paused']
    assert after['reserved_usd']==before['reserved_usd'] and after['spent_usd']==before['spent_usd']
    assert receipt['paused'] and (tmp_path/'approval.json').exists()
    with pytest.raises(inference_budget.BudgetStopped):
        inference_budget.amend_limit('.1','18','stale approval',tmp_path/'stale.json')


def test_budget_above_ten_requires_matching_persisted_amendment(budget_environment,monkeypatch,tmp_path):
    first=inference_budget.reserve('test/model','answer',{},100)
    inference_budget.settle(first,dict(usage=dict(inputTokens=1,outputTokens=1)),None)
    monkeypatch.setenv('BEDROCK_BUDGET_USD','17')
    with pytest.raises(inference_budget.BudgetStopped):inference_budget.reserve('test/model','answer',{},100)
    inference_budget.amend_limit('.1','17','Explicit approved increase',tmp_path/'approval.json')
    call=inference_budget.reserve('test/model','answer',{},100)
    assert call['run']==budget_environment
    inference_budget.settle(call,dict(usage=dict(inputTokens=1,outputTokens=1)),None)


def test_durable_trial_counts_spending_and_pending_holds_not_released_reservations(budget_environment):
    from app.db import sql
    with inference_budget.ledger_engine().connect() as conn:start=sql(conn,'SELECT clock_timestamp()').scalar_one()
    with inference_budget.bounded_trial('.04',3,ledger_since=str(start)):
        for _ in range(3):
            call=inference_budget.reserve('test/model','answer',{},100)
            inference_budget.settle(call,dict(usage=dict(inputTokens=1,outputTokens=1)),None)
    # Restarting the harness cannot obtain another attempt allowance.
    with inference_budget.bounded_trial('.04',3,ledger_since=str(start)):
        with pytest.raises(inference_budget.BudgetStopped):inference_budget.reserve('test/model','answer',{},100)


def test_explicit_resume_retains_unknown_call_and_requires_exact_expected_hold(budget_environment,tmp_path):
    call=inference_budget.reserve('test/model','answer',{},100)
    inference_budget.settle(call,{},'ExpiredTokenException');before=inference_budget.status()
    with pytest.raises(inference_budget.BudgetStopped):
        inference_budget.resume_with_holds('0','User approved resume',tmp_path/'wrong.json')
    inference_budget.resume_with_holds(before['reserved_usd'],'User approved resume with all unknowns retained',tmp_path/'resume.json')
    after=inference_budget.status()
    assert not after['paused'] and after['reserved_usd']==before['reserved_usd'] and after['spent_usd']==before['spent_usd']
    from app.db import sql
    with inference_budget.ledger_engine().connect() as conn:
        assert sql(conn,'SELECT status FROM inference_budget_calls WHERE id=:id',id=call['id']).scalar_one()=='unknown'
