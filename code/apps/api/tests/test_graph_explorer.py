from uuid import UUID,uuid4
from app.db import engine,sql
from test_m2 import call,upload,wait


def project_id():
    nodes=call("/graph/search?q=CB-ALPHA&limit=30")[1]["nodes"]
    candidates=[n["id"] for n in nodes if n["kind"]=="project" and n["name"]=="Project Alpha"]
    return next(root for root in candidates if any(c["value"]=="Amal" for c in call("/entities/"+root)[1]["claims"]))


def test_explorer_search_neighborhood_overview_and_filters():
    jobs=[upload("alpha-charter"),upload("alpha-review")]
    try:
        for job in jobs: wait(job)
        found=call("/graph/search?q=CB-ALPHA")
        assert found[0]==200 and found[1]["total"]>=1
        root=project_id()
        direct=call("/graph/search?q=Project+Alpha&kind=project")
        assert direct[0]==200 and all(n["kind"]=="project" for n in direct[1]["nodes"])
        one=call("/graph/explore?root="+root+"&limit=1")
        assert one[0]==200,one
        assert len(one[1]["nodes"])<=2 and one[1]["visible_edge_count"]<=1
        assert one[1]["truncated"] and one[1]["root_connection_count"]>1
        assert all(n["connection_count"]==n["incoming_count"]+n["outgoing_count"] for n in one[1]["nodes"])
        second=call("/graph/explore?root="+root+"&limit=1&offset=1")[1]
        assert not {n["id"] for n in one[1]["nodes"] if n["id"]!=root}&{n["id"] for n in second["nodes"] if n["id"]!=root}
        filtered=call("/graph/explore?root="+root+"&kind=person&depth=3")[1]
        assert all(n["kind"]=="person" or n["id"]==root for n in filtered["nodes"])
        assert all(edge["source"]==root or edge["target"]==root or len(filtered["edges"])<=120 for edge in filtered["edges"])
        deep=call("/graph/explore?root="+root+"&depth=3&limit=40")[1]
        assert len(deep["nodes"])<=80 and len(deep["edges"])<=120
        assert deep["root"]==root
        overview=call("/graph/overview?q=Project+Alpha")
        # Several fixtures legitimately share a name without sharing an identity.
        assert overview[0]==200 and overview[1]["entity"]["name"]=="Project Alpha"
        assert overview[1]["graph"]["root"]==overview[1]["entity"]["id"]
        identifier_overview=call("/graph/overview?q=CB-ALPHA")
        assert identifier_overview[0]==200 and identifier_overview[1]["entity"]["kind"]=="project"
        assert identifier_overview[1]["graph"]["root"]==root
        assert call("/graph/overview?q=who+owns+the+migration")[1] is None
        assert call("/graph/search?q=%25_")[0]==200
        assert call("/graph/explore?root="+root+"&kind=unknown")[0]==422
    finally:
        for job in jobs: call("/documents/"+job["document_id"],method="DELETE")


def test_explorer_revocation_removes_nodes_edges_and_counts():
    org=UUID("00000000-0000-4000-8000-000000000001")
    owner=UUID("00000000-0000-4000-8000-000000000101")
    did,vid,root,target,chunk=uuid4(),uuid4(),uuid4(),uuid4(),uuid4()
    with engine.begin() as conn:
        sql(conn,"INSERT INTO documents(id,organization_id,owner_id,filename,visibility) VALUES(:id,:org,:owner,'private-graph.md','team')",id=did,org=org,owner=owner)
        sql(conn,"INSERT INTO document_versions(id,organization_id,document_id,filename,checksum,byte_count,artifact_key) VALUES(:id,:org,:doc,'private-graph.md',:checksum,1,'unused')",id=vid,org=org,doc=did,checksum=uuid4().hex)
        sql(conn,"UPDATE documents SET current_version_id=:version WHERE id=:id",version=vid,id=did)
        sql(conn,"INSERT INTO chunks(id,organization_id,version_id,line_number,text) VALUES(:id,:org,:version,1,'Private relationship')",id=chunk,org=org,version=vid)
        for entity,kind,name in [(root,'project','Private connected project'),(target,'person','Private connected person')]:
            sql(conn,"INSERT INTO canonical_entities(id,organization_id,kind) VALUES(:id,:org,:kind)",id=entity,org=org,kind=kind)
            sql(conn,"INSERT INTO entities(id,organization_id,version_id,kind,name,canonical_id) VALUES(:id,:org,:version,:kind,:name,:root)",id=uuid4(),org=org,version=vid,kind=kind,name=name,root=entity)
        sql(conn,"""INSERT INTO relationships(id,organization_id,version_id,source_id,target_id,chunk_id,predicate)
            SELECT :id,:org,:version,s.id,t.id,:chunk,'owns' FROM entities s,entities t
            WHERE s.canonical_id=:root AND t.canonical_id=:target""",id=uuid4(),org=org,version=vid,chunk=chunk,root=root,target=target)
    try:
        before=call("/graph/explore?root="+str(root),"demo-omar")
        assert before[0]==200 and before[1]["root_connection_count"]==1
        assert call("/documents/"+str(did)+"/access",body={"visibility":"private"},method="PATCH")[0]==200
        after=call("/graph/explore?root="+str(root),"demo-omar")
        assert after[0]==404
        assert call("/graph/search?q=Private+connected","demo-omar")[1]["nodes"]==[]
        assert call("/documents/"+str(vid)+"/download","demo-omar")[0]==404
    finally:
        call("/documents/"+str(did),method="DELETE")



