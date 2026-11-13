"""Assess source-backed claim pairs before the atomic publication transaction."""
from app.contracts import ConflictJudgments
from app.db import engine,sql
from app.providers import structured,UNTRUSTED
from app.processing_periods import overlap

SINGULAR={"owner","status","deadline","target_database","managed_by","budget","launch_date"}
def assess(result,job):
    pairs=[]
    with engine.connect() as conn:
        for index,item in enumerate(result.claims):
            if item.predicate not in SINGULAR:
                continue
            entity=next(e for e in result.entities if e.key==item.entity_key)
            targets=set()
            for identifier in entity.identifiers:
                targets.update(sql(conn,"""SELECT canonical_id FROM entity_identifiers WHERE organization_id=:org
                    AND kind=:kind AND namespace=:namespace AND value=:value""",org=job.organization_id,
                    kind=entity.kind,namespace=identifier.namespace,value=identifier.value.strip().casefold()).scalars())
            if len(targets)!=1:
                continue
            candidates=sql(conn,"""SELECT c.id,c.value,c.asserted_by,c.effective_from,c.effective_to,k.text AS evidence
                FROM live_claims c JOIN live_entities e ON e.id=c.entity_id JOIN chunks k ON k.id=c.chunk_id
                JOIN document_versions v ON v.id=c.version_id JOIN documents d ON d.id=v.document_id
                WHERE e.organization_id=:org AND e.canonical_id=:id AND c.predicate=:predicate
                AND d.deleted_at IS NULL AND d.current_version_id=v.id AND d.id<>:document""",
                org=job.organization_id,id=next(iter(targets)),predicate=item.predicate,document=job.document_id).mappings()
            for other in candidates:
                if item.value.strip().casefold()!=other.value.strip().casefold() and overlap(item.model_dump(),other):
                    pairs.append(dict(pair_id=f"{index}:{other.id}",left=item.model_dump(),right=dict(other)))
    if not pairs:
        return {}
    if len(pairs)>50:
        raise ValueError("Too many conflict comparisons in one document. Split the document into smaller files.")
    result=structured(ConflictJudgments,UNTRUSTED+
        "Compare each claim pair. Set conflict=true only for mutually incompatible assertions about the same attribute "
        "and overlapping effective period. Complementary detail, equivalent wording, multiple compatible co-owners, "
        "or historical changes are not contradictions. Explain the decision using only the two sources. "
        "Return exactly one judgment for each pair_id.",
        {"pairs":pairs},dict(org=job.organization_id,user=job.owner_id,version=job.version_id,attempt=job.attempt_id),"conflict_detection")
    expected={p["pair_id"] for p in pairs}
    if len(result.judgments)!=len(expected) or {j.pair_id for j in result.judgments}!=expected:
        raise ValueError("Conflict assessment references do not match source claim pairs.")
    return {j.pair_id:j for j in result.judgments}
