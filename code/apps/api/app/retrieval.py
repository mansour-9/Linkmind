"""Permission-filtered retrieval shared by search and grounded chat."""
import json
import os
from collections import defaultdict
from uuid import UUID
from app.db import engine,sql
from app.providers import configured,embed

ACCESS="d.organization_id=:org AND d.deleted_at IS NULL AND (d.owner_id=:viewer OR d.visibility='team')"
CURRENT=ACCESS+" AND d.current_version_id=v.id"
PASSAGES="""FROM chunks k JOIN document_versions v ON v.id=k.version_id
 JOIN documents d ON d.id=v.document_id"""
def search(viewer,query,document_ids=None,semantic=True,filters=None,limit=12,offset=0):
    query=query.strip()
    if not query:
        return []
    params={**viewer.access(),"q":query,"pattern":"%"+query.replace("%","\\%").replace("_","\\_")+"%"}
    where=CURRENT
    if document_ids:
        where+=" AND d.id=ANY(:documents)"
        params["documents"]=[UUID(str(x)) for x in document_ids]
    filters=filters or {}
    if filters.get("kind"):
        where+=" AND EXISTS(SELECT 1 FROM entities fe WHERE fe.version_id=v.id AND fe.kind=:entity_kind)"
        params["entity_kind"]=filters["kind"]
    if filters.get("after"):
        where+=" AND v.created_at>=CAST(:after AS date)"
        params["after"]=filters["after"]
    if filters.get("before"):
        where+=" AND v.created_at<CAST(:before AS date)+interval '1 day'"
        params["before"]=filters["before"]
    with engine.connect() as conn:
        lexical=sql(conn,f"""SELECT k.id,ts_rank_cd(k.search_text,websearch_to_tsquery('english',:q)) score
           {PASSAGES} WHERE {where} AND k.search_text@@websearch_to_tsquery('english',:q)
           ORDER BY score DESC,k.id LIMIT 40""",**params).all()
        exact=sql(conn,f"""SELECT DISTINCT k.id {PASSAGES}
           JOIN entities e ON e.version_id=v.id
           LEFT JOIN entity_identifiers i ON i.canonical_id=e.canonical_id
           WHERE {where} AND (lower(e.name)=lower(:q) OR (i.value<>'' AND position(i.value in lower(:q))>0)
             OR k.text ILIKE :pattern) ORDER BY k.id LIMIT 40""",**params).all()
        graph=sql(conn,f"""WITH matched AS (
           SELECT DISTINCT e.canonical_id FROM entities e JOIN document_versions v ON v.id=e.version_id
           JOIN documents d ON d.id=v.document_id LEFT JOIN entity_identifiers i ON i.canonical_id=e.canonical_id
           WHERE {where} AND (e.name ILIKE :pattern OR (i.value<>'' AND position(i.value in lower(:q))>0))
        ), neighbors AS (
           SELECT DISTINCT target.canonical_id FROM relationships r JOIN entities source ON source.id=r.source_id
           JOIN entities target ON target.id=r.target_id JOIN document_versions v ON v.id=r.version_id
           JOIN documents d ON d.id=v.document_id WHERE {where}
           AND source.canonical_id IN (SELECT canonical_id FROM matched)
        ) SELECT DISTINCT k.id {PASSAGES} JOIN claims c ON c.chunk_id=k.id JOIN entities e ON e.id=c.entity_id
           WHERE {where} AND e.canonical_id IN (SELECT canonical_id FROM matched UNION SELECT canonical_id FROM neighbors)
           ORDER BY k.id LIMIT 40""",**params).all()
    rankings=[lexical,exact,graph]
    semantic_ranking=[]
    vector=None
    if semantic and configured() and os.getenv("BEDROCK_EMBEDDING_MODEL"):
        vector=embed(query,dict(org=viewer.organization_id,user=viewer.id))
    if vector:
        with engine.connect() as conn:
            semantic_ranking=sql(conn,f"""SELECT k.id {PASSAGES} WHERE {where}
                AND k.embedding_model=:model AND k.embedding_dimensions=:dim
                AND k.embedding IS NOT NULL AND k.embedding_error IS NULL
                ORDER BY k.embedding <=> CAST(:vector AS vector),k.id LIMIT 40""",
                **params,model=os.environ["BEDROCK_EMBEDDING_MODEL"],dim=len(vector),vector=json.dumps(vector)).all()
            rankings.append(semantic_ranking)
    scores=defaultdict(float)
    for ranking in rankings:
        for i,row in enumerate(ranking,1):
            scores[row.id]+=1/(60+i)
    if not scores:
        return []
    ranked=sorted(scores,key=lambda x:(-scores[x],str(x)))
    # Reserve leading semantic evidence so a rare qualifier is not buried by broad ID/graph matches.
    leading=[row.id for row in semantic_ranking[:2]]
    ranked=leading+[id for id in ranked if id not in leading]
    ids=ranked[offset:offset+limit]
    if not ids:
        return []
    # Recheck access after inference, before exposing passages.
    with engine.connect() as conn:
        rows=sql(conn,f"""SELECT k.id,k.text,k.locator,k.line_number,v.id AS version_id,
            d.id AS document_id,v.filename,
            (SELECT coalesce(jsonb_agg(DISTINCT jsonb_build_object('canonical_id',e.canonical_id,'name',e.name,'kind',e.kind)),'[]'::jsonb)
             FROM entities e WHERE e.version_id=v.id AND e.organization_id=d.organization_id) AS entities
            {PASSAGES} WHERE {where} AND k.id=ANY(:ids)""",**params,ids=ids).mappings().all()
    return [{**dict(row),"id":str(row.id),"score":scores[row.id]} for row in sorted(rows,key=lambda r:ids.index(r.id))]

def dependencies_allowed(conn,viewer,ids):
    if not ids:
        return True
    count=sql(conn,f"SELECT count(*) {PASSAGES} WHERE {CURRENT} AND k.id=ANY(:ids)",
              **viewer.access(),ids=[UUID(str(x)) for x in ids]).scalar_one()
    return count==len(set(ids))
