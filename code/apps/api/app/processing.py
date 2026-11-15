"""Leased processing. Model calls occur outside the publication transaction."""
import hashlib
import json
import logging
import os
from uuid import UUID, uuid4, uuid5
from pydantic import ValidationError
from app.artifacts import resolve
from app.contracts import Extraction, validate_extraction
from app.db import engine, sql
from app.fixture_provider import recognize
from app.parsers import parse_document
from app.providers import configured, extract_bedrock_batches, embed, ProviderUnavailable
from app.inference_budget import BudgetStopped
from app import enrichment_staging as staging

log=logging.getLogger(__name__)
MAX_ATTEMPTS=3

def mock_extract(content,passages):
    from app.company_demo import extract_fixture
    company=extract_fixture(content,passages)
    if company is not None:
        return company
    fixture=recognize(content)
    if fixture is None:
        from app.graph_demo import graph_demo_records
        expected=graph_demo_records(content)
        if expected is not None:
            lines=content.decode("utf-8").splitlines()
            byline={p["locator"].get("line"):p for p in passages if p["locator"].get("offset",0)==0}
            data={}
            for group in ("entities","claims","relationships"):
                data[group]=[]
                for record in expected[group]:
                    record=dict(record)
                    line=record.pop("line")
                    passage=byline.get(line)
                    quote=lines[line-1]
                    if passage is None or quote not in passage["text"]:
                        raise ValueError(f"Graph demo citation line {line} does not match its source passage.")
                    data[group].append({**record,"evidence":[{"passage_id":passage["id"],"quote":quote}]})
            return validate_extraction(Extraction(**data),passages)
        from pathlib import Path
        root=Path(__file__).resolve().parents[3]/"fixtures"/"benchmark"
        manifest=json.loads((root/"manifest.json").read_text())
        expected=next((x for x in manifest["fixtures"] if (root/x["filename"]).read_bytes()==content),None)
        if expected is None:
            raise ProviderUnavailable("No mock fixture matches this file. Configure Bedrock for arbitrary files.")
        byline={p["locator"].get("line"):p for p in passages}
        data={}
        for group in ("entities","claims","relationships"):
            data[group]=[]
            for item in expected[group]:
                item=dict(item)
                passage=byline[item.pop("line")]
                data[group].append({**item,"evidence":[{"passage_id":passage["id"],"quote":passage["text"]}]})
        return validate_extraction(Extraction(**data),passages)
    byline={p["locator"].get("line"):p for p in passages}
    def citation(line):
        p=byline[line]
        return [{"passage_id":p["id"],"quote":p["text"]}]
    entities=[]
    for key,kind,name in fixture.entities:
        line=next((x[3] for x in fixture.claims if x[0]==key),None)
        line=line or next((x[3] for x in fixture.relationships if key in x[:2]),3)
        entities.append(dict(key=key,kind=kind,name=name,identifiers=[],evidence=citation(line)))
    return validate_extraction(Extraction(entities=entities,
        claims=[dict(entity_key=k,predicate=p.lower().replace(" ","_"),value=v,asserted_by=None,
                     effective_from=None,effective_to=None,evidence=citation(n)) for k,p,v,n in fixture.claims],
        relationships=[dict(source_key=s,target_key=t,predicate=p.lower().replace(" ","_"),
                             evidence=citation(n)) for s,t,p,n in fixture.relationships]),passages)

def overlap(a,b):
    return not (a["effective_to"] and b["effective_from"] and a["effective_to"]<b["effective_from"]
             or b["effective_to"] and a["effective_from"] and b["effective_to"]<a["effective_from"])

def set_stage(job,stage):
    with engine.begin() as conn:
        changed=sql(conn,"""UPDATE processing_jobs SET stage=:stage,lease_until=now()+interval '15 minutes'
           WHERE id=:id AND lease_token=:lease AND status='processing'
           AND lease_until>clock_timestamp() RETURNING id""",
           stage=stage,id=job.id,lease=job.lease_token).first()
        if not changed:
            raise RuntimeError("Processing lease was replaced.")
        sql(conn,"UPDATE processing_attempts SET stage=:stage WHERE id=:attempt",stage=stage,attempt=job.attempt_id)

