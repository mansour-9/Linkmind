import importlib.util
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.db import engine, sql


def test_bilingual_index_preserves_original_evidence_and_is_reversible(monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/0015_bilingual_search.py'
    spec = importlib.util.spec_from_file_location('bilingual_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.connect() as conn:
        tx = conn.begin()
        try:
            schema = 'bilingual_test_' + uuid4().hex
            sql(conn, f'CREATE SCHEMA "{schema}"')
            sql(conn, f'SET LOCAL search_path TO "{schema}"')
            sql(conn, 'CREATE TABLE chunks(id uuid PRIMARY KEY,text text NOT NULL,locator jsonb)')
            sql(conn, "INSERT INTO chunks VALUES(:id,:text,jsonb_build_object('page',3))", id=uuid4(), text='إِجْرَاءَات العمل عـن بُعد')
            original = sql(conn, 'SELECT * FROM chunks').all()
            monkeypatch.setattr(migration, 'op', Operations(MigrationContext.configure(conn)))
            migration.upgrade()
            assert sql(conn, 'SELECT id,text,locator FROM chunks').all() == original
            assert sql(conn, "SELECT count(*) FROM chunks WHERE search_simple@@websearch_to_tsquery('simple','اجراءات')").scalar() == 1
            migration.downgrade()
            assert sql(conn, 'SELECT * FROM chunks').all() == original
        finally:
            tx.rollback()
