"""Main-chat retrieval over owner-authorized stored and live sources."""
import copy
import json
import re
import os
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from uuid import UUID
from fastapi import HTTPException
from app.db import sql
from app import connectors,source_answers,source_answer_provider,retrieval,source_discovery
from app.connector_transport import ReadLimits,SourceFailure,active
from app.query_limits import active as query_limits
from app.query_language import arabic,normalize,explain
from app.source_discovery import terms
from app.conversation_routing import plan,followup
from app import chat_trace,structured_chat,source_policy


def allowed(viewer,dependencies,db,cache=None):
    with chat_trace.stage('permissions'):
        return _allowed(viewer,dependencies,db,cache)


def _allowed(viewer,dependencies,db,cache=None):
    """Fresh source checks; optional memoization only for one history/previous scan."""
    if os.getenv('LINKMIND_CHAT_POLISH')=='1' and len(dependencies)>1:
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs=[pool.submit(copy_context().run,_allowed_one,viewer,item,db,cache) for item in dependencies]
            return all([job.result() for job in jobs])
    for item in dependencies:
        if not _allowed_one(viewer,item,db,cache):return False
    return True

def _allowed_one(viewer,item,db,cache):
        key=(item['connection_id'],item['native_id'],item['generation'],item['revision'])
        if cache is not None and key in cache:
            return cache[key]
        valid=False
        try:
            with db.connect() as conn:row=connectors.owned(conn,viewer,UUID(item['connection_id']))
            if row.mode!='disconnected' and row.generation==item['generation']:
                current=connectors.Provider(row.config,active() or ReadLimits(),row.id).authorize(item['native_id'])
                revision=current.get('eTag') if isinstance(current,dict) else current.revision
                valid=revision==item['revision']
        except (HTTPException,SourceFailure):pass
        if cache is not None:cache[key]=valid
        return valid


def retained_response(response):
    """Save the derived reply/citations, not complete Live Only source bodies."""
    value=copy.deepcopy(response)
    # Detailed resource discovery is request-local. Saved timing/usage diagnostics
    # must not become a second surface for revoked source titles or identifiers.
    for event in value.get('diagnostics',{}).get('events',[]):
        for key in ('title','native_id','revision','connection_id','candidates','selected','excluded','actions'):
            event.pop(key,None)
    for evidence in value.get('evidence',[]):
        if evidence.get('live'):
            evidence['text']=''
            evidence.pop('fields',None)
    return value


def connections(viewer,db):
    with db.connect() as conn:
        return [dict(r) for r in sql(conn,'''SELECT c.id,c.config,c.mode,c.generation,s.name,s.kind
            FROM source_connections c JOIN source_instances s ON s.id=c.id
            WHERE c.organization_id=:org AND c.owner_id=:viewer AND c.removed_at IS NULL
            AND c.mode<>'disconnected' ORDER BY c.created_at,c.id LIMIT 12''',**viewer.access()).mappings()]


def discovery_query(query,question,previous):
    # Conversation identifies the topic; previous replies never become evidence.
    topic=query
    if previous and followup(question):
        topic=' '.join(dict.fromkeys(terms(previous[0]['response'].get('retrieval_query',previous[0]['question']))+terms(query)))
    return topic[:500]


