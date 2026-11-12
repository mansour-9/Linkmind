import hashlib
import json
import os
from pathlib import PurePosixPath
from typing import Annotated, Literal
from uuid import UUID,uuid4
from fastapi import Depends,FastAPI,File,Form,HTTPException,UploadFile,Query
from fastapi.responses import FileResponse,JSONResponse
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
from pydantic import BaseModel,Field
from app.artifacts import MAX_BYTES,resolve,save
from app.db import engine,sql
from app.fixture_provider import FIXTURES
from app.parsers import validate_file,SUPPORTED
from app.retrieval import ACCESS,CURRENT,PASSAGES,search,dependencies_allowed
from app.providers import answer,configured,ProviderUnavailable

if os.environ.get("COMPANY_BRAIN_LOCAL_DEMO")!="1":
    raise RuntimeError("Local demo authentication must be explicitly enabled. Hosted authentication is not yet implemented.")
app=FastAPI(title="Company Brain",version="0.3.0",openapi_url="/api/v1/openapi.json",docs_url="/api/v1/docs",redoc_url=None)
PREFIX="/api/v1"
ANSWER_VALIDATION_VERSION="grounded-v3"
DEMO_USERS={f"demo-{name}":UUID(f"00000000-0000-4000-8000-00000000010{i}") for i,name in enumerate(["amal","omar","nour"],1)}
bearer=HTTPBearer(auto_error=False)

class Viewer(BaseModel):
    id:UUID
    organization_id:UUID
    name:str
    organization:str
    role:str
    def access(self):
        return dict(org=self.organization_id,viewer=self.id)

def authenticate(credentials:Annotated[HTTPAuthorizationCredentials|None,Depends(bearer)]):
    token=credentials.credentials if credentials else ""
    if token not in DEMO_USERS:
        raise HTTPException(401,"Choose a local demo identity.",headers={"WWW-Authenticate":"Bearer"})
    with engine.connect() as conn:
        user=sql(conn,"""SELECT u.*,o.name AS organization FROM users u
            JOIN organizations o ON o.id=u.organization_id WHERE u.id=:id""",id=DEMO_USERS[token]).mappings().one()
    return Viewer(**user)
Identity=Annotated[Viewer,Depends(authenticate)]

@app.middleware("http")
async def headers(request,call_next):
    if request.method=="POST" and (request.url.path.endswith("/upload") or request.url.path.endswith("/revisions")):
        length=request.headers.get("content-length","")
        if not length.isascii() or not length.isdecimal():
            return JSONResponse({"detail":"Upload requires a content length."},status_code=411)
        if len(length)>10 or int(length)>MAX_BYTES+16384:
            return JSONResponse({"detail":"Upload exceeds the 20 MiB file limit."},status_code=413)
    response=await call_next(request)
    response.headers["Cache-Control"]="no-store"
    return response

@app.get("/health")
def health():
    with engine.connect() as conn: sql(conn,"SELECT 1")
    return dict(status="ok",mode="local-demo",provider="bedrock" if configured() else "mock")

@app.get(PREFIX+"/me")
def me(viewer:Identity): return viewer

JOB_QUERY="""SELECT j.*,v.document_id,v.filename,v.created_at AS uploaded_at,v.processed_at,
  v.embedding_status,v.extraction_provider,d.visibility,d.current_version_id,
  (d.owner_id=:viewer OR :operator) AS can_manage,
  (SELECT count(*) FROM entities e WHERE e.version_id=v.id) AS entity_count,
  (SELECT count(*) FROM claims c WHERE c.version_id=v.id) AS claim_count,
  (SELECT count(*) FROM relationships r WHERE r.version_id=v.id) AS relationship_count
  FROM processing_jobs j JOIN document_versions v ON v.id=j.version_id JOIN documents d ON d.id=v.document_id"""
def job_params(viewer):
    return {**viewer.access(),"operator":viewer.role in {"admin","reviewer"}}
def find_job(conn,viewer,id):
    row=sql(conn,JOB_QUERY+f" WHERE {ACCESS} AND j.id=:id",**job_params(viewer),id=id).mappings().first()
    if not row: raise HTTPException(404,"Job not found.")
    return dict(row)
def owned_document(conn,viewer,id):
    row=sql(conn,f"SELECT d.* FROM documents d WHERE {ACCESS} AND d.id=:id FOR UPDATE",
            **viewer.access(),id=id).mappings().first()
    if not row: raise HTTPException(404,"Document not found.")
    if row.owner_id!=viewer.id and viewer.role!="admin":
        raise HTTPException(403,"Only the document owner or an authorized administrator can change it.")
    return row
