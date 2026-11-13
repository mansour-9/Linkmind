import pytest
from app import providers
from app.contracts import Extraction,AnswerVerdict


def test_incomplete_extraction_verdict_never_promotes_unverified_assertions(monkeypatch):
    passage=dict(id='source',text='Project Alpha exists.')
    calls=[]
    diagnostics=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        calls.append(operation)
        if operation=='extraction':
            return Extraction(entities=[dict(key='alpha',kind='project',name='Project Alpha',identifiers=[],
                evidence=[dict(passage_id='source',quote=passage['text'])])],claims=[],relationships=[])
        assert payload['expected_assertion_count']==1
        assert payload['assertions'][0]['assertion_index']==0
        return AnswerVerdict(supported=[])
    monkeypatch.setattr(providers,'structured',structured)
    monkeypatch.setattr(providers,'record',lambda *args:diagnostics.append(args[-1]))
    with pytest.raises(ValueError,match='incomplete verdict'):
        providers.extract_bedrock([passage],{})
    assert calls==['extraction','extraction_verification','extraction','extraction_verification']
    assert diagnostics==[dict(code='extraction_verdict_count_mismatch',expected_count=1,received_count=0)]*2
