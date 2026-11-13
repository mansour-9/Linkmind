"""Exercise staging with a recorded, verified Sonnet result; makes no model calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from app import main as api,processing,conflict_detection,retrieval
from app.company_demo import ROOT
from app.contracts import Extraction
from app.db import engine,sql
from test_search_readiness import source,viewer


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--probe',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--disposable',action='store_true',required=True,help='Confirm this is the isolated mock validation database')
    args=parser.parse_args()
    if os.getenv('AI_PROVIDER','mock')!='mock':
        raise RuntimeError('Recorded probe application is restricted to a disposable mock stack.')
    if args.report.exists():
        raise RuntimeError('Staging report exists; refusing to repeat the recorded probe.')
    data=json.loads(args.probe.read_text(encoding='utf-8'))
    if data['status']!='verified' or data['filename']!='atlas-charter.md':
        raise ValueError('Only the verified fictional probe is accepted.')
    content=(ROOT/data['filename']).read_bytes()
    if hashlib.sha256(content).hexdigest()!=data['sha256']:
        raise ValueError('Probe fixture has changed.')
    with engine.begin() as conn:
        job=source(conn,content)
        sql(conn,"UPDATE documents SET filename='F13-atlas-charter.md' WHERE id=:id",id=job.document_id)
        sql(conn,"UPDATE document_versions SET filename='F13-atlas-charter.md' WHERE id=:id",id=job.version_id)
    assert processing.process_one()
    original=api.job(job.id,viewer())
    assert original['status']=='ready'
    before=retrieval.search(viewer(),'NS-ATLAS',[job.document_id],semantic=False)
    known={item['id']:item['text'] for item in data['passages']}
    def recorded(passages,scope):
        result=Extraction.model_validate(data['result'])
        mapping={item['text']:item['id'] for item in passages}
        for group in (result.entities,result.claims,result.relationships):
            for item in group:
                for citation in item.evidence:
                    citation.passage_id=mapping[known[citation.passage_id]]
        return result
    processing.configured=lambda:True
    processing.extract_bedrock=recorded
    conflict_detection.assess=lambda *args:{}
    queued=api.reprocess(job.id,viewer())
    assert processing.process_one()
    active=api.job(job.id,viewer())
    assert active['status']=='ready' and active['active_enrichment_version_id']==queued['staged_version_id']
    after=retrieval.search(viewer(),'NS-ATLAS',[job.document_id],semantic=False)
    assert {p['id'] for p in before}=={p['id'] for p in after}
    def invalid(passages,scope):
        result=recorded(passages,scope)
        result.entities[0].evidence[0].quote='Injected unsupported replacement for rollback validation.'
        return result
    processing.extract_bedrock=invalid
    api.reprocess(job.id,viewer())
    assert processing.process_one()
    failed=api.job(job.id,viewer())
    assert failed['status']=='enrichment_staged_failed' and failed['preserved_enrichment']
    assert failed['active_enrichment_version_id']==active['active_enrichment_version_id']
    report=dict(status='passed',document_id=str(job.document_id),job_id=str(job.id),
        real_model_counts=data['counts'],activation='verified recorded Sonnet result',
        rollback='deterministic unsupported-quote injection after activation',
        search_ids_preserved=True,live_generation_retained=True,paid_calls_in_this_script=0)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
