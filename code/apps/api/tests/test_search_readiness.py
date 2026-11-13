"""Publication boundaries: source text must survive unavailable/failed enrichment."""
import hashlib
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app import main, processing, retrieval, conflict_detection
from app.artifacts import save
from app.db import engine, sql
from app.fixture_provider import FIXTURES

ORG = UUID("00000000-0000-4000-8000-000000000001")
AMAL = UUID("00000000-0000-4000-8000-000000000101")
OMAR = UUID("00000000-0000-4000-8000-000000000102")


@pytest.fixture
def workspace(monkeypatch):
    with engine.connect() as conn:
        transaction = conn.begin()

        class TestEngine:
            @contextmanager
            def begin(self):
                with conn.begin_nested():
                    yield conn

            @contextmanager
            def connect(self):
                yield conn

        for module in (main, processing, retrieval, conflict_detection):
            monkeypatch.setattr(module, "engine", TestEngine())
        monkeypatch.setattr(processing, "configured", lambda: False)
        monkeypatch.setattr(processing, "embed", lambda *args: None)
        monkeypatch.setattr(retrieval, "configured", lambda: False)
        try:
            yield conn
        finally:
            transaction.rollback()


def viewer(user=AMAL):
    return main.Viewer(id=user, organization_id=ORG, name="Test", organization="Test", role="admin" if user == AMAL else "member")


def source(conn, content=b"ReadinessZebra project evidence remains searchable.", document=None, visibility="team"):
    did, vid, jid = document or uuid4(), uuid4(), uuid4()
    checksum = hashlib.sha256(content).hexdigest()
    if document is None:
        sql(conn, """INSERT INTO documents(id,organization_id,owner_id,filename,visibility)
            VALUES(:id,:org,:owner,'readiness.md',:visibility)""", id=did, org=ORG, owner=AMAL, visibility=visibility)
    sql(conn, """INSERT INTO document_versions(id,organization_id,document_id,filename,checksum,byte_count,artifact_key,created_at)
        VALUES(:id,:org,:doc,'readiness.md',:checksum,:size,:artifact,clock_timestamp())""",
        id=vid, org=ORG, doc=did, checksum=checksum, size=len(content), artifact=save(ORG, checksum, content))
    sql(conn, """INSERT INTO processing_jobs(id,organization_id,version_id,owner_id,checksum,available_at)
        VALUES(:id,:org,:version,:owner,:checksum,clock_timestamp()-interval '100 years')""",
        id=jid, org=ORG, version=vid, owner=AMAL, checksum=checksum)
    return SimpleNamespace(id=jid, version_id=vid, document_id=did)


def fail(*args, **kwargs):
    raise ValueError("Injected enrichment failure")


def test_unavailable_extraction_keeps_source_searchable_and_citable(workspace):
    job = source(workspace)
    assert processing.process_one()
    assert sql(workspace, "SELECT current_version_id FROM documents WHERE id=:id", id=job.document_id).scalar() == job.version_id
    results = retrieval.search(viewer(), "ReadinessZebra", [job.document_id], semantic=False)
    assert len(results) == 1 and results[0]["entities"] == []
    details = main.job(job.id, viewer())
    assert details["status"] == "extraction_unavailable"
    assert details["search_status"] == "ready" and details["enrichment_status"] == "unavailable"
    assert details["search_ready_at"] and details["processed_at"] is None
    assert main.evidence(UUID(results[0]["id"]), viewer())["quote"] == results[0]["text"]
    conversation = main.create_conversation(main.NewConversation(document_ids=[job.document_id]), viewer())
    response = main.ask(conversation["id"], main.Question(question="ReadinessZebra"), viewer())
    assert response["provider"] == "mock-extractive" and response["statements"]
    assert response["statements"][0]["evidence"][0]["quote"] in results[0]["text"]


@pytest.mark.parametrize("failure_stage", ["extraction", "conflict"])
def test_failed_enrichment_keeps_text_without_partial_graph(workspace, monkeypatch, failure_stage):
    content = FIXTURES["cloud-migration"].path.read_bytes()
    job = source(workspace, content)
    real_extract = processing.mock_extract
    monkeypatch.setattr(processing, "configured", lambda: True)
    monkeypatch.setattr(processing, "extract_bedrock_batches", fail if failure_stage == "extraction" else lambda passages, scope: [real_extract(content, passages)])
    monkeypatch.setattr(conflict_detection, "assess", fail)
    assert processing.process_one()
    details = main.job(job.id, viewer())
    assert details["status"] == "failed" and details["search_status"] == "ready"
    assert details["enrichment_status"] == "failed" and details["entity_count"] == 0
    assert retrieval.search(viewer(), "Project Alpha", [job.document_id], semantic=False)
    assert sql(workspace, "SELECT count(*) FROM relationships WHERE version_id=:id", id=job.version_id).scalar() == 0


