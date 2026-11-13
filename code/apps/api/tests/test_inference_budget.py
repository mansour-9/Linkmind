import json
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest

from app import inference_budget,providers
from app.db import engine,sql


@pytest.fixture
def budget_environment(monkeypatch):
    run='test-budget-'+uuid4().hex
    monkeypatch.setenv('BEDROCK_BUDGET_RUN',run)
    monkeypatch.setenv('BEDROCK_BUDGET_USD','0.1')
    monkeypatch.setenv('BEDROCK_RATES_JSON',json.dumps({'us-east-1':{'test/model':{'input':3.3,'output':16.5,'currency':'USD','effective_date':'2026-11-12'}}}))
    monkeypatch.setenv('AWS_REGION','us-east-1')
    yield run
    with engine.begin() as conn:
        sql(conn,'DELETE FROM inference_budget_calls WHERE run_id=:id',id=run)
        sql(conn,'DELETE FROM inference_budget_runs WHERE id=:id',id=run)


def test_reservation_settlement_and_fixed_limit(budget_environment,monkeypatch):
    first=inference_budget.reserve('test/model','answer',{'source':'test'},3000)
    with pytest.raises(inference_budget.BudgetStopped):
        inference_budget.reserve('test/model','answer',{},3000)
    inference_budget.settle(first,{'usage':{'inputTokens':100,'outputTokens':20}},None)
    assert inference_budget.status()['spent_usd']==Decimal('0.00066')
    assert inference_budget.status()['reserved_usd']==0
    monkeypatch.setenv('BEDROCK_BUDGET_USD','0.2')
    with pytest.raises(inference_budget.BudgetStopped):
        inference_budget.reserve('test/model','answer',{},10)


def test_unknown_usage_pauses_all_new_calls_and_keeps_reservation(budget_environment):
    call=inference_budget.reserve('test/model','answer',{},100)
    inference_budget.settle(call,{},'TimeoutError')
    status=inference_budget.status()
    assert status['paused'] and status['reserved_usd']>0 and status['spent_usd']==0
    with pytest.raises(inference_budget.BudgetStopped):
        inference_budget.reserve('test/model','embedding',{},0)


def test_concurrent_processes_cannot_each_spend_the_whole_budget(budget_environment):
    def reserve():
        try:
            return inference_budget.reserve('test/model','answer',{},3000)
        except inference_budget.BudgetStopped:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:reserve(),range(2)))
    assert sum(call is not None for call in results)==1
    assert inference_budget.status()['reserved_usd']<=Decimal('0.1')


def test_missing_rates_stop_before_sdk_and_unbudgeted_runs_are_unchanged(budget_environment,monkeypatch):
    monkeypatch.setenv('BEDROCK_RATES_JSON','{}')
    with pytest.raises(inference_budget.BudgetStopped):
        inference_budget.reserve('test/model','answer',{},100)
    monkeypatch.delenv('BEDROCK_BUDGET_RUN')
    assert inference_budget.reserve('test/model','answer',{},100) is None


def test_budgeted_sdk_disables_automatic_retries(budget_environment,monkeypatch):
    monkeypatch.setenv('AWS_ACCESS_KEY_ID','testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY','testing')
    providers.runtime.cache_clear()
    try:
        client=providers.runtime()
        assert client.meta.config.retries['total_max_attempts']==1
    finally:
        providers.runtime.cache_clear()


def test_exhausted_budget_prevents_dispatch(budget_environment,monkeypatch):
    from app.contracts import AnswerVerdict
    from app import model_limits
    monkeypatch.setenv('BEDROCK_BUDGET_USD','0.001')
    monkeypatch.setenv('AI_PROVIDER','bedrock')
    monkeypatch.setenv('BEDROCK_EXTRACTION_MODEL','test/model')
    monkeypatch.setattr(model_limits,'pace',lambda *args:None)
    monkeypatch.setattr(providers,'runtime',lambda:pytest.fail('Budget denial must precede SDK dispatch'))
    with pytest.raises(inference_budget.BudgetStopped):
        providers.structured(AnswerVerdict,'test',{}, {},'test')


def test_excess_or_unknown_sdk_usage_pauses_budget(budget_environment):
    call=inference_budget.reserve('test/model','answer',{},100)
    inference_budget.settle(call,{'usage':{'inputTokens':10,'outputTokens':101}},None)
    assert inference_budget.status()['paused']
