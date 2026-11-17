"""Automatic chat scope, archived history and persistent attachment references."""
from alembic import op

revision = '0020_auto_chat'
down_revision = '0019_chat_source_policy'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE conversations DROP CONSTRAINT conversations_source_policy_check;
        ALTER TABLE conversations ADD CONSTRAINT conversations_source_policy_check
            CHECK (source_policy IN ('legacy','live','stored','combined','auto'));
        ALTER TABLE conversations ADD COLUMN archived_at timestamptz;
        ALTER TABLE conversations ADD COLUMN attachment_document_ids jsonb NOT NULL DEFAULT '[]';
    """)


def downgrade():
    op.execute("""
        UPDATE conversations SET source_policy='combined' WHERE source_policy='auto';
        ALTER TABLE conversations DROP COLUMN attachment_document_ids;
        ALTER TABLE conversations DROP COLUMN archived_at;
        ALTER TABLE conversations DROP CONSTRAINT conversations_source_policy_check;
        ALTER TABLE conversations ADD CONSTRAINT conversations_source_policy_check
            CHECK (source_policy IN ('legacy','live','stored','combined'));
    """)
