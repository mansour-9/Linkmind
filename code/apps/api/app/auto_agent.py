"""Ordinary chat: scoped retrieval, one answer, simple source links."""
import json,re
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from uuid import UUID
from fastapi import HTTPException
from app import providers,retrieval,connectors,source_answers,source_answer_provider,chat_agent,chat_trace,structured_chat
from app import content_domains as domains
from app.assistant_persona import local_reply
from app.question_intent import intent
from app.query_language import arabic, normalize
from app.query_limits import active as question_limits
from app.connector_transport import active as read_limits,SourceFailure
from app.chat_retrieval import rank_hits,purpose
from app.conversation_routing import followup


def failure_code(exc):
    if isinstance(exc,SourceFailure):return exc.code
    return exc.detail.get('code','source_unavailable') if isinstance(exc.detail,dict) else 'source_unavailable'


def assert_live(viewer,dependencies,db):
    """One fresh permission/revision check at delivery; no permission TTL cache."""
    def check(item):
        with db.connect() as conn:row=connectors.owned(conn,viewer,UUID(item['connection_id']))
        if row.mode=='disconnected' or row.generation!=item['generation']:
            raise HTTPException(409,'Connected source settings changed.')
        if domains.enabled() and not domains.live_mcp(row.config):
            raise HTTPException(409,'The source is outside the live MCP corpus.')
        try:current=connectors.Provider(row.config,read_limits(),row.id).authorize(item['native_id'])
        except SourceFailure as exc:
            raise HTTPException(503,dict(code=exc.code,message='A connected source could not be rechecked. No answer was published.')) from None
        revision=current.get('eTag') if isinstance(current,dict) else current.revision
        if revision!=item['revision']:raise HTTPException(409,'Connected source revision changed.')
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(copy_context().run,check,item) for item in dependencies]
        for job in jobs:job.result()


def handbook_question(question):
    text=question.casefold()
    if re.search(r'\b(?:jira|confluence|projects?|sprints?|issues?)\b|المشروع|جيرا|كونفلونس',text):return False
    return bool(handbook_lookup(question)
        or re.search(r'\b(?:notion|onedrive|sharepoint|handbook|polic(?:y|ies)|departments?|onboarding|leave|company|organization)\b|الشركة|الأقسام|الموظفين|الإجازة|سياسة',text)
        or (not followup(question) and re.match(r'^(?:what is|what\x27s|tell me about)\s+\S',text)))


def handbook_lookup(question):
    text=normalize(question)
    if re.search(r'\b(?:people operations|human resources|hr)\b|عمليات الموظفين|الموارد البشرية',text):
        return 'people operations'
    if re.search(r'\b(?:annual leave|paid time off|vacation allowance)\b|اجاز(?:ة|ه|تي|تنا|ات)\s+(?:ال)?سنوي',text):
        return 'annual leave policy'
    if re.search(r'\b(?:what (?:does|is) (?:our|the|this) company|(?:our|the) company (?:do|build)|company overview)\b|(?:وش|ايش|ماذا) (?:تسوي|تشتغل|تعمل|تقدم) الشركة|ما عمل الشركة|عن الشركة',text):
        return 'company and teams'
    return None


def topic(question,previous,rows):
    allowed={r['config']['scope_id'] for r in rows if r['kind']=='jira'}
    def projects(text):return [p for p in sorted(allowed) if re.search(r'\b'+re.escape(p)+r'\b',text,re.I)]
    explicit=projects(question);keys=re.findall(r'\b[A-Z][A-Z0-9_]{1,30}-\d+\b',question.upper())
    prior=next((p for p in previous if p.get('response',{}).get('topic') or p.get('question')),None)
    saved=(prior or {}).get('response',{}).get('topic',{})
    project_keys=explicit or [p for p in saved.get('project_keys',[]) if p in allowed]
    if not project_keys and prior:project_keys=projects(prior['question'])
    prior_keys=[k for k in saved.get('issue_keys',[]) if k.rsplit('-',1)[0] in allowed]
    focus=keys[0] if len(keys)==1 else None if explicit else saved.get('focus_issue')
    if focus and focus.rsplit('-',1)[0] not in allowed:focus=None
    return dict(project_keys=project_keys,issue_keys=keys or prior_keys,focus_issue=focus),keys


def question_kind(question):
    text=question.casefold()
    if re.search(r'entire|broader|whole|does.*mean|المشكلة.*كامل|كامل.*المشكلة',text):return 'context'
    if re.search(r'next|should.*do|الخطوة|وش.*نسوي|ماذا.*نفعل',text):return 'release'
    if re.search(r'criteria|acceptance|معايير|قبول',text):return 'issue'
    if re.search(r'owner|owns|responsib|who.*(own|lead)|مسؤول|المسئول|مالك|ملاك|اونر|مين.*يمسك',text):return 'ownership'
    if re.search(r'\b(status|resolved|closed|fixed|done|assignee)\b|حالة|حاله|انحلت|تم حل|خلصت',text):return 'status'
    return purpose(question)


