"""Deterministic identifier evidence and bounded extraction-correction regressions."""
import pytest

from app import providers
from app.contracts import Extraction, ExtractedEntity, ExtractedClaim, AnswerVerdict, EvidenceValidationError, validate_extraction


PASSAGES = [dict(id="p1", text="Project QA-101 is managed by Mira."),
            dict(id="p2", text="Project QB-202 is managed by Omar.")]


def candidate(value="QA-101", quote=None, passage_id="p1"):
    return Extraction(entities=[dict(key="project", kind="project", name="QA project",
        identifiers=[dict(namespace="project_key", value=value)],
        evidence=[dict(passage_id=passage_id, quote=quote or PASSAGES[0]["text"])])],
        claims=[], relationships=[])


@pytest.mark.parametrize("value", ["QA-101", "qa-101", "  qa-101  "])
def test_exact_and_persistence_normalized_identifier(value):
    result = candidate(value)
    assert validate_extraction(result, PASSAGES) is result
    assert result.entities[0].identifiers[0].value == value
    assert result.entities[0].evidence[0].quote == PASSAGES[0]["text"]


@pytest.mark.parametrize("mutation,code", [
    ("missing", "evidence_required"), ("mismatch", "identifier_not_in_evidence"),
    ("wrong_passage", "quote_not_in_passage"), ("unknown_passage", "unknown_evidence_passage"),
    ("alias", "identifier_not_in_evidence"), ("empty", "identifier_not_in_evidence"),
    ("namespace", "identifier_namespace_mismatch")])
def test_invalid_identifiers_never_borrow_other_passage_evidence(mutation, code):
    result = candidate()
    entity = result.entities[0]
    if mutation == "missing":
        entity.evidence = []
    elif mutation == "mismatch":
        entity.identifiers[0].value = "QB-202"  # Exists in p2, but p2 was not cited.
    elif mutation == "wrong_passage":
        entity.evidence[0].passage_id = "p2"
    elif mutation == "unknown_passage":
        entity.evidence[0].passage_id = "unknown"
    elif mutation == "alias":
        entity.identifiers[0].value = "QA101"
    elif mutation == "empty":
        entity.identifiers[0].value = " "
    else:
        entity.kind = "person"
    with pytest.raises(EvidenceValidationError) as rejected:
        validate_extraction(result, PASSAGES)
    diagnostic=rejected.value.diagnostic
    issues=diagnostic.get('issues',[diagnostic])
    assert code in [issue['code'] for issue in issues]
    if code.startswith("identifier_"):
        diagnostic = next(issue for issue in issues if issue['code']==code)
        assert diagnostic["entity_key"] == "project"
        assert diagnostic["identifier_index"] == 0
        assert diagnostic["evidence"][0] == dict(passage_id="p1", quote=PASSAGES[0]["text"])


def test_local_correction_revalidates_then_semantically_verifies(monkeypatch):
    operations, diagnostics = [], []
    def structured(contract, system, payload, scope, operation, *args, **kwargs):
        operations.append(operation)
        if operation == "extraction_verification":
            return AnswerVerdict(supported=[True])
        if len(operations) == 1:
            return candidate("QB-202")
        issue = payload["validation_feedback"]["issue"]
        assert issue["value"] == "QB-202" and issue["entity_name"] == "QA project"
        assert payload["passages"] == PASSAGES
        return candidate()
    monkeypatch.setattr(providers, "structured", structured)
    monkeypatch.setattr(providers, "record", lambda *args: diagnostics.append(args[-1]))
    assert providers.extract_bedrock(PASSAGES, {}).entities[0].identifiers[0].value == "QA-101"
    assert operations == ["extraction", "extraction", "extraction_verification"]
    assert diagnostics[0]["code"] == "identifier_not_in_evidence"


def test_repeated_invalid_identifier_fails_closed_without_verification(monkeypatch):
    operations, diagnostics = [], []
    def structured(contract, system, payload, scope, operation, *args, **kwargs):
        operations.append(operation)
        return candidate("INVENTED")
    monkeypatch.setattr(providers, "structured", structured)
    monkeypatch.setattr(providers, "record", lambda *args: diagnostics.append(args[-1]))
    with pytest.raises(EvidenceValidationError):
        providers.extract_bedrock(PASSAGES, {})
    assert operations == ["extraction", "extraction"]
    assert [d["attempt"] for d in diagnostics] == [1, 2]


