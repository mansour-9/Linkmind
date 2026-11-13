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
def search(viewer,query,document_ids=None,semantic=True,filters=None,limit=12,offset=0,diagnostics=None):
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
        where+=" AND EXISTS(SELECT 1 FROM live_entities fe WHERE fe.version_id=v.id AND fe.kind=:entity_kind)"
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
        if not lexical:
            from app.source_discovery import terms
            keywords=terms(query)
            if keywords:
                lexical=sql(conn,f"""SELECT k.id,ts_rank_cd(k.search_text,websearch_to_tsquery('english',:keywords)) score
                    {PASSAGES} WHERE {where} AND k.search_text@@websearch_to_tsquery('english',:keywords)
                    ORDER BY score DESC,k.id LIMIT 40""",**params,keywords=" OR ".join(keywords)).all()
        exact=sql(conn,f"""SELECT k.id {PASSAGES} WHERE {where} AND
           (k.text ILIKE :pattern OR EXISTS(SELECT 1 FROM live_entities e
             LEFT JOIN entity_identifiers i ON i.canonical_id=e.canonical_id
             WHERE e.version_id=v.id AND (lower(e.name)=lower(:q)
               OR (i.value<>'' AND position(i.value in lower(:q))>0))))
           ORDER BY k.id LIMIT 40""",**params).all()
        graph=sql(conn,f"""WITH matched AS (
           SELECT DISTINCT e.canonical_id FROM live_entities e JOIN document_versions v ON v.id=e.version_id
           JOIN documents d ON d.id=v.document_id LEFT JOIN entity_identifiers i ON i.canonical_id=e.canonical_id
           WHERE {where} AND (e.name ILIKE :pattern OR (i.value<>'' AND position(i.value in lower(:q))>0))
        ), neighbors AS (
           SELECT DISTINCT target.canonical_id FROM live_relationships r JOIN live_entities source ON source.id=r.source_id
           JOIN live_entities target ON target.id=r.target_id JOIN document_versions v ON v.id=r.version_id
           JOIN documents d ON d.id=v.document_id WHERE {where}
           AND source.canonical_id IN (SELECT canonical_id FROM matched)
        ) SELECT DISTINCT k.id {PASSAGES} JOIN live_claims c ON c.chunk_id=k.id JOIN live_entities e ON e.id=c.entity_id
           WHERE {where} AND e.canonical_id IN (SELECT canonical_id FROM matched UNION SELECT canonical_id FROM neighbors)
           ORDER BY k.id LIMIT 40""",**params).all()
    rankings=[lexical,exact,graph]
    semantic_ranking=[]
    vector=None
    semantic_status="not_requested" if not semantic else "unavailable"
    if semantic and configured() and os.getenv("BEDROCK_EMBEDDING_MODEL"):
        try:
            vector=embed(query,dict(org=viewer.organization_id,user=viewer.id))
            semantic_status="ready" if vector else "unavailable"
        except Exception:
            # This is only a model/index degradation. SQL source/ACL failures still
            # fail the request, and every returned passage is reauthorized below.
            semantic_status="failed"
    if vector:
        with engine.connect() as conn:
            semantic_ranking=sql(conn,f"""SELECT k.id {PASSAGES} WHERE {where}
                AND k.embedding_model=:model AND k.embedding_dimensions=:dim
                AND k.embedding IS NOT NULL AND k.embedding_error IS NULL
                ORDER BY k.embedding <=> CAST(:vector AS vector),k.id LIMIT 40""",
                **params,model=os.environ["BEDROCK_EMBEDDING_MODEL"],dim=len(vector),vector=json.dumps(vector)).all()
            rankings.append(semantic_ranking)
    if diagnostics is not None:
        diagnostics["semantic_status"]=semantic_status
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
            d.id AS document_id,v.filename,v.embedding_status,
            CASE WHEN v.processed_at IS NOT NULL THEN coalesce(v.active_enrichment_version_id,v.id)::text END AS enrichment_version_id,
            (SELECT coalesce(jsonb_agg(DISTINCT jsonb_build_object('canonical_id',e.canonical_id,'name',e.name,'kind',e.kind)),'[]'::jsonb)
             FROM live_entities e WHERE e.version_id=v.id AND e.organization_id=d.organization_id) AS entities
            {PASSAGES} WHERE {where} AND k.id=ANY(:ids)""",**params,ids=ids).mappings().all()
    return [{**dict(row),"id":str(row.id),"score":scores[row.id],"semantic_status":semantic_status}
            for row in sorted(rows,key=lambda r:ids.index(r.id))]

def dependencies_allowed(conn,viewer,ids,generations=()):
    for item in generations:
        try:
            source=UUID(str(item["source_version_id"]))
        except (KeyError,TypeError,ValueError):
            return False
        row=sql(conn,f"""SELECT CASE WHEN v.processed_at IS NOT NULL THEN coalesce(v.active_enrichment_version_id,v.id)::text END AS generation
            FROM document_versions v JOIN documents d ON d.id=v.document_id WHERE {CURRENT} AND v.id=:source""",
            **viewer.access(),source=source).mappings().first()
        if not row or row.generation!=item.get("generation_id"):
            return False
    if not ids:
        return True
    count=sql(conn,f"SELECT count(*) {PASSAGES} WHERE {CURRENT} AND k.id=ANY(:ids)",
              **viewer.access(),ids=[UUID(str(x)) for x in ids]).scalar_one()
    return count==len(set(ids))


def selected_context(viewer,document_ids,limit=24,max_characters=20000):
    """Bounded source overview, including text that has no extracted entities."""
    from fastapi import HTTPException
    ids=[UUID(str(id)) for id in dict.fromkeys(document_ids)]
    if not ids or len(ids)>30:
        raise ValueError("A document overview requires 1 to 30 selected sources.")
    with engine.connect() as conn:
        allowed=sql(conn,f"SELECT count(*) FROM documents d WHERE {ACCESS} AND d.id=ANY(:ids)",
            **viewer.access(),ids=ids).scalar_one()
        if allowed!=len(ids):
            raise HTTPException(404,"A selected source is no longer available.")
        rows=sql(conn,f"""WITH ranked AS (
            SELECT k.id,k.text,k.locator,k.line_number,v.id AS version_id,d.id AS document_id,v.filename,
                CASE WHEN v.processed_at IS NOT NULL THEN coalesce(v.active_enrichment_version_id,v.id)::text END AS enrichment_version_id,
                row_number() OVER(PARTITION BY d.id ORDER BY k.line_number,k.id) AS position,
                count(*) OVER(PARTITION BY d.id) AS total
            {PASSAGES} WHERE {CURRENT} AND d.id=ANY(:ids)
        ) SELECT * FROM ranked WHERE position<=3 OR position=total
            OR position%greatest(1,total/8)=0 ORDER BY document_id,position""",**viewer.access(),ids=ids).mappings().all()
    groups={id:[] for id in ids}
    totals={}
    for row in rows:
        groups[row.document_id].append(dict(row))
        totals[row.document_id]=row.total
    selected=[]
    characters=0
    for index in range(max((len(items) for items in groups.values()),default=0)):
        for id in ids:
            group=groups[id]
            if index<len(group) and len(selected)<limit:
                item=group[index]
                if characters+len(item["text"])<=max_characters:
                    selected.append({key:value for key,value in item.items() if key not in {"position","total"}})
                    selected[-1]["id"]=str(item["id"])
                    selected[-1]["entities"]=[]
                    characters+=len(item["text"])
    coverage=dict(mode="document_overview",selected_sources=len(ids),covered_sources=len({p["document_id"] for p in selected}),
        supplied_passages=len(selected),total_passages=sum(totals.values()),
        partial=len(selected)<sum(totals.values()) or len(totals)<len(ids))
    return selected,coverage
