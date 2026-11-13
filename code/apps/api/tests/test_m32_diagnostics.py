import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.contracts import Extraction
from diagnostics.m32_core import Budget,BudgetStopped,cases,validate,score
from diagnostics.m32_live import Adapters,SONNET,GEMMA
from diagnostics.m32_offline import run,reproduction

RATES={SONNET:{'currency':'USD','input':'3.3','output':'16.5'},GEMMA:{'currency':'USD','input':'.14','output':'.4'}}


def test_budget_has_hard_24_attempt_ceiling_and_no_reset(tmp_path):
    path=tmp_path/'ledger.json';budget=Budget(path,RATES,{'experiment':'frozen'})
    for i in range(24):
        attempt=budget.reserve(GEMMA,'extraction',str(i),{},100)
        # Reservation is on disk before inference can start.
        assert json.loads(path.read_text())['attempts'][-1]['state']=='reserved'
        budget.settle(attempt,20,10,1)
    with pytest.raises(BudgetStopped,match='attempt limit'):budget.reserve(GEMMA,'extraction','25',{},100)
    with pytest.raises(FileExistsError):Budget(path,RATES,{})
    assert len(json.loads(path.read_text())['attempts'])==24


@pytest.mark.parametrize('incoming,outgoing',[(None,None),(True,1),(1,False),(-1,1),(1,2.5)])
def test_missing_or_invalid_usage_stops_following_requests(tmp_path,incoming,outgoing):
    budget=Budget(tmp_path/'ledger.json',RATES,{})
    attempt=budget.reserve(SONNET,'extraction','test',{},100)
    with pytest.raises(BudgetStopped):budget.settle(attempt,incoming,outgoing,1)
    with pytest.raises(BudgetStopped):budget.reserve(GEMMA,'extraction','next',{},100)
    assert len(budget.data['attempts'])==1 and attempt['cost_usd']==attempt['reserved_usd']


def test_projection_and_approved_limits_fail_closed(tmp_path):
    budget=Budget(tmp_path/'ledger.json',RATES,{})
    with pytest.raises(BudgetStopped,match='Projected-spend'):budget.reserve(SONNET,'extraction','large',{'source':'x'*2_000_000},6000)
    assert not budget.data['attempts']
    for count,limit in [(25,'5'),(24,'5.01'),(24,'NaN'),(True,'5')]:
        with pytest.raises(ValueError):Budget(tmp_path/f'{count}-{limit}',RATES,{},max_attempts=count,usd=limit)
    with pytest.raises(ValueError):Budget(tmp_path/'rates',{SONNET:{'currency':'USD','input':'-1','output':'1'}},{})


def test_reservation_bound_breach_stops_run(tmp_path):
    budget=Budget(tmp_path/'ledger.json',RATES,{})
    attempt=budget.reserve(GEMMA,'extraction','test',{},1)
    with pytest.raises(BudgetStopped,match='reservation exceeded'):budget.settle(attempt,2,2,1)
    assert attempt['state']=='bound_exceeded'


def test_fixture_gold_is_frozen_and_format_matrix_is_honest():
    manifest,loaded=cases()
    assert len(loaded)==6 and len({c['id'] for c in loaded})==6
    assert all(c['expected']['entities'] and c['passages'] for c in loaded)
    result=run();assert result['format_matrix']['passed']==result['format_matrix']['total']
    assert result['format_matrix']['total']>=23
    assert result['synthetic_reproduction']['operations_reached']==['extraction']
    assert 'Unconfirmed' in result['synthetic_reproduction']['original_root_cause']