def response(viewer,question,previous,db,search,configured,document_ids=None,attachments=(),*,policy='auto'):
    limits=question_limits();limits.max_model_calls=2;limits.max_planner_calls=0;limits.max_retrievals=4
    if intent(question) in {'greeting','help','social'}:
        return dict(statements=[],evidence=[],provider='system',insufficient_evidence=False,
            message=local_reply(question,intent(question),previous),retrieval_activity=[]),[]
    rows=chat_agent.connections(viewer,db)
    if domains.enabled():
        rows=[row for row in rows if domains.live_mcp(row['config']) and policy!='stored']
    current,explicit_keys=topic(question,previous,rows);kind=question_kind(question)
    files=list(document_ids or []);attached=list(attachments)
    file_only=bool(files) or bool(re.search(
        r'\b(?:only|solely)\b.*\b(?:file|document|upload)|\b(?:file|document|upload)\w*\b.*\bonly\b|(?:الملف|المرفق|المستند).*فقط|فقط.*(?:الملف|المرفق|المستند)',question,re.I))
    project=current['project_keys'][0] if len(current['project_keys'])==1 else ''
    units={};evidence={};stored={};live={};outcomes=[];activity=[];read_keys=set()
    discovered=set(explicit_keys);project_coverage=None
    target_keys=explicit_keys or ([current['focus_issue']] if current['focus_issue'] and kind!='release' else current['issue_keys'] if kind=='status' else [])
    if project:
        query=project+(' ownership scope' if kind=='ownership' and not target_keys else ' release plan' if kind in {'release','status'} else ' scope overview')
    elif kind=='directory':query='people department directory'
    elif kind=='policy':
        query='analytics retention' if re.search(r'retain|retention|احتفاظ|تحليلات',question,re.I) else question[:200]
    else:query=question[:200]

    def authorize():
        # A source read already checked remote permission. Recheck local ownership
        # and generations before synthesis; MCP is freshly checked once at delivery.
        with db.connect() as conn:
            if domains.enabled() and not retrieval.manual_passages_allowed(conn,viewer,list(stored)):
                raise HTTPException(409,'Document evidence is outside the manual corpus.')
            if not retrieval.dependencies_allowed(conn,viewer,list(stored)):
                raise HTTPException(409,'Document access or revision changed.')
            for dep in live.values():
                row=connectors.owned(conn,viewer,UUID(dep['connection_id']))
                if row.mode=='disconnected' or row.generation!=dep['generation']:
                    raise HTTPException(409,'Connected source settings changed.')

    def documents(text):
        if policy=='live':return
        limits.retrieve()
        if domains.enabled():
            found=retrieval.search_manual(viewer,text,document_ids=files or None)
            if files and not found:found,_,_=retrieval.manual_context(viewer,files,question=text)
        else:
            found=search(viewer,text,document_ids=files or (attached if file_only else None),semantic=False,limit=6)
            if (files or attached) and not found:found,_=retrieval.selected_context(viewer,files or attached,question=text)
        for item in source_answers.stored_sources(found,manual=domains.enabled()):
            refs=[p for p in found if str(p['document_id'])==str(item['document_id'])]
            if item['kind']=='fields' and refs:item['reference_id']=refs[0]['id']
            units[item['reference_id']]=item
        for p in found:
            stored[str(p['id'])]=p;evidence[str(p['id'])]=dict(p,origin='stored',synthetic=bool(p.get('dataset_id')))
        activity.append(dict(operation='indexed_search',mode='stored',returned_passages=len(found),source_count=len({str(p['document_id']) for p in found}),semantic_status='not_requested'))

    def observe(row,native,title,value):
        item=value['evidence'];key=(str(row['id']),native)
        dep=dict(connection_id=str(row['id']),native_id=native,generation=row['generation'],revision=item['source_revision'])
        live[key]=dep
        fields=item['fields'];native_key=next((f['value'] for f in fields if f['field']=='key'),'')
        name=item.get('display_title') or title or row['name']
        if isinstance(native_key,str) and native_key and not name.startswith(native_key):name=native_key+' — '+name
        text=next((f['value'] for f in fields if f['field']=='description'),None)
        if text is None:text='\n'.join(p['text'] for p in value['passages'])
        ref=item.get('reference_id') or next(p['id'] for p in value['passages']);document='live:'+str(row['id'])+':'+native
        units[ref]=dict(reference_id=ref,document_id=document,kind='fields' if fields else 'passage',
            text=text,fields=[f for f in fields if f['field']!='description'],name=name,origin='live',
            original_url=item['original_url'],source_revision=item['source_revision'],source_updated_at=item['source_updated_at'],
            observed_at=item['observed_at'],synthetic=item['synthetic'],revision_role='live',locator={})
        evidence[ref]=dict(id=ref,filename=name,text=text,version_id='',document_id=document,locator={},live=dep,
            original_url=item['original_url'],source_key=native_key,source_application=row['kind'],
            observed_at=item['observed_at'],source_updated_at=item['source_updated_at'])
        discovered.update(re.findall(r'\b[A-Z][A-Z0-9_]{1,30}-\d+\b',text or ''))
        outcomes.append(dict(name=row['name'],code='observed',resources=1))

    def fetch(jobs):
        chat_trace.activity('reading_sources')
        available=[];seen=set(read_keys)
        for row,native,title in jobs:
            key=(str(row['id']),native)
            if key not in seen and len(live)+len(available)<6:
                seen.add(key);available.append((row,native,title))
        def run(job):
            row,native,title=job
            try:return job,connectors.live(viewer,row['id'],connectors.LiveRead(native_id=native,retrieval_query=query[:500])),None
            except (SourceFailure,HTTPException) as exc:return job,None,failure_code(exc)
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs=[pool.submit(copy_context().run,run,j) for j in available]
            for job in jobs:
                (row,native,title),value,error=job.result();read_keys.add((str(row['id']),native))
                if error:outcomes.append(dict(name=row['name'],code=error,resources=0))
                else:observe(row,native,title,value)
        activity.append(dict(operation='connected_read',mode='live',returned_passages=len(available),source_count=len(available),semantic_status=None))

    def exact(keys):
        jobs=[]
        for key in keys:
            row=next((r for r in rows if r['kind']=='jira' and r['config']['scope_id']==key.rsplit('-',1)[0]),None)
            if row:jobs.append((row,key,key))
        return jobs

    def discover(text,source_kind='confluence',count=2):
        limits.retrieve();jobs=[]
        chat_trace.activity('searching_'+source_kind)
        relevant=[r for r in rows if r['kind']==source_kind and (source_kind!='jira' or not project or r['config']['scope_id']==project)]
        for row in relevant[:2]:
            try:
                hits=connectors.Provider(row['config'],read_limits(),row['id']).search(text,limit=6)
                if source_kind!='notion':hits=rank_hits(text,hits)
                jobs.extend((row,h['native_id'],h['title']) for h in hits[:count])
                if not hits:outcomes.append(dict(name=row['name'],code='no_matches',resources=0))
            except (SourceFailure,HTTPException) as exc:outcomes.append(dict(name=row['name'],code=failure_code(exc),resources=0))
        return jobs

    # Keep working configured-project enumeration, including compound owner asks.
    from app.source_intent import words
    normalized=words(question)
    enumerating=bool(re.search(r'\bprojects?\b|المشاريع|مشاريع|مشروع',normalized) and
        re.search(r'\b(count|how (many|may)|number|total|list|available|which projects|what projects)\b|عدد|كم|الموجود',normalized))
    if enumerating and not file_only:
        direct=structured_chat.answer('count projects',rows,[])
        if direct:
            if kind!='ownership':return direct
            result=direct[0]
            project_coverage=result.get('project_coverage')
            for p in result['evidence']:
                ref=p['id'];dep=p['live'];live[(dep['connection_id'],dep['native_id'])]=dep;evidence[ref]=p
                quotes=[c['quote'] for s in result['statements'] for c in s['evidence'] if c['passage_id']==ref and c['quote'].startswith('project: ')]
                units[ref]=dict(reference_id=ref,document_id=p['document_id'],kind='fields',text=None,
                    fields=[dict(field='project',value=json.loads(q[9:])) for q in quotes],name=p['filename'],origin='live',
                    original_url=p['original_url'],source_revision=dep['revision'],observed_at=p['observed_at'],synthetic=False)
            query='project ownership register'

    notion=any(row['kind']=='notion' for row in rows)
    document_source='notion' if notion and not (project or target_keys) and handbook_question(question) else 'confluence'
    if files or attached:documents(question)
    if not file_only:
        if target_keys:fetch(exact(target_keys))
        else:
            jobs=discover((handbook_lookup(question) or question) if document_source=='notion' else query,document_source,
                count=1 if kind in {'release','status'} else 2)
            if not jobs and project:jobs=discover(project,'jira',count=2)
            if not jobs and notion and not project and document_source=='confluence':
                jobs=discover(question,'notion',count=2)
            fetch(jobs)
        if kind in {'release','status'} and project and not target_keys:
            linked=sorted((k for k in discovered if k.startswith(project+'-')),key=lambda k:int(k.rsplit('-',1)[1]))
            fetch(exact(linked[:3]))
    if not units and not stored and (file_only or not explicit_keys):documents(query)

    # Literal statuses never depend on prose generation or old chat answers.
    def native_status_points():
        statements=[]
        for source in units.values():
            fields={f['field']:f['value'] for f in source['fields']}
            if fields.get('key') not in target_keys:continue
            field='assignee' if 'assignee' in question.casefold() else 'status';value=fields.get(field)
            text=(f"{fields['key']} is {value} in Jira." if not arabic(question) else f"حالة {fields['key']} في Jira: {value}.") if value is not None else f"Jira does not record {field} for {fields['key']}."
            statements.append(dict(text=text,evidence=[dict(passage_id=source['reference_id'],quote=field+': '+source_answer_provider.canonical(value))]))
        return statements
    if kind=='status' and target_keys and not re.search(r'\b(owner|criteria|why|next)\b|معايير|مسؤول',question,re.I):
        statements=native_status_points()
        if statements:
            current['issue_keys']=[k for k in target_keys if any(e.get('source_key')==k for e in evidence.values())]
            return dict(statements=statements,evidence=list(evidence.values()),provider='structured',insufficient_evidence=False,
                retrieval_query=query,topic=current,live_dependencies=list(live.values()),source_outcomes=outcomes,retrieval_activity=activity,
                answer_state=dict(code='answered'),validation_summary=dict(independent_verification=False,native_fields=True)),list(stored)

    def synthesize():
        bounded,characters=source_answers.context(list(units.values()),limits)
        selected={s['reference_id'] for s in bounded}
        chat_trace.event('evidence_selection',selected=list(selected),available=len(units),characters=characters)
        return source_answer_provider.linked_answer(question,[{k:v for k,v in s.items() if k!='document_id'} for s in bounded],
            dict(org=viewer.organization_id,user=viewer.id),authorize,context=dict(topic=current,project_coverage=project_coverage)),selected

    if not units:
        return dict(statements=[],evidence=[],provider='system',insufficient_evidence=True,
            message='I could not reach enough relevant information from the available sources.',
            answer_state=dict(code='source_unavailable' if any(o['code']!='no_matches' for o in outcomes) else 'evidence_gap'),
            retrieval_query=query,topic=current,live_dependencies=[],source_outcomes=outcomes,retrieval_activity=activity),[]
    try:result,selected=synthesize()
    except providers.ModelResponseError:
        points=native_status_points() if re.search(r'\bstatus\b|حالة',question,re.I) else []
        if not points:raise
        return dict(statements=points,evidence=list(evidence.values()),provider='structured',insufficient_evidence=True,
            message='I could read the Jira fields, but could not generate the remaining explanation.',
            answer_state=dict(code='partial'),topic=current,retrieval_query=query,live_dependencies=list(live.values()),
            source_outcomes=outcomes,retrieval_activity=activity),list(stored)
    if result.get('followup_query') and result['insufficient_evidence'] and limits.remaining()>18 and limits.model_calls<2:
        followup=result['followup_query'][:200];before=set(units)
        keys=re.findall(r'\b[A-Z][A-Z0-9_]{1,30}-\d+\b',followup.upper())
        if keys:fetch(exact([k for k in keys if k in discovered]))
        elif not file_only:fetch(discover(followup,document_source,count=2))
        else:documents(followup)
        if set(units)!=before:result,selected=synthesize()
    used=[p for ref,p in evidence.items() if ref in selected]
    dependencies=[p['id'] for p in used if not p.get('live')]
    live_used=[d for d in live.values() if any(p.get('live')==d for p in used)]
    cited={c['passage_id'] for s in result['statements'] for c in s['evidence']}
    current['issue_keys']=list(dict.fromkeys(p.get('source_key') for p in used if p['id'] in cited and p.get('source_key')))
    if kind=='release':
        current['issue_keys']=[p['source_key'] for p in used if p.get('source_key') and
            not re.search(r'gate|rebaseline',p['filename'],re.I)]
    if len(explicit_keys)==1:current['focus_issue']=explicit_keys[0]
    result.pop('followup_query',None)
    result.update(evidence=used,live_dependencies=live_used,retrieval_query=query,topic=current,source_outcomes=outcomes,
        retrieval_activity=activity,project_coverage=project_coverage,answer_state=dict(code='partial' if result['insufficient_evidence'] else 'answered'))
    return result,dependencies
