"""No-inference format matrix and a labeled synthetic quote-failure reproduction."""
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import json
from docx import Document
from pypdf import PdfWriter
from app.parsers import parse_document,MAX_TEXT,PASSAGE_SIZE
from app.contracts import Extraction,validate_citations
from diagnostics.m32_core import cases,digest


def matrix():
    manifest,loaded=cases();rows=[]
    for case in loaded:
        raw=(Path(__file__).resolve().parents[3]/'fixtures/m32'/case['filename']).read_bytes()
        rebuilt=parse_document(case['filename'],raw)
        rows.append(dict(id=case['id'],expected='readable',actual='readable',passed=bool(rebuilt),passages=len(rebuilt),
            locators=[p.locator for p in rebuilt],source_sha256=case['sha256']))
    def word_empty():
        stream=BytesIO();Document().save(stream);return stream.getvalue()
    def pdf_blank(pages=1,password=None):
        writer=PdfWriter()
        for _ in range(pages):writer.add_blank_page(width=612,height=792)
        if password:writer.encrypt(password)
        stream=BytesIO();writer.write(stream);return stream.getvalue()
    invalid=[('empty_txt','empty.txt',b''),('empty_md','empty.md',b' \n'),('empty_docx','empty.docx',word_empty()),
        ('malformed_pdf','broken.pdf',b'%PDF-invalid'),('bad_signature','broken.pdf',b'not-pdf'),('scanned_pdf','scan.pdf',pdf_blank()),
        ('encrypted_pdf','locked.pdf',pdf_blank(password='synthetic-test-password')),('too_many_pages','large.pdf',pdf_blank(101)),
        ('malformed_docx','broken.docx',b'not-zip'),('invalid_utf8','bad.txt',b'\xff'),('control_character','bad.txt',b'fact\x00'),
        ('too_many_lines','lines.txt',b'x\n'*5001),('too_much_text','large.txt',b'x'*(MAX_TEXT+1)),
        ('too_many_passages','passages.md',b'x\n'*1001),('unsupported','file.xlsx',b'not-supported')]
    for key,name,raw in invalid:
        try:parse_document(name,raw)
        except (ValueError,UnicodeError) as exc:rows.append(dict(id=key,expected='rejected',actual='rejected',passed=True,error_type=type(exc).__name__,error=str(exc)))
        else:rows.append(dict(id=key,expected='rejected',actual='accepted',passed=False))
    source='Original fact. '*400
    split=parse_document('long.md',source.encode())
    rows.append(dict(id='long_section_roundtrip',expected='exact original slices',actual='exact original slices' if ''.join(p.text for p in split)==source else 'changed',
        passed=''.join(p.text for p in split)==source and [p.locator['offset'] for p in split]==list(range(0,len(source),PASSAGE_SIZE)),passages=len(split)))
    # Exercise the existing 20 MiB upload gate directly; no API request or database write.
    from app.main import read_upload
    from fastapi import HTTPException
    from types import SimpleNamespace
    try:read_upload(SimpleNamespace(filename='oversized.txt',file=BytesIO(b'x'*(20*1024*1024+1))))
    except HTTPException as exc:rows.append(dict(id='upload_20mib',expected=413,actual=exc.status_code,passed=exc.status_code==413))
    else:rows.append(dict(id='upload_20mib',expected=413,actual='accepted',passed=False))
    return dict(cases=rows,passed=sum(r['passed'] for r in rows),total=len(rows))


def reproduction():
    from app import providers
    _,loaded=cases();case=next(c for c in loaded if c['id']=='typography_pdf');passage=case['passages'][0]
    exact='Project Birch is owned by\nNora.'
    assert exact in passage['text'],'Synthetic PDF layout changed'
    altered=exact.replace('\n',' ')
    citation=dict(passage_id=passage['id'],quote=altered)
    result=Extraction.model_validate(dict(entities=[dict(key='birch',kind='project',name='Project Birch',identifiers=[],evidence=[citation])],claims=[],relationships=[]))
    calls=[]
    def structured(*args,**kwargs):calls.append(args[4]);return result
    caught=None
    with patch.object(providers,'structured',structured):
        try:providers.extract_bedrock(case['passages'],{})
        except ValueError as exc:caught=exc
    assert caught.diagnostic["code"]=="quote_not_in_passage" and caught.diagnostic["quote"]==altered and calls==['extraction']
    validate_citations([type(result.entities[0].evidence[0])(passage_id=passage['id'],quote=exact)],{passage['id']:passage['text']})
    return dict(classification='Synthetic reproduction of the recorded error, not recovery of the original model response.',
        failure=caught.diagnostic,source_quote=exact,altered_model_quote=altered,operations_reached=calls,
        finding='Exact quote validation raises before the semantic-verification/correction branch. Original raw model output is not retained.',
        original_root_cause='Unconfirmed; retained PDF passages match a current parse, and original sources have no character-boundary splits.')


def run():
    return dict(format_matrix=matrix(),synthetic_reproduction=reproduction())
