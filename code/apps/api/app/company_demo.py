"""Exact-byte fictional company fixtures. Edited or arbitrary files never match."""
import hashlib
import json
from pathlib import Path

from app.contracts import Extraction, validate_extraction

ROOT = Path(__file__).resolve().parents[3] / "fixtures/company_demo"
MANIFEST = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))


def extract_fixture(content, passages):
    digest = hashlib.sha256(content).hexdigest()
    fixture = next((f for f in MANIFEST["fixtures"] if f["sha256"] == digest
                    and (ROOT / f["filename"]).read_bytes() == content), None)
    if fixture is None:
        return None
    byline = {p["locator"].get("line"): p for p in passages if p["locator"].get("offset", 0) == 0}
    lines = content.decode("utf-8").splitlines()
    data = {}
    for group in ("entities", "claims", "relationships"):
        data[group] = []
        for expected in fixture[group]:
            item = dict(expected)
            number = item.pop("line")
            passage = byline.get(number)
            quote = lines[number - 1]
            if passage is None or quote not in passage["text"]:
                raise ValueError("Company demo evidence no longer matches its original passage.")
            item["evidence"] = [dict(passage_id=passage["id"], quote=quote)]
            data[group].append(item)
    return validate_extraction(Extraction(**data), passages)
