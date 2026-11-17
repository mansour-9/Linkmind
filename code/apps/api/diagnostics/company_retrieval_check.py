"""Per-question answer, citation, literal-value, permission, and abstention checks.

Runs all 15 manifest questions against the isolated Sonnet preview without replaying
already-recorded results. Reports pass/fail per question and an exit code summary.

Run inside the company-sonnet API container:
  docker exec linkmind-company-sonnet-api-1 python -m diagnostics.company_retrieval_check
"""
import json, os, sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from app.company_demo import MANIFEST
from app.db import engine, sql

BASE = 'http://api:8000/api/v1'
_AMAL = {'Authorization': 'Bearer demo-amal', 'X-Preview-Proxy': os.environ.get('COMPANY_BRAIN_PREVIEW_SECRET', '')}
_OMAR = {'Authorization': 'Bearer demo-omar', 'X-Preview-Proxy': os.environ.get('COMPANY_BRAIN_PREVIEW_SECRET', '')}
_NOUR = {'Authorization': 'Bearer demo-nour', 'X-Preview-Proxy': os.environ.get('COMPANY_BRAIN_PREVIEW_SECRET', '')}


def call(path, body=None, headers=None):
    h = dict(headers or _AMAL)
    if isinstance(body, dict):
        h['Content-Type'] = 'application/json'
        body = json.dumps(body).encode()
    try:
        with urlopen(Request(BASE + path, data=body, headers=h), timeout=240) as r:
            return r.status, json.load(r)
    except HTTPError as r:
        return r.code, json.load(r)


# Load company status to get document IDs
_, status = call('/demo/company/status')
jobs = {j['fixture_key']: j for j in status['jobs'] if j}

results = []
for idx, item in enumerate(MANIFEST['questions'], 1):
    mode = item.get('mode', 'normal')
    expected = item['expected']
    source_ids = [jobs[k]['document_id'] for k in item['sources'] if k in jobs]

    if not source_ids:
        results.append({'number': idx, 'question': item['question'], 'pass': False,
                        'error': 'source documents not found'})
        continue

    # Retrieval check: semantic search should return relevant passages
    _, rows = call('/search?q=' + item['question'].replace(' ', '+') + '&document_ids=' +
                   ','.join(source_ids))
    retrieved = len(rows) if isinstance(rows, list) else rows.get('results', [])

    # Ask the question
    code, conv = call('/conversations', {'document_ids': source_ids})
    if code != 201:
        results.append({'number': idx, 'question': item['question'], 'pass': False,
                        'error': f'conversation creation failed: {code}'})
        continue

    code, response = call(f'/conversations/{conv["id"]}/answers', {'question': item['question']})
    row = {
        'number': idx,
        'question': item['question'],
        'mode': mode,
        'expected': expected,
        'http_status': code,
        'retrieved': len(retrieved) if isinstance(retrieved, list) else 0,
    }

    if code == 200:
        texts = ' '.join(s['text'] for s in response.get('statements', []))
        row['has_supported_output'] = bool(response.get('statements'))
        # Verify all citations are exact substring quotes from their passage
        row['exact_source_quotes'] = all(
            c['quote'] in next(
                (p['text'] for p in response.get('evidence', []) if p['id'] == c['passage_id']), ''
            )
            for s in response.get('statements', [])
            for c in s.get('evidence', [])
        )

        if mode == 'missing-evidence':
            row['expected_abstention'] = response.get('insufficient_evidence', False)
            row['pass'] = row['expected_abstention']

        elif mode == 'permissions':
            # Amal can read; Omar (same org, no access to private) cannot
            row['expected_literal_present'] = expected.split(';')[0].casefold() in texts.casefold()
            omar_code, _ = call('/conversations', {'document_ids': source_ids}, headers=_OMAR)
            row['omar_denied'] = omar_code == 404
            nour_code, _ = call('/conversations', {'document_ids': source_ids}, headers=_NOUR)
            row['nour_denied'] = nour_code == 404
            row['pass'] = (row['has_supported_output'] and row['exact_source_quotes']
                           and row['omar_denied'] and row['nour_denied'])

        elif mode == 'selected-document':
            row['has_supported_output'] = row['has_supported_output']
            row['exact_source_quotes'] = row['exact_source_quotes']
            row['pass'] = row['has_supported_output'] and row['exact_source_quotes']

        elif mode == 'revision':
            # Revision answers are validated in company_revision_check.py
            row['pass'] = None  # deferred

        else:  # normal
            row['expected_literal_present'] = expected.casefold() in texts.casefold()
            row['pass'] = (row['has_supported_output'] and row['exact_source_quotes']
                           and row['expected_literal_present'])
    else:
        row['pass'] = False
        row['error'] = f'http {code}'

    results.append(row)
    status_str = 'PASS' if row['pass'] is True else ('SKIP' if row['pass'] is None else 'FAIL')
    print(json.dumps({'Q': idx, 'status': status_str, 'pass': row['pass'],
                      'supported': row.get('has_supported_output'),
                      'literal': row.get('expected_literal_present')}), flush=True)

passed = sum(1 for r in results if r.get('pass') is True)
failed = sum(1 for r in results if r.get('pass') is False)
skipped = sum(1 for r in results if r.get('pass') is None)
print(json.dumps({'summary': {'passed': passed, 'failed': failed, 'skipped': skipped,
                               'total': len(results)}}), flush=True)
sys.exit(0 if failed == 0 else 2)
