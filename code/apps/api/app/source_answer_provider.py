"""One bounded synthesis and independent support audit; all dispatch uses existing guards."""
import json
import os
import re
from app import providers
from app.contracts import AnswerSupportVerdict,recover_whitespace_quote
from app.source_answer_contracts import SourceAnswer,WireSourceAnswer,PointerAnswer
from app.source_answer_contracts import LinkedAnswer
from app.query_language import arabic,operational_question


def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))


def linked_answer(question,sources,scope,authorize,context=None):
    """Ordinary chat: one generation and known-source links, without audit passes."""
    authorize()
    if not providers.configured():
        points=[]
        for source in sources[:6]:
            text=source.get('text') or '; '.join(f['field']+': '+canonical(f['value']) for f in source.get('fields',[])[:3])
            if text:points.append(dict(text=text[:2500],evidence=[dict(passage_id=source['reference_id'],quote='')]))
        return dict(statements=points,provider='mock-extractive',insufficient_evidence=True,followup_query='',
            validation_summary=dict(independent_verification=False))
    system=providers.UNTRUSTED+'''
You are Linkmind, a practical workplace assistant. Answer the actual question directly,
naturally and concisely in the user's language. Use only the supplied company sources.
Conversation topic identifies the project or issue; it is not evidence for facts.
Explain project purpose, features, customer, explicit ownership and useful next actions
when asked. Distinguish product acceptance, delivery accountability and technical work.
Use one short paragraph for simple facts, a compact list for several owners or actions.
Never narrate search mechanics instead of answering. Avoid unnecessary background.

Jira status must come from its current status field, not a dated description. A null
assignee does not erase an accountable owner named in the description. A closed bug
does not prove an entire project or shared identity risk is fixed. Approved policy is
not implementation completion. Keep draft/superseded policy separate from approved
policy. Do not invent dates, owners, progress, or completion of individual criteria.
In Progress does not mean every acceptance criterion is unfinished: list documented
requirements unless actual per-criterion progress is supplied.
Preserve source conditions without adding "before/after" relationships or deadlines.
Give supported useful parts and briefly identify a particular missing detail.

Each statement names source_ids from the supplied sources. These are simple relevant
source links, not quotations: do not copy quotes, JSON field values into citation
objects, generate URLs, or invent source IDs. Values do belong in normal answer text.
Use at most two relevant source links per statement. State exact issue keys normally.
If a genuinely important requested part is missing, insufficient_evidence=true and
followup_query may request one short targeted search or an issue key already mentioned
in sources. Otherwise followup_query="" and answer now. Do not request broad repeated
searches just to polish an adequate answer.
Default to two short paragraphs. A project introduction needs purpose, useful
features and its customer; leave detailed ownership, ticket lists and release gates
for follow-up questions. Ownership answers should focus on the requested roles.
Keep delivery accountability separate from launch authorization: name the launch
approver exactly as recorded, never promote the delivery coordinator into that role.
native_statuses contains the actual Jira workflow values. Use those for any "status"
label. If a description says delivery is blocked while Jira says In Progress, explain
that distinction; never replace the workflow field with the narrative business state.
'''
    native={};native_refs={}
    for source in sources:
        fields={f['field']:f['value'] for f in source.get('fields',[])}
        if fields.get('key') and fields.get('status') is not None:
            native[fields['key']]=str(fields['status']);native_refs[fields['key']]=source['reference_id']
    wire=providers.structured(LinkedAnswer,system,dict(question=question,sources=sources,native_statuses=native,
        answer_language='Arabic' if arabic(question) else 'English',conversation_topic=context or {}),
        scope,'answer','BEDROCK_ANSWER_MODEL',authorize=authorize)
    mapping={s['reference_id']:s for s in sources};points=[];unknown=0;bad_status=0;normalized=0
    for point in wire.statements[:10]:
        refs=list(dict.fromkeys(r for r in point.source_ids if r in mapping))[:2]
        unknown+=sum(r not in mapping for r in point.source_ids)
        if not refs or not point.text.strip():continue
        # Plain status labels beside issue keys are literal source fields, not
        # generated business interpretations. Keep the native value authoritative.
        text=point.text;matches=list(re.finditer(r'\b[A-Z][A-Z0-9_]{1,30}-\d+\b',text))
        edits=[];field_links=[]
        for index,match in enumerate(matches):
            key=match[0]
            if key not in native:continue
            end=matches[index+1].start() if index+1<len(matches) else len(text)
            segment=text[match.end():end]
            label=re.search(r'(?<!business )(?<!delivery )\bstatus\s*:\s*\**([A-Za-z][A-Za-z -]*?)(?=\**[),.;\n])',segment,re.I)
            if label and label[1].strip().casefold()!=native[key].casefold():
                edits.append((match.end()+label.start(1),match.end()+label.end(1),native[key]));field_links.append(native_refs[key])
        for start,end,value in reversed(edits):text=text[:start]+value+text[end:];normalized+=1
        if field_links:refs=list(dict.fromkeys(field_links+refs))[:2]
        contradicted=False
        for key,status in native.items():
            if key not in text:continue
            completion=re.search(re.escape(key)+r'.{0,50}\b(?:is|has been|was)\s+(?:now\s+)?(?:done|closed|resolved|fixed|completed)\b',text,re.I)
            if completion and status.casefold() not in {'done','closed','resolved','complete','completed'}:contradicted=True
            claim=re.search(r'\bJira\s+status\s*(?:is|:)\s*\**([A-Za-z ]{2,30})',text,re.I)
            if claim and status.casefold() not in claim[1].casefold():contradicted=True
        if contradicted:bad_status+=1;continue
        points.append(dict(text=text.strip(),evidence=[dict(passage_id=r,quote='') for r in refs]))
    return dict(statements=points,provider='bedrock',insufficient_evidence=wire.insufficient_evidence or not points or bool(bad_status),
        followup_query=wire.followup_query,validation_summary=dict(independent_verification=False,
            unknown_source_ids=unknown,status_claims_rejected=bad_status,status_values_normalized=normalized))


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


