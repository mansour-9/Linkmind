"""One bounded synthesis and independent support audit; all dispatch uses existing guards."""
import json
from app import providers
from app.contracts import AnswerSupportVerdict,recover_whitespace_quote
from app.source_answer_contracts import SourceAnswer
from app.query_language import arabic,operational_question


def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))


def validate(result,sources):
    mapping={s['reference_id']:s for s in sources}
    for statement in result.statements:
        for citation in statement.evidence:
            source=mapping.get(citation.reference_id)
            if source is None:raise ValueError('Unknown source reference.')
            if citation.kind=='passage':
                if source['kind']!='passage':raise ValueError('Fields cannot support prose quotations.')
                if citation.quote not in source['text']:
                    recovered=recover_whitespace_quote(source['text'],citation.quote)
                    if recovered is None:raise ValueError('The quotation is not in its source.')
                    citation.quote=recovered[0]
            elif source['kind']!='fields' or not any(f['field']==citation.field and canonical(f['value'])==canonical(citation.value) for f in source['fields']):
                raise ValueError('The cited typed field/value is not in this source.')
    return result


def answer(question,sources,scope,authorize):
    authorize()
    if not sources:return SourceAnswer(statements=[],insufficient_evidence=True),'evidence_gap'
    if not providers.configured():
        statements=[]
        for source in sources[:8]:
            if source['kind']=='passage':
                quote=source['text'][:2500]
                statements.append(dict(text=quote,evidence=[dict(reference_id=source['reference_id'],kind='passage',quote=quote)]))
            else:
                for field in source['fields'][:3]:
                    statements.append(dict(text=field['field']+': '+canonical(field['value']),
                        evidence=[dict(reference_id=source['reference_id'],kind='field',field=field['field'],value=field['value'])]))
            if len(statements)>=10:break
        # Explicitly incomplete: extractive demo is not a synthesized answer to every part.
        return validate(SourceAnswer(statements=statements[:12],insufficient_evidence=True),sources),'demo_excerpts'
    system=providers.CONVERSATION_SYSTEM+'\n'+providers.UNTRUSTED+'''
Answer each supported part of the question using only supplied sources. Respond in the user's language.
Treat a source's actual structured fields as field/value evidence: cite their exact JSON types and values with kind=field. Never invent a prose quotation for a field.
For kind=passage cite an exact substring of that single source text. Every clause needs supporting references. Do not infer identity from names, authority from a narrower role, or temporal/causal relations not explicitly supported.
Keep dated stored reasons and current live fields distinguishable. Live evidence establishes only the observed resource at its observation time; saved facts are recorded facts. Never use today's live state as evidence for a missing past state.
Receipt/observation time is not a business effective date. Null fields do not establish an explanation or prove why a value is unavailable.
Attribute disagreements instead of silently picking a winner. Do not claim complete source review from partial context. If a requested part lacks support, give only supported statements and insufficient_evidence=true. Do not invent a source error explanation or expose internal IDs as business facts.
'''
    result=providers.structured(SourceAnswer,system,dict(question=question,answer_language='Arabic' if arabic(question) else 'English',sources=sources),scope,'answer','BEDROCK_ANSWER_MODEL',authorize=authorize)
    try:validate(result,sources)
    except ValueError:return SourceAnswer(statements=[],insufficient_evidence=True),'citation_failed'
    if result.statements:
        cited={c.reference_id for s in result.statements for c in s.evidence}
        verdict=providers.structured(AnswerSupportVerdict,providers.ANSWER_SUPPORT_SYSTEM+'''
For this typed-source answer, sources replaces passages. Check each entire statement only against its cited source references.
A field reference supports only the exact field/value and explicit subject identifiers in the same structured record. It is not a prose quotation. Passage references must be supported by their text and exact cited quotes.
Each source labels origin, revision, update and observation time. Only a live source can establish observed live operational state; historical questions require dated evidence for the requested period. Ordinary supported present-tense paraphrases do not imply a live check.
''',dict(question=question,requires_freshness_qualification=operational_question(question),
            statements=[s.model_dump() for s in result.statements],sources=[s for s in sources if s['reference_id'] in cited]),scope,'answer_verification','BEDROCK_ANSWER_MODEL',authorize=authorize)
        if not verdict.accepts(result.statements):return SourceAnswer(statements=[],insufficient_evidence=True),'verification_failed'
    authorize()
    return result,'partial' if result.insufficient_evidence else 'answered' if result.statements else 'evidence_gap'
