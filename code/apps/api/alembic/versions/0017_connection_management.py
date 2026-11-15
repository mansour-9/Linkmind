"""Admin configuration, authentication and test-before-enable lifecycle."""
from alembic import op
revision='0017_connection_management'
down_revision='0016_readonly_connectors'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("ALTER TABLE source_connections ADD COLUMN auth_state text NOT NULL DEFAULT 'unconfigured', ADD COLUMN tested_generation integer, ADD COLUMN tested_at timestamptz, ADD COLUMN removed_at timestamptz")

def downgrade():
    op.execute('ALTER TABLE source_connections DROP COLUMN auth_state,DROP COLUMN tested_generation,DROP COLUMN tested_at,DROP COLUMN removed_at')