def audit(conn,viewer,action,id):
    sql(conn,"INSERT INTO audit_events(id,organization_id,actor_id,action,resource_id) VALUES(:id,:org,:user,:action,:resource)",
        id=uuid4(),org=viewer.organization_id,user=viewer.id,action=action,resource=id)

def graph_demo_jobs(conn,viewer):
    from app.graph_demo import MANIFEST,ROOT
    jobs=[]
    for item in MANIFEST["fixtures"]:
        content=(ROOT/item["filename"]).read_bytes()
        checksum=hashlib.sha256(content).hexdigest()
        row=sql(conn,JOB_QUERY+f""" WHERE {ACCESS} AND d.visibility='team' AND v.checksum=:checksum
            AND (d.current_version_id=v.id OR d.current_version_id IS NULL)
            AND NOT EXISTS(SELECT 1 FROM document_versions newer WHERE newer.document_id=d.id
                AND (newer.created_at,newer.id)>(v.created_at,v.id))
            ORDER BY (j.status='ready') DESC,j.created_at LIMIT 1""",**job_params(viewer),checksum=checksum).mappings().first()
        jobs.append(dict(row) if row else None)
    return jobs


def graph_demo_status(conn,viewer):
    from app.graph_demo import MANIFEST
    jobs=graph_demo_jobs(conn,viewer)
    versions=[job["version_id"] for job in jobs if job and job["status"]=="ready" and job["current_version_id"]==job["version_id"] and job["extraction_provider"]=="graph-demo-fixture"]
    counts=dict(entity_count=0,entity_occurrence_count=0,relationship_count=0)
    if versions:
        counts=dict(sql(conn,"""SELECT count(DISTINCT canonical_id) AS entity_count,
            count(*) AS entity_occurrence_count,
            (SELECT count(*) FROM relationships WHERE version_id=ANY(:versions)) AS relationship_count
            FROM entities WHERE version_id=ANY(:versions)""",versions=versions).mappings().one())
    ready=len(versions)==2 and all(counts[key]==MANIFEST[key] for key in counts)
    return {**counts,"ready":ready,"source_count":len(versions),"jobs":jobs}


@app.get(PREFIX+"/demo/graph-dataset")
def graph_dataset(viewer:Identity):
    """Return exact, clearly labeled synthetic sources and expected dataset counts."""
    from app.graph_demo import MANIFEST,ROOT
    return {"description":MANIFEST["description"],
            **{key:MANIFEST[key] for key in ("entity_count","entity_occurrence_count","relationship_count")},
            "files":[{"filename":item["filename"],"content":(ROOT/item["filename"]).read_text(encoding="utf-8")}
                     for item in MANIFEST["fixtures"]]}


@app.post(PREFIX+"/demo/graph-dataset/load",status_code=202)
def load_graph_dataset(viewer:Identity):
    from app.graph_demo import MANIFEST,ROOT
    with engine.begin() as conn:
        # Serialize this fixed dataset per organization; normal upload behavior is unchanged.
        sql(conn,"SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",key=f"{viewer.organization_id}:graph-demo-v2")
        existing=graph_demo_jobs(conn,viewer)
        for item,job in zip(MANIFEST["fixtures"],existing):
            if job is not None:
                continue
            content=(ROOT/item["filename"]).read_bytes(); checksum=hashlib.sha256(content).hexdigest(); did=uuid4()
            sql(conn,"""INSERT INTO documents(id,organization_id,owner_id,filename,visibility)
                VALUES(:id,:org,:owner,:filename,'team')""",id=did,org=viewer.organization_id,owner=viewer.id,filename=item["filename"])
            add_version(conn,viewer,did,item["filename"],content,checksum)
        return graph_demo_status(conn,viewer)


@app.get(PREFIX+"/demo/graph-dataset/status")
def graph_dataset_status(viewer:Identity):
    with engine.connect() as conn:
        return graph_demo_status(conn,viewer)


@app.get(PREFIX+"/demo/fixtures/{name}")
def fixture(name:str,viewer:Identity):
    fixture=FIXTURES.get(name)
    if not fixture or (name=="private-review" and viewer.id!=DEMO_USERS["demo-amal"]):
        raise HTTPException(404,"Fixture not found.")
    return FileResponse(fixture.path,filename=fixture.filename,media_type="application/octet-stream")

