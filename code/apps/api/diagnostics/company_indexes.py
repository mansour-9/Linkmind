"""Repair missing vectors only for the approved fictional test corpus/run."""
import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from app import providers
from app.company_demo import MANIFEST,ROOT
from app.db import engine,sql

RUN="northstar-sonnet-2026-11-12"
ORG=UUID("00000000-0000-4000-8000-000000000001")
OWNER=UUID("00000000-0000-4000-8000-000000000101")
MODEL="amazon.titan-embed-text-v2:0"


def refresh():
    if not providers.configured() or os.getenv("BEDROCK_BUDGET_RUN")!=RUN or os.getenv("BEDROCK_EMBEDDING_MODEL")!=MODEL:
        raise RuntimeError("This repair requires the existing approved company Sonnet run.")
    checksums=[f["sha256"] for f in MANIFEST["fixtures"]]
    checksums.append(hashlib.sha256((ROOT/"your-addition.txt").read_bytes()).hexdigest())
    with engine.connect() as conn:
        budget=sql(conn,"SELECT limit_usd,paused FROM inference_budget_runs WHERE id=:id",id=RUN).mappings().first()
        if not budget or budget.limit_usd!=10 or budget.paused:
            raise RuntimeError("The approved budget must be verified and resumed before index repair.")
        rows=sql(conn,"""SELECT k.id,k.text,k.version_id,d.id AS document_id FROM chunks k
            JOIN document_versions v ON v.id=k.version_id JOIN documents d ON d.id=v.document_id
            WHERE d.organization_id=:org AND d.owner_id=:owner AND d.deleted_at IS NULL
              AND d.current_version_id=v.id AND v.checksum=ANY(:checksums)
              AND (k.embedding IS NULL OR k.embedding_error IS NOT NULL OR k.embedding_model IS DISTINCT FROM :model
                   OR k.embedding_dimensions IS DISTINCT FROM 256)
            ORDER BY v.created_at,k.line_number,k.id""",org=ORG,owner=OWNER,checksums=checksums,model=MODEL).mappings().all()
    repaired=0
    versions=set()
    for row in rows:
        # Recheck the exact active source before data is sent, then lock/recheck
        # before vector activation. Original text/locators/citation IDs never change.
        def current(conn,lock=False):
            return sql(conn,"""SELECT d.id FROM documents d JOIN document_versions v ON v.document_id=d.id
                WHERE d.id=:doc AND d.organization_id=:org AND d.owner_id=:owner AND d.deleted_at IS NULL
                AND d.current_version_id=:version AND v.id=:version AND v.checksum=ANY(:checksums)"""
                +(" FOR UPDATE OF d" if lock else ""),doc=row.document_id,version=row.version_id,
                org=ORG,owner=OWNER,checksums=checksums).first()
        with engine.connect() as conn:
            if not current(conn):
                continue
        vector=providers.embed(row.text,dict(org=ORG,user=OWNER,version=row.version_id))
        if not vector or len(vector)!=256:
            raise ValueError("No compatible embedding was returned; current source evidence was preserved.")
        with engine.begin() as conn:
            if not current(conn,lock=True):
                continue
            changed=sql(conn,"""UPDATE chunks SET embedding=CAST(:vector AS vector),embedding_model=:model,
                embedding_dimensions=256,embedding_error=NULL WHERE id=:id AND version_id=:version AND text=:text
                RETURNING id""",id=row.id,version=row.version_id,text=row.text,model=MODEL,vector=json.dumps(vector)).first()
            repaired+=bool(changed)
            versions.add(row.version_id)
    with engine.begin() as conn:
        for version in versions:
            sql(conn,"""UPDATE document_versions v SET embedding_status=CASE WHEN EXISTS(
                SELECT 1 FROM chunks k WHERE k.version_id=v.id AND (k.embedding IS NULL OR k.embedding_error IS NOT NULL
                OR k.embedding_model IS DISTINCT FROM :model OR k.embedding_dimensions IS DISTINCT FROM 256))
                THEN 'failed' ELSE 'ready' END WHERE v.id=:version""",version=version,model=MODEL)
    return dict(repaired_passages=repaired,versions=len(versions),candidate_passages=len(rows),model=MODEL,
                original_passages_unchanged=True,scope="approved fictional checksums only")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    result=refresh()
    args.report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result))
    return 0


if __name__=="__main__":
    sys.exit(main())
