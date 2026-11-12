from contextlib import contextmanager
from uuid import UUID,uuid4
from app import retrieval
from app.db import engine,sql
from app.main import Viewer

def test_rare_qualifier_survives_fusion_and_vectors_respect_permissions(monkeypatch):
    org=UUID("00000000-0000-4000-8000-000000000001")
    amal=UUID("00000000-0000-4000-8000-000000000101")
    omar=UUID("00000000-0000-4000-8000-000000000102")
    viewers=[Viewer(id=id,organization_id=org,name="Test",organization="Test",role="member") for id in (amal,omar)]
    monkeypatch.setattr(retrieval,"configured",lambda:True)
    monkeypatch.setattr(retrieval,"embed",lambda *args:[1,0,0])
    monkeypatch.setenv("BEDROCK_EMBEDDING_MODEL","test/embed-model")
    with engine.connect() as conn:
        tx=conn.begin()
        try:
            research_id=None
            for identified in (True,False):
                did,vid,cid,eid=uuid4(),uuid4(),uuid4(),uuid4()
                sql(conn,"INSERT INTO documents(id,organization_id,owner_id,filename,visibility) VALUES(:id,:org,:owner,'retrieval-test.md',:visibility)",
                    id=did,org=org,owner=amal,visibility="team" if identified else "private")
                sql(conn,"""INSERT INTO document_versions(id,organization_id,document_id,filename,checksum,byte_count,artifact_key)
                    VALUES(:id,:org,:doc,'retrieval-test.md',:checksum,1,'unused')""",id=vid,org=org,doc=did,checksum="0"*64)
                sql(conn,"UPDATE documents SET current_version_id=:version WHERE id=:id",id=did,version=vid)
                sql(conn,"INSERT INTO canonical_entities(id,organization_id,kind) VALUES(:id,:org,'project')",id=cid,org=org)
                sql(conn,"INSERT INTO entities(id,organization_id,version_id,kind,name,canonical_id) VALUES(:id,:org,:version,'project','Project Alpha',:canonical)",
                    id=eid,org=org,version=vid,canonical=cid)
                if identified:
                    sql(conn,"INSERT INTO entity_identifiers(organization_id,canonical_id,kind,namespace,value) VALUES(:org,:id,'project','project_key','cb-retrieval-test')",org=org,id=cid)
                else:
                    research_id=cid
                for i in range(10 if identified else 1):
                    sql(conn,"""INSERT INTO chunks(id,organization_id,version_id,line_number,text,embedding,embedding_model,embedding_dimensions)
                        VALUES(:id,:org,:version,:line,:text,CAST(:vector AS vector),'test/embed-model',3)""",
                        id=uuid4(),org=org,version=vid,line=i+1,
                        text="Project Alpha CB-RETRIEVAL-TEST general project facts." if identified else "Project Alpha is a research pilot with no identifier.",
                        vector="[0,1,0]" if identified else "[1,0,0]")
            class TestEngine:
                @contextmanager
                def connect(self): yield conn
            monkeypatch.setattr(retrieval,"engine",TestEngine())
            question="Is Project Alpha in research definitely CB-RETRIEVAL-TEST?"
            own=retrieval.search(viewers[0],question,limit=3)
            assert any(str(research_id)==e["canonical_id"] for p in own for e in p["entities"])
            other=retrieval.search(viewers[1],question,limit=3)
            assert all(str(research_id)!=e["canonical_id"] for p in other for e in p["entities"])
        finally:
            tx.rollback()
