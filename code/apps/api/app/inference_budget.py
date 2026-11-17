"""Optional local-test cost reservations; no AWS budgets/resources are provisioned."""
import json
import os
from pathlib import Path
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from uuid import uuid4
from sqlalchemy import create_engine

from app.db import engine, sql
from contextvars import ContextVar
from contextlib import contextmanager

_trial = ContextVar('bounded_acceptance_trial', default=None)


@contextmanager
def bounded_trial(limit_usd, max_calls,ledger_since=None):
    """An additional invocation bound; the original durable ledger still owns spend."""
    value=dict(limit=Decimal(str(limit_usd)),max_calls=max_calls,calls=0,reservations=Decimal('0'),ledger_since=ledger_since)
    token=_trial.set(value)
    try:yield value
    finally:_trial.reset(token)


class BudgetStopped(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _shared_engine(url):
    return create_engine(url,pool_pre_ping=True,pool_timeout=5,connect_args={"connect_timeout":5})


def ledger_engine(fallback=None):
    """Separate preview data from the existing spend/pacing database; never copy it."""
    url=os.getenv("BEDROCK_BUDGET_DATABASE_URL")
    if url:
        if not os.getenv("BEDROCK_BUDGET_RUN"):
            raise BudgetStopped("A shared spend guard requires its existing approved run ID.")
        return _shared_engine(url)
    return engine if fallback is None else fallback


def rates(model):
    try:
        raw=os.environ["BEDROCK_RATES_JSON"]
        item = json.loads(Path(raw).read_text(encoding="utf-8") if raw.startswith("/") else raw)[os.getenv("AWS_REGION", "us-east-1")][model]
        result = {key: Decimal(str(item[key])) for key in ("input", "output")}
        if item.get("currency") != "USD" or not item.get("effective_date") or any(not v.is_finite() or v < 0 for v in result.values()):
            raise ValueError()
        return result
    except (KeyError, ValueError, TypeError, InvalidOperation):
        raise BudgetStopped("Verified USD model rates are required for this test budget.") from None


def reserve(model, operation, request, max_output):
    run = os.getenv("BEDROCK_BUDGET_RUN")
    if not run:
        if os.getenv("BEDROCK_BUDGET_DATABASE_URL"):
            raise BudgetStopped("A shared spend guard requires its existing approved run ID.")
        return None
    try:
        limit = Decimal(os.environ["BEDROCK_BUDGET_USD"])
        if not limit.is_finite() or limit <= 0 or len(run) > 100:
            raise ValueError()
    except (KeyError, ValueError, InvalidOperation):
        raise BudgetStopped("The local test requires a finite positive approved budget matching its persisted ledger.") from None
    pricing = rates(model)
    # UTF-8 request bytes plus an explicit service/schema allowance are a conservative
    # reservation, never a reported token measurement. SDK automatic retries are off
    # for budgeted runs so an unobserved attempt cannot escape the ledger.
    incoming = len(json.dumps(request, ensure_ascii=False, default=str).encode("utf-8")) + 8192
    cost = (incoming * pricing["input"] + max_output * pricing["output"]) / 1_000_000
    trial=_trial.get()
    if trial and not trial['ledger_since'] and (trial['calls']>=trial['max_calls'] or trial['reservations']+cost>trial['limit']):
        raise BudgetStopped('The bounded acceptance trial reached its call or reservation limit. No additional paid call was made.')
    budget_db=ledger_engine()
    with budget_db.begin() as conn:
        if not os.getenv("BEDROCK_BUDGET_DATABASE_URL"):
            sql(conn, "INSERT INTO inference_budget_runs(id,limit_usd) VALUES(:id,:limit) ON CONFLICT DO NOTHING", id=run, limit=limit)
        row = sql(conn, "SELECT * FROM inference_budget_runs WHERE id=:id FOR UPDATE", id=run).mappings().first()
        if row is None:
            raise BudgetStopped("The shared approved spend run was not found. No replacement budget was created.")
        if row.limit_usd != limit or row.paused or row.spent_usd + row.reserved_usd + cost > limit:
            raise BudgetStopped("The Sonnet test budget is reached or paused. No additional paid call was made.")
        if trial and trial['ledger_since']:
            # Durable task window on the original ledger. Released reservations
            # are not spending; unknown/in-flight attempts retain their full hold.
            window=sql(conn,"""SELECT count(*) AS calls,coalesce(sum(CASE WHEN status='settled'
                THEN actual_usd ELSE greatest(reserved_usd,coalesce(actual_usd,0)) END),0) AS exposure
                FROM inference_budget_calls WHERE run_id=:run AND created_at>=CAST(:start AS timestamptz)""",
                run=run,start=trial['ledger_since']).mappings().one()
            if window.calls>=trial['max_calls'] or window.exposure+cost>trial['limit']:
                raise BudgetStopped('The approved task call or spend ceiling was reached. No additional paid call was made.')
        id = uuid4()
        sql(conn, """INSERT INTO inference_budget_calls(id,run_id,model,operation,input_bound,output_bound,reserved_usd,status)
            VALUES(:id,:run,:model,:operation,:incoming,:outgoing,:cost,'reserved')""",
            id=id, run=run, model=model, operation=operation, incoming=incoming, outgoing=max_output, cost=cost)
        sql(conn, "UPDATE inference_budget_runs SET reserved_usd=reserved_usd+:cost WHERE id=:id", id=run, cost=cost)
    if trial:
        trial['calls']+=1
        trial['reservations']+=cost
    return dict(id=id, run=run, rates=pricing, input_bound=incoming, output_bound=max_output, cost=cost,
                ledger_engine=budget_db)


def settle(reservation, response, error):
    if reservation is None:
        return
    usage = response.get("usage", {})
    incoming, outgoing = usage.get("inputTokens"), usage.get("outputTokens")
    known = all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in (incoming, outgoing))
    cost = (incoming * reservation["rates"]["input"] + outgoing * reservation["rates"]["output"]) / 1_000_000 if known else None
    uncertain = not known or incoming > reservation["input_bound"] or outgoing > reservation["output_bound"] or cost > reservation["cost"] or response.get("ResponseMetadata", {}).get("RetryAttempts", 0) > 0
    # Settle against the exact ledger used for this dispatch, even if configuration changes.
    with reservation.get("ledger_engine",engine).begin() as conn:
        sql(conn, "SELECT id FROM inference_budget_runs WHERE id=:id FOR UPDATE", id=reservation["run"])
        call = sql(conn, "SELECT status FROM inference_budget_calls WHERE id=:id FOR UPDATE", id=reservation["id"]).scalar_one()
        if call != "reserved":
            return
        sql(conn, "UPDATE inference_budget_calls SET status=:status,actual_usd=:cost WHERE id=:id",
            id=reservation["id"], status="unknown" if uncertain else "settled", cost=cost)
        if uncertain:
            sql(conn, "UPDATE inference_budget_runs SET paused=true WHERE id=:id", id=reservation["run"])
        else:
            sql(conn, """UPDATE inference_budget_runs SET reserved_usd=reserved_usd-:reserved,
                spent_usd=spent_usd+:actual WHERE id=:id""", id=reservation["run"], reserved=reservation["cost"], actual=cost)


