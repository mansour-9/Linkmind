"""Run with python -m diagnostics.m32. Default is offline and cannot call AWS."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import json
import sys
from pydantic import ValidationError
from app.contracts import Extraction,AnswerVerdict,validate_extraction
from app.providers import EXTRACT
from diagnostics.m32_core import cases,digest,score,assertions,Budget,BudgetStopped
from diagnostics.m32_live import Adapters,prices,SONNET,GEMMA,VERIFY


def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')


def frozen(out):
    manifest,loaded=cases()
    identity=dict(manifest_sha256=digest(json.dumps(manifest,sort_keys=True,ensure_ascii=False).encode()),
        extraction_schema_sha256=digest(json.dumps(Extraction.model_json_schema(),sort_keys=True).encode()),
        prompt_sha256=digest(EXTRACT.encode()),source_passages=[dict(id=c['id'],source_sha256=c['sha256'],passage_sha256=c['passage_sha256'],passages=len(c['passages'])) for c in loaded],
        settings=dict(region='us-east-1',models=[GEMMA,SONNET],max_attempts=24,projected_usd_limit='5',temperature=0,extraction_max_output=6000,verification_max_output=1024,automatic_retries=0,repair_calls=0))
    path=out/'frozen.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=identity:raise ValueError('Frozen experiment identity changed')
    if not path.exists():write(path,identity)
    return identity,manifest,loaded


def live(out):
    identity,manifest,loaded=frozen(out)
    report=dict(status='preflight',rows=[],limitations=[
        'Six paired synthetic cases are a pilot, not statistical model equivalence or full Chat/retrieval quality.',
        'Gold metrics use frozen literal/alias tuples; additional source-supported paraphrases require separate adjudication.',
        'Common Sonnet verification can be biased; gold matching and explicit source review remain separate.',
        'Sonnet uses native constrained output; Gemma uses a schema in the same prompt with strict local validation. No silent output repair.',
        'Costs are token estimates at verified list rates, not an AWS bill.'])
    budget=None
    try:
        adapters=Adapters();report['preflight']=adapters.preflight();rates=prices();report['prices']=rates
        budget=Budget(out/'ledger.json',rates,identity)
        report['status']='running';write(out/'live.json',report)
        for case in loaded:
            # Alternate order to avoid always giving the same candidate the first request.
            candidates=[GEMMA,SONNET] if loaded.index(case)%2==0 else [SONNET,GEMMA]
            for model in candidates:
                row=dict(case=case['id'],model=model,status='pending',schema_valid=False,exact_citations_valid=False)
                report['rows'].append(row);write(out/'live.json',report)
                response=adapters.call(budget,model,Extraction,EXTRACT,{'passages':case['passages']},'extraction',case['id'],6000)
                row['extraction']=response
                if not response['complete']:row['status']='incomplete_output';write(out/'live.json',report);continue
                try:result=Extraction.model_validate_json(response['text'],strict=True);row['schema_valid']=True
                except ValidationError:
                    row['status']='schema_failure';write(out/'live.json',report);continue
                try:validate_extraction(result,case['passages']);row['exact_citations_valid']=True
                except ValueError as exc:
                    row['status']='evidence_failure';row['validation_error']=str(exc);write(out/'live.json',report);continue
                row['gold']=score(result,case,manifest['scoring'])
                evidence_assertions=assertions(result)
                if evidence_assertions:
                    verdict=adapters.call(budget,SONNET,AnswerVerdict,VERIFY,{'assertions':evidence_assertions},'verification',case['id'],1024)
                    row['verification']=verdict
                    try:
                        if not verdict['complete']:raise ValueError('Incomplete verifier output')
                        checked=AnswerVerdict.model_validate_json(verdict['text'],strict=True)
                        if len(checked.supported)!=len(evidence_assertions):raise ValueError('Verifier verdict count mismatch')
                        row['unsupported_assertions']=sum(not value for value in checked.supported)
                        row['status']='accepted_first_pass' if all(checked.supported) else 'semantic_failure'
                    except (ValidationError,ValueError):row['status']='verification_failure'
                else:row['status']='empty_extraction'
                write(out/'live.json',report)
        report['status']='completed'
    except Exception as exc:
        report['status']='blocked' if budget is None else 'stopped'
        report['stop_reason']=type(exc).__name__+(':'+str(exc) if isinstance(exc,(BudgetStopped,ValueError)) or str(exc).startswith('MantleHTTP') else '')
    finally:
        if budget:
            report['attempts']=len(budget.data['attempts']);report['ledger']=budget.data
        else:report['attempts']=0
        write(out/'live.json',report)
    return 0 if report['status']=='completed' else 2


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--preflight',action='store_true');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    if args.live and args.preflight:parser.error('Choose one mode')
    if args.live:
        if (args.out/'ledger.json').exists():parser.error('Existing approved run ledger found; refusing to reset or repeat paid requests')
        return live(args.out)
    frozen(args.out)
    if args.preflight:
        write(args.out/'preflight.json',dict(access=Adapters().preflight(),prices=prices()));return 0
    from diagnostics.m32_offline import run
    result=run();write(args.out/'offline.json',result)
    print(json.dumps({'format_matrix':{'passed':result['format_matrix']['passed'],'total':result['format_matrix']['total']},'reproduction':result['synthetic_reproduction']['failure']}))
    return 0 if result['format_matrix']['passed']==result['format_matrix']['total'] else 1


if __name__=='__main__':sys.exit(main())