def read_upload(file):
    filename=PurePosixPath((file.filename or "").replace(chr(92),"/")).name
    if not filename or len(filename)>180 or any(ord(x)<32 for x in filename):
        raise HTTPException(400,"Invalid filename.")
    if PurePosixPath(filename).suffix.lower() not in SUPPORTED:
        raise HTTPException(415,"Supported formats are PDF, DOCX, TXT and Markdown.")
    content=file.file.read(MAX_BYTES+1)
    if not content: raise HTTPException(400,"The file is empty.")
    if len(content)>MAX_BYTES: raise HTTPException(413,"Upload exceeds the 20 MiB file limit.")
    try: validate_file(filename,content)
    except (ValueError,UnicodeError) as exc: raise HTTPException(422,str(exc)) from None
    return filename,content,hashlib.sha256(content).hexdigest()

def add_version(conn,viewer,document,filename,content,checksum):
    vid,jid=uuid4(),uuid4()
    artifact=save(viewer.organization_id,checksum,content)
    sql(conn,"""INSERT INTO document_versions(id,organization_id,document_id,filename,checksum,byte_count,artifact_key)
        VALUES(:id,:org,:doc,:filename,:checksum,:size,:artifact)""",
        id=vid,org=viewer.organization_id,doc=document,filename=filename,checksum=checksum,size=len(content),artifact=artifact)
    sql(conn,"""INSERT INTO processing_jobs(id,organization_id,version_id,owner_id,checksum)
        VALUES(:id,:org,:version,:owner,:checksum)""",
        id=jid,org=viewer.organization_id,version=vid,owner=viewer.id,checksum=checksum)
    return find_job(conn,viewer,jid)

@app.post(PREFIX+"/sources/upload",status_code=202)
def upload(viewer:Identity,file:Annotated[UploadFile,File()],
           visibility:Annotated[Literal["private","team"],Form()]="private"):
    filename,content,checksum=read_upload(file)
    with engine.begin() as conn:
        sql(conn,"SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",key=f"{viewer.organization_id}:{viewer.id}:{checksum}")
        existing=sql(conn,JOB_QUERY+f" WHERE {ACCESS} AND j.owner_id=:viewer AND j.checksum=:checksum ORDER BY j.created_at DESC LIMIT 1",
            **job_params(viewer),checksum=checksum).mappings().first()
        if existing:
            if existing.visibility!=visibility: raise HTTPException(409,"This file was already uploaded with different access.")
            return dict(existing)
        did=uuid4()
        sql(conn,"""INSERT INTO documents(id,organization_id,owner_id,filename,visibility)
            VALUES(:id,:org,:owner,:filename,:visibility)""",
            id=did,org=viewer.organization_id,owner=viewer.id,filename=filename,visibility=visibility)
        return add_version(conn,viewer,did,filename,content,checksum)

@app.get(PREFIX+"/documents")
def document_catalog(viewer:Identity,q:str=Query(default="",max_length=500),
                     id:list[UUID]|None=Query(default=None,max_length=30),
                     limit:int=Query(default=20,ge=1,le=40),offset:int=Query(default=0,ge=0,le=100000)):
    # One current revision per source, independent of the bounded processing-job list.
    params={**viewer.access(),"limit":30 if id else limit,"offset":0 if id else offset}
    where=CURRENT
    if id:
        where+=" AND d.id=ANY(:ids)"
        params["ids"]=id
    if q.strip():
        where+=" AND v.filename ILIKE :pattern"
        params["pattern"]="%"+q.strip().replace("%", "\\%").replace("_", "\\_")+"%"
    with engine.connect() as conn:
        return [dict(row) for row in sql(conn,f"""SELECT d.id AS document_id,v.id AS version_id,
            v.filename,v.created_at AS uploaded_at,d.visibility
            FROM documents d JOIN document_versions v ON v.id=d.current_version_id
            WHERE {where} ORDER BY v.created_at DESC,d.id LIMIT :limit OFFSET :offset""",
            **params).mappings()]

@app.get(PREFIX+"/sources")
@app.get(PREFIX+"/processing")
def sources(viewer:Identity):
    with engine.connect() as conn:
        return [dict(r) for r in sql(conn,JOB_QUERY+f" WHERE {ACCESS} ORDER BY v.created_at DESC LIMIT 200",
                                    **job_params(viewer)).mappings()]
@app.get(PREFIX+"/jobs/{id}")
def job(id:UUID,viewer:Identity):
    with engine.connect() as conn:
        result=find_job(conn,viewer,id)
        result["attempt_history"]=[dict(r) for r in sql(conn,"SELECT * FROM processing_attempts WHERE job_id=:id ORDER BY started_at",id=id).mappings()]
        return result

