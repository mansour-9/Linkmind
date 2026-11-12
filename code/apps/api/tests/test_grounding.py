import pytest
from app import providers
from app.contracts import GroundedAnswer,AnswerVerdict
PASSAGES=[{"id":"source","text":"Project Alpha is owned by Amal."}]

@pytest.mark.parametrize("eventual_success",[True,False])
def test_answer_correction_is_bounded_and_revalidated(monkeypatch,eventual_success):
    monkeypatch.setattr(providers,"configured",lambda:True)
    calls=[]
    checks=0
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        nonlocal checks
        calls.append(operation)
        if operation=="answer":
            return GroundedAnswer(statements=[{"text":"Project Alpha is owned by Amal.",
                "evidence":[{"passage_id":"source","quote":"Project Alpha is owned by Amal."}]}],insufficient_evidence=False)
        assert operation=="answer_verification"
        assert payload["passages"]==PASSAGES
        checks+=1
        return AnswerVerdict(supported=[eventual_success and checks==2])
    monkeypatch.setattr(providers,"structured",structured)
    if eventual_success:
        result=providers.answer("Who owns Project Alpha?",PASSAGES,{})
        assert result.statements[0].text=="Project Alpha is owned by Amal."
    else:
        with pytest.raises(ValueError): providers.answer("Who owns Project Alpha?",PASSAGES,{})
    assert calls==["answer","answer_verification","answer","answer_verification"]

def test_fabricated_quote_is_not_sent_for_verification(monkeypatch):
    monkeypatch.setattr(providers,"configured",lambda:True)
    calls=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        calls.append(operation)
        assert operation=="answer"
        return GroundedAnswer(statements=[{"text":"Invented claim","evidence":[{"passage_id":"source","quote":"Fabricated quote"}]}],insufficient_evidence=False)
    monkeypatch.setattr(providers,"structured",structured)
    with pytest.raises(ValueError): providers.answer("Who owns Project Alpha?",PASSAGES,{})
    assert calls==["answer","answer"]


def test_citation_verifier_receives_original_text_without_internal_entities(monkeypatch):
    monkeypatch.setattr(providers,"configured",lambda:True)
    source={**PASSAGES[0],"entities":[{"canonical_id":"internal-database-id","name":"Project Alpha"}]}
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        if operation=="answer":
            assert payload["passages"][0]["entities"]
            return GroundedAnswer(statements=[{"text":"Project Alpha is owned by Amal.",
                "evidence":[{"passage_id":"source","quote":"Project Alpha is owned by Amal."}]}],insufficient_evidence=False)
        assert operation=="answer_verification"
        assert payload["passages"]==PASSAGES
        return AnswerVerdict(supported=[True])
    monkeypatch.setattr(providers,"structured",structured)
    assert providers.answer("Who owns Project Alpha?",[source],{}).statements