def canonical(conn,job,item):
    found=set()
    for identifier in item.identifiers:
        existing=sql(conn,"""SELECT canonical_id FROM entity_identifiers
            WHERE organization_id=:org AND kind=:kind AND namespace=:namespace AND value=:value""",
            org=job.organization_id,kind=item.kind,namespace=identifier.namespace,
            value=identifier.value.strip().casefold()).scalar_one_or_none()
        if existing:
            found.add(existing)
    if not found and not item.identifiers and getattr(job,"staged_version_id",None):
        # Exact anchors in the same immutable source preserve reviewed identity;
        # similar names across sources remain unconfirmed.
        anchored={(UUID(c.passage_id),c.quote) for c in item.evidence}
        prior=sql(conn,"""SELECT id,canonical_id FROM live_entities WHERE organization_id=:org
            AND version_id=:source AND kind=:kind AND name=:name""",org=job.organization_id,
            source=job.version_id,kind=item.kind,name=item.name).mappings()
        for occurrence in prior:
            evidence=set(sql(conn,'SELECT chunk_id,quote FROM entity_evidence WHERE entity_id=:id',id=occurrence.id).all())
            if evidence==anchored:
                found.add(occurrence.canonical_id)
    # Ambiguous identifiers are never merged automatically.
    entity_id=next(iter(found)) if len(found)==1 else uuid4()
    if not found or len(found)>1:
        sql(conn,"INSERT INTO canonical_entities(id,organization_id,kind) VALUES(:id,:org,:kind)",
            id=entity_id,org=job.organization_id,kind=item.kind)
    if len(found)<=1:
        for identifier in item.identifiers:
            sql(conn,"""INSERT INTO entity_identifiers(organization_id,canonical_id,kind,namespace,value)
                 VALUES(:org,:id,:kind,:namespace,:value) ON CONFLICT DO NOTHING""",
                 org=job.organization_id,id=entity_id,kind=item.kind,namespace=identifier.namespace,
                 value=identifier.value.strip().casefold())
    return entity_id

def publication_guard(conn,job,require_search=False):
    # Match revision/access mutations' document -> job lock order. A new upload
    # cannot be inserted while its document's publication decision is in flight.
    document=sql(conn,"""SELECT d.id,d.current_version_id FROM documents d
        JOIN document_versions v ON v.document_id=d.id WHERE v.id=:version
        AND d.organization_id=:org AND d.deleted_at IS NULL FOR UPDATE OF d""",
        version=job.version_id,org=job.organization_id).mappings().first()
    lease=sql(conn,"""SELECT id FROM processing_jobs WHERE id=:id
        AND version_id=:version AND organization_id=:org AND lease_token=:lease
        AND status='processing' AND lease_until>clock_timestamp()
        AND staged_version_id IS NOT DISTINCT FROM :staged FOR UPDATE""",
        id=job.id,version=job.version_id,org=job.organization_id,lease=job.lease_token,
        staged=getattr(job,"staged_version_id",None)).first()
    newer=sql(conn,"""SELECT 1 FROM document_versions v JOIN document_versions newer
        ON newer.document_id=v.document_id AND (newer.created_at,newer.id)>(v.created_at,v.id)
        WHERE v.id=:version AND newer.source_version_id IS NULL LIMIT 1""",version=job.version_id).first()
    if not document or not lease or newer or (require_search and document.current_version_id!=job.version_id):
        raise ValueError("Document was deleted, superseded, or processing lease expired.")


def publish_content(conn,job,embedding_status):
    publication_guard(conn,job)
    sql(conn,"""UPDATE document_versions SET search_ready_at=coalesce(search_ready_at,now()),
        embedding_status=:status WHERE id=:version""",version=job.version_id,status=embedding_status)
    sql(conn,"UPDATE documents SET current_version_id=:version WHERE id=:id",
        version=job.version_id,id=job.document_id)


