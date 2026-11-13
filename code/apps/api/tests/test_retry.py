import hashlib
from contextlib import contextmanager
from uuid import UUID,uuid4
from app import processing
from app.db import engine,sql
from app.artifacts import save
from app.fixture_provider import FIXTURES

def test_worker_retries_rollback_publication(monkeypatch):
    org=UUID("00000000-0000-4000-8000-000000000001")
    owner=UUID("00000000-0000-4000-8000-000000000101")
    did,vid,jid=uuid4(),uuid4(),uuid4()
    content=FIXTURES["cloud-migration"].path.read_bytes()
    checksum=hashlib.sha256(content).hexdigest()
    artifact=save(org,checksum,content)
    with engine.connect() as conn:
        tx=conn.begin()
        try:
            sql(conn,"INSERT INTO documents(id,organization_id,owner_id,filename,visibility) VALUES(:id,:org,:owner,'retry.md','private')",id=did,org=org,owner=owner)
            sql(conn,"""INSERT INTO document_versions(id,organization_id,document_id,filename,checksum,byte_count,artifact_key)
                VALUES(:id,:org,:doc,'retry.md',:checksum,:size,:artifact)""",id=vid,org=org,doc=did,checksum=checksum,size=len(content),artifact=artifact)
            sql(conn,"""INSERT INTO processing_jobs(id,organization_id,version_id,owner_id,checksum,available_at)
                VALUES(:id,:org,:version,:owner,:checksum,now()-interval '100 days')""",id=jid,org=org,version=vid,owner=owner,checksum=checksum)
            class TestEngine:
                @contextmanager
                def begin(self):
                    with conn.begin_nested(): yield conn
            def fail(conn,job,*args):
                assert job.id==jid
                sql(conn,"INSERT INTO canonical_entities(id,organization_id,kind) VALUES(:id,:org,'project')",id=uuid4(),org=org)
                raise RuntimeError("Injected publication failure")
            monkeypatch.setattr(processing,"engine",TestEngine())
            monkeypatch.setattr(processing,"configured",lambda:False)
            monkeypatch.setattr(processing,"embed",lambda *args:None)
            monkeypatch.setattr(processing,"publish",fail)
            count=sql(conn,"SELECT count(*) FROM canonical_entities").scalar()
            for attempt in range(1,4):
                assert processing.process_one()
                row=sql(conn,"SELECT status,attempts FROM processing_jobs WHERE id=:id",id=jid).one()
                assert tuple(row)==("failed" if attempt==3 else "queued",attempt)
                assert sql(conn,"SELECT count(*) FROM canonical_entities").scalar()==count
                assert sql(conn,"SELECT count(*) FROM entities WHERE version_id=:id",id=vid).scalar()==0
                # Enrichment rolls back, while valid source search publication survives.
                assert sql(conn,"SELECT current_version_id FROM documents WHERE id=:id",id=did).scalar()==vid
                assert sql(conn,"SELECT search_ready_at FROM document_versions WHERE id=:id",id=vid).scalar()
                sql(conn,"UPDATE processing_jobs SET available_at=now()-interval '100 days' WHERE id=:id",id=jid)
        finally:
            tx.rollback()
