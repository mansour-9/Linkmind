"""Transient, explicitly scoped stored/live answers; no ingestion or answer persistence."""
import json
import re
from datetime import datetime,timezone
from uuid import UUID

from fastapi import HTTPException,Response
from pydantic import BaseModel,ConfigDict,Field,model_validator

from app.db import engine,sql
from app import connectors,retrieval,providers,source_answer_provider
from app import content_domains as domains
from app.connector_transport import SourceFailure,ReadLimits,active as active_reads
from app.query_limits import question_limits,QueryLimitReached
from app.query_language import historical_question,operational_question,normalize,explain
from app.retrieval_coordinator import QuestionRetriever
from app.inference_budget import BudgetStopped

POLICY='source-answer-v2-resolved-fields-partial-support'


class LiveResource(BaseModel):
    model_config=ConfigDict(extra='forbid')
    connection_id:UUID
    native_id:str=Field(min_length=1,max_length=200,pattern=r'^[A-Za-z0-9!_,.-]+$')


class SourceQuestion(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question:str=Field(min_length=2,max_length=2000)
    document_ids:list[UUID]=Field(default_factory=list,max_length=30)
    live_resources:list[LiveResource]=Field(default_factory=list,max_length=2)

    @model_validator(mode='after')
    def selected(self):
        if not self.document_ids and not self.live_resources:raise ValueError('Select at least one stored document or live resource.')
        if len(set(self.document_ids))!=len(self.document_ids) or len({(r.connection_id,r.native_id) for r in self.live_resources})!=len(self.live_resources):
            raise ValueError('Select each source resource once.')
        return self


class LiveDependency(LiveResource):
    generation:int=Field(ge=0)
    revision:str=Field(min_length=1,max_length=300)


class RetainedDependency(BaseModel):
    model_config=ConfigDict(extra='forbid')
    passage_id:UUID
    version_id:UUID
    document_id:UUID
    current_version_id:UUID


class AccessCheck(BaseModel):
    model_config=ConfigDict(extra='forbid')
    passage_ids:list[UUID]=Field(default_factory=list,max_length=24)
    historical_dependencies:list[RetainedDependency]=Field(default_factory=list,max_length=24)
    live:list[LiveDependency]=Field(default_factory=list,max_length=2)


def available(viewer):
    with engine.connect() as conn:
        rows=sql(conn,'''SELECT c.id,s.name,s.kind,c.mode,c.health,c.config,c.config->>'execution' AS execution,
            c.config->>'scope_id' AS scope FROM source_connections c JOIN source_instances s ON s.id=c.id
            WHERE c.organization_id=:org AND c.owner_id=:viewer AND c.removed_at IS NULL AND c.mode<>'disconnected'
            ORDER BY s.name,c.id LIMIT 50''',**viewer.access()).mappings()
        return [{k:v for k,v in r.items() if k!='config'} for r in rows if not domains.enabled() or domains.live_mcp(r.config)]


def allowed(viewer,checks):
    with engine.connect() as conn:
        if domains.enabled() and not retrieval.manual_passages_allowed(conn,viewer,checks.passage_ids):return False
        if not retrieval.dependencies_allowed(conn,viewer,[str(p) for p in checks.passage_ids],[],[d.model_dump(mode='json') for d in checks.historical_dependencies]):return False
    limits=active_reads() or ReadLimits(max_calls=12,seconds=20)
    for dependency in checks.live:
        with engine.connect() as conn:row=connectors.owned(conn,viewer,dependency.connection_id)
        if domains.enabled() and not domains.live_mcp(row.config):return False
        if row.generation!=dependency.generation or row.mode=='disconnected':return False
        current=connectors.Provider(row.config,limits,row.id).authorize(dependency.native_id)
        revision=current.get('eTag') if isinstance(current,dict) else getattr(current,'revision',None)
        if revision!=dependency.revision:return False
    return True


def assert_allowed(viewer,checks):
    try:valid=allowed(viewer,checks)
    except (HTTPException,SourceFailure):valid=False
    if not valid:raise HTTPException(409,'Source access, revisions or connection settings changed. Ask again with current evidence.')


def past_only(question):
    text=normalize(question)
    return not operational_question(question) and (historical_question(question) or bool(re.search(
        r'\b(yesterday|last week|last month|as of|what was)\b|امس|الاسبوع الماضي|الشهر الماضي|سابقا',text)))


def stored_sources(passages, *, manual=False):
    result=[];seen=set()
    if manual:
        return [dict(reference_id=p['id'],document_id=str(p['document_id']),name=p['filename'],kind='passage',
            text=p['text'],fields=[],origin='stored',locator=p['locator'],revision_role=p.get('revision_role','current')) for p in passages]
    with engine.connect() as conn:
        revisions={str(r.version_id):r for r in sql(conn,'''SELECT DISTINCT ON(v.id) v.id AS version_id,v.created_at AS received_at,
            v.dataset_id,r.source_revision,r.original_url,r.source_updated_at,r.observed_at,r.fields,r.payload
            FROM document_versions v LEFT JOIN connected_revisions r ON r.version_id=v.id
            WHERE v.id=ANY(:ids) ORDER BY v.id,r.observed_at DESC NULLS LAST''',ids=[UUID(str(p['version_id'])) for p in passages]).mappings()} if passages else {}
    for p in passages:
        version=revisions[str(p['version_id'])]
        external=version if version.source_revision is not None else None
        if external and external.fields:
            key='stored-fields-'+str(p['version_id'])
            if key in seen:continue
            seen.add(key)
            item=dict(reference_id=key,kind='fields',fields=external.fields,text=None)
        else:item=dict(reference_id=p['id'],kind='passage',text=p['text'],fields=[])
        item.update(origin='stored',name=p['filename'],document_id=str(p['document_id']),
            revision_role=p.get('revision_role','current'),source_revision=external.source_revision if external else str(p['version_id']),
            original_url=external.original_url if external else None,source_updated_at=external.source_updated_at.isoformat() if external else None,
            observed_at=(external.observed_at if external else version.received_at).isoformat(),synthetic=bool(version.dataset_id or (external and external.payload.get('synthetic'))),dataset_id=version.dataset_id,locator=p.get('locator',{}))
        result.append(item)
    return result


def context(sources,limits):
    groups={};bounded=[];characters=0
    for source in sources:
        source=dict(source)
        if source['kind']=='fields':
            fields=[];used=0
            for field in source['fields']:
                size=len(json.dumps(field,ensure_ascii=False))
                if used+size<=10000:fields.append(field);used+=size
            source['fields']=fields
            if not fields:continue
        groups.setdefault(source['document_id'],[]).append(source)
    for index in range(max((len(items) for items in groups.values()),default=0)):
        for group in groups.values():
            if index>=len(group):continue
            source=group[index];size=len(json.dumps(source,ensure_ascii=False))
            if len(bounded)<limits.max_passages and characters+size<=limits.max_context_characters:
                bounded.append(source);characters+=size
    return bounded,characters


def ask(viewer,body):
    # Validate every selected owner/tenant boundary before any source read or model.
    with engine.connect() as conn:
        for item in body.live_resources:
            row=connectors.owned(conn,viewer,item.connection_id)
            if domains.enabled() and not domains.live_mcp(row.config):raise HTTPException(404,'Live MCP source not found.')
        if domains.enabled() and not retrieval.manual_ids_allowed(conn,viewer,body.document_ids,ready=True):
            raise HTTPException(404,'Selected manual document not found.')
    try:
        with question_limits() as limits:
            retriever=QuestionRetriever(viewer,retrieval.search)
            passages=[];coverage=None;historical=[];outcomes=[];live_checks=[];sources=[]
            if body.document_ids:
                if domains.enabled():
                    limits.retrieve()
                    passages,coverage,historical=retrieval.manual_context(viewer,body.document_ids,question=body.question,
                        include_previous=historical_question(body.question))
                elif historical_question(body.question):passages,coverage,historical=retriever.history(body.document_ids,body.question)
                else:passages,coverage=retriever.context(body.document_ids,body.question)
                sources=stored_sources(passages,manual=domains.enabled())
            for selected in body.live_resources:
                if past_only(body.question):
                    outcomes.append(dict(connection_id=str(selected.connection_id),code='history_unavailable',message='Live current state was not used as evidence of a past state. Select dated stored evidence.'))
                    continue
                limits.retrieve()
                try:
                    with engine.connect() as conn:row=connectors.owned(conn,viewer,selected.connection_id)
                    observed=connectors.live(viewer,selected.connection_id,connectors.LiveRead(native_id=selected.native_id))
                    evidence=observed['evidence']
                    base=dict(origin='live',name=row.name,document_id='live:'+str(row.id)+':'+selected.native_id,
                        original_url=evidence['original_url'],source_revision=evidence['source_revision'],
                        source_updated_at=evidence['source_updated_at'],observed_at=evidence['observed_at'],synthetic=evidence['synthetic'],revision_role='live')
                    if evidence['fields']:sources.append(dict(base,reference_id=evidence['reference_id'],kind='fields',fields=evidence['fields'],text=None,locator={}))
                    else:
                        sources.extend(dict(base,reference_id=p['id'],kind='passage',text=p['text'],fields=[],locator=p['locator']) for p in observed['passages'])
                    live_checks.append(dict(connection_id=selected.connection_id,native_id=selected.native_id,generation=row.generation,revision=evidence['source_revision']))
                    outcomes.append(dict(connection_id=str(selected.connection_id),code='observed',message='Read one explicitly selected resource.'))
                    limits.activity.append(dict(operation='live_resource',mode='live',returned_passages=len(observed['passages']),source_count=1))
                except HTTPException as exc:
                    if exc.status_code not in {409,503}:raise
                    detail=exc.detail if isinstance(exc.detail,dict) else {}
                    outcomes.append(dict(connection_id=str(selected.connection_id),code=detail.get('code','not_connected'),message=detail.get('message','This selected source is not connected.')))
            checks=AccessCheck(passage_ids=[UUID(p['id']) for p in passages],historical_dependencies=historical,live=live_checks)
            authorize=lambda:assert_allowed(viewer,checks)
            original_count=len(sources);original_fields=sum(len(s['fields']) for s in sources)
            sources,characters=context(sources,limits)
            sources=[{key:value for key,value in s.items() if key!='document_id'} for s in sources]
            result,state=source_answer_provider.answer(body.question,sources,dict(org=viewer.organization_id,user=viewer.id),authorize)
            authorize()
            partial=bool(coverage and coverage['partial']) or any(o['code']!='observed' for o in outcomes) or len(sources)<original_count or sum(len(s['fields']) for s in sources)<original_fields
            if partial:result.insufficient_evidence=True
            limits.checkpoint()
            return dict(**result.model_dump(),state=state,provider='bedrock' if providers.configured() else 'mock-extractive',sources=sources,
                source_outcomes=outcomes,coverage=coverage,partial=partial,context_characters=characters,retrieval_activity=limits.activity,
                access_check=checks.model_dump(mode='json'),retained=False,saved=False,policy=POLICY,
                message=explain(body.question,state) if state in {'citation_failed','verification_failed','evidence_gap'} else None)
    except QueryLimitReached as exc:raise HTTPException(503,dict(code=exc.code,message=explain(body.question,'limit'))) from None
    except BudgetStopped as exc:raise HTTPException(503,str(exc)) from None
    except providers.ProviderUnavailable:raise HTTPException(503,'The answer provider is not configured.') from None
    except HTTPException:raise
    except Exception as exc:
        if getattr(exc,'response',{}).get('Error',{}).get('Code')=='ThrottlingException':
            raise HTTPException(429,'The answer provider is rate limited. Wait briefly and try again.',headers={'Retry-After':'10'}) from None
        raise HTTPException(503,'The source answer could not be verified. No answer or live content was saved.') from None


def install(app,Identity):
    @app.get('/api/v1/retrieval/connections')
    def options(viewer:Identity):return available(viewer)

    @app.post('/api/v1/source-answers')
    def answering(body:SourceQuestion,response:Response,viewer:Identity):
        response.headers['Cache-Control']='no-store'
        return ask(viewer,body)

    @app.post('/api/v1/source-answers/access')
    def checking(body:AccessCheck,response:Response,viewer:Identity):
        response.headers['Cache-Control']='no-store'
        try:return dict(allowed=allowed(viewer,body))
        except (HTTPException,SourceFailure):return dict(allowed=False)
