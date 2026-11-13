import pytest
from app import providers
from app.contracts import Extraction,AnswerVerdict


def test_incomplete_extraction_verdict_never_promotes_unverified_assertions(monkeypatch):
    passage=dict(id='source',text='Project Alpha exists.')
    calls=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        calls.append(operation)
        if operation=='extraction':
            return Extraction(entities=[dict(key='alpha',kind='project',name='Project Alpha',identifiers=[],
                evidence=[dict(passage_id='source',quote=passage['text'])])],claims=[],relationships=[])
        return AnswerVerdict(supported=[])
    monkeypatch.setattr(providers,'structured',structured)
    with pytest.raises(ValueError,match='incomplete verdict'):
        providers.extract_bedrock([passage],{})
    assert calls==['extraction','extraction_verification','extraction','extraction_verification']
