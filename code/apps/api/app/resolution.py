"""Explicit, permission-checked review of uncertain entity identities."""
from uuid import UUID,uuid4
from fastapi import HTTPException
from app.db import sql
from app.retrieval import CURRENT
from app.processing_periods import overlap

QUERY=f"""WITH visible AS (
 SELECT e.*,v.id AS source_version_id FROM live_entities e JOIN document_versions v ON v.id=e.version_id
 JOIN documents d ON d.id=v.document_id WHERE {CURRENT}
) SELECT DISTINCT ON(rc.id) rc.*,s.name AS source_name,t.name AS candidate_name,
 s.canonical_id AS source_canonical_id,s.kind AS source_kind,t.kind AS target_kind
 FROM resolution_candidates rc JOIN visible s ON s.id=rc.occurrence_id
 JOIN visible t ON t.canonical_id=rc.candidate_id WHERE rc.organization_id=:org"""

def candidates(conn,viewer):
    return [dict(r) for r in sql(conn,QUERY+" ORDER BY rc.id",**viewer.access()).mappings()]

def review(conn,viewer,id,action,rationale):
    sql(conn,"SELECT id FROM resolution_candidates WHERE id=:id FOR UPDATE",id=id)
    row=sql(conn,QUERY+" AND rc.id=:id",**viewer.access(),id=id).mappings().first()
    if not row: raise HTTPException(404,"Resolution candidate not found.")
    if row.status!="open": raise HTTPException(409,"This candidate was already reviewed.")
    if row.source_kind!=row.target_kind: raise HTTPException(422,"Different entity types cannot be merged.")
    if action=="merge":
        # A reviewer must be allowed to see every occurrence affected by a merge.
        hidden=sql(conn,f"""SELECT count(*) FROM live_entities e JOIN document_versions v ON v.id=e.version_id
           JOIN documents d ON d.id=v.document_id WHERE e.organization_id=:org
           AND e.canonical_id=ANY(:ids) AND d.deleted_at IS NULL
           AND NOT (d.owner_id=:viewer OR d.visibility='team')""",
           **viewer.access(),ids=[row.source_canonical_id,row.candidate_id]).scalar()
        if hidden: raise HTTPException(403,"A merge would affect sources you cannot access.")
        sql(conn,"SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",key=str(viewer.organization_id))
        if row.source_canonical_id==row.candidate_id:
            raise HTTPException(409,"These identities were already merged.")
        sql(conn,"INSERT INTO canonical_redirects(organization_id,source_id,target_id) VALUES(:org,:source,:target) ON CONFLICT(organization_id,source_id) DO UPDATE SET target_id=excluded.target_id",org=viewer.organization_id,source=row.source_canonical_id,target=row.candidate_id)
        for table in ("entities","entity_identifiers","entity_aliases","conflicts"):
            sql(conn,f"UPDATE {table} SET canonical_id=:target WHERE organization_id=:org AND canonical_id=:source",
                org=viewer.organization_id,target=row.candidate_id,source=row.source_canonical_id)
        # Newly connected claims remain attributed. Potential disagreements require review.
        pairs=sql(conn,"""SELECT a.id AS left_id,b.id AS right_id,a.predicate,
            a.effective_from AS a_from,a.effective_to AS a_to,b.effective_from AS b_from,b.effective_to AS b_to
            FROM live_claims a JOIN live_entities ea ON ea.id=a.entity_id JOIN document_versions va ON va.id=a.version_id
            JOIN documents da ON da.id=va.document_id JOIN live_claims b ON b.organization_id=a.organization_id
            JOIN live_entities eb ON eb.id=b.entity_id JOIN document_versions vb ON vb.id=b.version_id
            JOIN documents db ON db.id=vb.document_id
            WHERE ea.canonical_id=:id AND eb.canonical_id=:id AND a.organization_id=:org
            AND a.id<b.id AND a.predicate=b.predicate AND lower(trim(a.value))<>lower(trim(b.value))
            AND da.current_version_id=va.id AND db.current_version_id=vb.id
            AND da.deleted_at IS NULL AND db.deleted_at IS NULL
            AND a.predicate IN ('owner','status','deadline','launch_date','budget','target_database','managed_by')""",
            id=row.candidate_id,org=viewer.organization_id).mappings()
        for pair in pairs:
            if overlap(dict(effective_from=pair.a_from,effective_to=pair.a_to),dict(effective_from=pair.b_from,effective_to=pair.b_to)):
                sql(conn,"""INSERT INTO conflicts(id,organization_id,canonical_id,predicate,left_claim_id,right_claim_id,status,rationale)
                    VALUES(:id,:org,:canonical,:predicate,:left,:right,'needs_evidence',
                    'Identity was merged by a reviewer. These differing attributed claims require evidence review.') ON CONFLICT DO NOTHING""",
                    id=uuid4(),org=viewer.organization_id,canonical=row.candidate_id,predicate=pair.predicate,
                    left=pair.left_id,right=pair.right_id)
    sql(conn,"UPDATE resolution_candidates SET status=:status WHERE id=:id",id=id,status="merged" if action=="merge" else "rejected")
    sql(conn,"""INSERT INTO entity_resolution_reviews(id,organization_id,candidate_id,reviewer_id,action,rationale)
        VALUES(:id,:org,:candidate,:user,:action,:rationale)""",id=uuid4(),org=viewer.organization_id,
        candidate=id,user=viewer.id,action=action,rationale=rationale)
    return {"status":"merged" if action=="merge" else "rejected"}