def dense_graph():
    org=UUID("00000000-0000-4000-8000-000000000001")
    owner=UUID("00000000-0000-4000-8000-000000000101")
    did,vid,root,chunk=uuid4(),uuid4(),uuid4(),uuid4()
    with engine.begin() as conn:
        sql(conn,"INSERT INTO documents(id,organization_id,owner_id,filename,visibility) VALUES(:id,:org,:owner,'dense-test.md','team')",id=did,org=org,owner=owner)
        sql(conn,"INSERT INTO document_versions(id,organization_id,document_id,filename,checksum,byte_count,artifact_key) VALUES(:id,:org,:doc,'dense-test.md',:checksum,1,'unused')",id=vid,org=org,doc=did,checksum=uuid4().hex)
        sql(conn,"UPDATE documents SET current_version_id=:version WHERE id=:id",version=vid,id=did)
        sql(conn,"INSERT INTO chunks(id,organization_id,version_id,line_number,text) VALUES(:id,:org,:version,1,'Synthetic dense graph')",id=chunk,org=org,version=vid)
        sql(conn,"INSERT INTO canonical_entities(id,organization_id,kind) VALUES(:id,:org,'project')",id=root,org=org)
        sql(conn,"INSERT INTO entities(id,organization_id,version_id,kind,name,canonical_id) VALUES(:id,:org,:version,'project','Dense test project',:root)",id=uuid4(),org=org,version=vid,root=root)
        for index in range(30):
            target=uuid4()
            sql(conn,"INSERT INTO canonical_entities(id,organization_id,kind) VALUES(:id,:org,'person')",id=target,org=org)
            sql(conn,"INSERT INTO entities(id,organization_id,version_id,kind,name,canonical_id) VALUES(:id,:org,:version,'person',:name,:root)",id=uuid4(),org=org,version=vid,name="Test person "+str(index),root=target)
            sql(conn,"""INSERT INTO relationships(id,organization_id,version_id,source_id,target_id,chunk_id,predicate)
                SELECT :id,:org,:version,s.id,t.id,:chunk,'owns' FROM entities s,entities t
                WHERE s.canonical_id=:root AND t.canonical_id=:target""",id=uuid4(),org=org,version=vid,chunk=chunk,root=root,target=target)
    return did,root


def test_dense_graph_pages_stable_neighbors_and_counts():
    did,root=dense_graph()
    try:
        first=call("/graph/explore?root="+str(root)+"&limit=2")
        assert first[0]==200,first
        assert first[1]["root_connection_count"]==30,first
        assert len(first[1]["edges"])==2 and first[1]["truncated"]
        assert all(n["connection_count"]==1 or n["id"]==str(root) for n in first[1]["nodes"])
        second=call("/graph/explore?root="+str(root)+"&limit=2&offset=2")[1]
        assert len(second["edges"])==2
        assert not {n["id"] for n in first[1]["nodes"]}&{n["id"] for n in second["nodes"] if n["id"]!=str(root)}
        people=call("/graph/explore?root="+str(root)+"&kind=person&limit=2")[1]
        assert people["root_connection_count"]==30
        tasks=call("/graph/explore?root="+str(root)+"&kind=task")[1]
        assert tasks["root_connection_count"]==0 and len(tasks["nodes"])==1
    finally:
        call("/documents/"+str(did),method="DELETE")
