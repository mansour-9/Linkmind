"""Explicit model support stubs; these establish no real-model quality."""
from app.contracts import AnswerSupportVerdict

def support_verdict(payload, supported):
    statements=payload['statements']
    return AnswerSupportVerdict(reviews=[dict(statement=statements[i]['text'] if i<len(statements) else 'unexpected',
        supported=value,unsupported_fragments=[] if value else ['synthetic rejected clause'],
        temporal_scope_supported=value,authority_scope_supported=value,freshness_supported=value,
        reason='Deterministic stub, not model acceptance.') for i,value in enumerate(supported)])
