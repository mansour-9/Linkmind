"""Canonical knowledge, versioned evidence, retrieval and operational records."""
from alembic import op

revision = "0002_knowledge"
down_revision = "0001_m1"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE users ADD COLUMN role text NOT NULL DEFAULT 'member' CHECK (role IN ('member','reviewer','admin'));
UPDATE users SET role='admin' WHERE id='00000000-0000-4000-8000-000000000101';
ALTER TABLE documents ADD COLUMN deleted_at timestamptz;
ALTER TABLE documents ADD COLUMN current_version_id uuid;
ALTER TABLE document_versions ADD COLUMN filename text;
UPDATE document_versions v SET filename=d.filename FROM documents d WHERE d.id=v.document_id;
ALTER TABLE document_versions ALTER COLUMN filename SET NOT NULL;
ALTER TABLE document_versions ADD COLUMN processed_at timestamptz;
ALTER TABLE document_versions ADD COLUMN extraction_provider text;
ALTER TABLE document_versions ADD COLUMN embedding_status text NOT NULL DEFAULT 'pending';
UPDATE documents d SET current_version_id=(SELECT v.id FROM document_versions v WHERE v.document_id=d.id ORDER BY v.created_at DESC, v.id DESC LIMIT 1);
ALTER TABLE documents ADD CONSTRAINT current_version_fk FOREIGN KEY (organization_id,current_version_id) REFERENCES document_versions(organization_id,id);
ALTER TABLE processing_jobs DROP CONSTRAINT processing_jobs_organization_id_owner_id_checksum_key;
ALTER TABLE processing_jobs DROP CONSTRAINT processing_jobs_status_check;
ALTER TABLE processing_jobs ADD CONSTRAINT processing_jobs_status_check CHECK (status IN ('queued','processing','ready','extraction_unavailable','failed','cancelled'));
ALTER TABLE processing_jobs ADD COLUMN stage text NOT NULL DEFAULT 'queued';
ALTER TABLE processing_jobs ADD COLUMN lease_token uuid;
ALTER TABLE processing_jobs ADD COLUMN lease_until timestamptz;
ALTER TABLE processing_jobs ADD COLUMN finished_at timestamptz;
ALTER TABLE processing_jobs ADD COLUMN error_code text;
ALTER TABLE chunks ADD COLUMN locator jsonb NOT NULL DEFAULT '{}';
UPDATE chunks SET locator=jsonb_build_object('kind','text','line',line_number);
ALTER TABLE chunks ADD COLUMN search_text tsvector GENERATED ALWAYS AS (to_tsvector('english',text)) STORED;
CREATE INDEX chunks_search ON chunks USING gin(search_text);
ALTER TABLE chunks ADD COLUMN embedding vector;
ALTER TABLE chunks ADD COLUMN embedding_model text;
ALTER TABLE chunks ADD COLUMN embedding_dimensions integer;
ALTER TABLE chunks ADD COLUMN embedding_error text;
CREATE TABLE canonical_entities (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL REFERENCES organizations(id),
 kind text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(organization_id,id)
);
INSERT INTO canonical_entities(id,organization_id,kind) SELECT id,organization_id,kind FROM entities;
ALTER TABLE entities ADD COLUMN canonical_id uuid;
UPDATE entities SET canonical_id=id;
ALTER TABLE entities ALTER COLUMN canonical_id SET NOT NULL;
ALTER TABLE entities ADD FOREIGN KEY(organization_id,canonical_id) REFERENCES canonical_entities(organization_id,id);
CREATE INDEX entity_canonical ON entities(organization_id,canonical_id);
CREATE TABLE entity_identifiers (
 organization_id uuid NOT NULL, canonical_id uuid NOT NULL, kind text NOT NULL,
 namespace text NOT NULL, value text NOT NULL,
 PRIMARY KEY(organization_id,kind,namespace,value),
 FOREIGN KEY(organization_id,canonical_id) REFERENCES canonical_entities(organization_id,id)
);
CREATE TABLE entity_aliases (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL, canonical_id uuid NOT NULL,
 occurrence_id uuid NOT NULL REFERENCES entities(id), alias text NOT NULL,
 FOREIGN KEY(organization_id,canonical_id) REFERENCES canonical_entities(organization_id,id),
 UNIQUE(occurrence_id,alias)
);
CREATE TABLE resolution_candidates (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL, occurrence_id uuid NOT NULL REFERENCES entities(id),
 candidate_id uuid NOT NULL, reason text NOT NULL, status text NOT NULL DEFAULT 'open',
 FOREIGN KEY(organization_id,candidate_id) REFERENCES canonical_entities(organization_id,id),
 UNIQUE(occurrence_id,candidate_id)
);
ALTER TABLE claims DROP CONSTRAINT claims_provider_check;
ALTER TABLE claims ADD COLUMN value_json jsonb NOT NULL DEFAULT '{}';
ALTER TABLE claims ADD COLUMN asserted_by text;
ALTER TABLE claims ADD COLUMN effective_from date;
ALTER TABLE claims ADD COLUMN effective_to date;
ALTER TABLE claims ADD COLUMN verification_status text NOT NULL DEFAULT 'unverified';
CREATE TABLE claim_evidence (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL, claim_id uuid NOT NULL REFERENCES claims(id),
 chunk_id uuid NOT NULL REFERENCES chunks(id), quote text NOT NULL,
 span_start integer NOT NULL, span_end integer NOT NULL,
 CHECK(span_start >= 0 AND span_end > span_start), UNIQUE(claim_id,chunk_id,span_start,span_end)
);
INSERT INTO claim_evidence(id,organization_id,claim_id,chunk_id,quote,span_start,span_end)
 SELECT c.id,c.organization_id,c.id,k.id,k.text,0,length(k.text) FROM claims c JOIN chunks k ON k.id=c.chunk_id;
