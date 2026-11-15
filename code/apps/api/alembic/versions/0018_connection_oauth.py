"""Server-owned OAuth grants and short-lived, single-use consent state."""
from alembic import op

revision='0018_connection_oauth'
down_revision='0017_connection_management'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('''CREATE TABLE connection_oauth_grants (
        connection_id uuid PRIMARY KEY REFERENCES source_connections(id),
        generation integer NOT NULL, encrypted_token text NOT NULL,
        updated_at timestamptz NOT NULL DEFAULT now());
        CREATE TABLE connection_oauth_states (
        state_hash text PRIMARY KEY, connection_id uuid NOT NULL REFERENCES source_connections(id),
        owner_id uuid NOT NULL REFERENCES users(id), organization_id uuid NOT NULL REFERENCES organizations(id),
        generation integer NOT NULL, cookie_hash text NOT NULL, encrypted_verifier text NOT NULL,
        expires_at timestamptz NOT NULL DEFAULT now()+interval '10 minutes', consumed_at timestamptz);
        CREATE INDEX connection_oauth_states_expiry ON connection_oauth_states(expires_at)''')

def downgrade():
    op.execute('DROP TABLE connection_oauth_states; DROP TABLE connection_oauth_grants')
