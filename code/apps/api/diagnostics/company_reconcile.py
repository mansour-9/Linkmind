"""Reconcile the explicitly interrupted, isolated 24-document preview.

This is not a general ledger migration. It preserves known usage bounds and
refuses any other state. The prior inference call remains an upper-bound cost.
"""
import argparse
import json
from decimal import Decimal
from pathlib import Path
from app.company_demo import MANIFEST
from app.db import engine,sql


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    with engine.begin() as conn:
        run=sql(conn,"SELECT * FROM inference_budget_runs WHERE id='northstar-sonnet-2026-11-12' FOR UPDATE").mappings().one()
        calls=sql(conn,"SELECT * FROM inference_budget_calls WHERE run_id=:id ORDER BY created_at",id=run.id).mappings().all()
        versions=sql(conn,"SELECT v.id,v.filename,v.checksum,v.embedding_status,v.search_ready_at FROM document_versions v JOIN documents d ON d.id=v.document_id WHERE d.filename LIKE '%.md' ORDER BY v.created_at").mappings().all()
        expected={f['sha256'] for f in MANIFEST['fixtures'] if not f.get('revision_of')}
        if len(versions)!=24 or {v.checksum for v in versions}!=expected:
            raise RuntimeError('This is not the exact 24-document isolated preview')
        if any(c.status=='reserved' for c in calls):
            raise RuntimeError('Unsettled model calls remain; refusing reconciliation')
        embeddings=[c for c in calls if c.operation=='embedding']
        other=[c for c in calls if c.operation!='embedding']
        known=sum((Decimal(c.actual_usd or 0) for c in embeddings if c.status=='settled'),Decimal(0))
        bound=sum((Decimal(c.actual_usd if c.actual_usd is not None else c.reserved_usd) for c in calls),Decimal(0))
        if any(c.status!='settled' for c in embeddings):
            raise RuntimeError('Embedding evidence is incomplete')
        old_reserved=Decimal(run.reserved_usd)
        unresolved=sum((Decimal(c.reserved_usd) for c in other if c.status=='unknown'),Decimal(0))
        report={'run':run.id,'documents':len(versions),'embedding_calls':len(embeddings),
                'known_embedding_cost_usd':str(known),'preserved_cost_bound_usd':str(bound),
                'unresolved_upper_bound_usd':str(unresolved),'previous_reserved_usd':str(old_reserved),
                'actions':['Preserve all observed usage bounds','Clear only the settled embedding reservation']}
        if args.apply:
            if old_reserved!=unresolved:
                raise RuntimeError('Reservation is not exactly the unresolved non-embedding bound')
            sql(conn,"UPDATE inference_budget_runs SET reserved_usd=:bound WHERE id=:id",id=run.id,bound=unresolved)
            for version in versions:
                if version.search_ready_at:
                    sql(conn,"UPDATE document_versions SET embedding_status='ready' WHERE id=:id AND NOT EXISTS (SELECT 1 FROM chunks WHERE version_id=:id AND embedding IS NULL)",id=version.id)
            report['applied']=True
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8')
        print(json.dumps(report,default=str))

if __name__=='__main__': main()