def test_strict_json_and_citations_are_not_repaired():
    _,loaded=cases();p=loaded[0]['passages'][0]
    valid={'entities':[{'key':'a','kind':'project','name':'Project Aster','identifiers':[],
        'evidence':[{'passage_id':p['id'],'quote':p['text']}]}],'claims':[],'relationships':[]}
    assert validate(json.dumps(valid),[p]).entities
    with pytest.raises(ValidationError):validate('```json\n'+json.dumps(valid)+'\n```',[p])
    valid['entities'][0]['evidence'][0]['quote']='Invented exact quote'
    with pytest.raises(ValueError,match='quote_not_in_passage'):validate(json.dumps(valid),[p])
    valid['entities'][0]['evidence'][0]['quote']=p['text'];valid['claims']=[dict(entity_key='missing',predicate='owner',value='Nora',asserted_by=None,effective_from=None,effective_to=None,evidence=valid['entities'][0]['evidence'])]
    with pytest.raises(ValueError,match='unknown entity'):validate(json.dumps(valid),[p])


def test_candidate_requests_have_same_source_and_schema_without_hidden_retries():
    adapters=Adapters.__new__(Adapters)
    payload={'passages':[{'id':'1','text':'Original source'}]}
    sonnet=adapters.request(SONNET,Extraction,'instruction',payload,6000)
    gemma=adapters.request(GEMMA,Extraction,'instruction',payload,6000)
    assert sonnet['messages'][0]['content'][0]['text']==gemma['messages'][1]['content']
    assert sonnet['system'][0]['text']==gemma['messages'][0]['content']
    assert sonnet['inferenceConfig']['maxTokens']==gemma['max_tokens']==6000
    assert gemma['reasoning_effort']=='low' and gemma['stream'] is False


def test_gold_scoring_preserves_periods_and_detects_reversed_relationships():
    manifest,loaded=cases();case=loaded[0];p=case['passages'][0]
    entities=[{**e,'evidence':[{'passage_id':p['id'],'quote':p['text']}]} for e in case['expected']['entities']]
    result=Extraction.model_validate(dict(entities=entities,claims=[],relationships=[dict(source_key='nora',predicate='owned_by',target_key='aster',evidence=entities[0]['evidence'])]))
    observed=score(result,case,manifest['scoring'])
    assert observed['entities']['recall']==1 and observed['relationships']['recall']==0
    assert observed['incorrect_relationship_direction']==1


def test_default_runner_is_offline(monkeypatch,tmp_path):
    from diagnostics import m32
    def forbidden(*args,**kwargs):pytest.fail('Offline diagnostic attempted AWS access')
    monkeypatch.setattr(m32,'Adapters',forbidden);monkeypatch.setattr(m32,'prices',forbidden)
    monkeypatch.setattr('sys.argv',['m32','--out',str(tmp_path)])
    assert m32.main()==0
    assert (tmp_path/'offline.json').exists() and not (tmp_path/'ledger.json').exists()


def test_adapter_failure_consumes_one_attempt_and_never_retries(tmp_path):
    adapters=Adapters.__new__(Adapters)
    class Credentials:
        def get_frozen_credentials(self):return self
    class Session:
        def get_credentials(self):return Credentials()
    class Runtime:
        calls=0
        def converse(self,**request):self.calls+=1;raise RuntimeError('test outage')
    adapters.session=Session();adapters.runtime=Runtime();adapters.next_call=0
    budget=Budget(tmp_path/'ledger.json',RATES,{})
    with pytest.raises(BudgetStopped):adapters.call(budget,SONNET,Extraction,'system',{},'extraction','one',6000)
    assert adapters.runtime.calls==1 and len(budget.data['attempts'])==1
    assert budget.data['attempts'][0]['state']=='usage_unavailable'


def test_gemma_reasoning_is_not_returned_or_saved(tmp_path):
    adapters=Adapters.__new__(Adapters)
    class Credentials:
        def get_frozen_credentials(self):return self
    class Session:
        def get_credentials(self):return Credentials()
    adapters.session=Session();adapters.next_call=0
    adapters.mantle=lambda *args:dict(choices=[dict(message=dict(content='{"entities":[],"claims":[],"relationships":[]}',reasoning_content='private-reasoning'),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=20))
    budget=Budget(tmp_path/'ledger.json',RATES,{})
    result=adapters.call(budget,GEMMA,Extraction,'system',{},'extraction','one',6000)
    assert 'private-reasoning' not in json.dumps(result) and 'private-reasoning' not in json.dumps(budget.data)
