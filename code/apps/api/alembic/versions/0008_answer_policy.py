"""Version grounded-answer validation so superseded policies do not remain trusted."""
from alembic import op
revision="0008_answer_policy"
down_revision="0007_relationship_dates"
branch_labels=None
depends_on=None
def upgrade():
    op.execute("ALTER TABLE conversation_turns ADD COLUMN validation_version text NOT NULL DEFAULT 'legacy'")
def downgrade():
    op.execute("ALTER TABLE conversation_turns DROP COLUMN validation_version")
