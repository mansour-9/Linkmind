"""Explicit live regression checks for issues found in the full benchmark."""
import json
from test_m2 import call
def main():
    results=[]
    for question,expected in [
      ("What is the revised Alpha launch date?","2027-01-10"),
      ("When was the retention decision approved?","2026-11-05"),
      ("Who is Amal?","Platform Engineering"),
      ("Is Project Alpha in research definitely CB-ALPHA?","uncertain")]:
        _,conversation=call("/conversations",body={"title":"Live targeted regression"})
        status,response=call("/conversations/"+conversation["id"]+"/answers",body={"question":question})
        passages={p["id"]:p["text"] for p in response.get("evidence",[])}
        statements=response.get("statements",[])
        text=" ".join(s["text"] for s in statements)
        citations_valid=all(s["evidence"] and all(c["quote"] in passages.get(c["passage_id"],"") for c in s["evidence"]) for s in statements)
        content_pass=expected.casefold() in text.casefold()
        if expected=="uncertain":
            content_pass=response.get("insufficient_evidence",False) or any(term in text.casefold() for term in
                ("unconfirmed","cannot confirm","not confirmed","not definitively","not enough evidence","cannot be confirmed","does not establish","no explicit link"))
        results.append(dict(question=question,expected=expected,http_status=status,
            passed=status==200 and content_pass and citations_valid,response=response))
    print(json.dumps(dict(provider="bedrock",checks=results,passed=sum(r["passed"] for r in results),total=len(results)),default=str,indent=2))
if __name__=="__main__":main()
