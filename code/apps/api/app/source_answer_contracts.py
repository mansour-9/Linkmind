"""Citations distinguish original passages from typed source fields."""
from typing import Literal
import json
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


class WireSourceReference(Contract):
    reference_id:str
    kind:Literal['passage','field']
    quote:str|None
    field:str|None
    value_json:str|None


class WireSourceStatement(Contract):
    text:str
    evidence:list[WireSourceReference]


class WireSourceAnswer(Contract):
    """Bedrock schema stays non-recursive; strict application validation stays intact."""
    statements:list[WireSourceStatement]
    insufficient_evidence:bool

    def to_answer(self):
        statements=[]
        for statement in self.statements:
            references=[]
            for item in statement.evidence:
                data=item.model_dump(exclude={'value_json'})
                if item.kind=='field':
                    if item.value_json is None:raise ValueError('A field reference requires JSON-encoded source data.')
                    def invalid_constant(value):raise ValueError('Non-finite JSON field value.')
                    data['value']=json.loads(item.value_json,parse_constant=invalid_constant)
                elif item.value_json is not None:raise ValueError('A passage reference cannot contain field data.')
                references.append(data)
            statements.append(dict(text=statement.text,evidence=references))
        return SourceAnswer(statements=statements,insufficient_evidence=self.insufficient_evidence)
