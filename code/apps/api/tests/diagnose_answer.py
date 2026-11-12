"""Inspect a synthetic benchmark answer and its semantic check."""
from uuid import UUID
from app import providers
from app.main import Viewer
from app.retrieval import search
def main():
    viewer=Viewer(id=UUID("00000000-0000-4000-8000-000000000101"),
      organization_id=UUID("00000000-0000-4000-8000-000000000001"),
      name="Amal",organization="Engineering pilot",role="admin")
    question="When was the retention decision approved?"
    passages=[dict(id=p["id"],text=p["text"]) for p in search(viewer,question)]
    original=providers.structured
    def capture(contract,system,payload,scope,operation,*args,**kwargs):
        result=original(contract,system,payload,scope,operation,*args,**kwargs)
        print(operation,result.model_dump(),flush=True)
        return result
    providers.structured=capture
    try:
        providers.answer(question,passages,dict(org=viewer.organization_id,user=viewer.id))
    except ValueError as exc:
        print("Validation error:",str(exc),flush=True)
if __name__=="__main__":main()
