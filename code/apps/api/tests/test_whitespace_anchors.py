from answer_support import support_verdict
import pytest

from app import providers
from app.contracts import Citation,Extraction,GroundedAnswer,AnswerVerdict,recover_whitespace_quote,validate_citations,validate_extraction,EvidenceValidationError


@pytest.mark.parametrize("source,quote",[
    ("Before. Project Lantern is a\nshipment portal. After.","Project Lantern is a shipment portal."),
    ("x\r\nProject\tLantern has a review.\r\ny","Project Lantern has a review."),
    ("The budget is 1\u00a0000 dollars.","The budget is 1 000 dollars."),
    ("تبدأ\nالمراجعة يوم الخميس.","تبدأ المراجعة يوم الخميس."),
])
def test_unique_match_returns_exact_original_slice_and_bounds(source,quote):
    recovered=recover_whitespace_quote(source,quote)
    assert recovered is not None
    original,start,end=recovered
    assert original==source[start:end]
    assert " ".join(original.split())==" ".join(quote.split())
    citation=Citation(passage_id="source",quote=original)
    validate_citations([citation],{"source":source})


@pytest.mark.parametrize("source,quote",[
    ("Review is\nThursday. Review is Thursday.","Review is\tThursday."),
    ("The budget is 1000 dollars.","The budget is 100 dollars."),
    ("Project Lantern is planned.","Project Lantern is approved."),
    ("Project Lantern is planned.","project Lantern is planned."),
    ("The release is planned; review is pending.","The release is planned, review is pending."),
    ("The release is planned.","The release is planned. More evidence exists."),
    ("Source text."," \n\t"),
])
def test_ambiguous_or_changed_content_is_never_recovered(source,quote):
    assert recover_whitespace_quote(source,quote) is None


@pytest.mark.parametrize("supported",[True,False])
def test_repaired_answer_still_needs_semantic_support_and_uses_original_quotes(monkeypatch,supported):
    source="Project Lantern is a\nshipment visibility portal."
    passages=[dict(id="source",text=source)]
    monkeypatch.setattr(providers,"configured",lambda:True)
    operations=[]
    records=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        operations.append(operation)
        if operation=="answer":
            return GroundedAnswer(statements=[dict(text="Lantern is a shipment visibility portal.",
                evidence=[dict(passage_id="source",quote=source.replace("\n"," "))])],insufficient_evidence=False)
        assert payload["statements"][0]["evidence"][0]["quote"]==source
        assert payload["passages"]==passages
        return support_verdict(payload,[supported])
    monkeypatch.setattr(providers,"structured",structured)
    monkeypatch.setattr(providers,"record",lambda *args:records.append(args))
    answer=providers.answer("What is Lantern?",passages,{})
    assert bool(answer.statements)==supported
    assert answer.insufficient_evidence is not supported
    if supported:
        assert answer.statements[0].evidence[0].quote==source
    assert operations==["answer","answer_verification"]
    assert records[0][6]["code"]=="unique_whitespace_anchor"
    assert "quote" not in records[0][6]["repairs"][0]


def test_quote_is_not_moved_to_another_passage_or_joined_across_them(monkeypatch):
    passages=[dict(id="first",text="Project Lantern is a"),dict(id="second",text="shipment visibility portal.")]
    monkeypatch.setattr(providers,"configured",lambda:True)
    operations=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        operations.append(operation)
        assert operation=="answer"
        return GroundedAnswer(statements=[dict(text="Lantern is a portal.",evidence=[dict(
            passage_id="first",quote="Project Lantern is a shipment visibility portal.")])],insufficient_evidence=False)
    monkeypatch.setattr(providers,"structured",structured)
    monkeypatch.setattr(providers,"record",lambda *args:None)
    answer=providers.answer("What is Lantern?",passages,{})
    assert answer.insufficient_evidence and not answer.statements
    assert operations==["answer","answer"]


def test_extraction_validator_remains_exact_and_does_not_use_answer_repairs():
    result=Extraction(entities=[dict(key="p",kind="project",name="Lantern",identifiers=[],
        evidence=[dict(passage_id="source",quote="Project Lantern is planned.")])],claims=[],relationships=[])
    with pytest.raises(EvidenceValidationError):
        validate_extraction(result,[dict(id="source",text="Project Lantern\nis planned.")])
