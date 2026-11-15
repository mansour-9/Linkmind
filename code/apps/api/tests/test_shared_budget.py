"""A preview must use the original spend/pacing store, never a copied allowance."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from app import inference_budget,model_limits,providers
from app.contracts import AnswerVerdict
from app.db import engine,sql
from test_inference_budget import budget_environment


@pytest.fixture
def shared_ledger(budget_environment,monkeypatch):
    # Independent connections/search_path exercise a real separate ledger namespace.
    schema="shared_budget_"+uuid4().hex
    with engine.begin() as conn:
        sql(conn,f'CREATE SCHEMA "{schema}"')
        for table in ("inference_budget_runs","inference_budget_calls","model_request_slots"):
            sql(conn,f'CREATE TABLE "{schema}".{table} (LIKE public.{table} INCLUDING ALL)')
    url=engine.url.update_query_dict({"options":"-csearch_path="+schema})
    remote=create_engine(url,pool_pre_ping=True)
    monkeypatch.setenv("BEDROCK_BUDGET_DATABASE_URL",url.render_as_string(hide_password=False))
    with remote.begin() as conn:
        sql(conn,"INSERT INTO inference_budget_runs(id,limit_usd,spent_usd,reserved_usd) VALUES(:run,0.1,0.01,0.001)",run=budget_environment)
    try:
        yield remote
    finally:
        inference_budget._shared_engine(url.render_as_string(hide_password=False)).dispose()
        inference_budget._shared_engine.cache_clear()
        remote.dispose()
        with engine.begin() as conn:
            sql(conn,f'DROP SCHEMA "{schema}" CASCADE')


def test_existing_shared_spend_is_not_reset_or_copied(shared_ledger,budget_environment):
    before=inference_budget.status()
    assert before["spent_usd"]==Decimal("0.01") and before["reserved_usd"]==Decimal("0.001")
    reservation=inference_budget.reserve("test/model","answer",{},100)
    inference_budget.settle(reservation,{"usage":{"inputTokens":100,"outputTokens":20}},None)
    assert inference_budget.status()["spent_usd"]==Decimal("0.01066")
    assert inference_budget.status()["reserved_usd"]==Decimal("0.001")
    with engine.connect() as conn:
        assert sql(conn,"SELECT count(*) FROM inference_budget_runs WHERE id=:id",id=budget_environment).scalar()==0


def test_missing_shared_run_cannot_initialize_a_replacement(shared_ledger,budget_environment):
    with shared_ledger.begin() as conn:
        sql(conn,"DELETE FROM inference_budget_runs WHERE id=:id",id=budget_environment)
    with pytest.raises(inference_budget.BudgetStopped,match="No replacement budget"):
        inference_budget.reserve("test/model","answer",{},100)
    with pytest.raises(inference_budget.BudgetStopped,match="No replacement budget"):
        inference_budget.status()
    for db in (shared_ledger,engine):
        with db.connect() as conn:
            assert sql(conn,"SELECT count(*) FROM inference_budget_runs WHERE id=:id",id=budget_environment).scalar()==0


def test_shared_limit_pause_and_unknown_reservations_remain_binding(shared_ledger,monkeypatch):
    monkeypatch.setenv("BEDROCK_BUDGET_USD","0.2")
    with pytest.raises(inference_budget.BudgetStopped):
        inference_budget.reserve("test/model","answer",{},100)
    monkeypatch.setenv("BEDROCK_BUDGET_USD","0.1")
    reservation=inference_budget.reserve("test/model","answer",{},100)
    inference_budget.settle(reservation,{},"TimeoutError")
    status=inference_budget.status()
    assert status["paused"] and status["reserved_usd"]>Decimal("0.001")
    with pytest.raises(inference_budget.BudgetStopped):
        inference_budget.reserve("test/model","answer",{},100)


def test_concurrent_preview_calls_share_one_existing_limit(shared_ledger):
    def reserve():
        try:
            return inference_budget.reserve("test/model","answer",{},3000)
        except inference_budget.BudgetStopped:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:reserve(),range(2)))
    assert sum(r is not None for r in results)==1
    state=inference_budget.status()
    assert state["spent_usd"]+state["reserved_usd"]<=Decimal("0.1")


def test_settlement_keeps_original_ledger_if_configuration_changes(shared_ledger,monkeypatch):
    reservation=inference_budget.reserve("test/model","answer",{},100)
    monkeypatch.delenv("BEDROCK_BUDGET_DATABASE_URL")
    inference_budget.settle(reservation,{"usage":{"inputTokens":100,"outputTokens":20}},None)
    with shared_ledger.connect() as conn:
        assert sql(conn,"SELECT spent_usd FROM inference_budget_runs").scalar()==Decimal("0.01066")


def test_model_pacing_uses_the_same_shared_lane(shared_ledger,monkeypatch):
    model="test/shared-lane-"+uuid4().hex
    monkeypatch.setenv("BEDROCK_REQUESTS_PER_MINUTE","9")
    delays=[]
    monkeypatch.setattr(model_limits.time,"sleep",lambda seconds:delays.append(seconds))
    model_limits.pace(model,"test")
    model_limits.pace(model,"test")
    assert len(delays)==1 and 5<delays[0]<8
    with engine.connect() as conn:
        assert sql(conn,"SELECT count(*) FROM model_request_slots WHERE model=:model",model=model).scalar()==0


def test_shared_guard_unavailable_never_falls_back_or_dispatches(budget_environment,monkeypatch):
    monkeypatch.setenv("BEDROCK_BUDGET_DATABASE_URL","postgresql+psycopg://unavailable")
    class Unavailable:
        def begin(self):
            raise ConnectionError("Shared ledger unavailable")
    monkeypatch.setattr(inference_budget,"_shared_engine",lambda url:Unavailable())
    monkeypatch.setattr(model_limits,"pace",lambda *args:None)
    monkeypatch.setenv("BEDROCK_EXTRACTION_MODEL","test/model")
    monkeypatch.setattr(providers,"configured",lambda:True)
    monkeypatch.setattr(providers,"runtime",lambda:pytest.fail("No unguarded SDK dispatch"))
    with pytest.raises(ConnectionError):
        providers.structured(AnswerVerdict,"test",{}, {},"test")
    with engine.connect() as conn:
        assert sql(conn,"SELECT count(*) FROM inference_budget_runs WHERE id=:id",id=budget_environment).scalar()==0


def test_shared_url_without_run_is_not_unbudgeted(monkeypatch):
    monkeypatch.setenv("BEDROCK_BUDGET_DATABASE_URL","postgresql+psycopg://unavailable")
    monkeypatch.delenv("BEDROCK_BUDGET_RUN",raising=False)
    for action in (lambda:inference_budget.reserve("test/model","answer",{},100),inference_budget.status,
                   lambda:model_limits.pace("test/model","test")):
        with pytest.raises(inference_budget.BudgetStopped,match="existing approved run ID"):
            action()
