"""One-shot bounded real-model grounding acceptance; see RF34_FOLLOWUP_SCOPE.md."""
import argparse
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from fastapi.security import HTTPAuthorizationCredentials
from app import main, providers, inference_budget
from app.contracts import GroundedAnswer
from app.db import sql
from app.query_limits import question_limits


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--freshness-repair-controls',action='store_true')
    args=parser.parse_args()
    if args.report.exists():raise RuntimeError('A started trial cannot be repeated automatically.')
    if not providers.configured() or not os.getenv('BEDROCK_BUDGET_DATABASE_URL') or os.getenv('BEDROCK_BUDGET_RUN')!='northstar-sonnet-2026-11-12':
        raise RuntimeError('The original persistent spend guard is required.')
    before=inference_budget.status()
    if before['paused'] or before['limit_usd']!=Decimal('10'):raise RuntimeError('The original USD 10 guard must be available.')
    cases=json.loads(Path('fixtures/retrieval/grounding_followup.json').read_text(encoding='utf-8'))
    if args.freshness_repair_controls:
        cases['answers']=[]
        cases['verifications']=[c for c in cases['verifications'] if c['id'] in
            {'explicit-leader-control','unqualified-saved-latest','captured-temporal-addition'}]
    max_calls=3 if args.freshness_repair_controls else 14
    cap=Decimal('0.35') if args.freshness_repair_controls else Decimal('1.25')
    viewer=main.authenticate(HTTPAuthorizationCredentials(scheme='Bearer',credentials='demo-amal'))
    scope=dict(org=viewer.organization_id,user=viewer.id)
    report=dict(status='started',budget_before=before,policy=main.ANSWER_VALIDATION_VERSION,results=[],
        max_calls=max_calls,max_seconds=600,conservative_dispatch_cap_usd=str(cap),embedding_calls=0,
        freshness_repair_controls=args.freshness_repair_controls)
    started=time.monotonic();reservations=[];bound=Decimal('0')
    def save():
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    original=providers.reserve
    def guard(model,operation,request,max_output):
        nonlocal bound
        if operation not in {'answer','answer_verification'} or len(reservations)>=max_calls or time.monotonic()-started>=600:
            raise inference_budget.BudgetStopped('Grounding follow-up reached its operation/call/time scope.')
        current=inference_budget.status()
        if current['paused'] or current['reserved_usd']!=before['reserved_usd']:
            raise inference_budget.BudgetStopped('Unknown or concurrent usage; stop and preserve reservations.')
        rates=inference_budget.rates(model)
        estimate=((len(json.dumps(request,ensure_ascii=False,default=str).encode())+8192)*rates['input']+max_output*rates['output'])/1_000_000
        if bound+estimate>cap:raise inference_budget.BudgetStopped('Grounding follow-up reached its reservation cap.')
        reservation=original(model,operation,request,max_output)
        if reservation is None:raise RuntimeError('Unguarded dispatch forbidden.')
        reservations.append(reservation);bound+=reservation['cost']
        report.update(call_ids=[str(r['id']) for r in reservations],conservative_reservations_usd=bound)
        save();return reservation
    save()
    try:
        with patch.object(providers,'reserve',guard):
            for case in cases['answers']:
                passages=[dict(id=case['id'],text=case['text'])]
                with question_limits():answer=providers.answer(case['question'],passages,scope)
                report['results'].append(dict(id=case['id'],kind='generation',question=case['question'],
                    source=case['text'],answer=answer.model_dump(),failure_reason=answer._failure_reason))
                save();print(case['id'],bool(answer.statements),flush=True)
            for case in cases['verifications']:
                answer=GroundedAnswer(statements=[dict(text=case['statement'],evidence=[dict(passage_id=case['id'],quote=case['source'])])],insufficient_evidence=False)
                with question_limits():verdict=providers.verify_answer(case['question'],answer,[dict(id=case['id'],text=case['source'])],scope)
                accepted=verdict.accepts(answer.statements)
                report['results'].append(dict(**case,kind='verification',accepted=accepted,passed=accepted==case['expected'],verdict=verdict.model_dump()))
                save();print(case['id'],accepted==case['expected'],flush=True)
        report['status']='completed_pending_source_review'
    except Exception as exc:
        report.update(status='stopped',error_type=type(exc).__name__)
    finally:
        report.update(budget_after=inference_budget.status(),seconds=round(time.monotonic()-started,3))
        with inference_budget.ledger_engine().connect() as conn:
            calls=[dict(r) for r in sql(conn,'SELECT id,operation,status,actual_usd FROM inference_budget_calls WHERE id=ANY(:ids) ORDER BY created_at,id',ids=[r['id'] for r in reservations]).mappings()] if reservations else []
        report.update(calls=calls,all_usage_settled=all(c['status']=='settled' for c in calls),
            actual_test_cost_usd=sum((c['actual_usd'] for c in calls if c['actual_usd'] is not None),Decimal('0')))
        save();print(json.dumps({k:report[k] for k in ('status','seconds','actual_test_cost_usd','all_usage_settled')},default=str),flush=True)
    return 0 if report['status']=='completed_pending_source_review' else 1

if __name__=='__main__':raise SystemExit(run())
