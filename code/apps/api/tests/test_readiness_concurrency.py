"""Exercise publication/revision ordering with independent PostgreSQL sessions."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from app import processing
from app.contracts import Extraction
from app.db import engine, sql
from test_search_readiness import ORG, source


def test_content_activation_serializes_with_revision_and_late_enrichment_is_rejected():
    documents = []
    try:
        with engine.begin() as conn:
            old = source(conn)
            documents.append(old.document_id)
            token = uuid4()
            sql(conn, """UPDATE processing_jobs SET status='processing',lease_token=:token,
                lease_until=clock_timestamp()+interval '5 minutes' WHERE id=:id""", token=token, id=old.id)
            sql(conn, """INSERT INTO chunks(id,organization_id,version_id,line_number,text)
                VALUES(:id,:org,:version,1,'Original concurrent evidence')""", id=uuid4(), org=ORG, version=old.version_id)
        old_job = SimpleNamespace(**vars(old), organization_id=ORG, lease_token=token)
        activated, blocked = Event(), Event()

        def activate():
            with engine.begin() as conn:
                processing.publish_content(conn, old_job, "unavailable")
                activated.set()
                assert blocked.wait(10), "Revision session did not reach the locked boundary"

        def revise():
            assert activated.wait(10)
            with engine.begin() as conn:
                # Uncommitted publication is invisible to other readers.
                assert sql(conn, "SELECT current_version_id FROM documents WHERE id=:id", id=old.document_id).scalar() is None
                with pytest.raises(OperationalError) as locked:
                    with conn.begin_nested():
                        sql(conn, "SELECT id FROM documents WHERE id=:id FOR UPDATE NOWAIT", id=old.document_id)
                assert locked.value.orig.sqlstate == "55P03"
                blocked.set()
                sql(conn, "SELECT id FROM documents WHERE id=:id FOR UPDATE", id=old.document_id)
                latest = source(conn, b"New concurrent evidence", document=old.document_id)
                next_token = uuid4()
                sql(conn, """UPDATE processing_jobs SET status='processing',lease_token=:token,
                    lease_until=clock_timestamp()+interval '5 minutes' WHERE id=:id""", token=next_token, id=latest.id)
                sql(conn, """INSERT INTO chunks(id,organization_id,version_id,line_number,text)
                    VALUES(:id,:org,:version,1,'New concurrent evidence')""", id=uuid4(), org=ORG, version=latest.version_id)
                return SimpleNamespace(**vars(latest), organization_id=ORG, lease_token=next_token)

        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = pool.submit(activate), pool.submit(revise)
            first.result(timeout=20)
            latest_job = second.result(timeout=20)
        with pytest.raises(ValueError, match="superseded"):
            with engine.begin() as conn:
                processing.publish(conn, old_job, Extraction(entities=[], claims=[], relationships=[]), [], "fixture")
        with engine.begin() as conn:
            assert sql(conn, "SELECT current_version_id FROM documents WHERE id=:id", id=old.document_id).scalar() == old.version_id
            assert sql(conn, "SELECT processed_at FROM document_versions WHERE id=:id", id=old.version_id).scalar() is None
            processing.publish_content(conn, latest_job, "unavailable")
            assert sql(conn, "SELECT current_version_id FROM documents WHERE id=:id", id=old.document_id).scalar() == latest_job.version_id
    finally:
        with engine.begin() as conn:
            sql(conn, "UPDATE documents SET current_version_id=NULL WHERE id=ANY(:ids)", ids=documents)
            for table in ("processing_jobs", "chunks"):
                sql(conn, f"DELETE FROM {table} WHERE version_id IN (SELECT id FROM document_versions WHERE document_id=ANY(:ids))", ids=documents)
            sql(conn, "DELETE FROM document_versions WHERE document_id=ANY(:ids)", ids=documents)
            sql(conn, "DELETE FROM documents WHERE id=ANY(:ids)", ids=documents)
