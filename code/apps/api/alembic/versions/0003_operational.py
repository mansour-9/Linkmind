"""Attempt-scoped AI accounting and explicit entity-review history."""
from alembic import op
revision="0003_operational"
down_revision="0002_knowledge"
branch_labels=None
depends_on=None
def upgrade():
    op.execute("ALTER TABLE ai_usage ADD COLUMN processing_attempt_id uuid REFERENCES processing_attempts(id)")
    op.execute("UPDATE processing_jobs SET stage='complete' WHERE status='ready' AND stage='queued'")
    op.execute("UPDATE document_versions v SET extraction_provider='fixture',embedding_status='unavailable' FROM processing_jobs j WHERE j.version_id=v.id AND j.status='ready' AND v.extraction_provider IS NULL")
    op.execute("""CREATE TABLE entity_resolution_reviews (
       id uuid PRIMARY KEY, organization_id uuid NOT NULL REFERENCES organizations(id),
       candidate_id uuid NOT NULL REFERENCES resolution_candidates(id),
       reviewer_id uuid NOT NULL REFERENCES users(id), action text NOT NULL,
       rationale text NOT NULL, created_at timestamptz NOT NULL DEFAULT now())""")
def downgrade():
    op.execute("DROP TABLE entity_resolution_reviews")
    op.execute("ALTER TABLE ai_usage DROP COLUMN processing_attempt_id")
