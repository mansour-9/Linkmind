"""Separate immutable source search publication from knowledge enrichment."""
from alembic import op
import sqlalchemy as sa

revision = "0009_search_readiness"
down_revision = "0008_answer_policy"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE document_versions ADD COLUMN search_ready_at timestamptz")
    # Never infer readiness from retained chunks of an unsuccessful attempt.
    op.execute("UPDATE document_versions SET search_ready_at=processed_at WHERE processed_at IS NOT NULL")
    op.execute("""UPDATE document_versions v SET search_ready_at=j.created_at
        FROM processing_jobs j WHERE j.version_id=v.id AND j.status='ready'
        AND v.search_ready_at IS NULL""")


def downgrade():
    # Old workers cannot represent active source-only publication. Keep the data
    # intact and require the reviewed pre-rollout backup in that situation.
    unsafe = op.get_bind().execute(sa.text("""SELECT EXISTS(
        SELECT 1 FROM documents d JOIN document_versions v ON v.id=d.current_version_id
        WHERE d.deleted_at IS NULL AND v.search_ready_at IS NOT NULL AND v.processed_at IS NULL
    ) OR EXISTS(SELECT 1 FROM processing_jobs WHERE status='processing')""")).scalar()
    if unsafe:
        raise RuntimeError("Stop workers and restore the reviewed pre-F1.1 backup; active source-only content cannot be downgraded safely.")
    op.execute("ALTER TABLE document_versions DROP COLUMN search_ready_at")
