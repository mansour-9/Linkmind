"""Preserve canonical URLs after explicit identity review."""
from alembic import op
revision="0004_identity_links"
down_revision="0003_operational"
branch_labels=None
depends_on=None
def upgrade():
    op.execute("""CREATE TABLE canonical_redirects(
      organization_id uuid NOT NULL REFERENCES organizations(id),source_id uuid NOT NULL,
      target_id uuid NOT NULL,PRIMARY KEY(organization_id,source_id),
      FOREIGN KEY(organization_id,target_id) REFERENCES canonical_entities(organization_id,id),
      CHECK(source_id<>target_id))""")
    op.execute("UPDATE processing_jobs SET stage='complete' WHERE status='ready' AND stage='queued'")
    op.execute("UPDATE document_versions v SET extraction_provider='fixture',embedding_status='unavailable' FROM processing_jobs j WHERE j.version_id=v.id AND j.status='ready' AND v.extraction_provider IS NULL")
def downgrade():
    op.execute("DROP TABLE canonical_redirects")
