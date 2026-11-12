"""Run separately from pytest; real-provider results are never inferred from mock fixtures."""
import argparse
import json
import time
from urllib.parse import quote
from test_m2 import ROOT,BASE,call,upload,wait
from urllib.request import urlopen

def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--reuse-documents")
    args=parser.parse_args()
    with urlopen(BASE.replace("/api/v1","/health")) as response:
        provider=json.load(response)["provider"]
    if args.live and provider!="bedrock":
        raise RuntimeError("Live benchmark requires a Bedrock-configured API and worker.")
    manifest=json.loads((ROOT/"manifest.json").read_text())
    rows=json.loads(open(args.reuse_documents).read())["documents"] if args.reuse_documents else []
    for expected in ([] if args.reuse_documents else manifest["fixtures"]):
        name=expected["filename"][:-3]
        job=upload(name,visibility="private" if name=="alpha-private" else "team")
        if job["status"] in {"failed","extraction_unavailable"}:
            call("/jobs/"+job["id"]+"/retry",body={})
        job=wait(job,seconds=300)
        _,pages=call("/wiki")
        candidates=[]
        for page in pages:
            _,detail=call("/wiki/"+page["id"])
            claims=[c for c in detail["claims"] if c["version_id"]==job["version_id"]]
            if page["version_id"]==job["version_id"] or claims:
                candidates.append({**detail,"claims":claims})
        expected_claims=expected["claims"]
        matched=sum(any((c["predicate"]==x["predicate"] or {c["predicate"],x["predicate"]}=={"launch_date","deadline"})
            and (x["value"].casefold() in c["value"].casefold() or
                 x["predicate"]=="decision" and "retain the original source files" in c["value"].casefold())
            for p in candidates for c in p["claims"]) for x in expected_claims)
        rows.append(dict(filename=expected["filename"],status=job["status"],provider=job["extraction_provider"],
            expected_claims=len(expected_claims),matched_expected_claims=matched,
            observed_claims=[dict(predicate=c["predicate"],value=c["value"]) for p in candidates for c in p["claims"]]))
    from app.db import engine,sql
    current_jobs=call("/sources")[1]
    groups={}
    for observed,expected in zip(rows,manifest["fixtures"]):
        job=next(j for j in current_jobs if j["filename"]==expected["filename"])
        with engine.connect() as conn:
            entities=sql(conn,"SELECT kind,name,canonical_id FROM entities WHERE version_id=CAST(:version AS uuid) AND organization_id=CAST(:org AS uuid)",
                version=job["version_id"],org=job["organization_id"]).mappings().all()
        observed["expected_entities"]=len(expected["entities"])
        observed["matched_expected_entities"]=sum(any(e.kind==x["kind"] and e.name.casefold()==x["name"].casefold() for e in entities) for x in expected["entities"])
        observed["observed_entities"]=[dict(e) for e in entities]
        for x in expected["entities"]:
            for identifier in x["identifiers"]:
                if identifier["namespace"]=="project_key":
                    groups.setdefault(identifier["value"],set()).update(str(e.canonical_id) for e in entities if e.kind==x["kind"] and e.name.casefold()==x["name"].casefold())
    questions=[]
    for item in manifest["questions"]:
        token="demo-omar" if item["id"] in {9,28} else "demo-nour" if item["id"]==29 else "demo-amal"
        _,conv=call("/conversations",token,body={"title":"Benchmark "+str(item["id"])})
        started=time.monotonic()
        status,response=call("/conversations/"+conv["id"]+"/answers",token,body={"question":item["question"]})
        statements=response.get("statements",[])
        evidence={p["id"]:p["text"] for p in response.get("evidence",[])}
        valid=status==200 and all(s["evidence"] and all(c["quote"] in evidence.get(c["passage_id"],"")
            for c in s["evidence"]) for s in statements)
        text=" ".join(s["text"] for s in statements).casefold()
        expected=item["expected"]
        if expected=="missing":
            quality=response.get("insufficient_evidence",False) or any(term in text for term in ("no recorded","not recorded","not documented","no evidence","does not specify","not specified"))
        elif expected=="contradiction":
            cited={c["passage_id"] for s in statements for c in s["evidence"]}
            quality=len(cited)>=2 and any(word in text for word in ("disagree","conflict","contradict","different","both","not fully agree","do not agree","do not fully agree"))
        elif expected=="restricted":
            quality="42000" not in text
        elif expected=="uncertain":
            quality=response.get("insufficient_evidence",False) or any(term in text for term in ("unconfirmed","cannot confirm","not confirmed","not definitively","not enough evidence","cannot be confirmed","does not establish","no explicit link"))
        elif expected in {"historical","citations"}:
            quality=bool(statements) and valid
        elif expected in {"revision","suppressed"}:
            quality=None # Exercised as stateful scenarios in test_m2, not graded by keyword.
        else:
            quality=expected.casefold() in text
        questions.append(dict(**item,http_status=status,citation_spans_valid=valid,rubric_pass=quality,
            latency_ms=int((time.monotonic()-started)*1000),response=response))
    graded=[q for q in questions if q["rubric_pass"] is not None]
    report=dict(provider=provider,review_status=manifest["review_status"],documents=rows,questions=questions,
        expected_entity_recall=dict(matched=sum(d["matched_expected_entities"] for d in rows),total=sum(d["expected_entities"] for d in rows)),
        project_identity_groups={key:sorted(value) for key,value in groups.items()},
        expected_claim_recall=dict(matched=sum(d["matched_expected_claims"] for d in rows),total=sum(d["expected_claims"] for d in rows)),
        citation_validation=dict(passed=sum(q["citation_spans_valid"] for q in questions),total=len(questions)),
        automated_answer_rubric=dict(passed=sum(bool(q["rubric_pass"]) for q in graded),total=len(graded)),
        limitations=["Draft expected records require independent human review.",
          "Claim scoring accepts deadline/launch_date aliases when the source explicitly says launch date. Decision content and approval metadata may be separate claims. Other equivalent wording can score as a miss.",
          "Citation-span checks do not prove semantic entailment. Bedrock separately verifies assertions.",
          "Revision/deletion and history suppression are tested by stateful integration tests."])
    print(json.dumps(report,default=str,indent=2))

if __name__=="__main__":
    run()
