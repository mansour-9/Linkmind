"""RF1: ordinary source usefulness never requires structured extraction."""
from io import BytesIO
import os
from uuid import UUID

import pytest
from fastapi import HTTPException, UploadFile

from app import main, processing, retrieval, conflict_detection
from app.db import sql
from app.fixture_provider import FIXTURES
from app.contracts import Extraction
from test_search_readiness import workspace, source, viewer, OMAR


def forbidden(*args, **kwargs):
    pytest.fail("Ordinary ingestion must never invoke structured enrichment")


@pytest.mark.parametrize("content", [
    b"OptionalZebra release review is Thursday.\nThe coordinator is Leena.",
    FIXTURES["cloud-migration"].path.read_bytes(),
])
def test_default_upload_is_ready_without_any_extraction_even_for_known_bytes(workspace, monkeypatch, content):
    monkeypatch.setattr(processing, "mock_extract", forbidden)
    monkeypatch.setattr(processing, "extract_bedrock_batches", forbidden)
    monkeypatch.setattr(processing, "canonical", forbidden)
    monkeypatch.setattr(conflict_detection, "assess", forbidden)
    monkeypatch.setattr(processing, "configured", lambda: True)
    # Other suites intentionally enriched Amal's fixture; a new owner's upload must
    # still default off. Existing idempotent uploads correctly preserve their intent.
    job=main.upload(viewer(OMAR), UploadFile(BytesIO(content),filename="optional.md"), "team")
    assert not job["enrichment_requested"]
    assert job["enrichment_status"]=="not_requested"
    assert processing.process_one()
    result=main.job(job["id"], viewer())
    assert result["status"]=="ready" and result["search_status"]=="ready"
    assert result["enrichment_status"]=="not_requested" and result["error"] is None
    assert result["processed_at"] is None and result["can_reprocess"] and not result["can_retry"]
    for table in ("entities", "claims", "relationships"):
        assert sql(workspace,f"SELECT count(*) FROM {table} WHERE version_id=:id",id=result["version_id"]).scalar()==0
    evidence,coverage=retrieval.selected_context(viewer(),[result["document_id"]])
    assert evidence and not coverage["partial"]
    assert all(p["entities"]==[] for p in evidence)
    assert main.evidence(UUID(evidence[0]["id"]),viewer())["quote"]==evidence[0]["text"]
    assert sql(workspace,"SELECT count(*) FROM ai_usage WHERE version_id=:id",id=result["version_id"]).scalar()==0


def test_source_only_history_survives_enrichment_but_not_new_revision_or_revocation(workspace):
    job=source(workspace,FIXTURES["cloud-migration"].path.read_bytes(),enrichment_requested=False)
    assert processing.process_one()
    conversation=main.create_conversation(main.NewConversation(document_ids=[job.document_id]),viewer(OMAR))
    response=main.ask(conversation["id"],main.Question(question="summarize this document"),viewer(OMAR))
    assert response["statements"] and not response.get("enrichment_dependencies")
    before=[p["id"] for p in response["evidence"]]
    queued=main.reprocess(job.id,viewer())
    assert queued["enrichment_requested"] and queued["staged_version_id"]
    assert processing.process_one()
    assert main.job(job.id,viewer())["enrichment_status"]=="ready"
    assert not main.history(conversation["id"],viewer(OMAR))["turns"][0]["suppressed"]
    assert [p["id"] for p in retrieval.selected_context(viewer(),[job.document_id])[0]]==before
    # Overview still uses original text only, even after a graph generation exists.
    main.ask(conversation["id"],main.Question(question="summarize this document"),viewer(OMAR))
    main.reprocess(job.id,viewer())
    assert processing.process_one()
    assert all(not t["suppressed"] for t in main.history(conversation["id"],viewer(OMAR))["turns"])
    main.change_access(job.document_id,main.AccessChange(visibility="private"),viewer())
    assert all(t["suppressed"] for t in main.history(conversation["id"],viewer(OMAR))["turns"])
    main.change_access(job.document_id,main.AccessChange(visibility="team"),viewer())
    revised=main.revision(job.document_id,viewer(),UploadFile(BytesIO(b"CurrentOptionalZebra is the revised text."),filename="revision.md"))
    assert not revised["enrichment_requested"]
    assert processing.process_one()
    assert all(t["suppressed"] for t in main.history(conversation["id"],viewer(OMAR))["turns"])
    assert sql(workspace,"SELECT count(*) FROM live_entities WHERE version_id=:id",id=job.version_id).scalar()>0
    assert sql(workspace,"""SELECT count(*) FROM live_entities e JOIN documents d ON d.current_version_id=e.version_id
        WHERE d.id=:id""",id=job.document_id).scalar()==0
    assert main.evidence(UUID(before[0]),viewer())["quote"]


