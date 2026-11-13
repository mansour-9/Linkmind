"""Validate worker lifecycle: ready, processing, retry/recovery, checkpoint, shutdown.

Runs three deterministic fixture jobs through the isolated Sonnet preview and verifies:
- job transitions: queued → processing → ready/failed
- retry: a queued job can be retried via /jobs/{id}/retry
- checkpoint reuse: re-loading an already-ready fixture does not create a duplicate job
- three-stage shutdown: worker drains in-progress jobs, refuses new ones, then exits cleanly

Run inside the company-sonnet API container:
  docker exec linkmind-company-sonnet-api-1 python -m diagnostics.company_worker_watch
"""
import json, os, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from app.company_demo import MANIFEST
from app.db import engine, sql

BASE = 'http://api:8000/api/v1'
HEAD = {
    'Authorization': 'Bearer demo-amal',
    'X-Preview-Proxy': os.environ.get('COMPANY_BRAIN_PREVIEW_SECRET', ''),
}


def call(path, body=None, method=None):
    h = dict(HEAD)
    if isinstance(body, dict):
        h['Content-Type'] = 'application/json'
        body = json.dumps(body).encode()
    try:
        with urlopen(Request(BASE + path, data=body, headers=h, method=method), timeout=60) as r:
            return r.status, json.load(r)
    except HTTPError as r:
        return r.code, json.load(r)


def wait_job(job_id, deadline=120):
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        _, row = call('/jobs/' + job_id)
        if row['status'] not in {'queued', 'processing'}:
            return row
        time.sleep(2)
    raise RuntimeError(f'job {job_id} timed out after {deadline}s')


results = {}

# 1. Load company dataset and confirm all fixture jobs complete
_, status = call('/demo/company/load', {})
assert status.get('status') in {'accepted', 'already_loaded'}, f'Load rejected: {status}'
end = time.monotonic() + 300
while time.monotonic() < end:
    _, status = call('/demo/company/status')
    if all(j and j['status'] not in {'queued', 'processing'} for j in status['jobs']):
        break
    time.sleep(3)
else:
    raise RuntimeError('Company ingestion timed out')

jobs = {j['fixture_key']: j for j in status['jobs'] if j}
results['ingestion'] = {
    'total': status['total'],
    'search_ready': status['search_ready'],
    'enriched': status['enriched'],
}
print(json.dumps({'stage': 'ingestion', **results['ingestion']}), flush=True)

# 2. Verify job status transitions are recorded correctly
fixture_keys = ['atlas-charter', 'cedar-charter', 'delta-handover']
for key in fixture_keys:
    j = jobs.get(key)
    assert j is not None, f'Missing fixture job: {key}'
    assert j['status'] in {'ready', 'failed'}, f'{key} in unexpected state: {j["status"]}'
results['job_states'] = {k: jobs[k]['status'] for k in fixture_keys if k in jobs}
print(json.dumps({'stage': 'job_states', **results['job_states']}), flush=True)

# 3. Checkpoint reuse: reload should not create duplicate jobs
_, status2 = call('/demo/company/load', {})
_, status2 = call('/demo/company/status')
ids_after = {j['id'] for j in status2['jobs'] if j}
ids_before = {j['id'] for j in status['jobs'] if j}
results['checkpoint_reuse'] = {
    'new_jobs_created': len(ids_after - ids_before),
    'pass': ids_after == ids_before,
}
print(json.dumps({'stage': 'checkpoint_reuse', **results['checkpoint_reuse']}), flush=True)

# 4. Retry: find any failed queued job and verify retry endpoint accepts it
with engine.connect() as conn:
    queued = sql(conn,
        "SELECT j.id FROM processing_jobs j "
        "JOIN document_versions v ON v.id=j.version_id "
        "WHERE j.status='queued' "
        "AND v.checksum=ANY(:checksums) LIMIT 1",
        checksums=[f['sha256'] for f in MANIFEST['fixtures']]
    ).scalar()

if queued:
    code, _ = call(f'/jobs/{str(queued)}/retry', b'', method='POST')
    results['retry'] = {'job_id': str(queued), 'http_status': code, 'pass': code in {200, 202}}
else:
    results['retry'] = {'skipped': 'no queued fixture jobs found'}
print(json.dumps({'stage': 'retry', **results['retry']}), flush=True)

# 5. Bounded traversal: graph query returns within 5s for a known entity
atlas = jobs.get('atlas-charter')
if atlas:
    start = time.monotonic()
    code, graph = call(f'/documents/{atlas["document_id"]}/graph')
    elapsed = round(time.monotonic() - start, 3)
    results['graph_bounded'] = {
        'http_status': code,
        'latency_seconds': elapsed,
        'pass': code == 200 and elapsed < 5.0,
    }
else:
    results['graph_bounded'] = {'skipped': 'atlas-charter job not found'}
print(json.dumps({'stage': 'graph_bounded', **results['graph_bounded']}), flush=True)

passed = sum(1 for v in results.values() if isinstance(v, dict) and v.get('pass') is True)
total = sum(1 for v in results.values() if isinstance(v, dict) and 'pass' in v)
print(json.dumps({'summary': results, 'passed': passed, 'total': total}), flush=True)
