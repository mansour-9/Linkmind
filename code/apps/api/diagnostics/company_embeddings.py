"""Bounded recovery of the approved isolated corpus's stalled embeddings."""
import argparse,json,os,time
from pathlib import Path
from app.company_demo import MANIFEST
from app.db import engine,sql
from app.providers import embed


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    with engine.connect() as conn:
        rows=sql(conn,"SELECT v.id,v.checksum,v.filename,v.organization_id FROM document_versions v WHERE v.search_ready_at IS NOT NULL AND v.embedding_status='failed'").mappings().all()
        expected={f['sha256'] for f in MANIFEST['fixtures'] if not f.get('revision_of')}
        if not {r.checksum for r in rows}.issubset(expected): raise RuntimeError('Outside isolated corpus')
    results=[]
    for row in rows:
        time.sleep(7)
        with engine.begin() as conn:
            chunks=sql(conn,"SELECT id,text FROM chunks WHERE version_id=:id ORDER BY line_number,id",id=row.id).mappings().all()
        for chunk in chunks:
            time.sleep(7)
            try:
                vector=embed(chunk.text,{'org':str(row.organization_id),'version':str(row.id),'document_version_id':str(row.id)})
                with engine.begin() as conn:
                    sql(conn,"UPDATE chunks SET embedding=CAST(:vector AS vector),embedding_model=:model,embedding_dimensions=:dim,embedding_error=NULL WHERE id=:id",id=chunk.id,vector=str(vector),model=os.environ['BEDROCK_EMBEDDING_MODEL'],dim=len(vector))
            except Exception as exc:
                with engine.begin() as conn: sql(conn,"UPDATE chunks SET embedding_error=:error WHERE id=:id",id=chunk.id,error=type(exc).__name__)
                raise
        with engine.begin() as conn:
            sql(conn,"UPDATE document_versions SET embedding_status='ready' WHERE id=:id",id=row.id)
        results.append({'version':str(row.id),'filename':row.filename,'chunks':len(chunks)})
        print(json.dumps(results[-1]),flush=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps({'documents':len(rows),'results':results},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__': main()
