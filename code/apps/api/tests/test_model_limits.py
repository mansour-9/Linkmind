import json
import time
from uuid import UUID,uuid4
import pytest
from app import providers,model_limits
from app.contracts import AnswerVerdict
from app.db import engine,sql

def test_dispatch_authorizes_after_pacing(monkeypatch):
    steps=[]
    monkeypatch.setenv("BEDROCK_EXTRACTION_MODEL","test/no-network")
    monkeypatch.setattr(providers,"configured",lambda:True)
    monkeypatch.setattr(model_limits,"pace",lambda *args:steps.append("paced"))
    def authorize():
        steps.append("authorized")
        raise PermissionError("Source access changed")
    def runtime():
        pytest.fail("Unauthorized evidence must never reach an SDK call")
    monkeypatch.setattr(providers,"runtime",runtime)
    with pytest.raises(PermissionError):
        providers.structured(AnswerVerdict,"test",{},{},"test",authorize=authorize)
    assert steps==["paced","authorized"]

def test_cross_process_model_lane_allocates_bounded_slots(monkeypatch):
    model="test/"+str(uuid4())
    monkeypatch.setenv("BEDROCK_REQUESTS_PER_MINUTE","9")
    delays=[]
    monkeypatch.setattr(model_limits.time,"sleep",lambda seconds:delays.append(seconds))
    try:
        for _ in range(3): model_limits.pace(model,"test")
        assert len(delays)==2
        assert 5<delays[0]<8 and 11<delays[1]<15
    finally:
        with engine.begin() as conn:
            sql(conn,"DELETE FROM model_request_slots WHERE model=:model",model=model)

@pytest.mark.parametrize("configured",["invalid","{}",json.dumps({"us-east-1":{"test/model":{"input":2,"output":6,"currency":"USD","effective_date":"2026-11-11"}}})])
def test_cost_estimate_configuration_is_explicit(monkeypatch,configured):
    monkeypatch.setenv("BEDROCK_RATES_JSON",configured)
    monkeypatch.setenv("AWS_REGION","us-east-1")
    org=UUID("00000000-0000-4000-8000-000000000001")
    operation="test-cost-"+str(uuid4())
    providers.record({"org":org},operation,"test/model",time.monotonic(),
        {"usage":{"inputTokens":1000000,"outputTokens":500000}},None)
    with engine.begin() as conn:
        row=sql(conn,"SELECT * FROM ai_usage WHERE operation=:operation",operation=operation).mappings().one()
        assert row.estimated_cost==(5 if configured.startswith('{"us-east-1"') else None)
        if row.estimated_cost is not None:
            assert row.currency=="USD" and row.rate_date=="2026-11-11"
        sql(conn,"DELETE FROM ai_usage WHERE id=:id",id=row.id)