def test_new_search_revision_hides_old_graph_and_saved_answers(workspace):
    old = source(workspace, FIXTURES["cloud-migration"].path.read_bytes())
    assert processing.process_one()
    old_passages = retrieval.search(viewer(), "Project Alpha", [old.document_id], semantic=False)
    old_ids = [p["id"] for p in old_passages]
    assert old_ids
    conversation = main.create_conversation(main.NewConversation(document_ids=[old.document_id]), viewer())
    main.ask(conversation["id"], main.Question(question="Project Alpha"), viewer())
    replacement = source(workspace, document=old.document_id)
    assert processing.process_one()
    assert sql(workspace, "SELECT current_version_id FROM documents WHERE id=:id", id=old.document_id).scalar() == replacement.version_id
    assert not retrieval.dependencies_allowed(workspace, viewer(), old_ids)
    assert main.history(conversation["id"], viewer())["turns"][0]["suppressed"]
    assert main.evidence(UUID(old_ids[0]), viewer())["quote"]
    assert sql(workspace, """SELECT count(*) FROM relationships r JOIN document_versions v ON v.id=r.version_id
        JOIN documents d ON d.id=v.document_id WHERE d.current_version_id=v.id AND v.id=:id""", id=old.version_id).scalar() == 0
    assert all(p["version_id"] != old.version_id for p in main.wiki(viewer()))
    assert sql(workspace, "SELECT count(*) FROM relationships WHERE version_id=:id", id=old.version_id).scalar() > 0
    assert retrieval.search(viewer(), "ReadinessZebra", [old.document_id], semantic=False)


def test_enrichment_retry_preserves_citations_and_does_not_reindex(workspace, monkeypatch):
    content = FIXTURES["cloud-migration"].path.read_bytes()
    job = source(workspace, content)
    original = processing.mock_extract
    monkeypatch.setattr(processing, "mock_extract", fail)
    assert processing.process_one()
    before = sql(workspace, "SELECT id,text,locator FROM chunks WHERE version_id=:id ORDER BY id", id=job.version_id).all()
    activated = main.job(job.id, viewer())["search_ready_at"]
    with pytest.raises(HTTPException) as denied:
        main.retry(job.id, viewer(OMAR))
    assert denied.value.status_code == 403
    assert main.retry(job.id, viewer())["status"] == "queued"
    monkeypatch.setattr(processing, "mock_extract", original)
    monkeypatch.setattr(processing, "parse_document", fail)
    monkeypatch.setattr(processing, "embed", fail)
    assert processing.process_one()
    completed = main.job(job.id, viewer())
    assert completed["enrichment_status"] == "ready"
    assert completed["search_ready_at"] == activated
    assert completed["embedding_status"] == "unavailable"
    assert len(completed["attempt_history"]) == 2
    assert sql(workspace, "SELECT id,text,locator FROM chunks WHERE version_id=:id ORDER BY id", id=job.version_id).all() == before
    count = completed["entity_count"]
    # Recover a crash after enrichment commit but before the job completion commit.
    sql(workspace, "UPDATE processing_jobs SET status='queued',available_at=now() WHERE id=:id", id=job.id)
    monkeypatch.setattr(processing, "mock_extract", fail)
    assert processing.process_one()
    assert main.job(job.id, viewer())["entity_count"] == count
    with pytest.raises(HTTPException) as immutable:
        main.retry(job.id, viewer())
    assert immutable.value.status_code == 409


def test_parser_failure_preserves_previous_search_revision(workspace, monkeypatch):
    old = source(workspace)
    assert processing.process_one()
    replacement = source(workspace, b"Replacement text.", document=old.document_id)
    monkeypatch.setattr(processing, "parse_document", fail)
    assert processing.process_one()
    assert sql(workspace, "SELECT current_version_id FROM documents WHERE id=:id", id=old.document_id).scalar() == old.version_id
    assert main.job(replacement.id, viewer())["search_status"] == "failed"
    assert retrieval.search(viewer(), "ReadinessZebra", [old.document_id], semantic=False)


def test_embedding_failures_keep_text_and_report_degradation(workspace, monkeypatch):
    job = source(workspace, "ReadinessZebra مفتاح-123 remains exact evidence.".encode())
    monkeypatch.setattr(processing, "embed", fail)
    assert processing.process_one()
    assert main.job(job.id, viewer())["embedding_status"] == "failed"
    monkeypatch.setattr(retrieval, "configured", lambda: True)
    monkeypatch.setenv("BEDROCK_EMBEDDING_MODEL", "test/unavailable")
    monkeypatch.setattr(retrieval, "embed", fail)
    diagnostics = {}
    results = retrieval.search(viewer(), "مفتاح-123", [job.document_id], diagnostics=diagnostics)
    assert results and results[0]["entities"] == []
    assert results[0]["semantic_status"] == "failed" and diagnostics["semantic_status"] == "failed"
    response = main.Response()
    assert main.enterprise_search(viewer(), response, q="nevermatches928374", document_id=None, kind=None, after=None, before=None, limit=20, offset=0) == []
    assert response.headers["X-Linkmind-Semantic-Status"] == "failed"


