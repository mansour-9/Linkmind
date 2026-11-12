"""Coordinate request pacing across API and worker processes."""
from alembic import op
revision="0006_model_pacing"
down_revision="0005_entity_evidence"
branch_labels=None
depends_on=None
def upgrade():
    op.execute("""CREATE TABLE model_request_slots(
      model text NOT NULL,region text NOT NULL,next_at timestamptz NOT NULL,
      PRIMARY KEY(model,region))""")
def downgrade():
    op.execute("DROP TABLE model_request_slots")
