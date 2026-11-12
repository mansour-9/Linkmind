import json
from uuid import UUID,uuid4
import pytest
from app.contracts import Citation,validate_citations
from app.db import engine,sql
from app.providers import record
from test_m2 import call,upload,wait

def test_invalid_citation_ids_spans_and_missing_evidence():
    for citations in [[],[Citation(passage_id="missing",quote="real text")],
                      [Citation(passage_id="p",quote="fabrication")]]:
        with pytest.raises(ValueError): validate_citations(citations,{"p":"real text"})
    validate_citations([Citation(passage_id="p",quote="real")],{"p":"real text"})

def test_usage_survives_failed_knowledge_transaction():
    import time
    org=UUID("00000000-0000-4000-8000-000000000001")
    model="test-"+str(uuid4())
    with pytest.raises(RuntimeError):
        with engine.begin() as conn:
            sql(conn,"INSERT INTO canonical_entities(id,organization_id,kind) VALUES(:id,:org,'project')",id=uuid4(),org=org)
            record({"org":org},"independent_accounting_test",model,time.monotonic(),{},"InjectedFailure")
            raise RuntimeError("Rollback knowledge")
    with engine.begin() as conn:
        row=sql(conn,"SELECT * FROM ai_usage WHERE model=:model",model=model).mappings().one()
        assert row.status=="failed"
        assert row.input_tokens is None and row.output_tokens is None and row.estimated_cost is None
        sql(conn,"DELETE FROM ai_usage WHERE id=:id",id=row.id)

def test_access_change_invalidates_all_derived_surfaces_and_saved_chat():
    job=upload("cedar-charter")
    try:
        wait(job)
        _,pages=call("/wiki","demo-omar")
        page=next(p for p in pages if any(c["version_id"]==job["version_id"]
           for c in call("/wiki/"+p["id"],"demo-omar")[1]["claims"]))
        _,conversation=call("/conversations","demo-omar",body={"title":"Revocation test","document_ids":[job["document_id"]]})
        status,response=call("/conversations/"+conversation["id"]+"/answers","demo-omar",body={"question":"Who owns CB-CEDAR?"})
        assert status==200 and response["statements"]
        assert call("/documents/"+job["document_id"]+"/access",body={"visibility":"private"},method="PATCH")[0]==200
        assert call("/jobs/"+job["id"],"demo-omar")[0]==404
        assert call("/documents/"+job["version_id"]+"/download","demo-omar")[0]==404
        assert all(p["document_id"]!=job["document_id"] for p in call("/search?q=CB-CEDAR","demo-omar")[1])
        detail=call("/wiki/"+page["id"],"demo-omar")
        assert detail[0]==404 or all(c["version_id"]!=job["version_id"] for c in detail[1]["claims"])
        history=call("/conversations/"+conversation["id"],"demo-omar")[1]
        assert history["turns"][-1]["suppressed"] and history["turns"][-1]["response"] is None
        private_chunks={p["id"] for p in response["evidence"]}
        graph=call("/graph","demo-omar")[1]
        assert all(e["chunk_id"] not in private_chunks for e in graph["edges"])
        assert call("/evidence/"+next(iter(private_chunks)),"demo-omar")[0]==404
        # Source owner retains evidence and can see the same records.
        assert call("/evidence/"+next(iter(private_chunks)))[0]==200
    finally:
        call("/documents/"+job["document_id"],method="DELETE")

def test_conflict_review_requires_role_and_detects_stale_revision():
    jobs=[upload("alpha-charter"),upload("alpha-review")]
    try:
        for job in jobs: wait(job)
        _,conflicts=call("/conflicts")
        conflict=next(c for c in conflicts if c["predicate"]=="owner" and {c["left_value"],c["right_value"]}=={"Amal","Omar"})
        body=dict(status="needs_evidence",rationale="Sources genuinely disagree; request the project owner's confirmation.",
                  expected_updated_at=conflict["updated_at"])
        assert call("/conflicts/"+conflict["id"]+"/review","demo-omar",body=body)[0]==403
        assert call("/conflicts/"+conflict["id"]+"/review",body=body)[0]==200
        assert call("/conflicts/"+conflict["id"]+"/review",body=body)[0]==409
        _,history=call("/conflicts/"+conflict["id"]+"/history")
        assert history and history[-1]["action"]=="needs_evidence"
        assert call("/conflicts/"+conflict["id"]+"/history","demo-nour")[0]==404
    finally:
        for job in jobs: call("/documents/"+job["document_id"],method="DELETE")
