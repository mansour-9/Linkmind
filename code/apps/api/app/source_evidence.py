"""Adapter evidence contract. Live observations are transient until explicitly retained."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, HttpUrl, model_validator


class ResourceIdentity(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    organization_id: UUID
    source_instance_id: UUID
    resource_type: str = Field(min_length=1, max_length=80)
    native_id: str = Field(min_length=1, max_length=1000)


class FieldEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid')
    field: str = Field(min_length=1, max_length=120)
    value: JsonValue


class EvidenceCoverage(BaseModel):
    complete: bool
    description: str = Field(min_length=1, max_length=500)


class SourceEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reference_id: str = Field(min_length=1, max_length=200)
    identity: ResourceIdentity
    origin: Literal['stored', 'live']
    synthetic: bool = False
    original_url: HttpUrl | None = None
    source_revision: str | None = None
    source_updated_at: datetime | None = None
    observed_at: datetime
    excerpt: str | None = None
    fields: list[FieldEvidence] = Field(default_factory=list)
    locator: dict[str, JsonValue] = Field(default_factory=dict)
    access_dependencies: list[ResourceIdentity] = Field(min_length=1, max_length=30)
    coverage: EvidenceCoverage

    @model_validator(mode='after')
    def validate_support(self):
        if bool(self.excerpt) == bool(self.fields):
            raise ValueError('Supply an original excerpt or actual structured fields, never fabricated field quotations.')
        if self.identity not in self.access_dependencies or any(
            dep.organization_id != self.identity.organization_id for dep in self.access_dependencies
        ):
            raise ValueError('Evidence must retain its own same-organization access dependency.')
        if self.observed_at.tzinfo is None or any(t is not None and t.tzinfo is None for t in [self.source_updated_at]):
            raise ValueError('Evidence times must include a timezone.')
        if self.origin == 'stored' and not self.source_revision:
            raise ValueError('Stored evidence requires its retained source revision.')
        return self


def local_evidence(row):
    identity = ResourceIdentity(organization_id=row['organization_id'],
        source_instance_id=row['source_instance_id'], native_id=row['native_id'], resource_type='document')
    return SourceEvidence(reference_id=str(row['id']), identity=identity, origin='stored',
        source_revision=str(row['version_id']), observed_at=row['uploaded_at'], excerpt=row['quote'],
        locator=row['locator'], access_dependencies=[identity],
        coverage=EvidenceCoverage(complete=False, description='One retained source passage; not a complete document review.'))
