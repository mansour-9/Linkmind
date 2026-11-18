"""Separate content domains and record workspace synchronization runs."""
from alembic import op

revision = '0021_company_knowledge'
down_revision = '0020_auto_chat'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE documents ADD COLUMN content_domain text NOT NULL DEFAULT 'legacy_unclassified'
        CHECK(content_domain IN ('manual_document','synced_knowledge','legacy_unclassified'));
    UPDATE documents d SET content_domain='synced_knowledge' FROM connected_resources r
        WHERE r.document_id=d.id AND r.connection_id=d.source_instance_id AND r.native_id=d.native_id;
    UPDATE documents d SET content_domain='manual_document' FROM source_instances s
        WHERE d.source_instance_id=s.id AND s.kind='upload' AND d.id::text=d.native_id
        AND EXISTS(SELECT 1 FROM document_versions v WHERE v.document_id=d.id)
        AND NOT EXISTS(SELECT 1 FROM document_versions v WHERE v.document_id=d.id
            AND (v.dataset_id IS NOT NULL OR v.extraction_provider='fixture'));
    CREATE INDEX documents_content_domain ON documents(organization_id,content_domain,id) WHERE deleted_at IS NULL;
    CREATE FUNCTION preserve_content_domain() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF OLD.content_domain IS DISTINCT FROM NEW.content_domain THEN
            RAISE EXCEPTION 'Document content domain is immutable';
        END IF;
        RETURN NEW;
    END $$;
    CREATE TRIGGER document_domain_immutable BEFORE UPDATE OF content_domain ON documents
        FOR EACH ROW EXECUTE FUNCTION preserve_content_domain();
    ALTER TABLE connected_resources ALTER COLUMN source_updated_at DROP NOT NULL;
    ALTER TABLE connected_revisions ALTER COLUMN source_updated_at DROP NOT NULL;
    ALTER TABLE source_connections ADD COLUMN knowledge_checkpoint jsonb NOT NULL DEFAULT '{}';
    CREATE TABLE knowledge_sync_schedules (
        organization_id uuid NOT NULL, owner_id uuid NOT NULL, enabled boolean NOT NULL DEFAULT false,
        time_of_day time NOT NULL DEFAULT '02:00', timezone text NOT NULL DEFAULT 'Asia/Riyadh', next_run_at timestamptz,
        PRIMARY KEY(organization_id,owner_id), FOREIGN KEY(organization_id,owner_id) REFERENCES users(organization_id,id));
    CREATE TABLE knowledge_sync_runs (
        id uuid PRIMARY KEY, organization_id uuid NOT NULL, owner_id uuid NOT NULL,
        trigger text NOT NULL CHECK(trigger IN ('manual','scheduled')),
        status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','completed','partial','failed')),
        created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
        FOREIGN KEY(organization_id,owner_id) REFERENCES users(organization_id,id));
    CREATE UNIQUE INDEX knowledge_sync_active ON knowledge_sync_runs(organization_id,owner_id) WHERE finished_at IS NULL;
    CREATE INDEX knowledge_sync_history ON knowledge_sync_runs(organization_id,owner_id,created_at DESC);
    CREATE TABLE knowledge_sync_tasks (
        run_id uuid NOT NULL REFERENCES knowledge_sync_runs(id), connection_id uuid NOT NULL REFERENCES source_connections(id),
        source_name text NOT NULL, generation integer NOT NULL, status text NOT NULL DEFAULT 'queued',
        cursor jsonb NOT NULL DEFAULT '{}', lease_token uuid, lease_until timestamptz,
        available_at timestamptz NOT NULL DEFAULT now(), attempts integer NOT NULL DEFAULT 0, error_code text,
        imported integer NOT NULL DEFAULT 0, updated integer NOT NULL DEFAULT 0,
        skipped integer NOT NULL DEFAULT 0, failed integer NOT NULL DEFAULT 0,
        PRIMARY KEY(run_id,connection_id));
    CREATE INDEX knowledge_sync_task_queue ON knowledge_sync_tasks(available_at) WHERE status IN ('queued','running');
    CREATE TABLE knowledge_sync_items (
        run_id uuid NOT NULL, connection_id uuid NOT NULL, version_id uuid NOT NULL REFERENCES document_versions(id),
        PRIMARY KEY(run_id,connection_id,version_id),
        FOREIGN KEY(run_id,connection_id) REFERENCES knowledge_sync_tasks(run_id,connection_id));
    CREATE TABLE knowledge_sync_events (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id uuid NOT NULL REFERENCES knowledge_sync_runs(id),
        connection_id uuid, code text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
    CREATE INDEX knowledge_sync_events_run ON knowledge_sync_events(run_id,id);
    """)


def downgrade():
    raise RuntimeError('Use the reviewed pre-migration backup to preserve knowledge sync and content provenance.')
