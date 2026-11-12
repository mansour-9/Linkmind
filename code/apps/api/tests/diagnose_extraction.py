"""Run only on synthetic fixture content. Prints assertion structure and verdicts."""
from uuid import UUID
from pathlib import Path
from app import providers
from app.parsers import parse_document

def main():
    content=Path("/app/fixtures/benchmark/alpha-charter.md").read_bytes()
    passages=[dict(id=str(i),text=p.text) for i,p in enumerate(parse_document("a.md",content))]
    original=providers.structured
    def capture(contract,system,payload,scope,operation,*args,**kwargs):
        result=original(contract,system,payload,scope,operation,*args,**kwargs)
        print(operation,payload if operation=="extraction_verification" else result.model_dump(),flush=True)
        if operation=="extraction_verification": print(result.model_dump(),flush=True)
        return result
    providers.structured=capture
    try:
        providers.extract_bedrock(passages,dict(org=UUID("00000000-0000-4000-8000-000000000001")))
    except ValueError as exc:
        print(str(exc),flush=True)
if __name__=="__main__":main()
