"""Exact structured-source answers and citation actions, without model synthesis."""
import hashlib,json,re
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from urllib.parse import urlsplit
from fastapi import HTTPException
from app import connectors,chat_trace
from app.connector_transport import ReadLimits,SourceFailure,active
from app.query_language import arabic,normalize
from app.source_intent import project_request

def issue_key(source):
    value=source.get('source_key') or (source.get('live') or {}).get('native_id','')
    if not re.fullmatch(r'[A-Z][A-Z0-9_]+-\d+',value):value=urlsplit(source.get('original_url','')).path.rsplit('/',1)[-1]
    return value if re.fullmatch(r'[A-Z][A-Z0-9_]+-\d+',value) else ''

def record_evidence(row,record):
    fields={f['field']:f['value'] for f in record.fields}
    dependency=dict(connection_id=str(row['id']),native_id=fields['key'],generation=row['generation'],revision=record.revision)
    reference='live-'+hashlib.sha256(json.dumps([str(row['id']),record.native_id,record.revision]).encode()).hexdigest()[:24]
    return dict(id=reference,filename=fields.get('summary') or fields['key'],text='',version_id='',document_id='live:'+str(row['id'])+':'+record.native_id,
        locator={},live=dependency,original_url=record.original_url,source_key=fields['key'],source_application='Jira',
        observed_at=connectors.now().isoformat(),source_updated_at=record.updated.isoformat()),fields

def response(statements,evidence,query,**extra):
    dependencies=list({(p['live']['connection_id'],p['live']['native_id']):p['live'] for p in evidence if p.get('live')}.values())
    return dict(statements=statements,evidence=evidence,provider='structured',insufficient_evidence=False,answer_state=dict(code='answered'),
        live_dependencies=dependencies,retrieval_query=query,retrieval_activity=[],source_outcomes=[],**extra),[]

def answer(question,rows,previous):
    text=normalize(question)
    limits=active() or ReadLimits()
    references=bool(re.search(r'(which|what).*(jira|issue).*(support|source|evidence)|اي.*(تذاكر|مهام).*(دليل|تدعم|مصدر)',text))
    opening=bool(re.search(r'(open|افتح).*(original|source|مصدر|الاصلي)',text))
    if (references or opening) and previous:
        prior=previous[0]['response'];used={c['passage_id'] for s in prior.get('statements',[]) for c in s.get('evidence',[])}
        found=[];seen=set()
        for source in prior.get('evidence',[]):
            if source['id'] not in used or not source.get('original_url'):continue
            if references and not issue_key(source):continue
            identity=source['original_url']
            if identity in seen:continue
            seen.add(identity);found.append(source)
        statements=[dict(text=(issue_key(s)+' — ' if issue_key(s) else '')+s['filename'],evidence=[dict(passage_id=s['id'],quote='')]) for s in found]
        return response(statements,found,question,presentation=dict(kind='source_links'),message=(
            'افتح المصدر المطلوب من الروابط أدناه.' if arabic(question) else 'Open the source you need below.') if found else
            ('لم أستخدم مصدر Jira قابلًا للفتح في الرد السابق.' if arabic(question) else 'The previous answer has no matching source link.'))
    key=re.search(r'\b[A-Z][A-Z0-9_]+-\d+\b',question.upper())
    status=bool(re.search(r'\b(status|assignee)\b|حاله|حالة|المسند',text))
    if key and status:
        row=next((r for r in rows if r['kind']=='jira' and r['config']['scope_id']==key[0].rsplit('-',1)[0]),None)
        if row is None:return response([],[],question,message='This issue is outside your enabled Jira scopes.')
        chat_trace.activity('searching_jira')
        try:
            with chat_trace.stage('structured.issue'):
                record=connectors.Provider(row['config'],limits,row['id']).get(key[0],mcp=True)
            source,fields=record_evidence(row,record)
            field='assignee' if 'assignee' in text or 'المسند' in text else 'status';value=fields.get(field)
            if value is None:statement=('لا يوجد مسؤول مسجل في حقل التعيين لهذه التذكرة.' if arabic(question) else 'No assignee is recorded for this issue.') if field=='assignee' else ('لم يرجع Jira حالة لهذه التذكرة.' if arabic(question) else 'Jira did not return a status for this issue.')
            else:statement=(f'حالة {key[0]} في Jira: **{value}**.' if arabic(question) else f'{key[0]} Jira {field}: **{value}**.')
            return response([dict(text=statement,evidence=[dict(passage_id=source['id'],quote=field+': '+json.dumps(value))])],[source],question)
        except (SourceFailure,HTTPException) as exc:
            return response([],[],question,source_failures=[dict(name=row['name'],code=exc.code if isinstance(exc,SourceFailure) else 'access_denied')],message='Jira access could not be confirmed. Check the connection and try again.')
    project_intent=project_request(question)
    if not project_intent:return None
    jira=[row for row in rows if row['kind']=='jira'][:6]
    chat_trace.activity('searching_jira')
    def read(row):
        try:
            with chat_trace.stage('structured.project'):
                provider=connectors.Provider(row['config'],limits,row['id'])
                record=provider.project_snapshot()
            if record is None:return row,None,'no_visible_issue'
            return row,record,None
        except (SourceFailure,HTTPException) as exc:return row,None,exc.code if isinstance(exc,SourceFailure) else 'access_denied'
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(copy_context().run,read,row) for row in jira]
        values=[future.result() for future in futures]
    evidence=[];statements=[];items=[];failures=[]
    for row,record,error in values:
        if error:failures.append(dict(name=row['name'],code=error));continue
        source,fields=record_evidence(row,record);project=fields.get('project')
        if not project or not project.get('name'):failures.append(dict(name=row['name'],code='project_metadata_missing'));continue
        if any(item["key"]==project["key"] and next((p["original_url"].split("/browse/")[0] for p in evidence if p["id"]==item["source_id"]),None)==source["original_url"].split("/browse/")[0] for item in items):continue
        evidence.append(source);items.append(dict(key=project['key'],name=project['name'],source_id=source['id']))
        statements.append(dict(text=project['key']+' — '+project['name'],evidence=[dict(passage_id=source['id'],quote='project: '+json.dumps(project,ensure_ascii=False))]))
    result,_=response(statements,evidence,question,presentation=dict(kind='projects',items=items),source_failures=failures,
        message=('المشاريع المتاحة عبر وصلات Jira المفعّلة:' if arabic(question) else 'Projects available through your enabled Jira connections:') if statements else
        ('لا توجد مشاريع Jira يمكنني التحقق منها حاليًا.' if arabic(question) else 'No Jira projects could be verified through your enabled connections.'))
    result['project_coverage']=dict(verified_count=len(items),configured_scopes=len(jira),complete=not failures and len(jira)==len([r for r in rows if r['kind']=='jira']),scope='enabled_connections')
    result['retrieval_activity']=[dict(operation='project_enumeration',mode='live',returned_passages=len(evidence),source_count=len(items),semantic_status=None)]
    if items:
        result['message']=(f"تحققت من {len(items)} مشاريع Jira متصلة ضمن المصادر المفعلة لديك." if arabic(question) else f"I verified {len(items)} connected Jira projects within your enabled sources.")
        if failures:result['message']+=(' بعض المصادر تعذر التحقق منها، لذا العدد غير مكتمل.' if arabic(question) else ' Some sources could not be verified, so this count is incomplete.')
    result['insufficient_evidence']=bool(failures)
    if len([r for r in rows if r['kind']=='jira'])>len(jira):
        result['message']+=' Showing the first six enabled connections.'
        result['insufficient_evidence']=True
    return result,[]