def test_revocation_during_enrichment_applies_to_all_source_evidence(workspace, monkeypatch):
    job = source(workspace, FIXTURES["cloud-migration"].path.read_bytes())
    original = processing.mock_extract

    def revoke(content, passages):
        assert retrieval.search(viewer(OMAR), "Project Alpha", [job.document_id], semantic=False)
        main.change_access(job.document_id, main.AccessChange(visibility="private"), viewer())
        return original(content, passages)

    monkeypatch.setattr(processing, "mock_extract", revoke)
    assert processing.process_one()
    assert retrieval.search(viewer(OMAR), "Project Alpha", [job.document_id], semantic=False) == []
    assert retrieval.search(viewer(), "Project Alpha", [job.document_id], semantic=False)
    passage = sql(workspace, "SELECT id FROM chunks WHERE version_id=:id LIMIT 1", id=job.version_id).scalar_one()
    with pytest.raises(HTTPException) as denied:
        main.evidence(passage, viewer(OMAR))
    assert denied.value.status_code == 404
    assert main.job(job.id, viewer())["enrichment_status"] == "ready"


def test_deletion_during_enrichment_cannot_resurrect_source(workspace, monkeypatch):
    job = source(workspace, FIXTURES["cloud-migration"].path.read_bytes())
    original = processing.mock_extract

    def delete(content, passages):
        main.delete(job.document_id, viewer())
        return original(content, passages)

    monkeypatch.setattr(processing, "mock_extract", delete)
    assert processing.process_one()
    assert sql(workspace, "SELECT current_version_id FROM documents WHERE id=:id", id=job.document_id).scalar() is None
    assert sql(workspace, "SELECT status FROM processing_jobs WHERE id=:id", id=job.id).scalar() == "cancelled"
    assert sql(workspace, "SELECT count(*) FROM entities WHERE version_id=:id", id=job.version_id).scalar() == 0
    assert retrieval.search(viewer(), "Project Alpha", [job.document_id], semantic=False) == []


@pytest.mark.parametrize("boundary", ["content", "enrichment"])
@pytest.mark.parametrize("lease_change", ["expired", "replaced"])
def test_lost_lease_cannot_publish_or_finish(workspace, monkeypatch, boundary, lease_change):
    job = source(workspace, FIXTURES["cloud-migration"].path.read_bytes())
    original = processing.mock_extract
    new_token = uuid4()

    def lose_lease(*args):
        if lease_change == "expired":
            sql(workspace, "UPDATE processing_jobs SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:id", id=job.id)
        else:
            sql(workspace, "UPDATE processing_jobs SET lease_token=:token WHERE id=:id", id=job.id, token=new_token)
        return original(*args) if boundary == "enrichment" else None

    monkeypatch.setattr(processing, "mock_extract" if boundary == "enrichment" else "embed", lose_lease)
    assert processing.process_one()
    details = main.job(job.id, viewer())
    assert details["processed_at"] is None and details["entity_count"] == 0
    assert details["search_status"] == ("ready" if boundary == "enrichment" else "pending")
    assert details["status"] == "processing" and details["attempt_history"][-1]["status"] == "abandoned"
    if lease_change == "replaced":
        assert sql(workspace, "SELECT lease_token FROM processing_jobs WHERE id=:id", id=job.id).scalar() == new_token
    else:
        monkeypatch.setattr(processing, "mock_extract", original)
        monkeypatch.setattr(processing, "embed", lambda *args: None)
        assert processing.process_one()
        assert main.job(job.id, viewer())["enrichment_status"] == "ready"


def test_superseding_revision_blocks_old_activation_and_retry(workspace):
    old = source(workspace)
    latest = source(workspace, b"New ReadinessZebra facts.", document=old.document_id)
    assert processing.process_one()
    assert sql(workspace, "SELECT current_version_id FROM documents WHERE id=:id", id=old.document_id).scalar() is None
    assert not main.job(old.id, viewer())["can_retry"]
    with pytest.raises(HTTPException) as superseded:
        main.retry(old.id, viewer())
    assert superseded.value.status_code == 409
    assert processing.process_one()
    assert sql(workspace, "SELECT current_version_id FROM documents WHERE id=:id", id=old.document_id).scalar() == latest.version_id


def test_supersession_during_enrichment_never_promotes_old_graph(workspace, monkeypatch):
    old = source(workspace, FIXTURES["cloud-migration"].path.read_bytes())
    original = processing.mock_extract
    replacements = []

    def replace(content, passages):
        replacements.append(source(workspace, document=old.document_id))
        return original(content, passages)

    monkeypatch.setattr(processing, "mock_extract", replace)
    assert processing.process_one()
    assert main.job(old.id, viewer())["search_status"] == "ready"
    assert main.job(old.id, viewer())["entity_count"] == 0
    monkeypatch.setattr(processing, "mock_extract", original)
    assert processing.process_one()
    assert sql(workspace, "SELECT current_version_id FROM documents WHERE id=:id", id=old.document_id).scalar() == replacements[0].version_id
