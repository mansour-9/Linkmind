"""Four-original-PDF offline acceptance. All provider responses are explicit stubs."""
import hashlib
import json
import os
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app import main,processing,providers,retrieval
from app.contracts import Extraction,validate_extraction
from app.db import sql
from app.parsers import parse_document
from test_search_readiness import ORG,OMAR,viewer,source

pytestmark=pytest.mark.skipif(not os.getenv('LANTERN_ACCEPTANCE_DIR'),
    reason='Private Lantern originals are local-only; set LANTERN_ACCEPTANCE_DIR for offline acceptance.')


@pytest.fixture
def lantern_workspace(monkeypatch):
    from contextlib import contextmanager
    from app import retrieval
    from app.db import engine
    with engine.connect() as conn:
        transaction=conn.begin()
        class TestEngine:
            @contextmanager
            def begin(self):
                with conn.begin_nested():
                    yield conn
            @contextmanager
            def connect(self):
                yield conn
        for module in (main,processing,retrieval):
            monkeypatch.setattr(module,"engine",TestEngine())
        monkeypatch.setattr(processing,"configured",lambda:False)
        monkeypatch.setattr(processing,"embed",lambda *args:None)
        monkeypatch.setattr(processing,"mock_extract",lambda *args:None)
        monkeypatch.setattr(retrieval,"configured",lambda:False)
        monkeypatch.setattr(providers,"configured",lambda:False)
        try:
            yield conn
        finally:
            transaction.rollback()


