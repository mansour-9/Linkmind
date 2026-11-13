"""Add enrichment generations without replacing immutable source evidence."""
from alembic import op
import sqlalchemy as sa

revision="0011_staged_enrichment"
down_revision="0010_test_budget"
branch_labels=None
depends_on=None


def upgrade():
    op.execute("ALTER TABLE document_versions ADD COLUMN activation_state text NOT NULL DEFAULT 'live' CHECK(activation_state IN ('live','staged','rolled_back'))")
    op.execute("ALTER TABLE document_versions ADD COLUMN source_version_id uuid")
    op.execute("ALTER TABLE document_versions ADD COLUMN active_enrichment_version_id uuid")
    op.execute("ALTER TABLE document_versions ADD COLUMN staged_extraction jsonb")
    op.execute("ALTER TABLE document_versions ADD COLUMN verified_at timestamptz")
    op.execute("ALTER TABLE document_versions ADD CONSTRAINT version_document_identity UNIQUE(organization_id,document_id,id)")
    op.execute("ALTER TABLE document_versions ADD CONSTRAINT version_generation_identity UNIQUE(organization_id,source_version_id,id)")
    op.execute("""ALTER TABLE document_versions ADD CONSTRAINT generation_source_fk
        FOREIGN KEY(organization_id,document_id,source_version_id) REFERENCES document_versions(organization_id,document_id,id)""")
    op.execute("""ALTER TABLE document_versions ADD CONSTRAINT active_generation_fk
        FOREIGN KEY(organization_id,id,active_enrichment_version_id) REFERENCES document_versions(organization_id,source_version_id,id)""")
    op.execute("ALTER TABLE document_versions ADD CONSTRAINT generation_not_self CHECK(source_version_id IS NULL OR source_version_id<>id)")
    op.execute("CREATE INDEX enrichment_generations ON document_versions(source_version_id,created_at) WHERE source_version_id IS NOT NULL")
    op.execute("ALTER TABLE processing_jobs ADD COLUMN staged_version_id uuid")
    op.execute("""ALTER TABLE processing_jobs ADD CONSTRAINT staged_job_generation_fk
        FOREIGN KEY(organization_id,version_id,staged_version_id) REFERENCES document_versions(organization_id,source_version_id,id)""")
    op.execute("ALTER TABLE processing_jobs DROP CONSTRAINT processing_jobs_status_check")
    op.execute("""ALTER TABLE processing_jobs ADD CONSTRAINT processing_jobs_status_check
        CHECK(status IN ('queued','processing','ready','extraction_unavailable','failed','cancelled','enrichment_staged_failed'))""")
    op.execute("ALTER TABLE entities ADD COLUMN enrichment_version_id uuid")
    op.execute("""ALTER TABLE entities ADD CONSTRAINT entity_generation_fk
        FOREIGN KEY(organization_id,version_id,enrichment_version_id) REFERENCES document_versions(organization_id,source_version_id,id)""")
    op.execute("CREATE INDEX entities_enrichment_version ON entities(enrichment_version_id)")
    # Existing occurrences use their source revision as the legacy generation.
    # Claims and edges retain all original FK/evidence relationships and IDs.
    op.execute("""CREATE VIEW live_entities AS SELECT e.* FROM entities e
        JOIN document_versions source ON source.id=e.version_id
        JOIN document_versions generation ON generation.id=coalesce(e.enrichment_version_id,e.version_id)
        WHERE coalesce(e.enrichment_version_id,e.version_id)=coalesce(source.active_enrichment_version_id,source.id)
        AND generation.activation_state='live'""")
    op.execute("CREATE VIEW live_claims AS SELECT c.* FROM claims c JOIN live_entities e ON e.id=c.entity_id")
    op.execute("""CREATE VIEW live_relationships AS SELECT r.* FROM relationships r
        JOIN live_entities s ON s.id=r.source_id JOIN live_entities t ON t.id=r.target_id""")


def downgrade():
    unsafe=op.get_bind().execute(sa.text("""SELECT EXISTS(SELECT 1 FROM document_versions WHERE source_version_id IS NOT NULL)
        OR EXISTS(SELECT 1 FROM processing_jobs WHERE status IN ('processing','enrichment_staged_failed'))""")).scalar()
    if unsafe:
        raise RuntimeError("Retained enrichment generations require the reviewed database/artifact backup and prior build for rollback.")
    for name in ("live_relationships","live_claims","live_entities"):
        op.execute(f"DROP VIEW {name}")
    op.execute("ALTER TABLE entities DROP COLUMN enrichment_version_id")
    op.execute("ALTER TABLE processing_jobs DROP COLUMN staged_version_id")
    op.execute("ALTER TABLE processing_jobs DROP CONSTRAINT processing_jobs_status_check")
    op.execute("ALTER TABLE processing_jobs ADD CONSTRAINT processing_jobs_status_check CHECK(status IN ('queued','processing','ready','extraction_unavailable','failed','cancelled'))")
    op.execute("ALTER TABLE document_versions DROP CONSTRAINT active_generation_fk")
    op.execute("ALTER TABLE document_versions DROP CONSTRAINT generation_source_fk")
    op.execute("ALTER TABLE document_versions DROP CONSTRAINT version_generation_identity")
    op.execute("ALTER TABLE document_versions DROP CONSTRAINT version_document_identity")
    for name in ("source_version_id","active_enrichment_version_id","staged_extraction","verified_at","activation_state"):
        op.execute(f"ALTER TABLE document_versions DROP COLUMN {name}")
