import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.db import engine,sql


def test_additive_generation_migration_preserves_legacy_rows_and_safe_downgrade(monkeypatch):
    path=Path(__file__).resolve().parents[1]/'alembic/versions/0011_staged_enrichment.py'
    spec=importlib.util.spec_from_file_location('staged_migration',path)
    migration=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.connect() as conn:
        transaction=conn.begin()
        try:
            schema='staged_test_'+uuid4().hex
            sql(conn,f'CREATE SCHEMA "{schema}"')
            sql(conn,f'SET LOCAL search_path TO "{schema}"')
            sql(conn,'CREATE TABLE document_versions(id uuid PRIMARY KEY,organization_id uuid NOT NULL,document_id uuid NOT NULL,created_at timestamptz DEFAULT now())')
            sql(conn,"CREATE TABLE processing_jobs(id uuid PRIMARY KEY,organization_id uuid,version_id uuid,status text CONSTRAINT processing_jobs_status_check CHECK(status IN ('ready','processing')))")
            sql(conn,'CREATE TABLE entities(id uuid PRIMARY KEY,organization_id uuid,version_id uuid)')
            sql(conn,'CREATE TABLE claims(id uuid PRIMARY KEY,entity_id uuid)')
            sql(conn,'CREATE TABLE relationships(id uuid PRIMARY KEY,source_id uuid,target_id uuid)')
            org,doc,version,entity,job=[uuid4() for _ in range(5)]
            sql(conn,'INSERT INTO document_versions(id,organization_id,document_id) VALUES(:v,:org,:doc)',v=version,org=org,doc=doc)
            sql(conn,'INSERT INTO entities VALUES(:id,:org,:v)',id=entity,org=org,v=version)
            sql(conn,"INSERT INTO processing_jobs VALUES(:id,:org,:v,'ready')",id=job,org=org,v=version)
            before=sql(conn,'SELECT * FROM document_versions').all()
            monkeypatch.setattr(migration,'op',Operations(MigrationContext.configure(conn)))
            migration.upgrade()
            assert sql(conn,'SELECT id,organization_id,document_id,created_at FROM document_versions').all()==before
            assert sql(conn,'SELECT id FROM live_entities').scalars().all()==[entity]
            assert sql(conn,'SELECT staged_version_id FROM processing_jobs').scalar() is None
            migration.downgrade()
            assert sql(conn,'SELECT * FROM document_versions').all()==before
            migration.upgrade()
            candidate=uuid4()
            sql(conn,"INSERT INTO document_versions(id,organization_id,document_id,source_version_id,activation_state) VALUES(:id,:org,:doc,:source,'staged')",
                id=candidate,org=org,doc=doc,source=version)
            with pytest.raises(RuntimeError,match='reviewed database/artifact backup'):
                migration.downgrade()
            assert sql(conn,'SELECT id FROM live_entities').scalars().all()==[entity]
        finally:
            transaction.rollback()