def test_lexical_search_is_available_before_embedding_and_failure_is_not_enrichment_failure(workspace,monkeypatch):
    job=source(workspace,b"EarlyIndexZebra review is Thursday.",enrichment_requested=False)
    def embedding(text,scope):
        result=main.job(job.id,viewer())
        assert result["search_status"]=="ready" and result["embedding_status"]=="pending"
        assert result["enrichment_status"]=="not_requested"
        assert retrieval.search(viewer(),"EarlyIndexZebra",[job.document_id],semantic=False)
        raise RuntimeError("Injected embedding outage")
    monkeypatch.setattr(processing,"embed",embedding)
    monkeypatch.setattr(processing,"enrich",forbidden)
    assert processing.process_one()
    result=main.job(job.id,viewer())
    assert result["status"]=="ready" and result["error"] is None
    assert result["embedding_status"]=="failed" and result["enrichment_status"]=="not_requested"
    assert retrieval.search(viewer(),"EarlyIndexZebra",[job.document_id],semantic=False)


def test_unchanged_passages_reuse_embeddings_but_changed_model_and_dimensions_do_not(workspace,monkeypatch):
    monkeypatch.setenv("BEDROCK_EMBEDDING_MODEL","rf1-test-model")
    monkeypatch.setenv("BEDROCK_EMBEDDING_DIMENSIONS","3")
    calls=[]
    def embedding(text,scope):
        calls.append(text)
        return [1.0]+[0.0]*(int(os.environ["BEDROCK_EMBEDDING_DIMENSIONS"])-1)
    monkeypatch.setattr(processing,"embed",embedding)
    first=source(workspace,b"SharedIndexZebra unchanged paragraph.\nInitial paragraph.",enrichment_requested=False)
    assert processing.process_one()
    old_ids=set(sql(workspace,"SELECT id FROM chunks WHERE version_id=:id",id=first.version_id).scalars())
    assert len(calls)==2
    revised=source(workspace,b"SharedIndexZebra unchanged paragraph.\nRevised paragraph.",document=first.document_id,enrichment_requested=False)
    assert processing.process_one()
    assert calls==["SharedIndexZebra unchanged paragraph.","Initial paragraph.","Revised paragraph."]
    assert main.job(revised.id,viewer())["embedding_status"]=="ready"
    assert old_ids.isdisjoint(sql(workspace,"SELECT id FROM chunks WHERE version_id=:id",id=revised.version_id).scalars())
    # A different source, even with shared text, cannot borrow private source vectors.
    other=source(workspace,b"SharedIndexZebra unchanged paragraph.\nOther source.",enrichment_requested=False)
    assert processing.process_one() and len(calls)==5
    monkeypatch.setenv("BEDROCK_EMBEDDING_MODEL","rf1-other-model")
    model=source(workspace,b"SharedIndexZebra unchanged paragraph.\nChanged model.",document=first.document_id,enrichment_requested=False)
    assert processing.process_one() and len(calls)==7
    monkeypatch.setenv("BEDROCK_EMBEDDING_DIMENSIONS","2")
    dims=source(workspace,b"SharedIndexZebra unchanged paragraph.\nChanged dimensions.",document=first.document_id,enrichment_requested=False)
    assert processing.process_one() and len(calls)==9


