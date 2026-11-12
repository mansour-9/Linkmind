"""Preserve multiple entity evidence spans alongside claim/relationship evidence."""
from alembic import op
revision="0005_entity_evidence"
down_revision="0004_identity_links"
branch_labels=None
depends_on=None
def upgrade():
    op.execute("""CREATE TABLE entity_evidence (
      id uuid PRIMARY KEY,organization_id uuid NOT NULL REFERENCES organizations(id),
      entity_id uuid NOT NULL REFERENCES entities(id),chunk_id uuid NOT NULL REFERENCES chunks(id),
      quote text NOT NULL,span_start integer NOT NULL,span_end integer NOT NULL,
      CHECK(span_start>=0 AND span_end>span_start),UNIQUE(entity_id,chunk_id,span_start,span_end))""")
def downgrade():
    op.execute("DROP TABLE entity_evidence")
