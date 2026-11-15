"""One source-only overview using the original shared ledger; no upload or enrichment."""
import argparse
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from unittest.mock import patch

from fastapi.security import HTTPAuthorizationCredentials
from app import main as api,providers,inference_budget
from app.db import engine,sql


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--document-id",type=UUID,required=True)
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--question",default="Summarize this document")
    parser.add_argument("--max-additional-usd",type=Decimal,default=Decimal("0.75"))
    args=parser.parse_args()
    if args.report.exists():
        raise RuntimeError("Report exists; refusing to repeat the paid smoke question.")
    if not args.max_additional_usd.is_finite() or not 0<args.max_additional_usd<=1:
        raise ValueError("The bounded smoke allowance must be at most USD 1, within the existing cap.")
    if (not providers.configured() or not os.getenv("BEDROCK_BUDGET_DATABASE_URL")
            or os.getenv("BEDROCK_BUDGET_RUN")!="northstar-sonnet-2026-11-12"):
        raise RuntimeError("Use only the RF1 AI preview with the existing shared spend guard.")
    before=inference_budget.status()
    if before["paused"] or before["limit_usd"]!=Decimal("10"):
        raise inference_budget.BudgetStopped("The original USD 10 guard is not available for this question.")
    viewer=api.authenticate(HTTPAuthorizationCredentials(scheme="Bearer",credentials="demo-amal"))
    original=providers.reserve
    reservations=[]
    bound=Decimal("0")

    def bounded_reserve(model,operation,request,max_output):
        nonlocal bound
        if operation not in {"answer","answer_verification"} or len(reservations)>=3:
            raise inference_budget.BudgetStopped("Smoke question reached its three-call/answer-only bound.")
        pricing=inference_budget.rates(model)
        incoming=len(json.dumps(request,ensure_ascii=False,default=str).encode("utf-8"))+8192
        projected=(incoming*pricing["input"]+max_output*pricing["output"])/1_000_000
        if bound+projected>args.max_additional_usd:
            raise inference_budget.BudgetStopped("Smoke question reached its conservative additional-spend bound.")
        reservation=original(model,operation,request,max_output)
        if reservation is None:
            raise inference_budget.BudgetStopped("An unbudgeted smoke dispatch is forbidden.")
        reservations.append(reservation)
        bound+=reservation["cost"]
        return reservation

    report={"question":args.question,"document_id":str(args.document_id),
            "budget_before":before,"max_calls":3,"maximum_additional_usd":args.max_additional_usd}
    # Persist a start marker before inference, so an interrupted postflight cannot
    # make the same paid question look safe to repeat automatically.
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps({**report,"status":"started"},indent=2,default=str)+"\n",encoding="utf-8")
    started=time.monotonic()
    exit_code=1
    try:
        conversation=api.create_conversation(api.NewConversation(title="RF1 AI: Project Lantern overview",
            document_ids=[args.document_id]),viewer)
        report["conversation_id"]=conversation["id"]
        with patch.object(providers,"reserve",bounded_reserve):
            result=api.ask(conversation["id"],api.Question(question=report["question"]),viewer)
        report["answer"]=result
        accepted=result["provider"]=="bedrock" and bool(result["statements"])
        report["status"]="supported_answer" if accepted else "insufficient_evidence"
        exit_code=0 if accepted else 1
    except Exception as exc:
        report["status"]="stopped"
        report["error"]={"type":type(exc).__name__,"detail":str(exc)[:500]}
    finally:
        report["latency_seconds"]=round(time.monotonic()-started,3)
        report["reserved_call_ids"]=[str(r["id"]) for r in reservations]
        report["conservative_reservation_bound_usd"]=bound
        report["budget_after"]=inference_budget.status()
        with inference_budget.ledger_engine().connect() as conn:
            report["calls"]=[dict(r) for r in sql(conn,"""SELECT id,operation,status,actual_usd,reserved_usd
                FROM inference_budget_calls WHERE id=ANY(:ids) ORDER BY created_at,id""",
                ids=[r["id"] for r in reservations]).mappings()] if reservations else []
        report["source_only"]=all(r["operation"] in {"answer","answer_verification"} for r in report["calls"])
        with engine.connect() as conn:
            report["entity_count"]=sql(conn,"SELECT count(*) FROM entities WHERE version_id IN (SELECT id FROM document_versions WHERE document_id=:id)",id=args.document_id).scalar()
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({"status":report["status"],"model_calls":len(reservations),
            "source_only":report["source_only"],"latency_seconds":report["latency_seconds"],
            "conversation_id":str(report.get("conversation_id","")),"report":str(args.report)}),flush=True)
    return exit_code


if __name__=="__main__":
    raise SystemExit(main())