def load_documents():
    root=Path(os.environ["LANTERN_ACCEPTANCE_DIR"])
    manifest=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["files"])==4
    loaded=[]
    for item in manifest["files"]:
        raw=(root/item["local_filename"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item["sha256"]
        assert len(raw)==item["byte_count"]
        parsed=parse_document(item["filename"],raw)
        assert len(parsed)==item["passages"]
        loaded.append((item,raw,parsed))
    return loaded


def test_lantern_originals_cover_bounded_batches_and_truncation(monkeypatch):
    summary=[]
    for item,raw,parsed in load_documents():
        passages=[dict(id=f"{item['version_id']}-{index}",text=p.text,locator=p.locator)
                  for index,p in enumerate(parsed,1)]
        batches=providers.bounded_batches(passages)
        assert [p["id"] for batch in batches for p in batch]==[p["id"] for p in passages]
        assert all(len(batch)<=3 and sum(len(p["text"]) for p in batch)<=9000 for batch in batches)
        calls=[]
        def verified(batch,scope,payload,repair_allowed,**kwargs):
            calls.append(batch)
            if len(calls)==1:
                raise providers.ModelResponseError("output_truncated","max_tokens")
            evidence=[dict(passage_id=p["id"],quote=p["text"]) for p in batch]
            return Extraction(entities=[dict(key=f"lantern-{batch[0]['id']}",kind="project",name="Project Lantern",identifiers=[],evidence=evidence)],claims=[],relationships=[])
        monkeypatch.setattr(providers,"_extract_verified",verified)
        extracted=providers.extract_bedrock_batches(passages,{})
        for batch in extracted:
            validate_extraction(batch,passages)
        summary.append(dict(filename=item["filename"],passages=len(passages),initial_batches=len(batches),
                            batch_passages=[len(batch) for batch in batches],
                            extraction_calls=len(calls),maximum_batch_characters=max(sum(len(p["text"]) for p in batch) for batch in batches)))
    print("LANTERN_BATCHES="+json.dumps(summary))


def candidate(passages,index):
    identifier=next((value for value in ("LAN-DEC-002","LAN-ENG-003","LAN-PILOT-004","LAN-CHR-001","LANTERN")
                     if any(value in p["text"] for p in passages)),None)
    first=next(p for p in passages if identifier and identifier in p["text"])
    second=passages[min(1,len(passages)-1)]
    if identifier is None:
        first=second
    evidence=lambda p:[dict(passage_id=p["id"],quote=p["text"])]
    return Extraction(
        entities=[dict(key="lantern",kind="project",name="Project Lantern",
                       identifiers=[dict(namespace="project_key",value=identifier)] if identifier else [],evidence=evidence(first)),
                  dict(key="decision",kind="decision",name=f"Lantern decision {index+1}",identifiers=[],evidence=evidence(second))],
        claims=[dict(entity_key="lantern",predicate="status",value=f"stubbed-status-{index+1}",asserted_by="offline acceptance stub",
                     effective_from=None,effective_to=None,evidence=evidence(first))],
        relationships=[dict(source_key="lantern",target_key="decision",predicate="has_decision",evidence=evidence(second))])



def test_lantern_stubbed_publication_conflicts_rollback_and_permissions(lantern_workspace):
    assert not providers.configured() and not os.getenv("AI_PROVIDER")
    jobs=[]
    for index,(item,raw,parsed) in enumerate(load_documents()):
        file=SimpleNamespace(filename=item["filename"],file=BytesIO(raw))
        filename,content,checksum=main.read_upload(file)
        assert checksum==item["sha256"]
        job=source(lantern_workspace,raw)
        sql(lantern_workspace,"UPDATE documents SET filename=:filename WHERE id=:id",filename=filename,id=job.document_id)
        sql(lantern_workspace,"UPDATE document_versions SET filename=:filename WHERE id=:id",filename=filename,id=job.version_id)
        def offline_candidate(content,passages,source_index=index):
            return candidate(passages,source_index)
        with patch.object(processing,"mock_extract",offline_candidate):
            assert processing.process_one()
        jobs.append((job,offline_candidate))
        assert main.job(job.id,viewer())["status"]=="ready"
        assert retrieval.search(viewer(),"Lantern",[job.document_id],semantic=False)
        with lantern_workspace.begin_nested():
            passages=[dict(id=str(p.id),text=p.text,locator=p.locator) for p in sql(lantern_workspace,
                "SELECT id,text,locator FROM chunks WHERE version_id=:id ORDER BY line_number,id",id=job.version_id).mappings()]
        assert len(passages)==item["passages"]
        jobs[-1]=(job,None,passages)
    with main.engine.connect() as conn:
        versions=[job.version_id for job,_,_ in jobs]
        canonical_ids=sql(conn,"SELECT DISTINCT canonical_id FROM live_entities WHERE kind='project' AND name='Project Lantern' AND version_id=ANY(:ids)",ids=versions).scalars().all()
        occurrences=sql(conn,"SELECT count(*) FROM live_entities WHERE canonical_id=ANY(:ids)",ids=canonical_ids).scalar_one()
        assert len(canonical_ids)==1 and occurrences==4
        chunks={p["id"] for _,_,passages in jobs for p in passages}
        conflicts=[row for row in main.conflicts(viewer()) if str(row["left_chunk_id"]) in chunks or str(row["right_chunk_id"]) in chunks]
        edges=sql(conn,"SELECT count(*) FROM live_relationships WHERE version_id=ANY(:ids)",ids=versions).scalar_one()
        assert occurrences==4 and len(conflicts)==6 and edges==4
        citation=sql(conn,"SELECT ce.chunk_id,ce.quote FROM claim_evidence ce JOIN claims c ON c.id=ce.claim_id WHERE c.version_id=ANY(:ids) LIMIT 1",ids=versions).one()
        evidence=main.evidence(citation.chunk_id,viewer())
        assert citation.quote in evidence["quote"]
        before=sql(conn,"SELECT count(*) FROM live_claims WHERE version_id=ANY(:ids)",ids=versions).scalar_one()
    main.reprocess(jobs[0][0].id,viewer())
    def rejected(job,content,passages,scope,use_bedrock,is_graph_demo):
        raise providers.ModelResponseError("content_blocked","guardrail_intervened")
    with patch.object(processing,"enrich",rejected):
        assert processing.process_one()
    failed=main.job(jobs[0][0].id,viewer())
    assert failed["status"]=="enrichment_staged_failed" and failed["preserved_enrichment"]
    assert failed["staged_activation_state"]=="rolled_back"
    with main.engine.connect() as conn:
        assert sql(conn,"SELECT count(*) FROM live_claims WHERE version_id=:id",id=jobs[0][0].version_id).scalar_one()==1
    evidence=retrieval.search(viewer(),"Project Lantern",[job.document_id for job,_,_ in jobs[1:]],semantic=False,limit=12)
    assert len(evidence)>1 and len({p["document_id"] for p in evidence})>1
    main.change_access(jobs[0][0].document_id,main.AccessChange(visibility="private"),viewer())
    assert not retrieval.search(viewer(OMAR),"Lantern",[jobs[0][0].document_id],semantic=False)
    with pytest.raises(HTTPException):
        main.evidence(jobs[0][2][0]["id"],viewer(OMAR))
    print(json.dumps(dict(stubbed_provider=True,documents=4,shared_project_occurrences=occurrences,
                          cross_document_conflicts=len(conflicts),relationships=edges,citations_exact=True,
                          rollback_retained_claims=before,revocation_enforced=True)))
