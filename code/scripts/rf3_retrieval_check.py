"""Deterministic evidence-coverage comparison. Refuses configured real inference."""
import argparse
import json
import time
from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from app import main, processing, providers


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if providers.configured() or args.report.exists():
        raise RuntimeError('Use only the isolated mock project and a new evidence report.')
    corpus = json.loads(args.corpus.read_text(encoding='utf-8'))
    viewer = main.authenticate(HTTPAuthorizationCredentials(scheme='Bearer', credentials='demo-amal'))
    docs = {}
    def wait(job):
        for _ in range(100):
            current = main.job(job['id'], viewer)
            if current['search_status'] == 'ready':
                return
            processing.process_one()
            time.sleep(0.02)
        raise RuntimeError('Fixture did not become search ready.')
    for item in corpus['documents']:
        text = item.get('text')
        if text is None:
            text = '\n'.join(item['role_lines'].get(str(i), f'Project Harbor log section {i}: routine shipment status review and document notes.')
                for i in range(1, item['generated_sections'] + 1))
        job = main.upload(viewer, UploadFile(BytesIO(text.encode()), filename=item['filename']), item.get('visibility', 'team'))
        wait(job)
        docs[item['key']] = str(job['document_id'])
        if item.get('revision_text'):
            current = main.document_metadata(job['document_id'], viewer)
            # Preserve the earlier version across repeated baseline/final comparisons.
            from app.db import engine, sql
            with engine.connect() as conn:
                count = sql(conn, 'SELECT count(*) FROM document_versions WHERE document_id=:id AND source_version_id IS NULL', id=job['document_id']).scalar()
            if count == 1:
                revised = main.revision(job['document_id'], viewer, UploadFile(BytesIO(item['revision_text'].encode()), filename=item['filename']))
                wait(revised)
    rows = []
    for split in ('development_questions', 'heldout_questions'):
        for case in corpus[split]:
            conversation = main.create_conversation(main.NewConversation(title='RF3 check: ' + case['id'], document_ids=[UUID(docs[k]) for k in case['sources']]), viewer)
            started = time.monotonic()
            result = main.ask(conversation['id'], main.Question(question=case['question']), viewer)
            text = '\n'.join(p['text'] for p in result['evidence'])
            hits = [fragment in text for fragment in case['expected']]
            passed = all(hits) and (not case.get('must_abstain') or not result['statements'])
            rows.append(dict(id=case['id'], split=split, expected_fragments=len(hits), retrieved_fragments=sum(hits),
                passed=passed, passages=len(result['evidence']), context_characters=sum(len(p['text']) for p in result['evidence']),
                latency_seconds=round(time.monotonic() - started, 3), outcome=result.get('answer_state'),
                activity=result.get('retrieval_activity', [])))
    report = dict(provider='mock', purpose='Evidence retrieval only; not generated-answer acceptance',
        passed=sum(r['passed'] for r in rows), total=len(rows), results=rows, documents=docs)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('provider', 'purpose', 'passed', 'total')}))


if __name__ == '__main__':
    run()
