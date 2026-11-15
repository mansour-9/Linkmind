from answer_support import support_verdict
from app import providers
from app.contracts import GroundedAnswer,AnswerVerdict


def test_boundary_error_correction_gets_exact_authorized_source_without_changing_validation(monkeypatch):
    source="understand its present state without calling support. The second outcome is a support view."
    passages=[dict(id="page-three",text=source)]
    operations=[]
    monkeypatch.setattr(providers,"configured",lambda:True)
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        operations.append(operation)
        if operation=="answer_verification":
            assert payload["statements"][0]["evidence"][0]["quote"]==source
            return support_verdict(payload,[True])
        if len(operations)==1:
            quote="The main outcome is that customers can "+source
        else:
            feedback=payload["validation_feedback"]
            assert feedback["exact_source_for_failed_citation"]==dict(id="page-three",text=source)
            assert "do not reconstruct" in feedback["instruction"]
            quote=source
        return GroundedAnswer(statements=[dict(text="A support view is an outcome.",
            evidence=[dict(passage_id="page-three",quote=quote)])],insufficient_evidence=False)
    monkeypatch.setattr(providers,"structured",structured)
    result=providers.answer("What is an outcome?",passages,{})
    assert result.statements and result.statements[0].evidence[0].quote==source
    assert operations==["answer","answer","answer_verification"]