def publish(conn,job,result,passages,provider,judgments=None):
    byid={p["id"]:p for p in passages}
    scope=dict(org=job.organization_id,version=job.version_id)
    # Serialize identity resolution and conflicts within a tenant.
    sql(conn,"SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",key=str(job.organization_id))
    publication_guard(conn,job,require_search=True)
    # Retain immutable prior publications; retry of a published version does not duplicate knowledge.
    generation=getattr(job,"staged_version_id",None)
    if sql(conn,"SELECT processed_at FROM document_versions WHERE id=:id",id=generation or job.version_id).scalar():
        return
    result=validate_extraction(result,passages)
    staging.activation_guard(conn,job,result)
    ids={}
    canonical_ids={}
    for item in result.entities:
        cid=canonical(conn,job,item)
        eid=uuid4()
        ids[item.key]=eid
        canonical_ids[item.key]=cid
        sql(conn,"""INSERT INTO entities(id,organization_id,version_id,kind,name,canonical_id,enrichment_version_id)
             VALUES(:id,:org,:version,:kind,:name,:canonical,:generation)""",**scope,id=eid,kind=item.kind,name=item.name,canonical=cid,generation=generation)
        for cite in item.evidence:
            start=byid[cite.passage_id]["text"].index(cite.quote)
            sql(conn,"""INSERT INTO entity_evidence(id,organization_id,entity_id,chunk_id,quote,span_start,span_end)
                VALUES(:id,:org,:entity,:chunk,:quote,:start,:end) ON CONFLICT DO NOTHING""",
                id=uuid4(),org=job.organization_id,entity=eid,chunk=UUID(cite.passage_id),quote=cite.quote,
                start=start,end=start+len(cite.quote))
        sql(conn,"""INSERT INTO entity_aliases(id,organization_id,canonical_id,occurrence_id,alias)
             VALUES(:id,:org,:canonical,:occurrence,:alias)""",
             id=uuid4(),org=job.organization_id,canonical=cid,occurrence=eid,alias=item.name)
        candidates=sql(conn,"""SELECT DISTINCT canonical_id FROM live_entities
             WHERE organization_id=:org AND kind=:kind AND lower(name)=lower(:name)
             AND canonical_id<>:id LIMIT 10""",org=job.organization_id,kind=item.kind,name=item.name,id=cid).scalars()
        for candidate in candidates:
            sql(conn,"""INSERT INTO resolution_candidates(id,organization_id,occurrence_id,candidate_id,reason)
                 VALUES(:id,:org,:occurrence,:candidate,'Same name only; requires human review.')""",
                 id=uuid4(),org=job.organization_id,occurrence=eid,candidate=candidate)
    def evidence(table,key,parent,citations):
        for cite in citations:
            start=byid[cite.passage_id]["text"].index(cite.quote)
            sql(conn,f"""INSERT INTO {table}(id,organization_id,{key},chunk_id,quote,span_start,span_end)
                VALUES(:id,:org,:parent,:chunk,:quote,:start,:end) ON CONFLICT DO NOTHING""",
                id=uuid4(),org=job.organization_id,parent=parent,chunk=UUID(cite.passage_id),
                quote=cite.quote,start=start,end=start+len(cite.quote))
    new_claims=[]
    for item in result.claims:
        cid=uuid4()
        sql(conn,"""INSERT INTO claims(id,organization_id,version_id,entity_id,chunk_id,predicate,value,
            provider,value_json,asserted_by,effective_from,effective_to,verification_status)
            VALUES(:id,:org,:version,:entity,:chunk,:predicate,:value,:provider,CAST(:typed AS jsonb),
              :by,:start,:end,'evidence_validated')""",**scope,id=cid,entity=ids[item.entity_key],
            chunk=UUID(item.evidence[0].passage_id),predicate=item.predicate,value=item.value,provider=provider,
            typed=json.dumps({"type":"date" if item.predicate.endswith("_date") or item.predicate=="deadline" else "string","value":item.value}),
            by=item.asserted_by,start=item.effective_from,end=item.effective_to)
        evidence("claim_evidence","claim_id",cid,item.evidence)
        new_claims.append((cid,canonical_ids[item.entity_key],item))
    for item in result.relationships:
        rid=uuid4()
        sql(conn,"""INSERT INTO relationships(id,organization_id,version_id,source_id,target_id,chunk_id,predicate,effective_from,effective_to)
            VALUES(:id,:org,:version,:source,:target,:chunk,:predicate,:start,:end)""",**scope,id=rid,
            source=ids[item.source_key],target=ids[item.target_key],chunk=UUID(item.evidence[0].passage_id),predicate=item.predicate,start=item.effective_from,end=item.effective_to)
        evidence("relationship_evidence","relationship_id",rid,item.evidence)
    staging.activate(conn,job,provider)
    # Only intrinsically single-valued attributes are automatic conflict candidates.
    # Free-form decisions and descriptions remain separate attributed claims.
    for index,(cid,entity,item) in enumerate(new_claims):
        if item.predicate not in {"owner","status","deadline","target_database","managed_by","budget","launch_date"}:
            continue
        others=sql(conn,"""SELECT c.* FROM live_claims c JOIN live_entities e ON e.id=c.entity_id
            JOIN document_versions v ON v.id=c.version_id JOIN documents d ON d.id=v.document_id
            WHERE e.organization_id=:org AND e.canonical_id=:canonical AND c.predicate=:predicate
              AND c.id<>:id AND lower(trim(c.value))<>lower(trim(:value))
              AND d.deleted_at IS NULL AND d.current_version_id=v.id""",
            org=job.organization_id,canonical=entity,predicate=item.predicate,id=cid,value=item.value).mappings()
        for other in others:
            if overlap(item.model_dump(),other):
                judgment=(judgments or {}).get(f"{index}:{other.id}")
                if judgment is not None and not judgment.conflict:
                    continue
                left,right=sorted([cid,other.id],key=str)
                sql(conn,"""INSERT INTO conflicts(id,organization_id,canonical_id,predicate,left_claim_id,
                   right_claim_id,rationale) VALUES(:id,:org,:canonical,:predicate,:left,:right,:rationale)
                   ON CONFLICT DO NOTHING""",id=uuid4(),org=job.organization_id,canonical=entity,
                   predicate=item.predicate,left=left,right=right,
                   rationale=judgment.rationale if judgment else "Different values for a single-valued attribute with overlapping or unspecified effective periods; human review required.")
    sql(conn,"""UPDATE document_versions SET processed_at=now(),extraction_provider=:provider WHERE id=:version""",
        provider=provider,version=job.version_id)

