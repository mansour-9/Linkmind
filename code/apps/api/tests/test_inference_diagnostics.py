import importlib.util
import json
from pathlib import Path
from uuid import UUID,uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException

from app import main,providers,model_limits
from app.contracts import AnswerVerdict,Extraction
from app.db import engine,sql


@pytest.fixture
def no_network_dispatch(monkeypatch):
    monkeypatch.setenv("BEDROCK_EXTRACTION_MODEL","test/no-network")
    monkeypatch.setenv("BEDROCK_RATES_JSON","{}")
    monkeypatch.setattr(providers,"configured",lambda:True)
    monkeypatch.setattr(model_limits,"pace",lambda *args:None)
    monkeypatch.setattr(providers,"reserve",lambda *args:None)
    monkeypatch.setattr(providers,"settle",lambda *args:None)


def persist(stop_reason,content):
    response={"stopReason":stop_reason,"output":{"message":{"content":[{"text":content}]}},
              "usage":{"inputTokens":10,"outputTokens":20}}
    class Runtime:
        def converse(self,**request): return response
    return Runtime()


@pytest.mark.parametrize("stop_reason,classification",[
    ("max_tokens","output_truncated"),("guardrail_intervened","content_blocked"),
    ("content_filtered","content_blocked"),("tool_use","model_stopped")])
def test_actual_stop_reason_is_classified_and_persisted_without_aws(no_network_dispatch,monkeypatch,stop_reason,classification):
    monkeypatch.setattr(providers,"runtime",lambda:persist(stop_reason,"{}"))
    operation="test-stop-"+uuid4().hex
    original=providers.record
    monkeypatch.setattr(providers,"record",lambda scope,op,*args:original(scope,operation,*args))
    with pytest.raises(providers.ModelResponseError) as failure:
        providers.structured(Extraction,"test",{},dict(org=UUID("00000000-0000-4000-8000-000000000001")),operation)
    assert failure.value.classification==classification and failure.value.stop_reason==stop_reason
    with engine.begin() as conn:
        row=sql(conn,"SELECT stop_reason,diagnostic,error_code,input_tokens,output_tokens FROM ai_usage WHERE operation=:operation",operation=operation).mappings().one()
        assert row.stop_reason==stop_reason and row.diagnostic=={"code":classification,"stop_reason":stop_reason}
        assert (row.input_tokens,row.output_tokens)==(10,20)
        sql(conn,"DELETE FROM ai_usage WHERE operation=:operation",operation=operation)


def test_malformed_output_is_distinct_from_truncation_and_never_partially_accepted(no_network_dispatch,monkeypatch):
    monkeypatch.setattr(providers,"runtime",lambda:persist("end_turn","{\"entities\":["))
    operation="test-malformed-"+uuid4().hex
    original=providers.record
    monkeypatch.setattr(providers,"record",lambda scope,op,*args:original(scope,operation,*args))
    with pytest.raises(providers.ModelResponseError) as failure:
        providers.structured(Extraction,"test",{},dict(org=UUID("00000000-0000-4000-8000-000000000001")),operation)
    assert failure.value.classification=="malformed_output"
    with engine.begin() as conn:
        row=sql(conn,"SELECT stop_reason,diagnostic FROM ai_usage WHERE operation=:operation",operation=operation).mappings().one()
        assert row.stop_reason=="end_turn" and row.diagnostic["code"]=="malformed_output"
        assert row.diagnostic["locations"]
        sql(conn,"DELETE FROM ai_usage WHERE operation=:operation",operation=operation)


def test_success_still_parses_full_contract_and_records_stop_reason(no_network_dispatch,monkeypatch):
    content=json.dumps({"entities":[],"claims":[],"relationships":[]})
    monkeypatch.setattr(providers,"runtime",lambda:persist("end_turn",content))
    operation="test-success-"+uuid4().hex
    original=providers.record
    monkeypatch.setattr(providers,"record",lambda scope,op,*args:original(scope,operation,*args))
    assert providers.structured(Extraction,"test",{},dict(org=UUID("00000000-0000-4000-8000-000000000001")),operation)==Extraction(entities=[],claims=[],relationships=[])
    with engine.begin() as conn:
        row=sql(conn,"SELECT stop_reason,diagnostic,status FROM ai_usage WHERE operation=:operation",operation=operation).mappings().one()
        assert row.stop_reason=="end_turn" and row.diagnostic is None and row.status=="success"
        sql(conn,"DELETE FROM ai_usage WHERE operation=:operation",operation=operation)


def test_diagnostic_migration_is_additive_and_downgradable(monkeypatch):
    path=Path(__file__).resolve().parents[1]/"alembic/versions/0012_inference_diagnostics.py"
    spec=importlib.util.spec_from_file_location("diagnostic_migration",path)
    migration=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.connect() as conn:
        transaction=conn.begin()
        try:
            sql(conn,"ALTER TABLE ai_usage DROP COLUMN diagnostic")
            sql(conn,"ALTER TABLE ai_usage DROP COLUMN stop_reason")
            before=sql(conn,"SELECT count(*) FROM ai_usage").scalar_one()
            monkeypatch.setattr(migration,"op",Operations(MigrationContext.configure(conn)))
            migration.upgrade()
            assert sql(conn,"SELECT count(*) FROM ai_usage").scalar_one()==before
            migration.downgrade()
            columns=sql(conn,"SELECT column_name FROM information_schema.columns WHERE table_name='ai_usage'").scalars().all()
            assert "diagnostic" not in columns and "stop_reason" not in columns
            migration.upgrade()
        finally:
            transaction.rollback()


def test_usage_diagnostics_remain_reviewer_only():
    member=main.Viewer(id=UUID("00000000-0000-4000-8000-000000000102"),organization_id=UUID("00000000-0000-4000-8000-000000000001"),name="Member",organization="Test",role="member")
    with pytest.raises(HTTPException) as denied:
        main.usage(member)
    assert denied.value.status_code==403


def test_final_answer_fallback_is_clean_and_diagnostics_are_bounded(monkeypatch):
    from app.contracts import GroundedAnswer
    monkeypatch.setattr(providers,"configured",lambda:True)
    monkeypatch.setattr(providers,"structured",lambda *args,**kwargs:GroundedAnswer(statements=[],insufficient_evidence=True))
    result=providers.answer("Who owns Project Alpha?",[dict(id="source",text="Project Alpha exists.")],{})
    assert result.statements==[] and result.insufficient_evidence
    assert "validation_diagnostics" not in result.model_dump()
