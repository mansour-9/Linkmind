"""Additive, tenant-scoped provider and local evidence-validation diagnostics."""
from alembic import op

revision = "0012_inference_diagnostics"
down_revision = "0011_staged_enrichment"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE ai_usage ADD COLUMN stop_reason text")
    op.execute("ALTER TABLE ai_usage ADD COLUMN diagnostic jsonb")


def downgrade():
    op.execute("ALTER TABLE ai_usage DROP COLUMN diagnostic")
    op.execute("ALTER TABLE ai_usage DROP COLUMN stop_reason")
