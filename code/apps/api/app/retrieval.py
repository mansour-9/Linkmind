"""Permission-filtered retrieval shared by search and grounded chat."""
import json
import os
from collections import defaultdict
from uuid import UUID
from app.db import engine,sql
from app.providers import configured,embed
from app.source_access import ACCESS,CURRENT,PASSAGES
from app.repository import filter_clause
from app.query_language import search_terms,people_question,CONCEPTS
from app.query_limits import QueryLimitReached

def search(viewer,query,document_ids=None,semantic=True,filters=None,limit=12,offset=0,diagnostics=None):
    query=query.strip()
    if not query:
        return []
    from app.connectors import refresh_access
    refresh_access(viewer,document_ids,query=query)
    params={**viewer.access(),"q":query,"pattern":"%"+query.replace("%","\\%").replace("_","\\_")+"%"}
    where=CURRENT
    if document_ids:
        where+=" AND d.id=ANY(:documents)"
        params["documents"]=[UUID(str(x)) for x in document_ids]
    filters=filters or {}
    if filters.get("kind"):
        where+=" AND EXISTS(SELECT 1 FROM live_entities fe WHERE fe.version_id=v.id AND fe.kind=:entity_kind)"
        params["entity_kind"]=filters["kind"]
    where+=filter_clause(filters,params)
    with engine.connect() as conn:
        tokens=search_terms(query)
        bilingual=sql(conn,f"""SELECT k.id,ts_rank_cd(k.search_simple,websearch_to_tsquery('simple',:bilingual)) AS score
            {PASSAGES} WHERE {where} AND k.search_simple@@websearch_to_tsquery('simple',:bilingual)
            ORDER BY score DESC,k.id LIMIT 40""",**params,bilingual=' OR '.join(tokens)).all() if tokens else []
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
        metadata=sql(conn,f"""SELECT k.id {PASSAGES} WHERE {where} AND
            (d.title ILIKE :pattern OR EXISTS(SELECT 1 FROM repository_groups rg
              WHERE rg.organization_id=d.organization_id AND rg.id IN (d.project_id,d.team_id) AND rg.name ILIKE :pattern))
            ORDER BY k.line_number,k.id LIMIT 40""",**params).all()
    rankings=[lexical,exact,graph,metadata,bilingual]
    semantic_ranking=[]
    vector=None
    semantic_status="not_requested" if not semantic else "unavailable"
    if semantic and configured() and os.getenv("BEDROCK_EMBEDDING_MODEL"):
        try:
            vector=embed(query,dict(org=viewer.organization_id,user=viewer.id))
            semantic_status="ready" if vector else "unavailable"
        except QueryLimitReached:
            raise
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
            CASE WHEN v.processed_at IS NOT NULL AND EXISTS(SELECT 1 FROM live_entities ge
                WHERE ge.version_id=v.id AND ge.organization_id=d.organization_id)
                THEN coalesce(v.active_enrichment_version_id,v.id)::text END AS enrichment_version_id,
            (SELECT coalesce(jsonb_agg(DISTINCT jsonb_build_object('canonical_id',e.canonical_id,'name',e.name,'kind',e.kind)),'[]'::jsonb)
             FROM live_entities e WHERE e.version_id=v.id AND e.organization_id=d.organization_id) AS entities
            {PASSAGES} WHERE {where} AND k.id=ANY(:ids)""",**params,ids=ids).mappings().all()
    return [{**dict(row),"id":str(row.id),"score":scores[row.id],"semantic_status":semantic_status}
            for row in sorted(rows,key=lambda r:ids.index(r.id))]

def dependencies_allowed(conn,viewer,ids,generations=(),historical=()):
    if ids:
        from app.connectors import refresh_access
        documents=sql(conn,'''SELECT DISTINCT v.document_id FROM chunks k JOIN document_versions v ON v.id=k.version_id
            WHERE k.id=ANY(:ids)''',ids=[UUID(str(x)) for x in ids]).scalars().all()
        refresh_access(viewer,documents)
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
    historical_ids=set()
    try:
        for item in historical:
            passage_id=str(UUID(str(item['passage_id'])))
            if passage_id in historical_ids or passage_id not in {str(id) for id in ids}:
                return False
            allowed=sql(conn,f"""SELECT 1 {PASSAGES} WHERE {ACCESS} AND k.id=:passage
                AND v.id=:version AND d.id=:document AND d.current_version_id=:anchor
                AND v.id<>d.current_version_id AND v.source_version_id IS NULL AND v.search_ready_at IS NOT NULL""",
                **viewer.access(),passage=UUID(passage_id),version=UUID(str(item['version_id'])),
                document=UUID(str(item['document_id'])),anchor=UUID(str(item['current_version_id']))).scalar()
            if not allowed:
                return False
            historical_ids.add(passage_id)
    except (KeyError,ValueError,TypeError):
        return False
    ids=[id for id in ids if str(id) not in historical_ids]
    if not ids:
        return True
    count=sql(conn,f"SELECT count(*) {PASSAGES} WHERE {CURRENT} AND k.id=ANY(:ids)",
              **viewer.access(),ids=[UUID(str(x)) for x in ids]).scalar_one()
    return count==len(set(ids))


def selected_context(viewer,document_ids,limit=24,max_characters=20000,question=None):
    evidence,coverage,_=_source_context(viewer,document_ids,limit,max_characters,question,False)
    return evidence,coverage


def historical_context(viewer,document_ids,limit=24,max_characters=20000,question=None):
    return _source_context(viewer,document_ids,limit,max_characters,question,True)


def _source_context(viewer,document_ids,limit,max_characters,question,include_previous):
    """Bounded original passages; role matches first and fair source/version coverage."""
    from fastapi import HTTPException
    ids=[UUID(str(id)) for id in dict.fromkeys(document_ids)]
    from app.connectors import refresh_access
    refresh_access(viewer,ids)
    if not ids or len(ids)>30:
        raise ValueError("A document overview requires 1 to 30 selected sources.")
    with engine.connect() as conn:
        allowed=sql(conn,f"SELECT count(*) FROM documents d WHERE {ACCESS} AND d.id=ANY(:ids)",
            **viewer.access(),ids=ids).scalar_one()
        if allowed!=len(ids):
            raise HTTPException(404,"A selected source is no longer available.")
        where=CURRENT
        if include_previous:
            where=ACCESS+""" AND v.source_version_id IS NULL AND v.search_ready_at IS NOT NULL AND
                (v.id=d.current_version_id OR v.id=(SELECT prior.id FROM document_versions prior
                    JOIN document_versions current ON current.id=d.current_version_id
                    WHERE prior.document_id=d.id AND prior.source_version_id IS NULL AND prior.search_ready_at IS NOT NULL
                    AND (prior.created_at,prior.id)<(current.created_at,current.id)
                    ORDER BY prior.created_at DESC,prior.id DESC LIMIT 1))"""
        rows=sql(conn,f"""WITH ranked AS (
            SELECT k.id,k.text,k.locator,k.line_number,v.id AS version_id,d.id AS document_id,v.filename,
                d.current_version_id,
                NULL::text AS enrichment_version_id,
                row_number() OVER(PARTITION BY d.id,v.id ORDER BY
                    CASE WHEN :has_question THEN k.search_simple@@websearch_to_tsquery('simple',:context_terms) ELSE false END DESC,
                    k.line_number,k.id) AS position,
                count(*) OVER(PARTITION BY d.id,v.id) AS total
            {PASSAGES} WHERE {where} AND d.id=ANY(:ids)
        ) SELECT * FROM ranked WHERE position<=CASE WHEN :has_question THEN 24 ELSE 3 END OR position=total
            OR position%greatest(1,total/8)=0 ORDER BY document_id,version_id,position""",**viewer.access(),ids=ids,
            has_question=bool(question),context_terms=' OR '.join(CONCEPTS['people'] if question and people_question(question) else search_terms(question)) if question else '').mappings().all()
    groups={}
    totals={}
    for row in rows:
        key=(row.document_id,row.version_id)
        groups.setdefault(key,[]).append(dict(row))
        totals[key]=row.total
    selected=[]
    characters=0
    for index in range(max((len(items) for items in groups.values()),default=0)):
        for group in groups.values():
            if index<len(group) and len(selected)<limit:
                item=group[index]
                if characters+len(item["text"])<=max_characters:
                    selected.append({key:value for key,value in item.items() if key not in {"position","total","current_version_id"}})
                    selected[-1]["id"]=str(item["id"])
                    selected[-1]["entities"]=[]
                    selected[-1]['revision_role']='current' if item['version_id']==item['current_version_id'] else 'previous'
                    characters+=len(item["text"])
    coverage=dict(mode="document_overview",selected_sources=len(ids),covered_sources=len({p["document_id"] for p in selected}),
        supplied_passages=len(selected),total_passages=sum(totals.values()),
        partial=len(selected)<sum(totals.values()) or len({k[0] for k in totals})<len(ids))
    historical=[]
    if include_previous:
        coverage['mode']='revision_comparison'
        coverage['compared_versions']=len(totals)
        for p in selected:
            if p['revision_role']=='previous':
                row=next(r for r in rows if str(r['id'])==p['id'])
                historical.append(dict(passage_id=p['id'],version_id=str(p['version_id']),
                    document_id=str(p['document_id']),current_version_id=str(row['current_version_id'])))
    return selected,coverage,historical


def adjacent_context(viewer,passages,limit=8):
    """Neighbors preserve original IDs, source/current checks and boundary citations."""
    if not passages:
        return []
    ids=[UUID(str(p['id'])) for p in passages[:12]]
    with engine.connect() as conn:
        rows=sql(conn,f"""SELECT k.id,k.text,k.locator,k.line_number,v.id AS version_id,d.id AS document_id,v.filename,
            NULL::text AS enrichment_version_id {PASSAGES}
            WHERE {CURRENT} AND EXISTS(SELECT 1 FROM chunks anchor WHERE anchor.id=ANY(:ids)
                AND anchor.version_id=v.id AND abs(anchor.line_number-k.line_number)<=1)
            AND NOT k.id=ANY(:ids) ORDER BY k.line_number,k.id LIMIT :limit""",**viewer.access(),ids=ids,limit=limit).mappings()
        return [{**dict(row),'id':str(row.id),'entities':[]} for row in rows]
