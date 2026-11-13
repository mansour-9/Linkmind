from types import SimpleNamespace

import pytest

from app import processing,providers
from app.contracts import Extraction


def passages(count=8,size=2400):
    return [dict(id=f"source-{index}",text=f"Project item {index}."+("x"*size),locator={"page":index+1})
            for index in range(count)]


def extraction(batch):
    first,last=batch[0],batch[-1]
    evidence=lambda passage:[dict(passage_id=passage["id"],quote=passage["text"])]
    return Extraction(
        entities=[dict(key="same-local-key",kind="project",name=first["text"],identifiers=[],evidence=evidence(first)),
                  dict(key="target",kind="team",name=last["text"],identifiers=[],evidence=evidence(last))],
        claims=[dict(entity_key="same-local-key",predicate="status",value="documented",asserted_by=None,
                     effective_from=None,effective_to=None,evidence=evidence(first))],
        relationships=[dict(source_key="same-local-key",target_key="target",predicate="managed_by",evidence=evidence(first))])


def test_batches_bound_count_and_input_size_without_losing_passages():
    source=passages()
    batches=providers.bounded_batches(source)
    assert [len(batch) for batch in batches]==[3,3,2]
    assert all(sum(len(p["text"]) for p in batch)<=9000 for batch in batches)
    assert [p["id"] for batch in batches for p in batch]==[p["id"] for p in source]
    with pytest.raises(ValueError,match="input-size bound"):
        providers.bounded_batches([dict(id="large",text="x"*9001)])


def test_real_truncation_splits_once_preserves_coverage_and_local_key_mapping(monkeypatch):
    source=passages(3)
    calls=[]
    def verified(batch,scope,payload,repair_allowed):
        calls.append([p["id"] for p in batch])
        if len(calls)==1:
            raise providers.ModelResponseError("output_truncated","max_tokens")
        return extraction(batch)
    monkeypatch.setattr(providers,"_extract_verified",verified)
    result=providers.extract_bedrock_batches(source,{})
    assert calls==[["source-0","source-1","source-2"],["source-0"],["source-1","source-2"]]
    assert {c.passage_id for item in result for group in (item.entities,item.claims,item.relationships) for record in group for c in record.evidence}=={p["id"] for p in source}


def test_only_genuine_truncation_splits_and_single_passage_never_loops(monkeypatch):
    calls=[]
    def failed(batch,*args,**kwargs):
        calls.append(batch)
        raise providers.ModelResponseError("output_truncated","max_tokens")
    monkeypatch.setattr(providers,"_extract_verified",failed)
    with pytest.raises(providers.ModelResponseError,match="max_tokens"):
        providers.extract_bedrock_batches(passages(3),{})
    assert len(calls)==2 and [len(batch) for batch in calls]==[3,1]

    calls.clear()
    def blocked(*args,**kwargs):
        calls.append(True)
        raise providers.ModelResponseError("content_blocked","guardrail_intervened")
    monkeypatch.setattr(providers,"_extract_verified",blocked)
    with pytest.raises(providers.ModelResponseError,match="guardrail_intervened"):
        providers.extract_bedrock_batches(passages(3),{})
    assert len(calls)==1


def test_combined_batch_keys_are_unique_and_relationships_stay_local(monkeypatch):
    source=passages(4)
    monkeypatch.setattr(processing,"extract_bedrock_batches",lambda original,scope:[extraction(batch) for batch in providers.bounded_batches(original)])
    job=SimpleNamespace(staged_version_id=None)
    captured={}
    monkeypatch.setattr(processing,"set_stage",lambda *args:None)
    monkeypatch.setattr(processing,"publish",lambda conn,job,result,passages,provider,judgments:captured.update(result=result))
    class Connection:
        def begin(self): return self
        def __enter__(self): return self
        def __exit__(self,*args): pass
    monkeypatch.setattr(processing,"engine",Connection())
    processing.enrich(job,b"untrusted original",source,{},True,False)
    result=captured["result"]
    assert len(result.entities)==4 and len({entity.key for entity in result.entities})==4
    assert [entity.key for entity in result.entities]==["b0:same-local-key","b0:target","b1:same-local-key","b1:target"]
    assert {relationship.source_key for relationship in result.relationships}=={"b0:same-local-key","b1:same-local-key"}
    assert all(relationship.source_key[:2]==relationship.target_key[:2] for relationship in result.relationships)