def test_interrupted_index_resumes_without_reembedding_completed_passages(workspace,monkeypatch):
    monkeypatch.setenv("BEDROCK_EMBEDDING_MODEL","rf1-test-model")
    monkeypatch.setenv("BEDROCK_EMBEDDING_DIMENSIONS","2")
    job=source(workspace,b"ResumeIndexZebra first.\nResumeIndexZebra second.",enrichment_requested=False)
    embed_calls=[]
    original=processing.set_stage
    stages=0
    def stage(j,name):
        nonlocal stages
        if name=="embedding":
            stages+=1
            if stages==3:
                raise RuntimeError("Interrupted after first embedded passage")
        return original(j,name)
    monkeypatch.setattr(processing,"set_stage",stage)
    monkeypatch.setattr(processing,"embed",lambda text,scope: embed_calls.append(text) or [1.0,0.0])
    assert processing.process_one()
    assert main.job(job.id,viewer())["status"]=="queued"
    assert len(embed_calls)==1
    monkeypatch.setattr(processing,"set_stage",original)
    sql(workspace,"UPDATE processing_jobs SET available_at=clock_timestamp()-interval '1 day' WHERE id=:id",id=job.id)
    monkeypatch.setattr(processing,"parse_document",forbidden)
    assert processing.process_one()
    assert len(embed_calls)==2
    assert main.job(job.id,viewer())["status"]=="ready"


def test_optional_enrichment_requires_management_and_is_not_inherited_by_revision(workspace):
    job=source(workspace,enrichment_requested=False)
    assert processing.process_one()
    with pytest.raises(HTTPException) as denied:
        main.reprocess(job.id,viewer(OMAR))
    assert denied.value.status_code==403
    revised=main.revision(job.document_id,viewer(),UploadFile(BytesIO(b"AnotherZebra revision."),filename="new.md"))
    assert not revised["enrichment_requested"]
    assert processing.process_one()
    main.delete(job.document_id,viewer())
    with pytest.raises(HTTPException) as deleted:
        main.job(revised["id"],viewer())
    assert deleted.value.status_code==404


@pytest.mark.parametrize("extension",["pdf","docx"])
def test_readable_document_formats_use_the_same_source_only_path(workspace,monkeypatch,extension):
    text="FormatOptionalZebra confirms a Thursday review."
    if extension=="pdf":
        from test_pdf import text_pdf
        content=text_pdf(text)
    else:
        from docx import Document
        doc=Document()
        doc.add_paragraph(text)
        output=BytesIO()
        doc.save(output)
        content=output.getvalue()
    monkeypatch.setattr(processing,"enrich",forbidden)
    job=main.upload(viewer(OMAR),UploadFile(BytesIO(content),filename="format."+extension),"team")
    assert processing.process_one()
    details=main.job(job["id"],viewer())
    assert details["status"]=="ready" and details["enrichment_status"]=="not_requested"
    results=retrieval.search(viewer(),"FormatOptionalZebra",[details["document_id"]],semantic=False)
    assert results and text in results[0]["text"]
    assert results[0]["locator"]["kind"]==extension


def test_empty_optional_projection_does_not_create_unused_answer_dependencies(workspace,monkeypatch):
    job=source(workspace,b"EmptyFactsZebra remains source evidence.",enrichment_requested=False)
    assert processing.process_one()
    monkeypatch.setattr(processing,"mock_extract",lambda *args: Extraction(entities=[],claims=[],relationships=[]))
    main.reprocess(job.id,viewer())
    assert processing.process_one()
    conversation=main.create_conversation(main.NewConversation(document_ids=[job.document_id]),viewer())
    response=main.ask(conversation["id"],main.Question(question="EmptyFactsZebra"),viewer())
    assert response["statements"] and not response.get("enrichment_dependencies")
    main.reprocess(job.id,viewer())
    assert processing.process_one()
    assert not main.history(conversation["id"],viewer())["turns"][0]["suppressed"]
