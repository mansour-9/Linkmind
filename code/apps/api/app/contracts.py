from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

class EvidenceValidationError(ValueError):
    """A local evidence failure with safe, bounded correction diagnostics."""
    def __init__(self, diagnostic):
        self.diagnostic = {key: value for key, value in diagnostic.items() if value is not None}
        super().__init__(str(self.diagnostic))

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Citation(Contract):
    passage_id: str
    quote: str

class Identifier(Contract):
    namespace: Literal["project_key","issue_key","email","url"]
    value: str

class ExtractedEntity(Contract):
    key: str
    kind: Literal["project","person","team","task","document","decision","system","technology","event"]
    name: str
    identifiers: list[Identifier]
    evidence: list[Citation]

class ExtractedClaim(Contract):
    entity_key: str
    predicate: str
    value: str
    asserted_by: str | None
    effective_from: date | None
    effective_to: date | None
    evidence: list[Citation]

    @model_validator(mode="after")
    def valid_period(self):
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError("Effective period is reversed")
        return self

class ExtractedRelationship(Contract):
    source_key: str
    target_key: str
    predicate: str
    effective_from: date | None = None
    effective_to: date | None = None
    evidence: list[Citation]

class Extraction(Contract):
    entities: list[ExtractedEntity]
    claims: list[ExtractedClaim]
    relationships: list[ExtractedRelationship]

class AnswerStatement(Contract):
    text: str
    evidence: list[Citation]

class GroundedAnswer(Contract):
    statements: list[AnswerStatement]
    insufficient_evidence: bool

class ConflictJudgment(Contract):
    pair_id: str
    conflict: bool
    rationale: str

class ConflictJudgments(Contract):
    judgments: list[ConflictJudgment]

class AnswerVerdict(Contract):
    supported: list[bool]

def validate_extraction(result: Extraction, passages: list[dict]) -> Extraction:
    passage_map = {item["id"]: item["text"] for item in passages}
    keys = {item.key for item in result.entities}
    if len(keys) != len(result.entities):
        raise ValueError("Duplicate entity key")
    if len(result.entities) > 100 or len(result.claims) > 200 or len(result.relationships) > 200:
        raise ValueError("Extraction exceeds batch limits")
    for entity in result.entities:
        validate_citations(entity.evidence, passage_map)
        for identifier in entity.identifiers:
            if identifier.namespace=="project_key" and entity.kind not in {"project","decision"} or identifier.namespace=="issue_key" and entity.kind!="task":
                raise ValueError("Identifier namespace is incompatible with the entity type")
            if not identifier.value.strip() or not any(
                identifier.value.casefold() in citation.quote.casefold() for citation in entity.evidence):
                raise ValueError("Identifier lacks source evidence")
    for claim in result.claims:
        if claim.entity_key not in keys:
            raise ValueError("Claim references an unknown entity")
        validate_citations(claim.evidence, passage_map)
    for relationship in result.relationships:
        if relationship.source_key not in keys or relationship.target_key not in keys:
            raise ValueError("Relationship references an unknown entity")
        validate_citations(relationship.evidence, passage_map)
    return result

def validate_citations(citations: list[Citation], passages: dict[str,str], statement_index=None):
    if not citations:
        raise EvidenceValidationError(dict(code="evidence_required",statement_index=statement_index))
    for index,citation in enumerate(citations):
        diagnostic=dict(statement_index=statement_index,citation_index=index,
            passage_id=citation.passage_id,quote=citation.quote[:500])
        if not citation.quote.strip():
            raise EvidenceValidationError(dict(code="empty_evidence_quote",**diagnostic))
        if citation.passage_id not in passages:
            raise EvidenceValidationError(dict(code="unknown_evidence_passage",**diagnostic))
        if citation.quote not in passages[citation.passage_id]:
            raise EvidenceValidationError(dict(code="quote_not_in_passage",**diagnostic))
