import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

ROOT = Path(os.environ.get("ARTIFACT_ROOT", "/artifacts"))
MAX_BYTES = 20 * 1024 * 1024


def save(organization: UUID, checksum: str, content: bytes) -> str:
    key = f"{organization}/{checksum}"
    target = ROOT / key
    if target.exists():
        return key
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(content)
            handle.close()
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return key


def resolve(key: str) -> Path:
    target = (ROOT / key).resolve()
    if not target.is_relative_to(ROOT.resolve()):
        raise ValueError("Invalid artifact key")
    return target
