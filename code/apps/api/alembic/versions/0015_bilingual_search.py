"""Normalized bilingual lexical index; immutable citation text is unchanged."""
from alembic import op

revision = '0015_bilingual_search'
down_revision = '0014_repository_metadata'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(r"""ALTER TABLE chunks ADD COLUMN search_simple tsvector GENERATED ALWAYS AS (
        to_tsvector('simple',translate(regexp_replace(text,U&'[\064B-\065F\0670\0640]','','g'),
            U&'\0623\0625\0622\0649',U&'\0627\0627\0627\064A'))) STORED""")
    op.execute('CREATE INDEX chunks_search_simple ON chunks USING gin(search_simple)')


def downgrade():
    op.execute('DROP INDEX chunks_search_simple')
    op.execute('ALTER TABLE chunks DROP COLUMN search_simple')
