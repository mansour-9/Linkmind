import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError

from app.db import engine,sql


def test_legacy_intent_is_preserved_new_jobs_default_off_and_downgrade_is_guarded(monkeypatch):
    path=Path(__file__).resolve().parents[1]/"alembic/versions/0013_optional_enrichment.py"
    spec=importlib.util.spec_from_file_location("optional_migration",path)
    migration=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.connect() as conn:
        tx=conn.begin()
        try:
            schema="optional_test_"+uuid4().hex
            sql(conn,f'CREATE SCHEMA "{schema}"')
            sql(conn,f'SET LOCAL search_path TO "{schema}"')
            sql(conn,"CREATE TABLE processing_jobs(id int PRIMARY KEY,staged_version_id uuid)")
            sql(conn,"INSERT INTO processing_jobs VALUES(1,NULL),(2,:candidate)",candidate=uuid4())
            before=sql(conn,"SELECT * FROM processing_jobs ORDER BY id").all()
            monkeypatch.setattr(migration,"op",Operations(MigrationContext.configure(conn)))
            migration.upgrade()
            assert sql(conn,"SELECT id,staged_version_id FROM processing_jobs ORDER BY id").all()==before
            assert sql(conn,"SELECT bool_and(enrichment_requested) FROM processing_jobs").scalar()
            migration.downgrade()
            assert sql(conn,"SELECT * FROM processing_jobs ORDER BY id").all()==before
            migration.upgrade()
            sql(conn,"INSERT INTO processing_jobs(id) VALUES(3)")
            assert sql(conn,"SELECT enrichment_requested FROM processing_jobs WHERE id=3").scalar() is False
            with pytest.raises(RuntimeError,match="Source-only jobs require"):
                migration.downgrade()
            with pytest.raises(IntegrityError):
                with conn.begin_nested():
                    sql(conn,"UPDATE processing_jobs SET staged_version_id=:id WHERE id=3",id=uuid4())
            assert sql(conn,"SELECT enrichment_requested FROM processing_jobs WHERE id=3").scalar() is False
        finally:
            tx.rollback()
