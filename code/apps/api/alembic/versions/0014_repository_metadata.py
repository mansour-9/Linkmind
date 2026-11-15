"""Source-qualified resources and explicit organization without graph extraction."""
from alembic import op
import sqlalchemy as sa

revision = "0014_repository_metadata"
down_revision = "0013_optional_enrichment"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE source_instances (
        id uuid PRIMARY KEY, organization_id uuid NOT NULL REFERENCES organizations(id),
        kind text NOT NULL, instance_key text NOT NULL, name text NOT NULL,
        UNIQUE(organization_id,id), UNIQUE(organization_id,kind,instance_key))""")
    op.execute("""CREATE TABLE repository_groups (
        id uuid PRIMARY KEY, organization_id uuid NOT NULL REFERENCES organizations(id),
        kind text NOT NULL CHECK(kind IN ('project','team')), name text NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 120),
        created_by uuid NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE(organization_id,id,kind),
        FOREIGN KEY(organization_id,created_by) REFERENCES users(organization_id,id))""")
    op.execute("ALTER TABLE documents ADD COLUMN source_instance_id uuid, ADD COLUMN native_id text, ADD COLUMN title text CHECK(title IS NULL OR length(trim(title)) BETWEEN 1 AND 240)")
    op.execute("ALTER TABLE documents ADD COLUMN project_id uuid, ADD COLUMN team_id uuid, ADD COLUMN metadata_revision integer NOT NULL DEFAULT 0 CHECK(metadata_revision>=0)")
    op.execute("ALTER TABLE documents ADD COLUMN metadata_updated_at timestamptz, ADD COLUMN metadata_updated_by uuid")
    op.execute("ALTER TABLE documents ADD COLUMN project_kind text GENERATED ALWAYS AS ('project'::text) STORED, ADD COLUMN team_kind text GENERATED ALWAYS AS ('team'::text) STORED")
    op.execute("""INSERT INTO source_instances(id,organization_id,kind,instance_key,name)
        SELECT md5(id::text||'/uploads')::uuid,id,'upload','uploads','Uploaded documents' FROM organizations""")
    op.execute("UPDATE documents SET source_instance_id=md5(organization_id::text||'/uploads')::uuid,native_id=id::text")
    op.execute("ALTER TABLE documents ALTER COLUMN source_instance_id SET NOT NULL, ALTER COLUMN native_id SET NOT NULL")
    op.execute("ALTER TABLE documents ADD CONSTRAINT resource_native_identity UNIQUE(organization_id,source_instance_id,native_id)")
    op.execute("ALTER TABLE documents ADD CONSTRAINT resource_source_fk FOREIGN KEY(organization_id,source_instance_id) REFERENCES source_instances(organization_id,id)")
    op.execute("ALTER TABLE documents ADD CONSTRAINT resource_project_fk FOREIGN KEY(organization_id,project_id,project_kind) REFERENCES repository_groups(organization_id,id,kind)")
    op.execute("ALTER TABLE documents ADD CONSTRAINT resource_team_fk FOREIGN KEY(organization_id,team_id,team_kind) REFERENCES repository_groups(organization_id,id,kind)")
    op.execute("ALTER TABLE documents ADD CONSTRAINT metadata_actor_fk FOREIGN KEY(organization_id,metadata_updated_by) REFERENCES users(organization_id,id)")
    op.execute("ALTER TABLE documents ADD CONSTRAINT native_id_not_empty CHECK(length(trim(native_id)) BETWEEN 1 AND 1000)")
    op.execute("CREATE INDEX resource_project ON documents(organization_id,project_id) WHERE deleted_at IS NULL")
    op.execute("CREATE INDEX resource_team ON documents(organization_id,team_id) WHERE deleted_at IS NULL")
    # Covers all existing upload entry points and new organizations, including fixture loaders.
    op.execute("""CREATE FUNCTION assign_upload_source() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF NEW.source_instance_id IS NULL AND NEW.native_id IS NULL THEN
            INSERT INTO source_instances(id,organization_id,kind,instance_key,name)
                VALUES(md5(NEW.organization_id::text||'/uploads')::uuid,NEW.organization_id,'upload','uploads','Uploaded documents')
                ON CONFLICT(organization_id,kind,instance_key) DO NOTHING;
            NEW.source_instance_id=md5(NEW.organization_id::text||'/uploads')::uuid;
            NEW.native_id=NEW.id::text;
        END IF;
        RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER document_upload_identity BEFORE INSERT ON documents FOR EACH ROW EXECUTE FUNCTION assign_upload_source()")


def downgrade():
    conn = op.get_bind()
    if conn.execute(sa.text("""SELECT EXISTS(SELECT 1 FROM documents WHERE metadata_revision>0 OR title IS NOT NULL
        OR project_id IS NOT NULL OR team_id IS NOT NULL OR native_id<>id::text)
        OR EXISTS(SELECT 1 FROM repository_groups)
        OR EXISTS(SELECT 1 FROM source_instances WHERE kind<>'upload' OR instance_key<>'uploads'
            OR id<>md5(organization_id::text||'/uploads')::uuid OR name<>'Uploaded documents')""")).scalar():
        raise RuntimeError("Repository metadata requires preservation; restore a reviewed backup instead of discarding it.")
    op.execute("DROP TRIGGER document_upload_identity ON documents")
    op.execute("DROP FUNCTION assign_upload_source()")
    for name in ("resource_native_identity", "resource_source_fk", "resource_project_fk", "resource_team_fk", "metadata_actor_fk", "native_id_not_empty"):
        op.execute(f"ALTER TABLE documents DROP CONSTRAINT {name}")
    for name in ("source_instance_id", "native_id", "title", "project_id", "team_id", "metadata_revision", "metadata_updated_at", "metadata_updated_by", "project_kind", "team_kind"):
        op.execute(f"ALTER TABLE documents DROP COLUMN {name}")
    op.execute("DROP TABLE repository_groups,source_instances")
