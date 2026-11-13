"""Candidate enrichment is persisted separately; source revisions/chunks never move."""
from uuid import uuid4

from app.contracts import Extraction,validate_extraction
from app.db import sql


def create(conn,job):
    candidate=uuid4()
    row=sql(conn,"""INSERT INTO document_versions(id,organization_id,document_id,filename,checksum,
        byte_count,artifact_key,created_at,source_version_id,activation_state)
        SELECT :candidate,organization_id,document_id,filename,checksum,byte_count,artifact_key,clock_timestamp(),id,'staged'
        FROM document_versions WHERE id=:source AND source_version_id IS NULL RETURNING id""",
        candidate=candidate,source=job["version_id"]).first()
    if not row:
        raise ValueError("Only an immutable source revision can be reprocessed.")
    return candidate


def verify(conn,job,result,passages,provider):
    candidate=getattr(job,"staged_version_id",None)
    if not candidate:
        return result
    validated=validate_extraction(result,passages)
    # An empty replacement must not silently erase existing validated knowledge.
    count=sql(conn,"SELECT count(*) FROM live_entities WHERE version_id=:source",source=job.version_id).scalar_one()
    if count and not validated.entities:
        raise ValueError("No verified replacement facts were produced. Existing knowledge was retained.")
    changed=sql(conn,"""UPDATE document_versions SET staged_extraction=CAST(:payload AS jsonb),
        extraction_provider=:provider,verified_at=clock_timestamp()
        WHERE id=:candidate AND source_version_id=:source AND activation_state='staged' RETURNING id""",
        candidate=candidate,source=job.version_id,payload=validated.model_dump_json(),provider=provider).first()
    if not changed:
        raise ValueError("The enrichment candidate was replaced or rolled back.")
    return validated


def activation_guard(conn,job,result):
    candidate=getattr(job,"staged_version_id",None)
    if not candidate:
        return
    row=sql(conn,"""SELECT staged_extraction FROM document_versions WHERE id=:candidate
        AND organization_id=:org AND source_version_id=:source AND activation_state='staged'
        AND verified_at IS NOT NULL FOR UPDATE""",candidate=candidate,source=job.version_id,org=job.organization_id).mappings().first()
    if not row or Extraction.model_validate(row.staged_extraction)!=result:
        raise ValueError("Enrichment must match the verified staged candidate before activation.")


def activate(conn,job,provider):
    candidate=getattr(job,"staged_version_id",None)
    if not candidate:
        return
    previous=sql(conn,"SELECT coalesce(active_enrichment_version_id,id) FROM document_versions WHERE id=:source FOR UPDATE",
        source=job.version_id).scalar_one()
    sql(conn,"UPDATE document_versions SET activation_state='rolled_back' WHERE id=:previous",previous=previous)
    sql(conn,"""UPDATE document_versions SET activation_state='live',processed_at=clock_timestamp(),
        extraction_provider=:provider WHERE id=:candidate""",candidate=candidate,provider=provider)
    sql(conn,"UPDATE document_versions SET active_enrichment_version_id=:candidate WHERE id=:source",
        source=job.version_id,candidate=candidate)


def rollback(conn,candidate):
    if candidate:
        sql(conn,"UPDATE document_versions SET activation_state='rolled_back' WHERE id=:id AND activation_state='staged'",id=candidate)
