"""One bounded fictional RF3 acceptance run against the ORIGINAL shared ledger."""
import argparse
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from unittest.mock import patch

from fastapi.security import HTTPAuthorizationCredentials
from app import main, providers, inference_budget
from app.db import engine, sql


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise RuntimeError('A started report cannot be repeated automatically.')
    if (not providers.configured() or not os.getenv('BEDROCK_BUDGET_DATABASE_URL')
            or os.getenv('BEDROCK_BUDGET_RUN') != 'northstar-sonnet-2026-11-12'):
        raise RuntimeError('Real RF3 requires the original shared spend guard.')
    before = inference_budget.status()
    if before['paused'] or before['limit_usd'] != Decimal('10'):
        raise RuntimeError('The original unpaused USD 10 guard is required.')
    docs = json.loads(args.sources.read_text(encoding='utf-8'))['documents']
    keys = ('roles', 'arabic', 'policy', 'decision', 'disagreement', 'long_roles', 'history')
    ids = [UUID(docs[key]) for key in keys]
    viewer = main.authenticate(HTTPAuthorizationCredentials(scheme='Bearer', credentials='demo-amal'))
    started = time.monotonic()
    reservations = []
    bound = Decimal('0')
    counts = {'embedding': 0, 'sonnet': 0}
    report = dict(status='started', budget_before=before, sources={k: docs[k] for k in keys},
                  maximum_additional_usd='1.50', max_sonnet_calls=24, max_embedding_calls=80,
                  max_seconds=900, questions=[], indexed_passages=0)

    def save():
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + '\n', encoding='utf-8')

    original_reserve = providers.reserve

    def bounded_reserve(model, operation, request, max_output):
        nonlocal bound
        if time.monotonic() - started >= 900:
            raise inference_budget.BudgetStopped('RF3 trial reached its 15 minute bound.')
        if operation not in {'embedding', 'answer', 'answer_verification', 'query_understanding', 'conversation_verification'}:
            raise inference_budget.BudgetStopped('RF3 forbids extraction or other operations.')
        kind = 'embedding' if operation == 'embedding' else 'sonnet'
        if counts[kind] >= (80 if kind == 'embedding' else 24):
            raise inference_budget.BudgetStopped('RF3 reached its call bound.')
        pricing = inference_budget.rates(model)
        incoming = len(json.dumps(request, ensure_ascii=False, default=str).encode()) + 8192
        projected = (incoming * pricing['input'] + max_output * pricing['output']) / 1_000_000
        if bound + projected > Decimal('1.50'):
            raise inference_budget.BudgetStopped('RF3 reached its conservative USD 1.50 dispatch bound.')
        reservation = original_reserve(model, operation, request, max_output)
        if reservation is None:
            raise inference_budget.BudgetStopped('An unguarded RF3 dispatch is forbidden.')
        reservations.append(reservation)
        counts[kind] += 1
        bound += reservation['cost']
        report.update(reserved_call_ids=[str(r['id']) for r in reservations],
                      conservative_reservation_bound_usd=bound, calls_by_kind=counts.copy())
        save()
        return reservation

    def ensure_guard():
        current = inference_budget.status()
        if current['paused'] or current['reserved_usd'] != before['reserved_usd']:
            raise inference_budget.BudgetStopped('RF3 stopped after unknown/concurrent usage; reservations remain preserved.')

    save()
    try:
        with patch.object(providers, 'reserve', bounded_reserve):
            # All seven sources and the history source's previous revision are
            # fictional, explicitly selected, source-only and already published.
            with engine.connect() as conn:
                rows = sql(conn, '''SELECT k.id,k.text,k.version_id,k.embedding_model,k.embedding_dimensions,
                    k.embedding IS NOT NULL AS has_embedding,k.embedding_error
                    FROM chunks k JOIN document_versions v ON v.id=k.version_id
                    JOIN documents d ON d.id=v.document_id
                    WHERE d.id=ANY(:ids) AND d.organization_id=:org AND d.owner_id=:owner
                      AND d.deleted_at IS NULL AND v.source_version_id IS NULL
                    ORDER BY d.id,v.created_at,k.line_number,k.id''', ids=ids,
                           org=viewer.organization_id, owner=viewer.id).mappings().all()
                enriched = sql(conn, '''SELECT count(*) FROM entities e JOIN document_versions v ON v.id=e.version_id
                    WHERE v.document_id=ANY(:ids)''', ids=ids).scalar_one()
            if enriched or not rows or len(rows) > 72:
                raise RuntimeError('RF3 source-only indexing scope did not match its reviewed bound.')
            model = os.environ['BEDROCK_EMBEDDING_MODEL']
            dimension = int(os.environ['BEDROCK_EMBEDDING_DIMENSIONS'])
            for row in rows:
                if (row.has_embedding and row.embedding_model == model
                        and row.embedding_dimensions == dimension and not row.embedding_error):
                    continue
                vector = providers.embed(row.text, dict(org=viewer.organization_id, user=viewer.id, version=row.version_id))
                ensure_guard()
                with engine.begin() as conn:
                    changed = sql(conn, '''UPDATE chunks SET embedding=CAST(:vector AS vector),embedding_model=:model,
                        embedding_dimensions=:dimensions,embedding_error=NULL WHERE id=:id AND version_id=:version
                        AND text=:text RETURNING id''', vector=json.dumps(vector), model=model, dimensions=dimension,
                                  id=row.id, version=row.version_id, text=row.text).scalar_one_or_none()
                    if changed is None:
                        raise RuntimeError('A source passage changed while indexing.')
                report['indexed_passages'] += 1
                save()
            with engine.begin() as conn:
                sql(conn, '''UPDATE document_versions v SET embedding_status='ready' WHERE v.document_id=ANY(:ids)
                    AND v.source_version_id IS NULL AND NOT EXISTS(SELECT 1 FROM chunks k WHERE k.version_id=v.id
                    AND (k.embedding IS NULL OR k.embedding_model IS DISTINCT FROM :model
                    OR k.embedding_dimensions IS DISTINCT FROM :dimensions OR k.embedding_error IS NOT NULL))''',
                    ids=ids, model=model, dimensions=dimension)
            cases = [
                ('roles-ar', ['long_roles'], 'مين الأشخاص ومسؤولياتهم في المشروع؟'),
                ('ambiguous-followup', None, 'What will he do?'),
                ('policy-en-over-arabic', ['arabic'], 'Who reviews remote work requests, and when must employees submit them?'),
                ('approved-and-draft', ['decision', 'disagreement'], 'Compare the pilot dates and distinguish the approved decision from the unapproved draft. Why did the approved date change?'),
                ('history-ar', ['history'], 'قارن النسخة السابقة بالحالية: من مسؤول الإصدار وما تاريخ نقطة الإصدار في كل نسخة؟'),
                ('source-summary', ['roles'], 'Summarize this document in three sentences.'),
                ('missing-evidence', ['policy'], 'What is the approved annual budget in Saudi riyals?'),
                ('stored-only-status', ['decision'], 'What is the latest pilot date right now?'),
            ]
            previous = None
            for key, selected, question in cases:
                ensure_guard()
                if selected is not None:
                    previous = main.create_conversation(main.NewConversation(title='RF3 AI: ' + key,
                        document_ids=[UUID(docs[k]) for k in selected]), viewer)['id']
                item = dict(id=key, question=question, conversation_id=previous, status='started')
                report['questions'].append(item)
                save()
                question_started = time.monotonic()
                result = main.ask(previous, main.Question(question=question), viewer)
                item.update(status='completed', answer=result, latency_seconds=round(time.monotonic()-question_started, 3))
                passages = {p['id']: p['text'] for p in result['evidence']}
                item['exact_citations'] = all(c['passage_id'] in passages and c['quote'] in passages[c['passage_id']]
                    for s in result['statements'] for c in s['evidence'])
                ensure_guard()
                save()
                print(json.dumps(dict(case=key, statements=len(result['statements']),
                    outcome=result.get('answer_state'), clarification=result.get('clarification', False),
                    exact_citations=item['exact_citations'], latency_seconds=item['latency_seconds'])), flush=True)
        report['status'] = 'completed_pending_answer_review'
    except Exception as exc:
        report['status'] = 'stopped'
        report['error'] = dict(type=type(exc).__name__, detail=str(exc)[:800])
    finally:
        report['latency_seconds'] = round(time.monotonic() - started, 3)
        report['budget_after'] = inference_budget.status()
        with inference_budget.ledger_engine().connect() as conn:
            report['calls'] = [dict(r) for r in sql(conn, '''SELECT id,operation,status,actual_usd,reserved_usd
                FROM inference_budget_calls WHERE id=ANY(:ids) ORDER BY created_at,id''',
                ids=[r['id'] for r in reservations]).mappings()] if reservations else []
        report['actual_test_cost_usd'] = sum((r['actual_usd'] for r in report['calls'] if r['actual_usd'] is not None), Decimal('0'))
        report['all_usage_settled'] = all(r['status'] == 'settled' for r in report['calls'])
        save()
        print(json.dumps({k: report[k] for k in ('status', 'indexed_passages', 'latency_seconds',
            'actual_test_cost_usd', 'all_usage_settled')}, default=str), flush=True)
    return 0 if report['status'] == 'completed_pending_answer_review' else 1


if __name__ == '__main__':
    raise SystemExit(run())
