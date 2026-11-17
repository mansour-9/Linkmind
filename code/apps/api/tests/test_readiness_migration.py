"""Run the actual additive migration on an isolated legacy-shaped schema."""
import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.db import engine, sql


def test_readiness_backfill_preserves_ids_and_downgrade_requires_safe_state(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "alembic/versions/0009_search_readiness.py"
    spec = importlib.util.spec_from_file_location("readiness_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            schema = "readiness_test_" + uuid4().hex
            sql(conn, f'CREATE SCHEMA "{schema}"')
            sql(conn, f'SET LOCAL search_path TO "{schema}"')
            sql(conn, "CREATE TABLE documents(id int PRIMARY KEY,current_version_id int,deleted_at timestamptz)")
            sql(conn, "CREATE TABLE document_versions(id int PRIMARY KEY,processed_at timestamptz)")
            sql(conn, "CREATE TABLE processing_jobs(version_id int,status text,created_at timestamptz DEFAULT now())")
            sql(conn, "CREATE TABLE chunks(id int PRIMARY KEY,version_id int,text text)")
            sql(conn, "INSERT INTO document_versions VALUES(1,now()),(2,NULL),(3,NULL),(4,NULL),(5,now())")
            sql(conn, "INSERT INTO processing_jobs(version_id,status) VALUES(1,'ready'),(2,'failed'),(3,'ready'),(4,'queued')")
            sql(conn, "INSERT INTO documents VALUES(1,1,NULL),(2,NULL,NULL),(3,3,NULL),(4,NULL,NULL)")
            sql(conn, "INSERT INTO chunks VALUES(11,1,'original'),(22,2,'retained failed attempt')")
            monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(conn)))
            migration.upgrade()
            ready = sql(conn, "SELECT id FROM document_versions WHERE search_ready_at IS NOT NULL ORDER BY id").scalars().all()
            assert ready == [1, 3, 5]  # Ready jobs and processed versions without jobs.
            assert sql(conn, "SELECT id,current_version_id FROM documents ORDER BY id").all() == [(1, 1), (2, None), (3, 3), (4, None)]
            assert sql(conn, "SELECT id,version_id,text FROM chunks ORDER BY id").all() == [(11, 1, "original"), (22, 2, "retained failed attempt")]
            with pytest.raises(RuntimeError, match="pre-F1.1 backup"):
                migration.downgrade()
            # Quiesced, fully enriched legacy state permits metadata-only reversal.
            sql(conn, "UPDATE document_versions SET processed_at=now() WHERE id=3")
            sql(conn, "UPDATE processing_jobs SET status='processing' WHERE version_id=4")
            with pytest.raises(RuntimeError):
                migration.downgrade()
            sql(conn, "UPDATE processing_jobs SET status='queued' WHERE version_id=4")
            migration.downgrade()
            migration.upgrade()
            assert sql(conn, "SELECT id FROM document_versions WHERE search_ready_at IS NOT NULL ORDER BY id").scalars().all() == [1, 3, 5]
            assert sql(conn, "SELECT text FROM chunks WHERE id=22").scalar() == "retained failed attempt"
        finally:
            transaction.rollback()
