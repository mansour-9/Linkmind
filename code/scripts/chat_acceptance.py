"""Explicit real-source acceptance harness. Never imported by application startup.

The manifest contains questions, optional conversation groups and expected review
notes. Gold notes never enter application/model inputs. Private outputs stay offline.
"""
import argparse
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from app import main,chat_trace
from app.db import sql,engine
from app.connector_transport import request_limits
from app.inference_budget import ledger_engine,bounded_trial,status,BudgetStopped

def save(path,value):
    temporary=path.with_suffix('.writing')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    temporary.replace(path)

def main_entry():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--out',required=True)
    parser.add_argument('--window',required=True)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--capture-model',action='store_true',help='Save structured outputs only to the private acceptance artifact.')
    args=parser.parse_args()
    if os.getenv('AI_PROVIDER')!='bedrock' or os.getenv('LINKMIND_CONNECTOR_NETWORK')!='1':
        raise RuntimeError('Real acceptance requires explicit Bedrock and connector networking.')
    window=Path(args.window);output=Path(args.out)
    with ledger_engine().connect() as conn:
        if not window.exists():
            start=sql(conn,'SELECT clock_timestamp()').scalar_one()
            save(window,dict(start=start,before=status(),max_calls=120,reservation_limit='7'))
        scope=json.loads(window.read_text(encoding='utf-8'))
        prior=sql(conn,"""SELECT count(*) AS calls,coalesce(sum(reserved_usd),0) AS reservations
            FROM inference_budget_calls WHERE run_id=:run AND created_at>=CAST(:start AS timestamptz)""",
            run=os.environ['BEDROCK_BUDGET_RUN'],start=scope['start']).mappings().one()
    with engine.connect() as conn:
        user=sql(conn,'SELECT u.*,o.name AS organization FROM users u JOIN organizations o ON o.id=u.organization_id WHERE u.id=:id',id=UUID(args.owner)).mappings().one()
    viewer=main.Viewer(**user)
    cases=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    for case in cases:
        if case.get('expected_language')=='Arabic' and not any('\u0600'<=char<='\u06ff' for char in case['question']):
            raise RuntimeError('The Arabic benchmark prompt was corrupted before dispatch. No model call was made.')
    results=json.loads(output.read_text(encoding='utf-8')) if output.exists() else []
    completed={r['id'] for r in results};conversations={r['group']:UUID(r['conversation_id']) for r in results if r.get('group') and r.get('conversation_id')}
    with bounded_trial(scope['reservation_limit'],scope['max_calls'],ledger_since=scope['start']) as trial:
        trial.update(calls=prior.calls,reservations=Decimal(str(prior.reservations)))
        for case in cases:
            if case['id'] in completed:continue
            entry=dict(id=case['id'],question=case['question'],group=case.get('group'),before=status())
            started=time.monotonic()
            model_results=[]
            if args.capture_model:
                from app import providers
                original=providers.structured
                def capture(contract,system,payload,scope,operation,*a,**kw):
                    result=original(contract,system,payload,scope,operation,*a,**kw)
                    model_results.append(dict(operation=operation,result=result.model_dump()))
                    return result
                providers.structured=capture
            try:
                group=case.get('group')
                cid=conversations.get(group) if group else None
                if cid is None:
                    cid=main.create_conversation(main.NewConversation(title='Chat repair acceptance',source_policy='auto'),viewer)['id']
                if group:conversations[group]=cid
                entry['conversation_id']=str(cid)
                with request_limits(seconds=85),chat_trace.session() as trace:
                    response=main.ask(cid,main.Question(question=case['question']),viewer)
                    entry.update(response=response,trace=trace.summary())
            except Exception as exc:
                detail=getattr(exc,'detail',None)
                # Never stringify provider exceptions containing credentials/requests.
                entry.update(error=type(exc).__name__,detail=detail if isinstance(detail,(str,dict)) else None)
            finally:
                if args.capture_model:providers.structured=original
            if args.capture_model:entry['model_results']=model_results
            entry.update(total_ms=round((time.monotonic()-started)*1000),after=status(),
                trial_calls=trial['calls'],trial_reservations=str(trial['reservations']))
            results.append(entry);save(output,results)
            print(json.dumps(dict(id=case['id'],ms=entry['total_ms'],error=entry.get('error'),
                state=entry.get('response',{}).get('answer_state'),calls=trial['calls'],reservations=str(trial['reservations'])),default=str),flush=True)
            current=status()
            if current['paused'] or trial['calls']>=scope['max_calls']:break

if __name__=='__main__':main_entry()
