from uuid import UUID,uuid4
import pytest
from fastapi import HTTPException
from app.db import engine,sql
from app.main import Viewer,entity_detail
from app.resolution import review,candidates

def test_explicit_identity_merge_preserves_links_and_audit():
    org=UUID("00000000-0000-4000-8000-000000000001")
    owner=UUID("00000000-0000-4000-8000-000000000101")
    viewer=Viewer(id=owner,organization_id=org,name="Amal",organization="Engineering pilot",role="admin")
    with engine.connect() as conn:
        tx=conn.begin()
        try:
            rows=[]
            for i in range(2):
                did,vid,cid,eid=uuid4(),uuid4(),uuid4(),uuid4()
                sql(conn,"INSERT INTO documents(id,organization_id,owner_id,filename,visibility) VALUES(:id,:org,:owner,'identity-test.md','team')",id=did,org=org,owner=owner)
                sql(conn,"""INSERT INTO document_versions(id,organization_id,document_id,filename,checksum,byte_count,artifact_key)
                    VALUES(:id,:org,:doc,'identity-test.md',:checksum,1,'unused-test-artifact')""",
                    id=vid,org=org,doc=did,checksum="0"*64)
                sql(conn,"UPDATE documents SET current_version_id=:version WHERE id=:id",version=vid,id=did)
                sql(conn,"INSERT INTO canonical_entities(id,organization_id,kind) VALUES(:id,:org,'project')",id=cid,org=org)
                sql(conn,"""INSERT INTO entities(id,organization_id,version_id,kind,name,canonical_id)
                    VALUES(:id,:org,:version,'project','Reviewed same project',:canonical)""",id=eid,org=org,version=vid,canonical=cid)
                rows.append((cid,eid))
            candidate=uuid4()
            sql(conn,"""INSERT INTO resolution_candidates(id,organization_id,occurrence_id,candidate_id,reason)
                VALUES(:id,:org,:occurrence,:candidate,'Same name needs review')""",
                id=candidate,org=org,occurrence=rows[0][1],candidate=rows[1][0])
            assert any(x["id"]==candidate for x in candidates(conn,viewer))
            result=review(conn,viewer,candidate,"merge","Verified the synthetic source identities refer to the same project.")
            assert result["status"]=="merged"
            assert entity_detail(conn,viewer,rows[0][0])["id"]==rows[1][0]
            assert entity_detail(conn,viewer,rows[0][1])["id"]==rows[1][0]
            assert sql(conn,"SELECT count(*) FROM entity_resolution_reviews WHERE candidate_id=:id",id=candidate).scalar()==1
            with pytest.raises(HTTPException) as error:
                review(conn,viewer,candidate,"merge","Repeated review must not change an already reviewed identity.")
            assert error.value.status_code==409
        finally:
            tx.rollback()
