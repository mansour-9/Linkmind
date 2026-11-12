"""Retain explicit relationship effective periods."""
from alembic import op
revision="0007_relationship_dates"
down_revision="0006_model_pacing"
branch_labels=None
depends_on=None
def upgrade():
    op.execute("ALTER TABLE relationships ADD COLUMN effective_from date")
    op.execute("ALTER TABLE relationships ADD COLUMN effective_to date")
    op.execute("ALTER TABLE relationships ADD CHECK(effective_from IS NULL OR effective_to IS NULL OR effective_from<=effective_to)")
def downgrade():
    op.execute("ALTER TABLE relationships DROP COLUMN effective_from")
    op.execute("ALTER TABLE relationships DROP COLUMN effective_to")
