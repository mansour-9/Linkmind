"""Explicitly approved Lantern acceptance in an empty isolated database.

Use the existing shared ledger directly; never seed/copy/reset a budget. Raw model
responses and source-bearing reports must be written to an ignored local directory.
No worker may run against the acceptance database during this single-process test.
"""
import argparse
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import boto3
from sqlalchemy import create_engine

from app import main, processing, providers, retrieval, inference_budget as budget
from app.contracts import validate_extraction
from app.db import engine, sql
from app.parsers import parse_document

RUN = "northstar-sonnet-2026-11-12"
MODEL = "us.anthropic.claude-sonnet-4-6"
CAP = Decimal("1.50")
ORG = UUID("00000000-0000-4000-8000-000000000001")
USER = UUID("00000000-0000-4000-8000-000000000101")
QUESTIONS = [
    "What is Project Lantern?",
    "Who are the key people working on Project Lantern?",
    "Who is responsible for support training?",
    "What is the latest approved budget?",
    "Why was the launch date changed?",
    "Are there conflicting sources about the shipment delay rule?",
    "Which documents support these decisions?",
    "What relationships exist between the project, people, tasks, and decisions?",
]


def viewer():
    return main.Viewer(id=USER, organization_id=ORG, name="Acceptance",
        organization="Isolated", role="admin")


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def run(sources, report_path, resume=False):
    if os.getenv("LANTERN_PAID_APPROVED") != "1":
        raise RuntimeError("Explicit paid acceptance authorization is required.")
    if os.getenv("BEDROCK_BUDGET_RUN") != RUN or os.getenv("BEDROCK_BUDGET_USD") != "10":
        raise RuntimeError("Use the unchanged existing USD 10 run.")
    if not providers.configured() or any(os.getenv(k) != MODEL for k in
            ("BEDROCK_EXTRACTION_MODEL", "BEDROCK_ANSWER_MODEL")):
        raise RuntimeError("Only the existing Sonnet configuration is authorized.")
    if os.getenv("BEDROCK_EMBEDDING_MODEL"):
        raise RuntimeError("This focused run excludes new embeddings.")
    if report_path.exists() and not resume:
        raise RuntimeError("Refusing to repeat an existing acceptance run.")
    previous = json.loads(report_path.read_text(encoding="utf-8")) if resume else None
    if resume and previous.get("status") != "stopped":
        raise RuntimeError("Only an explicitly stopped acceptance run can resume.")
    with engine.connect() as conn:
        document_count = sql(conn, "SELECT count(*) FROM documents").scalar_one()
        if not resume and document_count:
            raise RuntimeError("Acceptance requires a fresh empty isolated database.")
        if resume and (document_count != 4 or len(previous["jobs"]) != 4):
            raise RuntimeError("Resumption requires the same four isolated sources.")
    ledger = create_engine(os.environ["LANTERN_SHARED_LEDGER_URL"])
    if ledger.url == engine.url:
        raise RuntimeError("The application and shared ledger databases must be distinct.")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = report_path.parent / "raw"
    raw_dir.mkdir(exist_ok=resume)
    report = previous or dict(status="preflight", jobs=[], questions=[], calls=[], first_batch_validated=False)
    report["status"] = "running"
    report.pop("error", None)
    for job in report["jobs"]:
        for key in ("job_id", "document_id", "version_id"):
            job[key] = UUID(str(job[key]))
    original_reserve, original_settle, original_verified = providers.reserve, providers.settle, providers._extract_verified
    original_runtime = providers.runtime
    original_batches = providers.extract_bedrock_batches
    report['acceptance_batch_bounds'] = dict(max_passages=3, max_source_characters=3000)
    owned = [UUID(str(call["id"])) for call in report["calls"]]
    before = None

    def existing_status():
        with ledger.connect() as conn:
            row = sql(conn, "SELECT id,limit_usd,spent_usd,reserved_usd,paused FROM inference_budget_runs WHERE id=:id", id=RUN).mappings().first()
        if row is None:
            raise budget.BudgetStopped("The existing shared ledger row is required; creation is forbidden.")
        return dict(row)

    def guarded_reserve(model, operation, request, max_output):
        if model != MODEL or len(owned) >= 144:
            raise budget.BudgetStopped("Acceptance model/call limit reached.")
        current = existing_status()
        if not current or current["paused"] or Decimal(str(current["limit_usd"])) != 10:
            raise budget.BudgetStopped("Shared ledger missing, changed, or paused.")
        with ledger.connect() as conn:
            calls = [dict(sql(conn, "SELECT status,actual_usd,reserved_usd FROM inference_budget_calls WHERE id=:id",
                id=id).mappings().one()) for id in owned]
        if any(c["status"] != "settled" for c in calls):
            raise budget.BudgetStopped("An acceptance call has uncertain or unsettled usage.")
        spent = sum((c["actual_usd"] for c in calls), Decimal(0))
        rates = budget.rates(model)
        bound = len(json.dumps(request, ensure_ascii=False, default=str).encode("utf-8")) + 8192
        cost = (bound * rates["input"] + max_output * rates["output"]) / 1_000_000
        if spent + cost > CAP:
            raise budget.BudgetStopped("Next reservation exceeds the additional USD 1.50 authorization.")
        reservation = original_reserve(model, operation, request, max_output)
        if reservation is None:
            raise RuntimeError("The existing shared ledger is required before dispatch.")
        owned.append(reservation["id"])
        report["calls"].append(dict(id=reservation["id"], operation=operation, reserved_usd=reservation["cost"]))
        write(report_path, report)
        return reservation

    def guarded_settle(reservation, response, error):
        original_settle(reservation, response, error)
        # Original settlement retains uncertain reservations and pauses the shared run.
        write(report_path, report)

    class RecordingRuntime:
        def converse(self, **request):
            response = original_runtime().converse(**request)
            write(raw_dir / f"{len(owned):03d}-response.json", response)
            return response

    def verified(passages, scope, payload, repair_allowed, **kwargs):
        result = original_verified(passages, scope, payload, repair_allowed, **kwargs)
        validate_extraction(result, passages)
        report["first_batch_validated"] = True
        write(raw_dir / f"{len(owned):03d}-validated.json", result.model_dump())
        write(report_path, report)
        return result

    with patch.object(budget, "engine", ledger), patch.object(providers, "reserve", guarded_reserve), \
            patch.object(providers, "settle", guarded_settle), patch.object(providers, "runtime", lambda: RecordingRuntime()), \
            patch.object(providers, "_extract_verified", verified), \
            patch.object(processing, "extract_bedrock_batches", lambda passages, scope:
                original_batches(passages, scope, max_characters=3000)):
        try:
            before = existing_status()
            if not before or before["paused"] or Decimal(str(before["limit_usd"])) != 10:
                raise RuntimeError("The persistent ledger is missing, changed, or paused.")
            if before["spent_usd"] + before["reserved_usd"] + CAP > before["limit_usd"]:
                raise RuntimeError("Insufficient confirmed ledger headroom.")
            report.setdefault("budget_before", before)
            boto3.Session().client("sts", region_name=os.getenv("AWS_REGION", "us-east-1")).get_caller_identity()
            manifest = json.loads((sources / "manifest.json").read_text(encoding="utf-8"))
            if len(manifest["files"]) != 4:
                raise RuntimeError("Exactly the four existing Lantern originals are required.")
            for item in manifest["files"]:
                raw = (sources / item["local_filename"]).read_bytes()
                assert hashlib.sha256(raw).hexdigest() == item["sha256"]
                assert len(raw) == item["byte_count"]
                assert len(parse_document(item["filename"], raw)) == item["passages"]
                if resume:
                    job = next(j for j in report["jobs"] if j["filename"] == item["filename"])
                    with engine.connect() as conn:
                        source = sql(conn, """SELECT v.checksum,v.byte_count,d.current_version_id,d.organization_id
                            FROM document_versions v JOIN documents d ON d.id=v.document_id
                            WHERE v.id=:version AND d.id=:document""", version=job["version_id"], document=job["document_id"]).mappings().one()
                    assert source.checksum == item["sha256"] and source.byte_count == item["byte_count"]
                    assert source.current_version_id == job["version_id"] and source.organization_id == ORG
                    continue
                with engine.begin() as conn:
                    did = uuid4()
                    sql(conn, """INSERT INTO documents(id,organization_id,owner_id,filename,visibility)
                        VALUES(:id,:org,:owner,:filename,'team')""", id=did, org=ORG, owner=USER, filename=item["filename"])
                    job = main.add_version(conn, viewer(), did, item["filename"], raw, item["sha256"])
                # Search publication is an independent no-inference gate. Arbitrary
                # PDFs honestly remain unenriched until the real provider succeeds.
                with patch.object(processing, "configured", lambda: False):
                    assert processing.process_one()
                detail = main.job(job["id"], viewer())
                assert detail["search_status"] == "ready" and detail["enrichment_status"] != "ready"
                report["jobs"].append(dict(filename=item["filename"], job_id=job["id"],
                    document_id=did, version_id=job["version_id"]))
            write(report_path, report)
            for job in report["jobs"]:
                if main.job(job["job_id"], viewer())["status"] == "ready":
                    continue
                candidate = main.reprocess(job["job_id"], viewer())["staged_version_id"]
                job["candidate"] = candidate
                assert processing.process_one()
                detail = main.job(job["job_id"], viewer())
                job.update({k: detail[k] for k in ("status", "search_status", "enrichment_status",
                    "entity_count", "claim_count", "relationship_count", "error", "staged_activation_state")})
                write(report_path, report)
                if detail["status"] != "ready":
                    raise RuntimeError("Staged extraction stopped: " + str(detail["error"]))
                assert detail["active_enrichment_version_id"] == candidate
                assert detail["staged_activation_state"] == "live"
            ids = [j["document_id"] for j in report["jobs"]]
            for question in QUESTIONS:
                evidence = retrieval.search(viewer(), question, ids, semantic=False)
                def authorize():
                    with engine.connect() as conn:
                        assert retrieval.dependencies_allowed(conn, viewer(), [p["id"] for p in evidence])
                answer = providers.answer(question, evidence, dict(org=ORG, user=USER), authorize=authorize)
                mapping = {p["id"]: p["text"] for p in evidence}
                for statement in answer.statements:
                    for citation in statement.evidence:
                        assert citation.quote in mapping[citation.passage_id]
                        assert main.evidence(UUID(citation.passage_id), viewer())["quote"] == mapping[citation.passage_id]
                report["questions"].append(dict(question=question, answer=answer.model_dump(),
                    retrieved_documents=sorted({p["filename"] for p in evidence}), evidence=evidence))
                write(report_path, report)
            report["status"] = "completed"
        except Exception as exc:
            report["status"] = "stopped"
            report["error"] = dict(type=type(exc).__name__, message=str(exc)[:2000],
                diagnostic=getattr(exc, "diagnostic", None))
            raise
        finally:
            with engine.connect() as conn:
                report["usage"] = [dict(r) for r in sql(conn, """SELECT operation,stop_reason,status,error_code,
                    input_tokens,output_tokens,estimated_cost,diagnostic FROM ai_usage ORDER BY created_at""").mappings()]
                report["knowledge"] = {table: sql(conn, f"SELECT count(*) FROM {table}").scalar_one()
                    for table in ("live_entities", "live_claims", "live_relationships", "conflicts")}
                report["all_sources_search_ready"] = sql(conn, "SELECT count(*) FROM document_versions WHERE source_version_id IS NULL AND search_ready_at IS NOT NULL").scalar_one() == 4
            after = existing_status()
            report["budget_after"] = after
            with ledger.connect() as conn:
                calls = [dict(sql(conn, "SELECT status,actual_usd,reserved_usd FROM inference_budget_calls WHERE id=:id",
                    id=id).mappings().one()) for id in owned]
            report["additional_spent"] = str(sum((c["actual_usd"] or Decimal(0) for c in calls), Decimal(0)))
            report["additional_reserved"] = str(sum((c["reserved_usd"] for c in calls if c["status"] != "settled"), Decimal(0)))
            report["paid_calls"] = len(owned)
            write(report_path, report)
            print(json.dumps({k: report.get(k) for k in ("status", "paid_calls", "additional_spent", "additional_reserved",
                "first_batch_validated", "knowledge", "all_sources_search_ready", "budget_after")}, default=str), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--resume", action="store_true", help="Continue the same stopped isolated run and cumulative cost cap.")
    args = parser.parse_args()
    run(args.sources, args.report, args.resume)