def response(viewer,question,previous,db,search,configured,document_ids=None):
    from app.source_intent import meaningful_previous
    from app.question_intent import intent
    if intent(question) not in {"greeting","help","social"}:previous=meaningful_previous(previous)
    limits=query_limits()
    polished=os.getenv('LINKMIND_CHAT_POLISH')=='1'
    mode=source_policy.current()
    rows=connections(viewer,db) if not document_ids and mode!="stored" else []
    from app.source_intent import source_action
    requested=[kind for kind in ("jira","confluence") if kind in question.casefold()] if source_action(question) else []
    if requested and mode=="stored":
        return dict(statements=[],evidence=[],provider="system",insufficient_evidence=True,message="This conversation uses stored knowledge. Start a Live Only conversation to query Jira or Confluence."),[]
    if requested:rows=[r for r in rows if r["kind"] in requested]
    if (polished or mode=="live") and not document_ids and mode!="stored":
        with chat_trace.stage('structured_routing'):
            direct=structured_chat.answer(question,rows,previous)
        if direct is not None:return direct
    named=any(re.search(r'\b'+re.escape(row['config']['scope_id'])+r'(?:\b|-)',question,re.I) for row in rows if row['kind']=='jira')
    with chat_trace.stage('planning'):
        if polished and (named or (previous and followup(question))):
            routing=dict(route='answer',query=question,use_previous=bool(previous and followup(question)))
        else:routing=plan(question,previous,dict(org=viewer.organization_id,user=viewer.id),lambda:None,document_ids)
    if routing['route'] in {'greeting','help','social','clarify'}:
        return dict(statements=[],evidence=[],insufficient_evidence=False,provider='system',message=routing.get('reply') or
            ('أي شخص أو مشروع تقصد؟' if arabic(question) else 'Which person or project do you mean?')),[]
    query=discovery_query(routing['query'],question,previous)
    if mode!="live" and not document_ids and not re.search(r'\b(compare|both|difference|across)\b|قارن|الفرق',normalize(question)):
        with db.connect() as conn:identities=source_discovery.identity_choices(conn,viewer,query)
        if identities:
            return dict(statements=[],evidence=[],provider='system',insufficient_evidence=False,
                clarification=True,source_matches=identities,message=explain(question,'identity_scope')),[]
    sources=[];evidence=[];stored=[];live=[];outcomes=[];activity=[]
    diagnostics={}
    if mode!="live" and not requested:
        # One bounded stored-index search; graph/enrichment is never a prerequisite.
        limits.retrieve()
        chat_trace.activity('searching_knowledge')
        with chat_trace.stage('stored_retrieval'):
            stored=search(viewer,query,document_ids=document_ids or None,semantic=not (polished and named),limit=4 if polished else 8,diagnostics=diagnostics)
        if not stored and document_ids:
            stored,_=retrieval.selected_context(viewer,document_ids,question=query)
        if stored:
            sources=source_answers.stored_sources(stored)
            for source in sources:
                if source['kind']=='fields':
                    source['reference_id']=next(p['id'] for p in stored if str(p['document_id'])==str(source['document_id']))
            evidence=[dict(p,synthetic=bool(p.get("dataset_id")),origin="stored") for p in stored]
        activity.append(dict(operation='indexed_search',mode='stored',returned_passages=len(stored),source_count=len({str(p['document_id']) for p in stored}),semantic_status=diagnostics.get('semantic_status')))
    identifiers=set(re.findall(r'\b[A-Z][A-Z0-9_]{1,30}\b',query.upper()))
    projects=[row for row in rows if row['kind']=='jira' and row['config']['scope_id'] in identifiers]
    # Prefer the named project plus connected document spaces. Broad questions have
    # a bounded sample; no silent fan-out through an entire organization.
    selected=(projects+[row for row in rows if row['kind']!='jira']) if projects else ([row for row in rows if row['kind']!='jira']+[row for row in rows if row['kind']=='jira'])
    selected=selected[:3]
    partial=len(selected)<len(rows) and not projects
    tokens=terms(query)
    if projects:
        lookup=' '.join(row['config']['scope_id'] for row in projects)
    else:
        lookup=' '.join(tokens[:5])
        if any(t in normalize(question) for t in ('الشرك','الموظف','company','onboard')):lookup='company'
    historic=source_answers.past_only(question)
    prefetched={}
    if polished and not historic and selected:
        source_limits=active() or ReadLimits(seconds=35)
        def discover(row,quota):
            found=[]
            try:
                chat_trace.activity('searching_jira' if row['kind']=='jira' else 'searching_confluence')
                with chat_trace.stage('discovery.'+row['kind']):
                    provider=connectors.Provider(row['config'],source_limits,row['id'])
                    discovery=lookup or query
                    # Source-owned text search narrows explicit topics. No project
                    # identifiers, answers or source URLs are encoded in routing.
                    if row['kind']=='jira' and projects:
                        topic=next((word for word in ('incident','beta','delivery','authentication','webhook') if re.search(r'\b'+word+r'\b',query,re.I)),None)
                        if topic:discovery=row['config']['scope_id']+' '+topic
                    hits=provider.search(discovery,limit=6)
                    if not hits and discovery!=lookup:hits=provider.search(lookup,limit=6)
                    words=set(terms(query))
                    hits=sorted(hits,key=lambda h:-sum(word in h['title'].casefold() for word in words))
                    for hit in hits[:quota]:
                        observed=connectors.live(viewer,row['id'],connectors.LiveRead(native_id=hit['native_id']))
                        found.append((hit,observed))
                return found,None
            except (SourceFailure,HTTPException) as exc:return found,exc
        with ThreadPoolExecutor(max_workers=3) as pool:
            quotas=[1]*len(selected)
            if len(selected)==2 and selected[0]['kind']=='jira':quotas[0]=2
            jobs=[pool.submit(copy_context().run,discover,row,quota) for row,quota in zip(selected,quotas)]
            prefetched={str(row['id']):job.result() for row,job in zip(selected,jobs)}
    for row in ([] if historic else selected):
        if len(live)>=(3 if polished else 4):partial=True;break
        if limits.remaining()<20:partial=True;break
        try:
            if polished:
                originals,failure=prefetched[str(row['id'])]
                hits=[hit for hit,_ in originals]
                observed_by_id={hit['native_id']:value for hit,value in originals}
                if failure and not originals:raise failure
                if failure:
                    partial=True
                    outcomes.append(dict(name=row['name'],code=failure.code if isinstance(failure,SourceFailure) else 'source_unavailable',resources=len(originals)))
            else:
                provider=connectors.Provider(row['config'],active() or ReadLimits(),row['id'])
                hits=provider.search(lookup or query,limit=4)
            # Discovery metadata narrows retrieval, but only fetched originals may
            # support answers. Prefer matching titles, then provider relevance.
            words=set(terms(query))
            hits=sorted(hits,key=lambda h:-sum(word in h['title'].casefold() for word in words))
            read=0
            for hit in hits[:(1 if polished and row['kind']=='confluence' else 2)]:
                if len(live)>=(3 if polished else 4):partial=True;break
                observed=observed_by_id[hit['native_id']] if polished else connectors.live(viewer,row['id'],connectors.LiveRead(native_id=hit['native_id']))
                item=observed['evidence']
                dependency=dict(connection_id=str(row['id']),native_id=hit['native_id'],generation=row['generation'],revision=item['source_revision'])
                live.append(dependency);read+=1
                base=dict(origin='live',name=hit['title'] or row['name'],document_id='live:'+str(row['id'])+':'+hit['native_id'],
                    original_url=item['original_url'],source_revision=item['source_revision'],source_updated_at=item['source_updated_at'],
                    observed_at=item['observed_at'],synthetic=item['synthetic'],revision_role='live')
                if item['fields']:
                    sources.append(dict(base,reference_id=item['reference_id'],kind='fields',fields=[f for f in item['fields'] if not (polished and f['field']=='description')],text=None,locator={}))
                    # Prose inside a typed field is citable as exact prose as well;
                    # this never substitutes a fragment for the typed field value.
                    for field in item['fields']:
                        if field['field']=='description' and isinstance(field['value'],str) and field['value']:
                            sources.append(dict(base,reference_id=item['reference_id']+'-description',kind='passage',fields=[],text=field['value'],locator={'field':'description'}))
                else:
                    # Full original resource remains bounded; short headings alone
                    # must not displace the decision paragraphs later in a page.
                    sources.extend(dict(base,reference_id=p['id'],kind='passage',text=p['text'],fields=[],locator=p['locator']) for p in observed['passages'])
                for source in sources:
                    if source.get('document_id')!=base['document_id']:continue
                    evidence.append(dict(id=source['reference_id'],filename=base['name'],text=source['text'] or '',version_id='',
                        document_id=base['document_id'],locator=source['locator'],live=dependency,original_url=item['original_url'],
                        source_application={'jira':'Jira','confluence':'Confluence'}.get(row['kind'],row['kind']),source_key=next((f['value'] for f in item['fields'] if f['field']=='key'),''),
                        observed_at=item['observed_at'],source_updated_at=item['source_updated_at']))
            outcomes.append(dict(name=row['name'],code='observed' if read else 'no_matches',resources=read))
            activity.append(dict(operation='connected_search',mode='live',returned_passages=read,source_count=1,semantic_status=None))
        except (SourceFailure,HTTPException) as exc:
            partial=True
            code=exc.code if isinstance(exc,SourceFailure) else (exc.detail.get('code','source_unavailable') if isinstance(exc.detail,dict) else 'source_unavailable')
            outcomes.append(dict(name=row['name'],code=code,resources=0))
    if historic and rows:partial=True
    if polished:
        limits.max_passages=12;limits.max_context_characters=12000
        def score(s):
            text=(s.get('text') or '').casefold()
            return (4 if s['kind']=='fields' else 0)+sum(word in text for word in terms(query))-(3 if len(text)<70 and s['kind']=='passage' else 0)
        sources.sort(key=score,reverse=True)
    count=len(sources)
    sources,characters=source_answers.context(sources,limits)
    partial=partial or len(sources)<count
    refs={source['reference_id'] for source in sources}
    sources=[{key:value for key,value in s.items() if key!='document_id'} for s in sources]
    evidence=[p for p in evidence if p['id'] in refs]
    dependencies=[str(p['id']) for p in stored]
    checked_model=[limits.model_calls]
    def authorize():
        with db.connect() as conn:
            if not retrieval.dependencies_allowed(conn,viewer,dependencies):raise HTTPException(409,'Source access or versions changed.')
            for dependency in live:
                row=connectors.owned(conn,viewer,UUID(dependency['connection_id']))
                if row.generation!=dependency['generation'] or row.mode=='disconnected':raise HTTPException(409,'Connected source settings changed.')
        # Fresh remote checks precede each model invocation. Duplicate callbacks
        # inside the same stage only repeat local generation/owner checks; main.ask
        # always performs another fresh remote check before committing/delivery.
        if not polished or limits.model_calls!=checked_model[0]:
            if not allowed(viewer,live,db):raise HTTPException(409,'Connected source access or revision changed.')
            checked_model[0]=limits.model_calls
    result,state=source_answer_provider.answer(question,sources,dict(org=viewer.organization_id,user=viewer.id),authorize)
    statements=[dict(text=s.text,evidence=[dict(passage_id=c.reference_id,quote=c.quote or
        c.field+': '+source_answer_provider.canonical(c.value)) for c in s.evidence]) for s in result.statements]
    provider='bedrock' if configured() else 'mock-extractive'
    message=None
    if not statements and sources:
        # Useful exact excerpts remain available when synthesis cannot be approved.
        # Clearly label these; never present them as verified model reasoning.
        excerpts=[s for s in sources if s['kind']=='passage' and len(s['text'])>90][:2]
        statements=[dict(text=s['text'],evidence=[dict(passage_id=s['reference_id'],quote=s['text'])]) for s in excerpts]
        provider='source-excerpts'
        message='هذه مقاطع من المصادر المتاحة؛ لم أتمكن من اعتماد صياغة جواب موثوق بعد.' if arabic(question) else 'Here are relevant original excerpts. I could not approve a synthesized answer yet.'
    elif not statements:
        message='ما لقيت معلومات كافية في المصادر التي استطعت الوصول إليها. أضف اسم مشروع أو موضوع أوضح.' if arabic(question) else 'I could not find enough information in the sources I could access. Try a project name or a more specific topic.'
    elif result.insufficient_evidence and not polished:
        message='هذا ما تدعمه المصادر المتاحة؛ بعض التفاصيل أو المصادر لم أتمكن من تأكيدها.' if arabic(question) else 'This is what the available sources support; some details or sources could not be confirmed.'
    elif partial and not polished:
        message='بناءً على المصادر ذات الصلة التي راجعتها:' if arabic(question) else 'Based on the relevant sources I reviewed:'
    return dict(statements=statements,evidence=evidence,provider=provider,insufficient_evidence=partial or result.insufficient_evidence,
        message=message,answer_state=dict(code='partial' if statements and (partial or result.insufficient_evidence) else state),
        retrieval_query=query,live_dependencies=live,source_outcomes=outcomes,retrieval_activity=activity,context_characters=characters,
        validation_summary=result._validation),dependencies
