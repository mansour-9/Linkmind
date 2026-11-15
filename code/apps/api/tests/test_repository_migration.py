"""Additive RF2 migration preserves content and refuses lossy rollback."""
import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError

from app.db import engine, sql


def test_repository_upgrade_preserves_old_source_rows_and_new_upload_identity(monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/0014_repository_metadata.py'
    spec = importlib.util.spec_from_file_location('repository_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.connect() as conn:
        tx = conn.begin()
        try:
            schema = 'repository_test_' + uuid4().hex
            sql(conn, f'CREATE SCHEMA "{schema}"')
            sql(conn, f'SET LOCAL search_path TO "{schema}"')
            sql(conn, 'CREATE TABLE organizations(id uuid PRIMARY KEY)')
            sql(conn, 'CREATE TABLE users(id uuid PRIMARY KEY,organization_id uuid,UNIQUE(organization_id,id))')
            sql(conn, 'CREATE TABLE documents(id uuid PRIMARY KEY,organization_id uuid NOT NULL,owner_id uuid,filename text,deleted_at timestamptz)')
            sql(conn, 'CREATE TABLE immutable_evidence(id uuid PRIMARY KEY,body text)')
            org, user, document, evidence = uuid4(), uuid4(), uuid4(), uuid4()
            sql(conn, 'INSERT INTO organizations VALUES(:id)', id=org)
            sql(conn, 'INSERT INTO users VALUES(:id,:org)', id=user, org=org)
            sql(conn, "INSERT INTO documents VALUES(:id,:org,:user,'legacy.pdf',NULL)", id=document, org=org, user=user)
            sql(conn, "INSERT INTO immutable_evidence VALUES(:id,'Original immutable quotation')", id=evidence)
            before = sql(conn, 'SELECT * FROM documents').all()
            original_evidence = sql(conn, 'SELECT * FROM immutable_evidence').all()
            monkeypatch.setattr(migration, 'op', Operations(MigrationContext.configure(conn)))
            migration.upgrade()
            assert sql(conn, 'SELECT id,organization_id,owner_id,filename,deleted_at FROM documents').all() == before
            assert sql(conn, 'SELECT * FROM immutable_evidence').all() == original_evidence
            identity = sql(conn, 'SELECT source_instance_id,native_id FROM documents').one()
            assert identity.native_id == str(document)
            migration.downgrade()
            assert sql(conn, 'SELECT * FROM documents').all() == before
            migration.upgrade()
            assert identity == sql(conn, 'SELECT source_instance_id,native_id FROM documents').one()
            new_org, new_doc = uuid4(), uuid4()
            sql(conn, 'INSERT INTO organizations VALUES(:id)', id=new_org)
            sql(conn, "INSERT INTO documents(id,organization_id,filename) VALUES(:id,:org,'new.md')", id=new_doc, org=new_org)
            fresh = sql(conn, 'SELECT source_instance_id,native_id FROM documents WHERE id=:id', id=new_doc).one()
            assert fresh.native_id == str(new_doc) and fresh.source_instance_id != identity.source_instance_id
            with pytest.raises(IntegrityError):
                with conn.begin_nested():
                    sql(conn, 'UPDATE documents SET source_instance_id=:other WHERE id=:id', other=fresh.source_instance_id, id=document)
            sql(conn, 'UPDATE documents SET title=:title,metadata_revision=1 WHERE id=:id', title='Retain my organization', id=document)
            with pytest.raises(RuntimeError, match='requires preservation'):
                migration.downgrade()
            assert sql(conn, 'SELECT * FROM immutable_evidence').all() == original_evidence
        finally:
            tx.rollback()
