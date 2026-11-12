from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile, BadZipFile

from docx import Document
from pypdf import PdfReader
from pypdf.errors import PdfReadError

SUPPORTED = {".pdf",".docx",".txt",".md"}
MAX_PAGES = 100
MAX_TEXT = 500_000
MAX_PASSAGES = 1000
PASSAGE_SIZE = 2400

@dataclass(frozen=True)
class Passage:
    text: str
    locator: dict

def validate_file(filename: str, content: bytes):
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError("Supported formats are PDF, DOCX, TXT and Markdown.")
    if suffix == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ValueError("The PDF signature is invalid.")
    elif suffix == ".docx":
        try:
            with ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                if len(entries) > 2000 or sum(item.file_size for item in entries) > 64 * 1024 * 1024:
                    raise ValueError("The Word document exceeds safe unpacking limits.")
                if "word/document.xml" not in archive.namelist():
                    raise ValueError("The file is not a Word DOCX document.")
        except BadZipFile as exc:
            raise ValueError("The Word document is invalid.") from exc
    else:
        text = content.decode("utf-8-sig")
        if not text.strip() or any(ord(char) < 32 and char not in "\n\r\t" for char in text):
            raise ValueError("The file must contain UTF-8 plain text.")
        if len(text.splitlines()) > 5000:
            raise ValueError("The file exceeds the 5,000-line limit.")

def parse_document(filename: str, content: bytes) -> list[Passage]:
    validate_file(filename,content)
    suffix = PurePosixPath(filename).suffix.lower()
    sections: list[Passage] = []
    if suffix == ".pdf":
        try:
            reader = PdfReader(BytesIO(content), strict=False)
        except PdfReadError as exc:
            raise ValueError('The PDF is damaged or unreadable.') from exc
        if reader.is_encrypted:
            raise ValueError("Password-protected PDFs are unsupported.")
        if len(reader.pages) > MAX_PAGES:
            raise ValueError("PDF exceeds the 100-page limit.")
        for index,page in enumerate(reader.pages,1):
            text = page.extract_text() or ""
            if not text.strip():
                raise ValueError(f"Page {index} has no readable text. Use a text-based PDF.")
            sections.append(Passage(text,{"kind":"pdf","page":index}))
    elif suffix == ".docx":
        document = Document(BytesIO(content))
        paragraph = 0
        table_index = 0
        for element in document.element.body:
            if element.tag.endswith("}p"):
                paragraph += 1
                text = "".join(node.text or "" for node in element.xpath(".//w:t"))
                if text.strip():
                    sections.append(Passage(text,{"kind":"docx","paragraph":paragraph}))
            elif element.tag.endswith("}tbl"):
                table_index += 1
                for row_index,row in enumerate(element.findall("{*}tr"),1):
                    cells = ["".join(node.text or "" for node in cell.xpath(".//w:t")) for cell in row.findall("{*}tc")]
                    sections.append(Passage(" | ".join(cells),{"kind":"docx","table":table_index,"row":row_index}))
    else:
        sections = [Passage(line,{"kind":"text","line":number}) for number,line in
                    enumerate(content.decode("utf-8-sig").splitlines(),1) if line.strip()]
    if sum(len(section.text) for section in sections) > MAX_TEXT:
        raise ValueError("Extracted text exceeds the 500,000-character limit.")
    passages = []
    for section in sections:
        for start in range(0,len(section.text),PASSAGE_SIZE):
            text = section.text[start:start+PASSAGE_SIZE]
            if text.strip():
                passages.append(Passage(text,{**section.locator,"offset":start}))
    if not passages:
        raise ValueError("No readable content was found.")
    if len(passages) > MAX_PASSAGES:
        raise ValueError("Document exceeds the processing passage limit.")
    return passages
