"""Retry interrupted jobs in the isolated preview, without replaying test answers."""
import json
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from app.company_demo import MANIFEST
from app.db import engine,sql
from app.main import JOB_QUERY
from app.retrieval import ACCESS

with engine.connect() as conn:
    rows=sql(conn,"SELECT j.id,j.version_id,j.organization_id FROM processing_jobs j JOIN document_versions v ON v.id=j.version_id WHERE j.status='queued'").mappings().all()
for row in rows:
    with engine.connect() as conn:
        if not sql(conn,"SELECT 1 FROM document_versions WHERE id=:id AND checksum=ANY(:checksums)",id=row.version_id,checksums=[f['sha256'] for f in MANIFEST['fixtures']]).scalar(): continue
    req=Request('http://api:8000/api/v1/jobs/'+str(row.id)+'/retry',data=b'',method='POST',headers={'Authorization':'Bearer demo-amal','X-Preview-Proxy':'northstar-local-preview-2026-11-12'})
    try:
        with urlopen(req,timeout=30) as response: print(json.dumps({'job':str(row.id),'status':response.status}),flush=True)
    except HTTPError as response: print(json.dumps({'job':str(row.id),'status':response.code,'body':response.read().decode()}),flush=True)