def answer(question,sources,scope,authorize,context=None):
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
Answer each supported part of the question using only supplied sources. Never infer that a project, document, or list does not exist because a sampled passage omits it. Missing search evidence only establishes that this bounded search could not verify the requested fact. Count/list requests require explicit enumeration evidence; do not count a sample of unrelated passages. Respond in the user's language. question_context can resolve references and enumeration coverage, but is not source evidence. Answer every requested part. Each statement must stand alone, naming its subject and project. Start with the direct supported answer and omit peripheral details that obscure it.
Use natural workplace Arabic. In a software context, pilot means a trial program (برنامج تجريبي), sandbox means a test environment (بيئة اختبار), and owns means مسؤول عن. Do not translate software pilot into طيار or sandbox into صندوق رمل. Keep names and project keys accurate.
For a structured record cite reference_id and its actual field name, with quote=null. The server resolves the original typed value. Never repeat JSON values or invent a quotation for a field. For a prose source cite reference_id and an exact short substring in quote, with field=null. Never quote across sources.
Write a useful, natural answer to the question, rather than a list of technical fields. Start with the direct answer, explain relevant implications supported by the sources, and separate each independently supported point into its own statement. Every factual clause needs support. Answer every requested part, including owners when the question also asks for a project count. Each ownership statement must identify the project and the specific role. An unsourced statement that a policy or owner does not exist is not supported by an unrelated page. If a limited search cannot find an HR policy, explain only that you could not verify it from the sources read; do not infer the company has no policy. If one requested detail is unknown, still answer the other parts and set insufficient_evidence=true. Do not reject a useful answer because a peripheral detail is missing. Explain uncertainty plainly, preserving native status versus narrative business state, dated roles and conditions.
Answer directly instead of narrating source headings or metadata unless the user asks about them. For ownership questions prefer explicit responsibility statements in the body and distinguish delivery, product and technical roles. A page maintainer is not automatically a project owner. For employee onboarding give a practical introduction and the explicitly named contact, without inventing HR policies or access already granted.
For onboarding, first explain the company's purpose, then summarize its teams and the starting contact. Do not dump a whole employee directory unless requested. A delivery cohort is not the entire company headcount; keep those claims separate.
Do not infer identity from names, authority from a narrower role, or temporal/causal relations not explicitly supported.
Keep dated stored reasons and current live fields distinguishable. Live evidence establishes only the observed resource at its observation time; saved facts are recorded facts. Never use today's live state as evidence for a missing past state.
Receipt/observation time is not a business effective date. Null fields do not establish an explanation or prove why a value is unavailable.
Attribute disagreements instead of silently picking a winner. Do not claim complete source review from partial context. If a requested part lacks support, give only supported statements and insufficient_evidence=true. Do not invent a source error explanation or expose internal IDs as business facts.
'''
    if os.getenv('LINKMIND_CHAT_POLISH')=='1':
        system+='\nUse at most four concise statements. A simple factual question usually needs one or two short statements. For complex questions, start with the reason or outcome, then explain only relevant supported dependencies. Do not add generic uncertainty introductions; qualify the particular missing fact only. Keep native Jira workflow/assignee separate from business readiness and delivery ownership described in prose.'
    payload=dict(question=question,answer_language='Arabic' if arabic(question) else 'English',sources=sources)
    if context:payload['question_context']=context
    wire=providers.structured(PointerAnswer,system,payload,scope,'answer','BEDROCK_ANSWER_MODEL',authorize=authorize)
    if isinstance(wire,WireSourceAnswer):
        # Compatibility for deterministic contract fixtures; runtime uses pointers.
        candidates=[];rejected=0
        for statement in wire.statements:
            try:candidates.extend(WireSourceAnswer(statements=[statement],insufficient_evidence=wire.insufficient_evidence).to_answer().statements)
            except (ValueError,RecursionError):rejected+=1
    else:candidates,rejected=wire.candidates(sources)
    anchored=[]
    for candidate in candidates:
        try:
            validate(SourceAnswer(statements=[candidate],insufficient_evidence=False),sources)
            anchored.append(candidate)
        except (ValueError,RecursionError):rejected+=1
    result=SourceAnswer(statements=anchored,insufficient_evidence=wire.insufficient_evidence or bool(rejected))
    result._validation=dict(candidates=len(wire.statements),citation_rejected=rejected,anchored=len(anchored))
    if not result.statements:return result,'citation_failed' if rejected else 'evidence_gap'
    if result.statements:
        cited={c.reference_id for s in result.statements for c in s.evidence}
        verdict=providers.structured(AnswerSupportVerdict,providers.ANSWER_SUPPORT_SYSTEM+'''