def process_one():
    with engine.begin() as conn:
        # Recover abandoned leases without permitting unlimited worker retries.
        # Lock jobs before attempts, matching completion. Multiple workers must
        # neither recover the same lease nor deadlock a completing worker.
        expired_rows=sql(conn,"""SELECT id,staged_version_id FROM processing_jobs WHERE status='processing'
            AND lease_until<clock_timestamp() FOR UPDATE SKIP LOCKED""").mappings().all()
        expired=[row.id for row in expired_rows]
        if expired:
            for row in expired_rows:
                staging.rollback(conn,row.staged_version_id)
            sql(conn,"""UPDATE processing_attempts SET status='abandoned',error='Worker lease expired.',finished_at=now()
                WHERE job_id=ANY(:ids) AND status='processing'""",ids=expired)
            sql(conn,"""UPDATE processing_jobs SET status=CASE WHEN attempts<3 THEN 'queued'
                WHEN staged_version_id IS NOT NULL THEN 'enrichment_staged_failed' ELSE 'failed' END,
                lease_token=NULL,error='Worker lease expired.',error_code='lease_expired'
                WHERE id=ANY(:ids)""",ids=expired)
        row=sql(conn,"""SELECT j.*,v.artifact_key,v.filename,v.document_id,v.search_ready_at,v.processed_at,v.embedding_status FROM processing_jobs j
            JOIN document_versions v ON v.id=j.version_id JOIN documents d ON d.id=v.document_id
            WHERE j.status='queued' AND j.available_at<=clock_timestamp() AND d.deleted_at IS NULL
            ORDER BY j.available_at,j.created_at LIMIT 1 FOR UPDATE OF j SKIP LOCKED""").mappings().first()
        if row is None:
            return False
        job=dict(row)
        if job.get("staged_version_id"):
            state=sql(conn,"SELECT activation_state FROM document_versions WHERE id=:id",id=job["staged_version_id"]).scalar_one()
            if state!='staged':
                job["staged_version_id"]=staging.create(conn,job)
                sql(conn,"UPDATE processing_jobs SET staged_version_id=:staged WHERE id=:id",staged=job["staged_version_id"],id=job["id"])
        job.update(lease_token=uuid4(),attempt_id=uuid4(),attempts=row.attempts+1)
        sql(conn,"""UPDATE processing_jobs SET status='processing',stage='parsing',attempts=:attempts,
            lease_token=:lease_token,lease_until=now()+interval '15 minutes',error=NULL WHERE id=:id""",
            **{k:job[k] for k in ["id","attempts","lease_token"]})
        sql(conn,"""INSERT INTO processing_attempts(id,organization_id,job_id,attempt,stage,status)
             VALUES(:id,:org,:job,:attempt,'parsing','processing')""",
             id=job["attempt_id"],org=row.organization_id,job=row.id,attempt=job["attempts"])
    from types import SimpleNamespace
    job=SimpleNamespace(**job)
    status="ready"
    error=None
    code=None
    try:
        content=resolve(job.artifact_key).read_bytes()
        if hashlib.sha256(content).hexdigest()!=job.checksum:
            raise ValueError("Artifact checksum mismatch.")
        from app.graph_demo import graph_demo_records
        is_graph_demo=graph_demo_records(content) is not None
        use_bedrock=configured() and not is_graph_demo
        scope=dict(org=job.organization_id,user=job.owner_id,version=job.version_id,attempt=job.attempt_id)
        if job.search_ready_at:
            # Enrichment retries reuse published evidence verbatim, including its IDs.
            with engine.begin() as conn:
                publication_guard(conn,job,require_search=True)
                passages=[dict(id=str(p.id),text=p.text,locator=p.locator) for p in sql(conn,
                    "SELECT id,text,locator FROM chunks WHERE version_id=:id ORDER BY line_number,id",
                    id=job.version_id).mappings()]
            if job.embedding_status=="pending" and not job.staged_version_id:
                index_passages(job,passages,scope,is_graph_demo)
        else:
            passages=prepare_content(job,content,scope,is_graph_demo)
        if job.enrichment_requested and (not job.processed_at or job.staged_version_id):
            enrich(job,content,passages,scope,use_bedrock,is_graph_demo)
    except (ProviderUnavailable,BudgetStopped) as exc:
        status="extraction_unavailable"
        error=str(exc)
        code="test_budget_stopped" if isinstance(exc,BudgetStopped) else "provider_unavailable"
    except Exception as exc:
        code=getattr(exc,"response",{}).get("Error",{}).get("Code",type(exc).__name__)
        log.warning("Job %s attempt %s failed: %s",job.id,job.attempts,code)
        error="The model response did not match the required schema. No unverified knowledge was published." if isinstance(exc,ValidationError) else str(exc)[:300] if isinstance(exc,ValueError) else f"Processing failed ({code}). Check model access, file content, and worker configuration."
        status="failed" if job.attempts>=MAX_ATTEMPTS or code in {"AccessDeniedException","ValidationException","ModelResponseError","EvidenceValidationError","ValueError"} else "queued"
    if job.staged_version_id and status not in {"ready","cancelled"}:
        status="enrichment_staged_failed"
    with engine.begin() as conn:
        changed=sql(conn,"""UPDATE processing_jobs SET status=:status,stage=:stage,error=:error,error_code=:code,
           finished_at=now(),lease_until=NULL,available_at=now()+interval '10 seconds'
           WHERE id=:id AND lease_token=:lease AND status='processing'
           AND lease_until>clock_timestamp() RETURNING id""",id=job.id,lease=job.lease_token,status=status,
           stage="complete" if status=="ready" else status,error=error,code=code).first()
        sql(conn,"""UPDATE processing_attempts SET status=:status,error=:error,finished_at=now()
            WHERE id=:id AND status='processing'""",id=job.attempt_id,
            status=status if changed else "abandoned",error=error if changed else "Processing lease expired or was replaced.")
        if job.staged_version_id and status!='ready':
            staging.rollback(conn,job.staged_version_id)
    return True


