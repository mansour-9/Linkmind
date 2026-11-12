import json
import time
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from urllib.parse import quote
from uuid import UUID,uuid4
import pytest
from docx import Document
from app.contracts import Extraction,validate_extraction
from app.parsers import parse_document
from app.processing import mock_extract,overlap
from app.db import engine,sql

BASE="http://api:8000/api/v1"
ROOT=Path("/app/fixtures/benchmark")
def call(path,token="demo-amal",body=None,method=None):
    headers={"Authorization":"Bearer "+token}
    if isinstance(body,dict):
        headers["Content-Type"]="application/json"
        body=json.dumps(body).encode()
    try:
        with urlopen(Request(BASE+path,data=body,method=method,headers=headers),timeout=180) as r:
            return r.status,json.loads(r.read())
    except HTTPError as r:
        return r.code,json.loads(r.read())
def upload(name,token="demo-amal",visibility="team",revision=None):
    boundary=uuid4().hex
    content=(ROOT/(name+".md")).read_bytes()
    data=(f'--{boundary}\r\nContent-Disposition: form-data; name="visibility"\r\n\r\n{visibility}\r\n'
          f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}.md"\r\n\r\n').encode()+content+f"\r\n--{boundary}--\r\n".encode()
    path=f"/documents/{revision}/revisions" if revision else "/sources/upload"
    with urlopen(Request(BASE+path,data=data,headers={"Authorization":"Bearer "+token,"Content-Type":f"multipart/form-data; boundary={boundary}"}),timeout=30) as r:
        assert r.status==202
        return json.loads(r.read())
def wait(job,token="demo-amal",seconds=90):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        status,row=call("/jobs/"+job["id"],token)
        assert status==200,row
        if row["status"] not in {"queued","processing"}:
            assert row["status"]=="ready",row
            return row
        time.sleep(.5)
    pytest.fail("Processing did not complete")

def test_parser_and_evidence_contract():
    doc=Document()
    doc.add_paragraph("Exact original text.")
    table=doc.add_table(rows=1,cols=2)
    table.cell(0,0).text="Budget"
    table.cell(0,1).text="42000"
    output=BytesIO()
    doc.save(output)
    passages=parse_document("input.docx",output.getvalue())
    assert passages[0].text=="Exact original text."
    assert passages[1].text=="Budget | 42000"
    assert passages[1].locator["table"]==1
    with pytest.raises(ValueError): parse_document("input.pdf",b"%PDF-invalid")
    with pytest.raises(ValueError): parse_document("input.md",b"")
    manifest=json.loads((ROOT/"manifest.json").read_text())
    assert len(manifest["fixtures"])==12 and len(manifest["questions"])==30
    for fixture in manifest["fixtures"]:
        content=(ROOT/fixture["filename"]).read_bytes()
        parsed=parse_document(fixture["filename"],content)
        source=[dict(id=str(uuid4()),text=p.text,locator=p.locator) for p in parsed]
        result=mock_extract(content,source)
        assert len(result.entities)==len(fixture["entities"])
        assert len(result.claims)==len(fixture["claims"])
        assert len(result.relationships)==len(fixture["relationships"])
        if result.claims:
            result.claims[0].evidence[0].quote="A fabricated quotation"
            with pytest.raises(ValueError): validate_extraction(result,source)
    assert not overlap(dict(effective_from=None,effective_to=1),dict(effective_from=2,effective_to=None))

def test_end_to_end_permissions_revision_deletion_and_history():
    jobs=[]
    # Isolated test-owned sources, cleaned in finally. Existing matching uploads can be safely reused.
    try:
        for name,access in [("alpha-charter","team"),("alpha-review","team"),("alpha-private","private"),("alpha-history","team"),("alpha-architecture","team"),("ambiguous-alpha","team")]:
            job=upload(name,visibility=access)
            jobs.append(job)
            wait(job)
        graph=call("/graph")[1]
        alpha=[n for n in graph["nodes"] if n["name"]=="Project Alpha"]
        # Two identified documents link, ambiguous same-name source stays separate.
        identified=next(n for n in alpha if any(c["value"]=="Amal" for c in call("/entities/"+n["id"])[1]["claims"]))
        detail=call("/wiki/"+identified["id"])[1]
        assert {"Amal","Omar","Nadia"}.issubset({c["value"] for c in detail["claims"]})
        assert len(alpha)>=2
        assert all(c["evidence"] for c in detail["claims"])
        conflicts=call("/conflicts")[1]
        owner_conflicts=[c for c in conflicts if c["canonical_id"]==identified["id"] and c["predicate"]=="owner"]
        assert any({c["left_value"],c["right_value"]}=={"Amal","Omar"} for c in owner_conflicts)
        assert all("Nadia" not in {c["left_value"],c["right_value"]} for c in owner_conflicts)
        private_id=jobs[2]["document_id"]
        for token in ["demo-omar","demo-nour"]:
            assert call("/jobs/"+jobs[2]["id"],token)[0]==404
            assert all(p["document_id"]!=private_id for p in call("/search?q=42000",token)[1])
            assert call("/usage",token)[0]==403
        assert call("/wiki/"+identified["id"],"demo-nour")[0]==404
        assert call("/graph/neighborhood?root="+identified["id"],"demo-nour")[0]==404
        omar_claims=call("/wiki/"+identified["id"],"demo-omar")[1]["claims"]
        assert all("42000" not in c["value"] for c in omar_claims)
        code,conv=call("/conversations",body={"title":"Privacy test","document_ids":[private_id]})
        assert code==201
        assert call("/conversations/"+conv["id"],"demo-omar")[0]==404
        code,response=call("/conversations/"+conv["id"]+"/answers",body={"question":"What is the CB-ALPHA budget?"})
        assert code==200,response
        assert response["statements"]
        assert all(s["evidence"] for s in response["statements"])
        with engine.connect() as conn:
            old_occurrence=sql(conn,"SELECT id FROM entities WHERE version_id=:version AND kind='project' LIMIT 1",
                version=UUID(jobs[0]["version_id"])).scalar_one()
        revised=upload("alpha-revision",revision=jobs[0]["document_id"])
        wait(revised)
        revised_claims=call("/wiki/"+identified["id"])[1]["claims"]
        assert "2027-01-10" in {c["value"] for c in revised_claims}
        assert call("/entities/"+str(old_occurrence))[0]==200
        assert all(c["version_id"]!=jobs[0]["version_id"] for c in revised_claims)
        assert call("/documents/"+private_id,method="DELETE")[0]==200
        history=call("/conversations/"+conv["id"])[1]
        assert history["turns"][0]["suppressed"]
        assert history["turns"][0]["response"] is None
        assert call("/evidence/"+response["evidence"][0]["id"])[0]==404
        assert all(p["document_id"]!=private_id for p in call("/search?q=42000")[1])
    finally:
        for job in jobs:
            call("/documents/"+job["document_id"],method="DELETE")

def test_publication_rollback_and_independent_usage(monkeypatch):
    # Deliberate database failure after partial graph publication must roll back.
    from app import processing
    before=None
    with engine.connect() as conn:
        before=sql(conn,"SELECT count(*) FROM canonical_entities").scalar()
    with pytest.raises(RuntimeError):
        with engine.begin() as conn:
            sql(conn,"INSERT INTO canonical_entities(id,organization_id,kind) VALUES(:id,'00000000-0000-4000-8000-000000000001','project')",id=uuid4())
            raise RuntimeError("Simulated publication crash")
    with engine.connect() as conn:
        assert sql(conn,"SELECT count(*) FROM canonical_entities").scalar()==before
