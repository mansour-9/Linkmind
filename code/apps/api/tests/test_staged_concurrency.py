from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from app import processing,enrichment_staging as staging,main
from app.contracts import Extraction
from app.db import engine,sql
from test_search_readiness import source,viewer,ORG


def test_generation_activation_is_atomic_to_other_sessions_and_revision_waits():
    activated,observed=Event(),Event()
    job=None
    try:
        with engine.begin() as conn:
            job=source(conn,b'ConcurrentStagingZebra remains searchable throughout activation.')
            sql(conn,"UPDATE document_versions SET processed_at=now(),search_ready_at=now() WHERE id=:id",id=job.version_id)
            sql(conn,'UPDATE documents SET current_version_id=:version WHERE id=:id',version=job.version_id,id=job.document_id)
            token=uuid4()
            candidate=staging.create(conn,dict(version_id=job.version_id))
            sql(conn,"""UPDATE processing_jobs SET status='processing',staged_version_id=:candidate,lease_token=:token,
                lease_until=clock_timestamp()+interval '5 minutes' WHERE id=:id""",id=job.id,candidate=candidate,token=token)
            active_job=SimpleNamespace(**vars(job),organization_id=ORG,lease_token=token,staged_version_id=candidate)
            result=Extraction(entities=[],claims=[],relationships=[])
            staging.verify(conn,active_job,result,[],'fixture')

        def activate():
            with engine.begin() as conn:
                processing.publish(conn,active_job,result,[],'fixture')
                activated.set()
                assert observed.wait(10)

        def observe_and_revise():
            assert activated.wait(10)
            with engine.begin() as conn:
                # Neither activation pointer nor candidate state leaks before commit.
                assert sql(conn,'SELECT active_enrichment_version_id FROM document_versions WHERE id=:id',id=job.version_id).scalar() is None
                assert sql(conn,'SELECT activation_state FROM document_versions WHERE id=:id',id=candidate).scalar()=='staged'
                assert sql(conn,'SELECT current_version_id FROM documents WHERE id=:id',id=job.document_id).scalar()==job.version_id
                with pytest.raises(OperationalError) as locked:
                    with conn.begin_nested():
                        sql(conn,'SELECT id FROM documents WHERE id=:id FOR UPDATE NOWAIT',id=job.document_id)
                assert locked.value.orig.sqlstate=='55P03'
                observed.set()
                sql(conn,'SELECT id FROM documents WHERE id=:id FOR UPDATE',id=job.document_id)
                assert sql(conn,'SELECT active_enrichment_version_id FROM document_versions WHERE id=:id',id=job.version_id).scalar()==candidate
                source(conn,b'A newer source revision must win over this enrichment.',document=job.document_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first,second=pool.submit(activate),pool.submit(observe_and_revise)
            first.result(timeout=20)
            second.result(timeout=20)
        with pytest.raises(ValueError,match='superseded'):
            with engine.begin() as conn:
                processing.publish(conn,active_job,result,[],'fixture')
    finally:
        observed.set()
        if job:
            main.delete(job.document_id,viewer())