CREATE TABLE relationship_evidence (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL, relationship_id uuid NOT NULL REFERENCES relationships(id),
 chunk_id uuid NOT NULL REFERENCES chunks(id), quote text NOT NULL,
 span_start integer NOT NULL, span_end integer NOT NULL,
 CHECK(span_start >= 0 AND span_end > span_start),
 UNIQUE(relationship_id,chunk_id,span_start,span_end)
);
INSERT INTO relationship_evidence(id,organization_id,relationship_id,chunk_id,quote,span_start,span_end)
 SELECT r.id,r.organization_id,r.id,k.id,k.text,0,length(k.text) FROM relationships r JOIN chunks k ON k.id=r.chunk_id;
CREATE TABLE conflicts (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL, canonical_id uuid NOT NULL,
 predicate text NOT NULL, left_claim_id uuid NOT NULL REFERENCES claims(id),
 right_claim_id uuid NOT NULL REFERENCES claims(id), status text NOT NULL DEFAULT 'open'
 CHECK(status IN ('open','resolved','not_a_conflict','needs_evidence')),
 severity text NOT NULL DEFAULT 'review', rationale text, authoritative_claim_id uuid REFERENCES claims(id),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(organization_id,canonical_id) REFERENCES canonical_entities(organization_id,id),
 UNIQUE(organization_id,left_claim_id,right_claim_id)
);
CREATE TABLE review_actions (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL, conflict_id uuid NOT NULL REFERENCES conflicts(id),
 reviewer_id uuid NOT NULL REFERENCES users(id), action text NOT NULL, rationale text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE processing_attempts (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL, job_id uuid NOT NULL REFERENCES processing_jobs(id),
 attempt integer NOT NULL, stage text NOT NULL, status text NOT NULL, error text,
 started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz
);
CREATE TABLE audit_events (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL, actor_id uuid REFERENCES users(id),
 action text NOT NULL, resource_id uuid NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE conversations (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL, user_id uuid NOT NULL REFERENCES users(id),
 title text NOT NULL, document_ids jsonb NOT NULL DEFAULT '[]',
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE conversation_turns (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL,
 conversation_id uuid NOT NULL REFERENCES conversations(id), question text NOT NULL,
 response jsonb NOT NULL, dependency_ids jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX turns_conversation ON conversation_turns(conversation_id,created_at);
CREATE TABLE ai_usage (
 id uuid PRIMARY KEY, organization_id uuid NOT NULL, user_id uuid REFERENCES users(id),
 version_id uuid REFERENCES document_versions(id), operation text NOT NULL,
 provider text NOT NULL, model text NOT NULL, region text,
 input_tokens integer, output_tokens integer, latency_ms integer NOT NULL,
 status text NOT NULL, error_code text, sdk_retries integer NOT NULL DEFAULT 0,
 estimated_cost numeric(20,10), currency text, rate_date text,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX usage_org ON ai_usage(organization_id,created_at);
"""

def upgrade():
    for statement in SCHEMA.split(";"):
        if statement.strip():
            op.execute(statement)

def downgrade():
    raise RuntimeError("Restore a pre-migration backup to reverse canonical knowledge migration.")