def prepare_content(job,content,scope,is_graph_demo):
    parsed=parse_document(job.filename,content)
    passages=[dict(id=str(uuid5(job.version_id,str(i))),text=p.text,locator=p.locator) for i,p in enumerate(parsed,1)]
    with engine.begin() as conn:
        publication_guard(conn,job)
        existing=sql(conn,"SELECT id,line_number,text,locator FROM chunks WHERE version_id=:id",id=job.version_id).mappings().all()
        def signature(text,locator):
            return text,json.dumps({"offset":0,**locator},sort_keys=True)
        old={signature(p.text,p.locator):p for p in existing}
        occupied_ids={str(p.id) for p in existing}
        next_line=max((p.line_number for p in existing),default=0)
        for p in passages:
            match=old.get(signature(p["text"],p["locator"]))
            if match:
                p["id"]=str(match.id)
                continue
            if p["id"] in occupied_ids:
                p["id"]=str(uuid5(job.version_id,json.dumps(signature(p["text"],p["locator"]))))
            next_line+=1
            sql(conn,"""INSERT INTO chunks(id,organization_id,version_id,line_number,text,locator)
               VALUES(:id,:org,:version,:line,:text,CAST(:locator AS jsonb)) ON CONFLICT(id) DO NOTHING""",
               id=UUID(p["id"]),org=job.organization_id,version=job.version_id,line=next_line,
               text=p["text"],locator=json.dumps(p["locator"]))
        expected={signature(p["text"],p["locator"]) for p in passages}
        if any(signature(p.text,p.locator) not in expected for p in existing):
            raise ValueError("Stored source passages differ from parsing; explicit reprocessing is required.")
    # Publish lexical availability first. Optional semantic work cannot gate source use.
    set_stage(job,"publishing_content")
    with engine.begin() as conn:
        publish_content(conn,job,"pending")
    index_passages(job,passages,scope,is_graph_demo)
    return passages


