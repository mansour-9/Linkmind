import hashlib
from contextlib import contextmanager
from uuid import UUID,uuid4
from app import processing
from app.artifacts import save
from app.db import engine,sql
from app.fixture_provider import FIXTURES

def test_pre_migration_job_retry_reuses_evidence_ids(monkeypatch):
    org=UUID("00000000-0000-4000-8000-000000000001")
    owner=UUID("00000000-0000-4000-8000-000000000101")
    did,vid,jid=uuid4(),uuid4(),uuid4()
    content=FIXTURES["cloud-migration"].path.read_bytes()
    checksum=hashlib.sha256(content).hexdigest()
    artifact=save(org,checksum,content)
    with engine.connect() as conn:
        tx=conn.begin()
        try:
            sql(conn,"INSERT INTO documents(id,organization_id,owner_id,filename,visibility) VALUES(:id,:org,:owner,'legacy.md','private')",id=did,org=org,owner=owner)
            sql(conn,"""INSERT INTO document_versions(id,organization_id,document_id,filename,checksum,byte_count,artifact_key)
                VALUES(:id,:org,:document,'legacy.md',:checksum,:size,:artifact)""",
                id=vid,org=org,document=did,checksum=checksum,size=len(content),artifact=artifact)
            sql(conn,"""INSERT INTO processing_jobs(id,organization_id,version_id,owner_id,checksum,available_at,enrichment_requested)
                VALUES(:id,:org,:version,:owner,:checksum,now()-interval '100 days',true)""",
                id=jid,org=org,version=vid,owner=owner,checksum=checksum)
            existing=[]
            for number,line in enumerate(content.decode().splitlines(),1):
                if not line.strip(): continue
                cid=uuid4()
                existing.append(cid)
                sql(conn,"""INSERT INTO chunks(id,organization_id,version_id,line_number,text,locator)
                    VALUES(:id,:org,:version,:line,:text,jsonb_build_object('kind','text','line',CAST(:line AS integer)))""",
                    id=cid,org=org,version=vid,line=number,text=line)
            class TestEngine:
                @contextmanager
                def begin(self):
                    with conn.begin_nested(): yield conn
            monkeypatch.setattr(processing,"engine",TestEngine())
            monkeypatch.setattr(processing,"configured",lambda:False)
            monkeypatch.setattr(processing,"embed",lambda *args:None)
            assert processing.process_one()
            assert sql(conn,"SELECT status FROM processing_jobs WHERE id=:id",id=jid).scalar()=="ready"
            assert set(sql(conn,"SELECT id FROM chunks WHERE version_id=:id",id=vid).scalars())==set(existing)
            assert set(sql(conn,"SELECT chunk_id FROM claims WHERE version_id=:id",id=vid).scalars()).issubset(existing)
        finally:
            tx.rollback()