For this typed-source answer, sources replaces passages. Check each entire statement only against its cited source references.
For Arabic statements, verify meaning in context rather than literal word matching. In software sources a pilot is a trial program, not an aircraft pilot, and sandbox is a test environment. Reject mistranslations that change the supported meaning.
A field reference supports only the exact field/value and explicit subject identifiers in the same structured record. It is not a prose quotation. Passage references must be supported by their text and exact cited quotes.
Each source labels origin, revision, update and observation time. Only a live source can establish observed live operational state; historical questions require dated evidence for the requested period. Ordinary supported present-tense paraphrases do not imply a live check.
''',dict(question=question,requires_freshness_qualification=operational_question(question),
            statements=[s.model_dump() for s in result.statements],sources=[s for s in sources if s['reference_id'] in cited]),scope,'answer_verification','BEDROCK_ANSWER_MODEL',authorize=authorize)
        if len(verdict.reviews)!=len(result.statements):return SourceAnswer(statements=[],insufficient_evidence=True),'verification_failed'
        accepted=[statement for statement,review in zip(result.statements,verdict.reviews)
            if AnswerSupportVerdict(reviews=[review]).accepts([statement])]
        rejected+=len(result.statements)-len(accepted)
        counts={**result._validation,'semantic_rejected':len(result.statements)-len(accepted),'accepted':len(accepted)}
        result=SourceAnswer(statements=accepted,insufficient_evidence=result.insufficient_evidence or bool(rejected))
        result._validation=counts
        if not accepted:return result,'verification_failed'
    authorize()
    return result,'partial' if result.insufficient_evidence else 'answered' if result.statements else 'evidence_gap'
