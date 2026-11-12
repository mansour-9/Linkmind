"""Create local M1 storage and demo identities."""

from alembic import op

revision = "0001_m1"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE organizations (
    id uuid PRIMARY KEY,
    name text NOT NULL
);
CREATE TABLE users (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations(id),
    name text NOT NULL,
    UNIQUE (organization_id, id)
);
CREATE TABLE documents (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations(id),
    owner_id uuid NOT NULL,
    filename text NOT NULL,
    visibility text NOT NULL CHECK (visibility IN ('private', 'team')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, owner_id) REFERENCES users(organization_id, id)
);
CREATE TABLE document_versions (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    document_id uuid NOT NULL,
    checksum char(64) NOT NULL,
    byte_count integer NOT NULL CHECK (byte_count > 0),
    artifact_key text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, document_id) REFERENCES documents(organization_id, id)
);
CREATE TABLE processing_jobs (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    version_id uuid NOT NULL UNIQUE,
    owner_id uuid NOT NULL,
    checksum char(64) NOT NULL,
    status text NOT NULL DEFAULT 'queued'
      CHECK (status IN ('queued', 'ready', 'extraction_unavailable', 'failed')),
    attempts integer NOT NULL DEFAULT 0,
    available_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    error text,
    UNIQUE (organization_id, owner_id, checksum),
    FOREIGN KEY (organization_id, owner_id) REFERENCES users(organization_id, id),
    FOREIGN KEY (organization_id, version_id) REFERENCES document_versions(organization_id, id)
);
CREATE INDEX pending_jobs ON processing_jobs (available_at, created_at) WHERE status = 'queued';
CREATE INDEX documents_access ON documents (organization_id, owner_id, created_at);
CREATE TABLE chunks (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    version_id uuid NOT NULL,
    line_number integer NOT NULL CHECK (line_number > 0),
    text text NOT NULL,
    UNIQUE (organization_id, version_id, id),
    UNIQUE (version_id, line_number),
    FOREIGN KEY (organization_id, version_id) REFERENCES document_versions(organization_id, id)
);
CREATE TABLE entities (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    version_id uuid NOT NULL,
    kind text NOT NULL,
    name text NOT NULL,
    UNIQUE (organization_id, version_id, id),
    FOREIGN KEY (organization_id, version_id) REFERENCES document_versions(organization_id, id)
);
CREATE TABLE claims (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    version_id uuid NOT NULL,
    entity_id uuid NOT NULL,
    chunk_id uuid NOT NULL,
    predicate text NOT NULL,
    value text NOT NULL,
    provider text NOT NULL CHECK (provider = 'fixture'),
    FOREIGN KEY (organization_id, version_id, entity_id)
        REFERENCES entities(organization_id, version_id, id),
    FOREIGN KEY (organization_id, version_id, chunk_id)
        REFERENCES chunks(organization_id, version_id, id)
);
CREATE INDEX claims_entity ON claims (entity_id);
CREATE TABLE relationships (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    version_id uuid NOT NULL,
    source_id uuid NOT NULL,
    target_id uuid NOT NULL,
    chunk_id uuid NOT NULL,
    predicate text NOT NULL,
    FOREIGN KEY (organization_id, version_id, source_id)
        REFERENCES entities(organization_id, version_id, id),
    FOREIGN KEY (organization_id, version_id, target_id)
        REFERENCES entities(organization_id, version_id, id),
    FOREIGN KEY (organization_id, version_id, chunk_id)
        REFERENCES chunks(organization_id, version_id, id)
);
CREATE INDEX entities_version ON entities (version_id);
CREATE INDEX relationships_version ON relationships (version_id);
"""

def upgrade() -> None:
    for statement in SCHEMA.split(";"):
        if statement.strip():
            op.execute(statement)
    op.execute("""
        INSERT INTO organizations (id, name) VALUES
          ('00000000-0000-4000-8000-000000000001', 'Engineering pilot'),
          ('00000000-0000-4000-8000-000000000002', 'Separate test team')
    """)
    op.execute("""
        INSERT INTO users (id, organization_id, name) VALUES
          ('00000000-0000-4000-8000-000000000101', '00000000-0000-4000-8000-000000000001', 'Amal'),
          ('00000000-0000-4000-8000-000000000102', '00000000-0000-4000-8000-000000000001', 'Omar'),
          ('00000000-0000-4000-8000-000000000103', '00000000-0000-4000-8000-000000000002', 'Nour')
    """)

def downgrade() -> None:
    op.execute("DROP TABLE relationships, claims, entities, chunks, processing_jobs, document_versions, documents, users, organizations")
