from contextlib import contextmanager

from app.db import sql
from app.company_demo import MANIFEST,ROOT
from app import processing,providers
from diagnostics import company_indexes
from test_search_readiness import workspace,source


def test_repair_is_scoped_to_approved_sources_and_preserves_evidence(workspace,monkeypatch):
    fixture=MANIFEST['fixtures'][0]
    known=source(workspace,(ROOT/fixture['filename']).read_bytes())
    assert processing.process_one()
    arbitrary=source(workspace,b'Arbitrary uploaded confidential source, outside the approved fictional corpus.')
    assert processing.process_one()
    before=sql(workspace,'SELECT id,text,locator FROM chunks ORDER BY id').all()
    sql(workspace,"INSERT INTO inference_budget_runs(id,limit_usd) VALUES(:id,10)",id=company_indexes.RUN)

    class TestEngine:
        @contextmanager
        def connect(self):
            yield workspace

        @contextmanager
        def begin(self):
            with workspace.begin_nested():
                yield workspace

    monkeypatch.setattr(company_indexes,'engine',TestEngine())
    monkeypatch.setattr(providers,'configured',lambda:True)
    monkeypatch.setenv('BEDROCK_BUDGET_RUN',company_indexes.RUN)
    monkeypatch.setenv('BEDROCK_EMBEDDING_MODEL',company_indexes.MODEL)
    calls=[]
    def embed(text,scope):
        calls.append(scope['version'])
        return [1.0]+[0.0]*255
    monkeypatch.setattr(providers,'embed',embed)
    result=company_indexes.refresh()
    assert result['repaired_passages']>0 and known.version_id in calls and arbitrary.version_id not in calls
    assert sql(workspace,'SELECT id,text,locator FROM chunks ORDER BY id').all()==before
    assert sql(workspace,'SELECT embedding_status FROM document_versions WHERE id=:id',id=known.version_id).scalar()=='ready'
    assert sql(workspace,'SELECT count(*) FROM chunks WHERE version_id=:id AND embedding IS NOT NULL',id=arbitrary.version_id).scalar()==0
    assert company_indexes.refresh()['repaired_passages']==0
