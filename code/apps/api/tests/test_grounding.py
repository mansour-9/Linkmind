import pytest
from app import providers
from app.contracts import GroundedAnswer,AnswerVerdict
PASSAGES=[{"id":"source","text":"Project Alpha is owned by Amal."}]

@pytest.mark.parametrize("supported",[[True],[False],[],[True,True]])
def test_answer_verification_abstains_on_rejection_or_mismatched_verdict(monkeypatch,supported):
    monkeypatch.setattr(providers,"configured",lambda:True)
    calls=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        calls.append(operation)
        if operation=="answer":
            return GroundedAnswer(statements=[{"text":"Project Alpha is owned by Amal.",
                "evidence":[{"passage_id":"source","quote":"Project Alpha is owned by Amal."}]}],insufficient_evidence=False)
        assert operation=="answer_verification"
        assert payload["passages"]==PASSAGES
        return AnswerVerdict(supported=supported)
    monkeypatch.setattr(providers,"structured",structured)
    result=providers.answer("Who owns Project Alpha?",PASSAGES,{})
    if supported==[True]:
        assert result.statements[0].text=="Project Alpha is owned by Amal."
        assert result.insufficient_evidence is False
    else:
        assert result.statements==[]
        assert result.insufficient_evidence is True
    assert calls==["answer","answer_verification"]


def test_invalid_quote_correction_is_bounded_and_revalidated(monkeypatch):
    monkeypatch.setattr(providers,"configured",lambda:True)
    calls=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        calls.append(operation)
        if operation=="answer":
            quote="Fabricated quote" if len(calls)==1 else PASSAGES[0]["text"]
            if len(calls)>1:
                assert payload["validation_feedback"]
            return GroundedAnswer(statements=[{"text":PASSAGES[0]["text"],
                "evidence":[{"passage_id":"source","quote":quote}]}],insufficient_evidence=False)
        assert operation=="answer_verification"
        return AnswerVerdict(supported=[True])
    monkeypatch.setattr(providers,"structured",structured)
    result=providers.answer("Who owns Project Alpha?",PASSAGES,{})
    assert result.statements[0].text==PASSAGES[0]["text"]
    assert result.insufficient_evidence is False
    assert calls==["answer","answer","answer_verification"]

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
