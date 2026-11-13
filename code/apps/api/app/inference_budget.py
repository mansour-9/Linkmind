"""Optional local-test cost reservations; no AWS budgets/resources are provisioned."""
import json
import os
from pathlib import Path
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from app.db import engine, sql


class BudgetStopped(RuntimeError):
    pass


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
        return None
    try:
        limit = Decimal(os.environ["BEDROCK_BUDGET_USD"])
        if not limit.is_finite() or not 0 < limit <= 10 or len(run) > 100:
            raise ValueError()
    except (KeyError, ValueError, InvalidOperation):
        raise BudgetStopped("The local test requires a valid approved budget of at most USD 10.") from None
    pricing = rates(model)
    # UTF-8 request bytes plus an explicit service/schema allowance are a conservative
    # reservation, never a reported token measurement. SDK automatic retries are off
    # for budgeted runs so an unobserved attempt cannot escape the ledger.
    incoming = len(json.dumps(request, ensure_ascii=False, default=str).encode("utf-8")) + 8192
    cost = (incoming * pricing["input"] + max_output * pricing["output"]) / 1_000_000
    with engine.begin() as conn:
        sql(conn, "INSERT INTO inference_budget_runs(id,limit_usd) VALUES(:id,:limit) ON CONFLICT DO NOTHING", id=run, limit=limit)
        row = sql(conn, "SELECT * FROM inference_budget_runs WHERE id=:id FOR UPDATE", id=run).mappings().one()
        if row.limit_usd != limit or row.paused or row.spent_usd + row.reserved_usd + cost > limit:
            raise BudgetStopped("The Sonnet test budget is reached or paused. No additional paid call was made.")
        id = uuid4()
        sql(conn, """INSERT INTO inference_budget_calls(id,run_id,model,operation,input_bound,output_bound,reserved_usd,status)
            VALUES(:id,:run,:model,:operation,:incoming,:outgoing,:cost,'reserved')""",
            id=id, run=run, model=model, operation=operation, incoming=incoming, outgoing=max_output, cost=cost)
        sql(conn, "UPDATE inference_budget_runs SET reserved_usd=reserved_usd+:cost WHERE id=:id", id=run, cost=cost)
    return dict(id=id, run=run, rates=pricing, input_bound=incoming, output_bound=max_output, cost=cost)


def settle(reservation, response, error):
    if reservation is None:
        return
    usage = response.get("usage", {})
    incoming, outgoing = usage.get("inputTokens"), usage.get("outputTokens")
    known = all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in (incoming, outgoing))
    cost = (incoming * reservation["rates"]["input"] + outgoing * reservation["rates"]["output"]) / 1_000_000 if known else None
    uncertain = not known or incoming > reservation["input_bound"] or outgoing > reservation["output_bound"] or cost > reservation["cost"] or response.get("ResponseMetadata", {}).get("RetryAttempts", 0) > 0
    with engine.begin() as conn:
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
        return None
    with engine.connect() as conn:
        row = sql(conn, "SELECT id,limit_usd,spent_usd,reserved_usd,paused FROM inference_budget_runs WHERE id=:id", id=run).mappings().first()
    return dict(row) if row else dict(id=run, limit_usd=os.environ.get("BEDROCK_BUDGET_USD"), spent_usd=0, reserved_usd=0, paused=False)
