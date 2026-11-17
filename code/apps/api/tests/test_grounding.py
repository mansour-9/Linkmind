from answer_support import support_verdict
import pytest
from app import providers
from app.contracts import GroundedAnswer,AnswerVerdict
PASSAGES=[{"id":"source","text":"Project Alpha is owned by Amal."}]

@pytest.mark.parametrize("supported",[[True],[False],[],[True,True]])
def test_answer_verification_abstains_on_rejection_or_mismatched_verdict(monkeypatch,supported):
    monkeypatch.setattr(providers,"configured",lambda:True)
    monkeypatch.setattr(providers,"record",lambda *a,**k:None)
    calls=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        calls.append(operation)
        if operation=="answer":
            return GroundedAnswer(statements=[{"text":"Project Alpha is owned by Amal.",
                "evidence":[{"passage_id":"source","quote":"Project Alpha is owned by Amal."}]}],insufficient_evidence=False)
        assert operation=="answer_verification"
        assert payload["passages"]==PASSAGES
        return support_verdict(payload,supported)
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
        return support_verdict(payload,[True])
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
    monkeypatch.setattr(providers,"record",lambda *args,**kwargs:None)
    result=providers.answer("Who owns Project Alpha?",PASSAGES,{})
    assert result.statements==[] and result.insufficient_evidence is True
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
        return support_verdict(payload,[True])
    monkeypatch.setattr(providers,"structured",structured)

    assert providers.answer("Who owns Project Alpha?",[source],{}).statements


def test_exhausted_citation_correction_records_exact_bounded_diagnostics(monkeypatch):
    monkeypatch.setattr(providers,"configured",lambda:True)
    calls=[]
    records=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        calls.append(operation)
        if len(calls)==2:
            issues=payload["validation_feedback"]["previous_evidence_errors"]
            assert issues[0]["code"]=="unknown_evidence_passage"
            assert issues[0]["statement_index"]==0 and issues[0]["citation_index"]==1
        return GroundedAnswer(statements=[{"text":"Unsupported statement",
            "evidence":[{"passage_id":"source","quote":PASSAGES[0]["text"]},
                {"passage_id":"missing","quote":"x"*600}]}],insufficient_evidence=False)
    monkeypatch.setattr(providers,"structured",structured)
    monkeypatch.setattr(providers,"record",lambda *args:records.append(args))
    result=providers.answer("Who owns Project Alpha?",PASSAGES,{})
    assert result.statements==[] and result.insufficient_evidence
    assert calls==["answer","answer"]
    diagnostic=records[0][6]
    assert diagnostic["correction_attempts"]==1
    assert diagnostic["issues"][0]["passage_id"]=="missing"
    assert len(diagnostic["issues"][0]["quote"])==500
    assert diagnostic["issues"][0]["attempt"]==1 and diagnostic["issues"][1]["attempt"]==2


def test_internal_id_correction_is_exact_and_bounded(monkeypatch):
    internal_id="12345678-1234-1234-1234-123456789012"
    passages=[{**PASSAGES[0],"entities":[{"canonical_id":internal_id,"name":"Project Alpha"}]}]
    monkeypatch.setattr(providers,"configured",lambda:True)
    calls=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        calls.append(operation)
        if len(calls)==2:
            issue=payload["validation_feedback"]["previous_evidence_errors"][0]
            assert issue=={"code":"internal_identity_id","statement_index":0,"internal_id":internal_id}
        text="The identifier is "+internal_id[:8] if len(calls)==1 else PASSAGES[0]["text"]
        return GroundedAnswer(statements=[{"text":text,"evidence":[{"passage_id":"source","quote":PASSAGES[0]["text"]}]}],insufficient_evidence=False) if len(calls)<3 else support_verdict(payload,[True])
    monkeypatch.setattr(providers,"structured",structured)
    result=providers.answer("Who owns Project Alpha?",passages,{})
    assert result.statements[0].text==PASSAGES[0]["text"]
    assert calls==["answer","answer","answer_verification"]


def test_unrelated_answer_failures_are_not_retried_or_hidden(monkeypatch):
    monkeypatch.setattr(providers,"configured",lambda:True)
    calls=[]
    def failed(*args,**kwargs):
        calls.append(args[4])
        raise ValueError("unrelated provider failure")
    monkeypatch.setattr(providers,"structured",failed)
    with pytest.raises(ValueError,match="unrelated provider failure"):
        providers.answer("Who owns Project Alpha?",PASSAGES,{})
    assert calls==["answer"]


def test_provider_transport_error_during_correction_is_not_hidden(monkeypatch):
    from botocore.exceptions import ClientError
    monkeypatch.setattr(providers,"configured",lambda:True)
    calls=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        calls.append(operation)
        if len(calls)==1:
            return GroundedAnswer(statements=[{"text":"Unsupported","evidence":[]}],insufficient_evidence=False)
        raise ClientError({"Error":{"Code":"ExpiredTokenException","Message":"test"}},"Converse")
    monkeypatch.setattr(providers,"structured",structured)
    with pytest.raises(ClientError):
        providers.answer("Who owns Project Alpha?",PASSAGES,{})
    assert calls==["answer","answer"]