@app.post(PREFIX+"/jobs/{id}/retry",status_code=202)
def retry(id:UUID,viewer:Identity):
    with engine.begin() as conn:
        job=find_job(conn,viewer,id)
        if not job["can_manage"]: raise HTTPException(403,"Retry requires source ownership or an operational role.")
        sql(conn,"SELECT id FROM processing_jobs WHERE id=:id FOR UPDATE",id=id)
        if job["status"] in {"queued","processing"}: raise HTTPException(409,"This job is already pending.")
        if job["status"]=="cancelled": raise HTTPException(409,"Cancelled jobs cannot be retried.")
        if job["processed_at"] or job["status"]=="ready": raise HTTPException(409,"Published versions are immutable. Upload a revision to reprocess.")
        sql(conn,"""UPDATE processing_jobs SET status='queued',stage='queued',attempts=0,
           available_at=now(),error=NULL,error_code=NULL,lease_token=NULL WHERE id=:id""",id=id)
        audit(conn,viewer,"retry",id)
        return find_job(conn,viewer,id)

@app.post(PREFIX+"/documents/{id}/revisions",status_code=202)
def revision(id:UUID,viewer:Identity,file:Annotated[UploadFile,File()]):
    filename,content,checksum=read_upload(file)
    with engine.begin() as conn:
        owned_document(conn,viewer,id)
        existing=sql(conn,"SELECT j.id FROM processing_jobs j JOIN document_versions v ON v.id=j.version_id WHERE v.document_id=:id AND v.checksum=:checksum",
                     id=id,checksum=checksum).scalar_one_or_none()
        if existing: return find_job(conn,viewer,existing)
        audit(conn,viewer,"revision",id)
        return add_version(conn,viewer,id,filename,content,checksum)

class AccessChange(BaseModel):
    visibility:Literal["private","team"]
@app.patch(PREFIX+"/documents/{id}/access")
def change_access(id:UUID,body:AccessChange,viewer:Identity):
    with engine.begin() as conn:
        owned_document(conn,viewer,id)
        sql(conn,"UPDATE documents SET visibility=:visibility WHERE id=:id",id=id,visibility=body.visibility)
        audit(conn,viewer,"access:"+body.visibility,id)
    return {"status":"updated"}
@app.delete(PREFIX+"/documents/{id}")
def delete(id:UUID,viewer:Identity):
    with engine.begin() as conn:
        owned_document(conn,viewer,id)
        sql(conn,"UPDATE documents SET deleted_at=now(),current_version_id=NULL WHERE id=:id",id=id)
        sql(conn,"""UPDATE processing_jobs SET status='cancelled',lease_token=NULL WHERE version_id IN
            (SELECT id FROM document_versions WHERE document_id=:id) AND status IN ('queued','processing')""",id=id)
        audit(conn,viewer,"delete",id)
    return {"status":"deleted"}

ENTITY_JOIN="FROM entities e JOIN document_versions v ON v.id=e.version_id JOIN documents d ON d.id=v.document_id"
def entity_detail(conn,viewer,id):
    occurrence=sql(conn,f"SELECT e.canonical_id {ENTITY_JOIN} WHERE {ACCESS} AND e.id=:id",
                   **viewer.access(),id=id).scalar_one_or_none()
    if occurrence:
        id=occurrence
    for _ in range(10):
        target=sql(conn,"SELECT target_id FROM canonical_redirects WHERE organization_id=:org AND source_id=:id",org=viewer.organization_id,id=id).scalar_one_or_none()
        if not target: break
        id=target
    row=sql(conn,f"""SELECT e.canonical_id AS id,e.kind,e.name,v.id AS version_id,v.filename
        {ENTITY_JOIN} WHERE {CURRENT} AND (e.canonical_id=:id OR e.id=:id)
        ORDER BY v.created_at DESC,e.id LIMIT 1""",**viewer.access(),id=id).mappings().first()
    if not row: raise HTTPException(404,"Entity not found.")
    claims=sql(conn,f"""SELECT c.*,k.line_number,k.locator,k.text AS quote,v.filename
        {ENTITY_JOIN} JOIN claims c ON c.entity_id=e.id JOIN chunks k ON k.id=c.chunk_id
        WHERE {CURRENT} AND e.canonical_id=:id ORDER BY v.created_at,c.id""",**viewer.access(),id=row.id).mappings().all()
    result={**dict(row),"claims":[]}
    result["sources"]=[dict(x) for x in sql(conn,f"""SELECT DISTINCT v.id AS version_id,v.filename,
       v.created_at,(d.current_version_id=v.id) AS current FROM entities e
       JOIN document_versions v ON v.id=e.version_id JOIN documents d ON d.id=v.document_id
       WHERE {ACCESS} AND e.canonical_id=:id ORDER BY v.created_at DESC""",**viewer.access(),id=row.id).mappings()]
    result["entity_evidence"]=[dict(x) for x in sql(conn,f"""SELECT ee.chunk_id,ee.quote,k.locator,v.filename,
       v.id AS version_id FROM entity_evidence ee JOIN entities e ON e.id=ee.entity_id
       JOIN chunks k ON k.id=ee.chunk_id JOIN document_versions v ON v.id=e.version_id
       JOIN documents d ON d.id=v.document_id WHERE {CURRENT} AND e.canonical_id=:id""",
       **viewer.access(),id=row.id).mappings()]
    from app.resolution import candidates
    result["uncertain_matches"]=sum(1 for x in candidates(conn,viewer) if x["status"]=="open" and
       row.id in {x["source_canonical_id"],x["candidate_id"]})
    for claim in claims:
        evidence=sql(conn,f"""SELECT ce.chunk_id,ce.quote,ce.span_start,ce.span_end,k.locator,v.filename,v.id AS version_id
            FROM claim_evidence ce JOIN chunks k ON k.id=ce.chunk_id
            JOIN document_versions v ON v.id=k.version_id JOIN documents d ON d.id=v.document_id
            WHERE {CURRENT} AND ce.claim_id=:id""",**viewer.access(),id=claim.id).mappings()
        result["claims"].append({**dict(claim),"evidence":[dict(x) for x in evidence]})
    return result
