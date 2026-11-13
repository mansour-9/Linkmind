"""One explicitly authorized Sonnet probe using the existing persistent T1 ledger."""
import argparse
import hashlib
import json
from pathlib import Path
from uuid import UUID,uuid5,NAMESPACE_URL

from app import providers
from app.company_demo import ROOT
from app.contracts import validate_extraction
from app.inference_budget import status
from app.parsers import parse_document


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if args.report.exists():
        raise RuntimeError('Probe report already exists; refusing to repeat paid work.')
    before=status()
    if not before or before['id']!='northstar-sonnet-2026-11-12' or float(before['limit_usd'])!=10 or before['paused']:
        raise RuntimeError('The existing approved USD 10 run must be available; no budget is changed by this probe.')
    if float(before['spent_usd'])+float(before['reserved_usd'])+0.75>10:
        raise RuntimeError('Insufficient existing headroom for this bounded probe.')
    filename='atlas-charter.md'
    content=(ROOT/filename).read_bytes()
    passages=[dict(id=str(uuid5(NAMESPACE_URL,'f13-probe:'+str(index))),text=p.text,locator=p.locator)
        for index,p in enumerate(parse_document(filename,content),1)]
    report=dict(schema_version=1,scope='F1.3 single fictional-source extraction and verification',filename=filename,
        sha256=hashlib.sha256(content).hexdigest(),budget_before=before,passages=passages,status='started')
    try:
        result=validate_extraction(providers.extract_bedrock(passages,dict(
            org=UUID('00000000-0000-4000-8000-000000000001'),user=UUID('00000000-0000-4000-8000-000000000101'))),passages)
        if not result.entities:
            raise ValueError('Probe returned no verified entities; no staging success is claimed.')
        report.update(status='verified',result=result.model_dump(mode='json'),
            counts=dict(entities=len(result.entities),claims=len(result.claims),relationships=len(result.relationships)))
    except Exception as exc:
        report.update(status='stopped',error_type=type(exc).__name__)
        raise
    finally:
        report['budget_after']=status()
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8')
        print(json.dumps({key:report[key] for key in ('status','budget_before','budget_after')},default=str),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
