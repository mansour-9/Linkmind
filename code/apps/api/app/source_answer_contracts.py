"""Citations distinguish original passages from typed source fields."""
from typing import Literal
from pydantic import Field,JsonValue,model_validator
from app.contracts import Contract


class SourceReference(Contract):
    reference_id:str
    kind:Literal['passage','field']
    quote:str|None=None
    field:str|None=None
    value:JsonValue=None

    @model_validator(mode='after')
    def valid(self):
        if self.kind=='passage' and (not self.quote or self.field is not None or self.value is not None):
            raise ValueError('Passage references require an exact quote, without field data.')
        if self.kind=='field' and (not self.field or self.quote is not None):
            raise ValueError('Field references require a field/value, never a fabricated quotation.')
        return self


class SourceStatement(Contract):
    text:str=Field(min_length=1,max_length=3000)
    evidence:list[SourceReference]=Field(min_length=1,max_length=12)


class SourceAnswer(Contract):
    statements:list[SourceStatement]=Field(max_length=12)
    insufficient_evidence:bool