def status():
    run = os.getenv("BEDROCK_BUDGET_RUN")
    if not run:
        if os.getenv("BEDROCK_BUDGET_DATABASE_URL"):
            raise BudgetStopped("A shared spend guard requires its existing approved run ID.")
        return None
    with ledger_engine().connect() as conn:
        row = sql(conn, "SELECT id,limit_usd,spent_usd,reserved_usd,paused FROM inference_budget_runs WHERE id=:id", id=run).mappings().first()
    if row is None and os.getenv("BEDROCK_BUDGET_DATABASE_URL"):
        raise BudgetStopped("The shared approved spend run was not found. No replacement budget was created.")
    return dict(row) if row else dict(id=run, limit_usd=os.environ.get("BEDROCK_BUDGET_USD"), spent_usd=0, reserved_usd=0, paused=False)


def amend_limit(expected_limit, approved_limit, approval, audit_path):
    """Explicit operator action, never called by reserve or an HTTP endpoint.

    The durable approval receipt is written before the locked amendment. Existing
    spending, reservations, pause state and calls are deliberately untouched.
    """
    old,new=Decimal(str(expected_limit)),Decimal(str(approved_limit))
    if not all(x.is_finite() and x>0 for x in (old,new)) or new<=old or not approval.strip():
        raise BudgetStopped('A documented positive increase and expected previous limit are required.')
    run=os.environ.get('BEDROCK_BUDGET_RUN')
    if not run:raise BudgetStopped('Amend an existing approved run only.')
    with ledger_engine().begin() as conn:
        row=sql(conn,'SELECT * FROM inference_budget_runs WHERE id=:id FOR UPDATE',id=run).mappings().one()
        if row.limit_usd!=old:raise BudgetStopped('The ledger limit changed; no amendment was applied.')
        receipt=dict(run_id=run,old_limit=str(old),approved_limit=str(new),approval=approval,
            spent_usd=str(row.spent_usd),reserved_usd=str(row.reserved_usd),paused=row.paused)
        with Path(audit_path).open('x',encoding='utf-8') as handle:
            json.dump(receipt,handle,indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        sql(conn,'UPDATE inference_budget_runs SET limit_usd=:limit WHERE id=:id',limit=new,id=run)
    return receipt


def resume_with_holds(expected_reserved,approval,audit_path):
    """Explicit operator-approved resume; never releases an unknown reservation."""
    expected=Decimal(str(expected_reserved));run=os.environ.get('BEDROCK_BUDGET_RUN')
    if not run or not expected.is_finite() or expected<0 or not approval.strip():
        raise BudgetStopped('An existing run, expected held amount and explicit approval are required.')
    with ledger_engine().begin() as conn:
        row=sql(conn,'SELECT * FROM inference_budget_runs WHERE id=:id FOR UPDATE',id=run).mappings().one()
        if not row.paused or row.reserved_usd!=expected:
            raise BudgetStopped('The paused ledger or held amount changed; no resume was applied.')
        receipt=dict(run_id=run,approval=approval,limit_usd=str(row.limit_usd),spent_usd=str(row.spent_usd),
            reserved_usd=str(row.reserved_usd),operation='resume_preserving_holds')
        with Path(audit_path).open('x',encoding='utf-8') as handle:
            json.dump(receipt,handle,indent=2);handle.flush();os.fsync(handle.fileno())
        sql(conn,'UPDATE inference_budget_runs SET paused=false WHERE id=:id',id=run)
    return receipt
