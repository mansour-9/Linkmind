from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Fixture:
    filename: str
    entities: tuple[tuple[str, str, str], ...]
    claims: tuple[tuple[str, str, str, int], ...]
    relationships: tuple[tuple[str, str, str, int], ...]

    @property
    def path(self) -> Path:
        return Path(__file__).resolve().parents[3] / "fixtures" / self.filename


FIXTURES = {
    "cloud-migration": Fixture(
        "cloud-migration.md",
        (
            ("project", "project", "Project Alpha"),
            ("team", "team", "Platform Engineering"),
            ("database", "technology", "Amazon RDS for PostgreSQL"),
            ("person", "person", "Amal"),
            ("task", "task", "DB-123 · Database migration"),
        ),
        (
            ("project", "Managed by", "Platform Engineering", 3),
            ("project", "Target database", "Amazon RDS for PostgreSQL", 4),
            ("task", "Owner", "Amal", 5),
            ("task", "Status", "Implementation complete; QA pending", 7),
        ),
        (
            ("project", "team", "Managed by", 3),
            ("project", "database", "Targets", 4),
            ("person", "task", "Owns", 5),
            ("task", "project", "Part of", 6),
        ),
    ),
    "private-review": Fixture(
        "private-review.md",
        (
            ("project", "project", "Project Cedar"),
            ("team", "team", "Finance Operations"),
            ("person", "person", "Nadia"),
            ("task", "task", "Internal cost review"),
        ),
        (
            ("project", "Managed by", "Finance Operations", 3),
            ("task", "Owner", "Nadia", 4),
            ("task", "Status", "Pending approval", 5),
        ),
        (
            ("project", "team", "Managed by", 3),
            ("person", "task", "Owns", 4),
        ),
    ),
}


def recognize(content: bytes) -> Fixture | None:
    for fixture in FIXTURES.values():
        if content == fixture.path.read_bytes():
            return fixture
    return None