@app.get(PREFIX+"/entities/{id}")
@app.get(PREFIX+"/wiki/{id}")
def entity(id:UUID,viewer:Identity):
    with engine.connect() as conn: return entity_detail(conn,viewer,id)
@app.get(PREFIX+"/wiki")
def wiki(viewer:Identity):
    with engine.connect() as conn:
        return [dict(r) for r in sql(conn,f"""SELECT DISTINCT ON(e.canonical_id) e.canonical_id AS id,e.name,e.kind,
            v.filename,v.id AS version_id {ENTITY_JOIN} WHERE {CURRENT}
            ORDER BY e.canonical_id,v.created_at DESC LIMIT 200""",**viewer.access()).mappings()]

@app.get(PREFIX+"/graph/explore")
def graph_explore(viewer:Identity,root:UUID,depth:int=Query(1,ge=1,le=3),kind:str|None=None,
                  relationship:str|None=Query(None,max_length=100),offset:int=Query(0,ge=0,le=10000),
                  limit:int=Query(24,ge=1,le=40)):
    from app.graph_explorer import explore
    with engine.begin() as conn:
        sql(conn,"SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return explore(conn,viewer,root,depth,kind,relationship,offset,limit)

@app.get(PREFIX+"/graph/search")
def graph_search(viewer:Identity,q:str=Query("",max_length=200),kind:str|None=None,
                 offset:int=Query(0,ge=0,le=10000),limit:int=Query(8,ge=1,le=30)):
    from app.graph_explorer import search
    with engine.begin() as conn:
        sql(conn,"SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return search(conn,viewer,q.strip(),kind,offset,limit)

@app.get(PREFIX+"/graph/overview")
def graph_overview(viewer:Identity,q:str=Query(...,min_length=1,max_length=200)):
    from app.graph_explorer import overview
    with engine.begin() as conn:
        sql(conn,"SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return overview(conn,viewer,q.strip())

@app.get(PREFIX+"/graph/relationships")
def graph_relationship_types(viewer:Identity):
    from app.graph_explorer import relationship_types
    with engine.connect() as conn: return relationship_types(conn,viewer)

@app.get(PREFIX+"/graph")
@app.get(PREFIX+"/graph/neighborhood")
def graph(viewer:Identity,root:UUID|None=None,q:str=Query("",max_length=200),kind:str|None=None,limit:int=Query(150,ge=1,le=150)):
    params={**viewer.access(),"q":"%"+q+"%","kind":kind,"limit":limit}
    condition=""
    if root:
        entity_detail_id=None
        with engine.connect() as conn: entity_detail_id=entity_detail(conn,viewer,root)["id"]
        params["root"]=entity_detail_id
        condition=f""" AND e.canonical_id IN (
          SELECT :root UNION SELECT t.canonical_id FROM relationships r JOIN entities s ON s.id=r.source_id
          JOIN entities t ON t.id=r.target_id JOIN document_versions v ON v.id=r.version_id
          JOIN documents d ON d.id=v.document_id WHERE {CURRENT} AND s.canonical_id=:root
          UNION SELECT s.canonical_id FROM relationships r JOIN entities s ON s.id=r.source_id
          JOIN entities t ON t.id=r.target_id JOIN document_versions v ON v.id=r.version_id
          JOIN documents d ON d.id=v.document_id WHERE {CURRENT} AND t.canonical_id=:root)"""
    with engine.begin() as conn:
        sql(conn,"SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        nodes=sql(conn,f"""SELECT DISTINCT ON(e.canonical_id) e.canonical_id AS id,e.name,e.kind,
             v.filename,v.id AS version_id {ENTITY_JOIN} WHERE {CURRENT}
             AND e.name ILIKE :q AND (CAST(:kind AS text) IS NULL OR e.kind=:kind) {condition}
             ORDER BY e.canonical_id,v.created_at DESC LIMIT :limit""",**params).mappings().all()
        ids=[r.id for r in nodes]
        edges=sql(conn,f"""SELECT r.id,s.canonical_id AS source,t.canonical_id AS target,r.predicate AS label,r.effective_from,r.effective_to,r.chunk_id
             FROM relationships r JOIN entities s ON s.id=r.source_id JOIN entities t ON t.id=r.target_id
             JOIN document_versions v ON v.id=r.version_id JOIN documents d ON d.id=v.document_id
             WHERE {CURRENT} AND s.canonical_id=ANY(:ids) AND t.canonical_id=ANY(:ids) ORDER BY r.id""",
             **viewer.access(),ids=ids).mappings() if ids else []
        conflicts=sql(conn,CONFLICT_QUERY+" AND f.status IN ('open','needs_evidence')",**viewer.access()).mappings().all()
        return dict(nodes=[{**dict(r),"conflict_count":sum(c.canonical_id==r.id for c in conflicts)} for r in nodes],edges=[dict(r) for r in edges])

@app.get(PREFIX+"/evidence/{id}")
def evidence(id:UUID,viewer:Identity):
    with engine.connect() as conn:
        row=sql(conn,f"""SELECT k.id,k.line_number,k.locator,k.text AS quote,v.id AS version_id,v.filename
            {PASSAGES} WHERE {ACCESS} AND k.id=:id""",**viewer.access(),id=id).mappings().first()
    if not row: raise HTTPException(404,"Evidence not found.")
    return dict(row)
@app.get(PREFIX+"/documents/{id}/download")
def download(id:UUID,viewer:Identity):
    with engine.connect() as conn:
        row=sql(conn,f"""SELECT v.artifact_key,v.filename FROM document_versions v JOIN documents d ON d.id=v.document_id
            WHERE {ACCESS} AND v.id=:id""",**viewer.access(),id=id).mappings().first()
    if not row: raise HTTPException(404,"Document not found.")
    path=resolve(row.artifact_key)
    if not path.is_file(): raise HTTPException(503,"Original file is temporarily unavailable.")
    return FileResponse(path,filename=row.filename,media_type="application/octet-stream")
@app.get(PREFIX+"/search")
def enterprise_search(viewer:Identity,q:str=Query(...,min_length=1,max_length=500),
    document_id:UUID|None=None,kind:str|None=None,after:str|None=None,before:str|None=None,
    limit:int=Query(20,ge=1,le=40),offset:int=Query(0,ge=0,le=200)):
    from datetime import date
    try:
        filters={"kind":kind,"after":date.fromisoformat(after) if after else None,"before":date.fromisoformat(before) if before else None}
    except ValueError:
        raise HTTPException(422,"Date filters must use YYYY-MM-DD.") from None
    try: return search(viewer,q,[document_id] if document_id else None,filters=filters,limit=limit,offset=offset)
    except Exception as exc:
        raise HTTPException(503,"Search could not complete. Check Bedrock embedding access or retry.") from exc

CONFLICT_QUERY=f"""WITH authorized_claims AS (
 SELECT c.id,c.value,c.chunk_id,c.predicate {ENTITY_JOIN} JOIN claims c ON c.entity_id=e.id WHERE {CURRENT}
) SELECT f.*,l.value AS left_value,r.value AS right_value,l.chunk_id AS left_chunk_id,r.chunk_id AS right_chunk_id
 FROM conflicts f JOIN authorized_claims l ON l.id=f.left_claim_id JOIN authorized_claims r ON r.id=f.right_claim_id
 WHERE f.organization_id=:org"""
@app.get(PREFIX+"/conflicts")
def conflicts(viewer:Identity):
    with engine.connect() as conn:
        return [dict(r) for r in sql(conn,CONFLICT_QUERY+" ORDER BY f.created_at DESC",**viewer.access()).mappings()]
class Review(BaseModel):
    status:Literal["resolved","not_a_conflict","needs_evidence"]
    rationale:str=Field(min_length=10,max_length=2000)
    authoritative_claim_id:UUID|None=None
    expected_updated_at:str|None=None
@app.post(PREFIX+"/conflicts/{id}/review")
def review(id:UUID,body:Review,viewer:Identity):
    if viewer.role not in {"admin","reviewer"}: raise HTTPException(403,"A reviewer role is required.")
    with engine.begin() as conn:
        sql(conn,"SELECT id FROM conflicts WHERE id=:id AND organization_id=:org FOR UPDATE",id=id,org=viewer.organization_id)
        row=sql(conn,CONFLICT_QUERY+" AND f.id=:id",**viewer.access(),id=id).mappings().first()
        if not row: raise HTTPException(404,"Conflict not found.")
        if body.expected_updated_at and row.updated_at.isoformat()!=body.expected_updated_at:
            raise HTTPException(409,"This conflict changed. Refresh before reviewing it.")
        if body.authoritative_claim_id not in {None,row.left_claim_id,row.right_claim_id}: raise HTTPException(422,"Invalid authoritative claim.")
        if body.status=="resolved" and not body.authoritative_claim_id: raise HTTPException(422,"Choose the supported authoritative claim.")
        sql(conn,"""UPDATE conflicts SET status=:status,rationale=:reason,authoritative_claim_id=:claim,updated_at=now() WHERE id=:id""",
            id=id,status=body.status,reason=body.rationale,claim=body.authoritative_claim_id)
        sql(conn,"""INSERT INTO review_actions(id,organization_id,conflict_id,reviewer_id,action,rationale)
             VALUES(:id,:org,:conflict,:user,:action,:reason)""",id=uuid4(),org=viewer.organization_id,
             conflict=id,user=viewer.id,action=body.status,reason=body.rationale)
    return {"status":body.status}

@app.get(PREFIX+"/resolution-candidates")
def resolution_candidates(viewer:Identity):
    from app.resolution import candidates
    with engine.connect() as conn: return candidates(conn,viewer)

class IdentityReview(BaseModel):
    action:Literal["merge","reject"]
    rationale:str=Field(min_length=10,max_length=2000)
@app.post(PREFIX+"/resolution-candidates/{id}/review")
def identity_review(id:UUID,body:IdentityReview,viewer:Identity):
    if viewer.role not in {"admin","reviewer"}: raise HTTPException(403,"A reviewer role is required.")
    from app.resolution import review
    with engine.begin() as conn: return review(conn,viewer,id,body.action,body.rationale)

@app.get(PREFIX+"/conflicts/{id}/history")
def review_history(id:UUID,viewer:Identity):
    with engine.connect() as conn:
        if not sql(conn,CONFLICT_QUERY+" AND f.id=:id",**viewer.access(),id=id).first():
            raise HTTPException(404,"Conflict not found.")
        return [dict(r) for r in sql(conn,"SELECT action,rationale,created_at FROM review_actions WHERE conflict_id=:id ORDER BY created_at",id=id).mappings()]

class NewConversation(BaseModel):
    title:str=Field(default="New conversation",max_length=120)
    document_ids:list[UUID]=Field(default_factory=list,max_length=30)
def conversation(conn,viewer,id):
    row=sql(conn,"SELECT * FROM conversations WHERE id=:id AND organization_id=:org AND user_id=:viewer",
            **viewer.access(),id=id).mappings().first()
    if not row: raise HTTPException(404,"Conversation not found.")
    return row
@app.post(PREFIX+"/conversations",status_code=201)
def create_conversation(body:NewConversation,viewer:Identity):
    with engine.begin() as conn:
        for id in body.document_ids:
            if not sql(conn,f"SELECT d.id FROM documents d WHERE {ACCESS} AND d.id=:id",**viewer.access(),id=id).first():
                raise HTTPException(404,"Selected source not found.")
        id=uuid4()
        sql(conn,"""INSERT INTO conversations(id,organization_id,user_id,title,document_ids)
            VALUES(:id,:org,:user,:title,CAST(:documents AS jsonb))""",id=id,org=viewer.organization_id,user=viewer.id,
            title=body.title,documents=json.dumps([str(x) for x in body.document_ids]))
        return dict(conversation(conn,viewer,id))
@app.get(PREFIX+"/conversations")
def conversations(viewer:Identity):
    with engine.connect() as conn:
        return [dict(r) for r in sql(conn,"SELECT * FROM conversations WHERE organization_id=:org AND user_id=:viewer ORDER BY created_at DESC LIMIT 100",**viewer.access()).mappings()]
@app.get(PREFIX+"/conversations/{id}")
def history(id:UUID,viewer:Identity):
    with engine.connect() as conn:
        row=conversation(conn,viewer,id)
        turns=[]
        for turn in sql(conn,"SELECT * FROM conversation_turns WHERE conversation_id=:id ORDER BY created_at",id=id).mappings():
            allowed=turn.validation_version==ANSWER_VALIDATION_VERSION and dependencies_allowed(conn,viewer,turn.dependency_ids)
            turns.append(dict(id=turn.id,question=turn.question,response=turn.response if allowed else None,
                suppressed=not allowed,created_at=turn.created_at))
        return {**dict(row),"turns":turns}
class Question(BaseModel):
    question:str=Field(min_length=2,max_length=2000)
@app.post(PREFIX+"/conversations/{id}/answers")
def ask(id:UUID,body:Question,viewer:Identity):
    previous=[]
    with engine.connect() as conn:
        row=conversation(conn,viewer,id)
        for turn in sql(conn,"SELECT question,response,dependency_ids FROM conversation_turns WHERE conversation_id=:id AND validation_version=:policy ORDER BY created_at DESC LIMIT 3",id=id,policy=ANSWER_VALIDATION_VERSION).mappings():
            if dependencies_allowed(conn,viewer,turn.dependency_ids):
                previous.append(dict(turn))
    try:
        evidence=search(viewer,body.question,row.document_ids)
        # Reuse only current, permission-checked passages for follow-up references.
        prior_passages=previous[0]["response"].get("evidence",[]) if previous else []
        byid={p["id"]:p for p in evidence+prior_passages[:4]}
        evidence=list(byid.values())
        payload=[dict(id=p["id"],text=p["text"],filename=p["filename"],locator=p["locator"],entities=p.get("entities",[])) for p in evidence]
        context_dependencies=sorted({p["id"] for p in evidence}.union(*(set(t["dependency_ids"]) for t in previous)))
        def authorize_context():
            with engine.connect() as conn:
                if not dependencies_allowed(conn,viewer,context_dependencies):
                    raise HTTPException(409,"Source access or versions changed. Ask again.")
        authorize_context()
        result=answer(body.question,payload,dict(org=viewer.organization_id,user=viewer.id),
            history=[{"question":t["question"],"statements":t["response"].get("statements",[])} for t in reversed(previous)],authorize=authorize_context)
    except HTTPException:
        raise
    except Exception as exc:
        code=getattr(exc,"response",{}).get("Error",{}).get("Code",type(exc).__name__)
        if code=="ThrottlingException":
            raise HTTPException(429,"Bedrock is temporarily rate limited. Please wait and retry.",headers={"Retry-After":"10"}) from exc
        raise HTTPException(503,"Answer unavailable ("+code+"). No unverified answer was saved. Retry or check the provider.") from exc
    dependencies=context_dependencies
    response={**result.model_dump(),"evidence":evidence,"provider":"bedrock" if configured() else "mock-extractive"}
    with engine.begin() as conn:
        conversation(conn,viewer,id)
        if not dependencies_allowed(conn,viewer,dependencies):
            raise HTTPException(409,"Source access or versions changed. Ask again using current evidence.")
        sql(conn,"""INSERT INTO conversation_turns(id,organization_id,conversation_id,question,response,dependency_ids,validation_version)
            VALUES(:id,:org,:conversation,:question,CAST(:response AS jsonb),CAST(:dependencies AS jsonb),:policy)""",
            id=uuid4(),org=viewer.organization_id,conversation=id,question=body.question,
            response=json.dumps(response,default=str),dependencies=json.dumps(dependencies),policy=ANSWER_VALIDATION_VERSION)
    return response

@app.get(PREFIX+"/usage")
def usage(viewer:Identity):
    if viewer.role not in {"admin","reviewer"}: raise HTTPException(403,"Operational usage requires a reviewer role.")
    with engine.connect() as conn:
        rows=sql(conn,"""SELECT operation,provider,model,region,status,count(*) AS calls,
            sum(input_tokens) AS input_tokens,sum(output_tokens) AS output_tokens,
            round(avg(latency_ms)) AS latency_ms,sum(estimated_cost) AS estimated_cost,
            count(*) FILTER(WHERE estimated_cost IS NULL) AS unknown_cost_calls,currency,rate_date,
            sum(sdk_retries) AS retries FROM ai_usage WHERE organization_id=:org
            GROUP BY operation,provider,model,region,status,currency,rate_date
            ORDER BY operation,model,status""",org=viewer.organization_id).mappings()
        return [dict(r) for r in rows]
