from datetime import date
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

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
    # Local classification, never a new model-generated field or source fact.
    _failure_reason: str | None = PrivateAttr(default=None)

class ConflictJudgment(Contract):
    pair_id: str
    conflict: bool
    rationale: str

class ConflictJudgments(Contract):
    judgments: list[ConflictJudgment]

class AnswerVerdict(Contract):
    supported: list[bool]


class StatementSupport(Contract):
    statement: str
    supported: bool
    unsupported_fragments: list[str]
    temporal_scope_supported: bool
    authority_scope_supported: bool
    freshness_supported: bool
    reason: str = Field(min_length=1)


class AnswerSupportVerdict(Contract):
    reviews: list[StatementSupport]

    def accepts(self, statements):
        # A verdict for a shortened/reordered statement cannot certify the answer.
        return len(self.reviews) == len(statements) and all(
            review.statement == statement.text and review.supported
            and not review.unsupported_fragments and review.temporal_scope_supported
            and review.authority_scope_supported and review.freshness_supported
            for review, statement in zip(self.reviews, statements))


def recover_whitespace_quote(source: str, quote: str):
    """Map one unique whitespace-only match back to exact original character bounds.

    No punctuation, case, words, identifiers or source boundaries are changed. The
    returned quotation is always a literal source substring, never normalized text.
    """
    needle=" ".join(quote.split())
    if not needle:
        return None
    characters=[]
    bounds=[]
    previous_end=0
    for token in re.finditer(r"\S+",source):
        if characters:
            characters.append(" ")
            bounds.append((previous_end,token.start()))
        characters.extend(token.group())
        bounds.extend((i,i+1) for i in range(token.start(),token.end()))
        previous_end=token.end()
    normalized="".join(characters)
    position=normalized.find(needle)
    if position<0 or normalized.find(needle,position+1)>=0:
        return None
    start=bounds[position][0]
    end=bounds[position+len(needle)-1][1]
    return source[start:end],start,end


def validate_extraction(result: Extraction, passages: list[dict]) -> Extraction:
    passage_map = {item["id"]: item["text"] for item in passages}
    keys = {item.key for item in result.entities}
    if len(keys) != len(result.entities):
        raise ValueError("Duplicate entity key")
    if len(result.entities) > 100 or len(result.claims) > 200 or len(result.relationships) > 200:
        raise ValueError("Extraction exceeds batch limits")
    issues = []
    def check_evidence(citations, item_kind, item_index):
        for citation_index, citation in enumerate(citations or [None]):
            try:
                validate_citations([citation] if citation else [], passage_map)
            except EvidenceValidationError as exc:
                issues.append({**exc.diagnostic, "item_kind":item_kind, "item_index":item_index,
                    **({"citation_index":citation_index} if citation else {})})
    for entity_index, entity in enumerate(result.entities):
        check_evidence(entity.evidence, "entity", entity_index)
        for identifier_index, identifier in enumerate(entity.identifiers):
            diagnostic = dict(entity_index=entity_index, entity_key=entity.key[:200],
                entity_name=entity.name[:200], identifier_index=identifier_index,
                namespace=identifier.namespace, value=identifier.value[:200],
                evidence=[dict(passage_id=c.passage_id, quote=c.quote[:500]) for c in entity.evidence[:4]])
            if identifier.namespace=="project_key" and entity.kind not in {"project","decision"} or identifier.namespace=="issue_key" and entity.kind!="task":
                issues.append(dict(code="identifier_namespace_mismatch", **diagnostic))
                continue
            # Match the same conservative normalization used by identity persistence.
            # Keep the supplied value and the exact original quote unchanged. Aliases,
            # punctuation changes and URL rewrites need their own literal source support.
            value = identifier.value.strip().casefold()
            if not value or not any(value in citation.quote.casefold() for citation in entity.evidence):
                issues.append(dict(code="identifier_not_in_evidence", **diagnostic))
    for claim_index, claim in enumerate(result.claims):
        if claim.entity_key not in keys:
            raise ValueError("Claim references an unknown entity")
        check_evidence(claim.evidence, "claim", claim_index)
    for relationship_index, relationship in enumerate(result.relationships):
        if relationship.source_key not in keys or relationship.target_key not in keys:
            raise ValueError("Relationship references an unknown entity")
        check_evidence(relationship.evidence, "relationship", relationship_index)
    if issues:
        if len(issues)==1:
            raise EvidenceValidationError(issues[0])
        code="invalid_identifiers" if all(i["code"].startswith("identifier_") for i in issues) else "invalid_extraction_evidence"
        raise EvidenceValidationError(dict(code=code, issue_count=len(issues), issues=issues[:12]))
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