def test_correction_does_not_hide_unrelated_failure(monkeypatch):
    calls = []
    def structured(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            return candidate("INVENTED")
        raise RuntimeError("provider unavailable")
    monkeypatch.setattr(providers, "structured", structured)
    monkeypatch.setattr(providers, "record", lambda *args: None)
    with pytest.raises(RuntimeError, match="provider unavailable"):
        providers.extract_bedrock(PASSAGES, {})
    assert len(calls) == 2


def test_split_and_correction_share_three_extraction_calls(monkeypatch):
    operations = []
    def structured(contract, system, payload, scope, operation, *args, **kwargs):
        operations.append(operation)
        if operation == "extraction_verification":
            return AnswerVerdict(supported=[True])
        if len(operations) == 1:
            raise providers.ModelResponseError("output_truncated", "max_tokens")
        return candidate("INVENTED" if len(operations) == 2 else "QA-101")
    monkeypatch.setattr(providers, "structured", structured)
    monkeypatch.setattr(providers, "record", lambda *args: None)
    with pytest.raises(providers.ModelResponseError, match="extraction_call_limit"):
        providers.extract_bedrock_batches(PASSAGES, {})
    assert operations.count("extraction") == 3


def test_identifiers_remain_source_local_across_batches(monkeypatch):
    def structured(contract, system, payload, scope, operation, *args, **kwargs):
        if operation == "extraction_verification":
            return AnswerVerdict(supported=[True])
        p = payload["passages"][0]
        return candidate("QA-101" if p["id"] == "p1" else "QB-202", p["text"], p["id"])
    monkeypatch.setattr(providers, "structured", structured)
    results = providers.extract_bedrock_batches(PASSAGES, {}, max_passages=1)
    combined = Extraction(entities=[], claims=[], relationships=[])
    for index, result in enumerate(results):
        result.entities[0].key = f"b{index}:project"
        combined.entities.extend(result.entities)
    validate_extraction(combined, PASSAGES)
    assert [(e.identifiers[0].value, e.evidence[0].passage_id) for e in combined.entities] == [
        ("QA-101", "p1"), ("QB-202", "p2")]
    combined.entities[0].evidence = combined.entities[1].evidence
    with pytest.raises(EvidenceValidationError, match="identifier_not_in_evidence"):
        validate_extraction(combined, PASSAGES)


def test_all_invalid_identifiers_are_reported_for_one_complete_correction(monkeypatch):
    # Synthetic equivalent of the captured failure: a document ID assigned both
    # to the project with a different quote and to documents as task identifiers.
    passages=[dict(id='p',text='Project Aurora is a portal. Document ID DOC-001. See DOC-002.')]
    evidence=lambda quote:[dict(passage_id='p',quote=quote)]
    invalid=Extraction(entities=[
        dict(key='project',kind='project',name='Project Aurora',identifiers=[dict(namespace='project_key',value='DOC-001')],evidence=evidence('Project Aurora is a portal.')),
        dict(key='doc1',kind='document',name='DOC-001',identifiers=[dict(namespace='issue_key',value='DOC-001')],evidence=evidence('Document ID DOC-001.')),
        dict(key='doc2',kind='document',name='DOC-002',identifiers=[dict(namespace='issue_key',value='DOC-002')],evidence=evidence('See DOC-002.'))],
        claims=[],relationships=[])
    with pytest.raises(EvidenceValidationError) as rejected:
        validate_extraction(invalid,passages)
    assert rejected.value.diagnostic['issue_count']==3
    calls=[]
    def structured(contract,system,payload,scope,operation,*args,**kwargs):
        calls.append(operation)
        if operation=='extraction_verification':
            assert all(a['identifiers']==[] for a in payload['assertions'])
            return AnswerVerdict(supported=[True]*3)
        if len(calls)==1:
            return invalid
        issues=payload['validation_feedback']['issue']['issues']
        assert [i['entity_key'] for i in issues]==['project','doc1','doc2']
        assert [i['code'] for i in issues]==['identifier_not_in_evidence','identifier_namespace_mismatch','identifier_namespace_mismatch']
        corrected=invalid.model_copy(deep=True)
        for entity in corrected.entities:
            entity.identifiers=[]
        return corrected
    monkeypatch.setattr(providers,'structured',structured)
    monkeypatch.setattr(providers,'record',lambda *args:None)
    result=providers.extract_bedrock(passages,{})
    assert len(result.entities)==3 and all(not e.identifiers for e in result.entities)
    assert [e.evidence for e in result.entities]==[e.evidence for e in invalid.entities]
    assert calls==['extraction','extraction','extraction_verification']


def test_identifier_feedback_includes_later_pdf_quote_failures():
    result=candidate('INVENTED')
    result.entities.append(ExtractedEntity(key='person',kind='person',name='Mira',identifiers=[],
        evidence=[dict(passage_id='p3',quote='Mira owns planning.')]))
    result.claims.append(ExtractedClaim(
        entity_key='person',predicate='owner',value='planning',asserted_by=None,effective_from=None,effective_to=None,
        evidence=[dict(passage_id='p3',quote='Mira owns planning.')]))
    with pytest.raises(EvidenceValidationError) as rejected:
        validate_extraction(result,PASSAGES+[dict(id='p3',text='Mira owns\nplanning.')])
    diagnostic=rejected.value.diagnostic
    assert diagnostic['code']=='invalid_extraction_evidence' and diagnostic['issue_count']==3
    assert [i['code'] for i in diagnostic['issues']]==['identifier_not_in_evidence','quote_not_in_passage','quote_not_in_passage']
    assert [i.get('item_kind') for i in diagnostic['issues']]==[None,'entity','claim']
