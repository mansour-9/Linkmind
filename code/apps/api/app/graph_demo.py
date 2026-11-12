"""Synthetic graph-demo sources and expected records, separate from the benchmark."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "graph_demo"
MANIFEST = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))


def graph_demo_records(content):
    expected = next((item for item in MANIFEST["fixtures"]
                     if (ROOT / item["filename"]).read_bytes() == content), None)
    return json.loads(json.dumps(expected)) if expected else None
