"""Read-only source connections, resumable collection and retained provenance."""
from alembic import op
import sqlalchemy as sa

revision = '0016_readonly_connectors'
down_revision = '0015_bilingual_search'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE source_connections (
      id uuid PRIMARY KEY REFERENCES source_instances(id), organization_id uuid NOT NULL,
      owner_id uuid NOT NULL, config jsonb NOT NULL, credential_ref text NOT NULL,
      mode text NOT NULL DEFAULT 'disconnected' CHECK(mode IN ('disconnected','live','sync')),
      health text NOT NULL DEFAULT 'not_connected', error_code text,
      generation integer NOT NULL DEFAULT 0, cursor jsonb NOT NULL DEFAULT '{}',
      sync_requested boolean NOT NULL DEFAULT false, lease_token uuid, lease_until timestamptz,
      next_sync_at timestamptz, last_successful_sync_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(),
      FOREIGN KEY(organization_id,id) REFERENCES source_instances(organization_id,id),
      FOREIGN KEY(organization_id,owner_id) REFERENCES users(organization_id,id),
      UNIQUE(organization_id,id))''')
    op.execute('''CREATE TABLE connected_resources (
      connection_id uuid NOT NULL REFERENCES source_connections(id), native_id text NOT NULL,
      document_id uuid NOT NULL UNIQUE REFERENCES documents(id), source_revision text NOT NULL,
      source_updated_at timestamptz NOT NULL, observed_at timestamptz NOT NULL,
      original_url text NOT NULL, access_until timestamptz, revoked boolean NOT NULL DEFAULT false,
      generation integer NOT NULL, PRIMARY KEY(connection_id,native_id))''')
    op.execute('''CREATE TABLE connected_revisions (
      id uuid PRIMARY KEY, version_id uuid NOT NULL REFERENCES document_versions(id), connection_id uuid NOT NULL,
      native_id text NOT NULL, source_revision text NOT NULL, source_updated_at timestamptz NOT NULL,
      observed_at timestamptz NOT NULL DEFAULT now(), original_url text NOT NULL, payload jsonb NOT NULL,
      fields jsonb NOT NULL DEFAULT '[]',
      FOREIGN KEY(connection_id,native_id) REFERENCES connected_resources(connection_id,native_id))''')
    op.execute('CREATE INDEX connected_access_expiry ON connected_resources(access_until) WHERE NOT revoked')
    op.execute('CREATE INDEX connected_revision_lookup ON connected_revisions(version_id,observed_at DESC)')


def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS(SELECT 1 FROM source_connections)')).scalar():
        raise RuntimeError('Retain connector history; use a reviewed backup instead of discarding it.')
    op.execute('DROP TABLE connected_revisions,connected_resources,source_connections')
