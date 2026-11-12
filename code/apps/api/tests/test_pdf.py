from app.parsers import parse_document

def text_pdf(text):
    stream=("BT /F1 12 Tf 72 720 Td ("+text+") Tj ET").encode("ascii")
    objects=[
      b"<< /Type /Catalog /Pages 2 0 R >>",
      b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
      b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
      b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
      b"<< /Length "+str(len(stream)).encode()+b" >>\nstream\n"+stream+b"\nendstream"]
    result=bytearray(b"%PDF-1.4\n")
    offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(result))
        result.extend(str(i).encode()+b" 0 obj\n"+obj+b"\nendobj\n")
    xref=len(result)
    result.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(result)

def test_selectable_pdf_has_exact_text_and_page_evidence():
    source="Project Birch has project key CB-BIRCH."
    passages=parse_document("source.pdf",text_pdf(source))
    assert len(passages)==1
    assert passages[0].text.strip()==source
    assert passages[0].locator=={"kind":"pdf","page":1,"offset":0}

def test_text_split_preserves_original_line_and_offsets():
    source="# heading\n\n"+"Original fact. "*200
    passages=parse_document("source.md",source.encode())
    assert passages[0].locator["line"]==1
    assert passages[1].locator=={"kind":"text","line":3,"offset":0}
    assert passages[2].locator=={"kind":"text","line":3,"offset":2400}
    assert passages[1].text+passages[2].text==source.splitlines()[2]