def index_passages(job,passages,scope,is_graph_demo):
    """Resume indexing and reuse compatible unchanged text only within this document."""
    set_stage(job,"embedding")
    embedding_failed=False
    embedded=0
    model=None if is_graph_demo else os.getenv("BEDROCK_EMBEDDING_MODEL")
    dimensions=int(os.getenv("BEDROCK_EMBEDDING_DIMENSIONS","256"))
    for p in passages:
        set_stage(job,"embedding")
        vector=None
        embedding_error=None
        if model:
            with engine.connect() as conn:
                publication_guard(conn,job,require_search=True)
                cached=sql(conn,"""SELECT k.embedding::text FROM chunks k
                    JOIN document_versions v ON v.id=k.version_id
                    WHERE v.organization_id=:org AND v.document_id=:document AND v.source_version_id IS NULL
                    AND k.text=:text AND k.embedding_model=:model AND k.embedding_dimensions=:dimensions
                    AND k.embedding IS NOT NULL AND vector_dims(k.embedding)=:dimensions AND k.embedding_error IS NULL
                    ORDER BY (v.id=:version) DESC,v.created_at DESC,k.id LIMIT 1""",
                    org=job.organization_id,document=job.document_id,version=job.version_id,
                    text=p["text"],model=model,dimensions=dimensions).scalar()
                if cached:
                    vector=json.loads(cached)
        try:
            if vector is None and not is_graph_demo:
                vector=embed(p["text"],scope)
        except Exception as exc:
            embedding_failed=True
            embedding_error=type(exc).__name__
        embedded+=bool(vector)
        with engine.begin() as conn:
            publication_guard(conn,job,require_search=True)
            sql(conn,"""UPDATE chunks SET embedding=CAST(:vector AS vector),embedding_model=:model,
                embedding_dimensions=:dimensions,embedding_error=:error WHERE id=:id""",
                id=UUID(p["id"]),vector=json.dumps(vector) if vector else None,
                model=model if vector else None,
                dimensions=len(vector) if vector else None,error=embedding_error)
    with engine.begin() as conn:
        publication_guard(conn,job,require_search=True)
        sql(conn,"UPDATE document_versions SET embedding_status=:status WHERE id=:version",
            version=job.version_id,status="failed" if embedding_failed else ("ready" if embedded==len(passages) else "unavailable"))


def enrich(job,content,passages,scope,use_bedrock,is_graph_demo):
    set_stage(job,"extracting")
    if is_graph_demo:
        result=mock_extract(content,passages)
        provider="graph-demo-fixture"
    elif use_bedrock:
        result=Extraction(entities=[],claims=[],relationships=[])
        batches=extract_bedrock_batches(passages,scope)
        for index,batch in enumerate(batches):
            # Each independently extracted batch has its own model-local key namespace.
            prefix=f"b{index}:"
            for e in batch.entities: e.key=prefix+e.key
            for c in batch.claims: c.entity_key=prefix+c.entity_key
            for r in batch.relationships:
                r.source_key=prefix+r.source_key
                r.target_key=prefix+r.target_key
            result.entities.extend(batch.entities)
            result.claims.extend(batch.claims)
            result.relationships.extend(batch.relationships)
        # All candidate facts are checked again before staging/atomic activation.
        result=validate_extraction(result,passages)
        provider="bedrock"
    else:
        result=mock_extract(content,passages)
        provider="fixture"
    if job.staged_version_id:
        set_stage(job,"verifying_staged_enrichment")
        with engine.begin() as conn:
            publication_guard(conn,job,require_search=True)
            result=staging.verify(conn,job,result,passages,provider)
    set_stage(job,"checking_conflicts")
    from app.conflict_detection import assess
    judgments=assess(result,job) if use_bedrock else {}
    set_stage(job,"publishing")
    with engine.begin() as conn:
        publish(conn,job,result,passages,provider,judgments)
