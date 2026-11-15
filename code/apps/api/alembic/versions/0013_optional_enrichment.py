"""Make enrichment an explicit job intent, preserving existing work."""
from alembic import op
import sqlalchemy as sa

revision = "0013_optional_enrichment"
down_revision = "0012_inference_diagnostics"
branch_labels = None
depends_on = None


def upgrade():
    # Existing jobs retain their original intent and history. Only new jobs default off.
    op.execute("ALTER TABLE processing_jobs ADD COLUMN enrichment_requested boolean NOT NULL DEFAULT true")
    op.execute("ALTER TABLE processing_jobs ALTER COLUMN enrichment_requested SET DEFAULT false")
    op.execute("""ALTER TABLE processing_jobs ADD CONSTRAINT staged_enrichment_requested
        CHECK(staged_version_id IS NULL OR enrichment_requested)""")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM processing_jobs WHERE NOT enrichment_requested)")).scalar():
        raise RuntimeError("Source-only jobs require the reviewed database/originals snapshot and prior build for rollback.")
    op.execute("ALTER TABLE processing_jobs DROP CONSTRAINT staged_enrichment_requested")
    op.execute("ALTER TABLE processing_jobs DROP COLUMN enrichment_requested")
