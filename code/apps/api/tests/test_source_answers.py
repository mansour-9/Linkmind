import json
from uuid import uuid4
import pytest
from fastapi import HTTPException

from app import main,processing,retrieval,providers,connectors,source_answers as combined,source_answer_provider as synthesis
from app.connector_providers import ConnectionSpec,Provider
from app.connector_demo import DemoProvider
from app.source_answer_contracts import SourceAnswer
from app.contracts import AnswerSupportVerdict
from app.db import sql
from test_search_readiness import workspace,source,viewer,OMAR


@pytest.fixture
def local(workspace,monkeypatch):
    for module in (connectors,combined,providers):monkeypatch.setattr(module,'engine',main.engine)
    monkeypatch.setattr(providers,'configured',lambda:False)
    monkeypatch.setattr(providers,'embed',lambda *a,**k:pytest.fail('No embedding dispatch for explicitly selected context.'))
    return workspace


def document(local):
    job=source(local,b'Fictional project DEMO: the review moved from Wednesday to Thursday because integration tests were incomplete.',enrichment_requested=False)
    assert processing.process_one()
    return job.document_id


def connection():
    id=connectors.create(viewer(),ConnectionSpec(kind='jira',execution='mock',name='Synthetic project',scope_id='rf5-'+uuid4().hex))['id']
    connectors.authenticate_connection(viewer(),id);connectors.test_connection(viewer(),id)
    with main.engine.connect() as conn:generation=connectors.owned(conn,viewer(),id).generation
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='live',expected_generation=generation))
    return id


def question(id,doc=None,text='Why did the review date change, and what is the selected resource status now?'):
    return combined.SourceQuestion(question=text,document_ids=[doc] if doc else [],live_resources=[dict(connection_id=id,native_id='demo-1')])


def test_combined_result_preserves_original_quotes_typed_fields_and_zero_retention(local):
    doc=document(local);id=connection()
    before=sql(local,'SELECT count(*) FROM documents').scalar_one()
    turns=sql(local,'SELECT count(*) FROM conversation_turns').scalar_one()
    result=combined.ask(viewer(),question(id,doc))
    assert result['provider']=='mock-extractive' and not result['retained'] and not result['saved']
    assert {s['origin'] for s in result['sources']}=={'stored','live'}
    assert result['context_characters']<=22000 and len(result['sources'])<=24
    assert any('integration tests' in s['text'] for s in result['sources'] if s['kind']=='passage')
    refs=[c for s in result['statements'] for c in s['evidence']]
    assert any(c['kind']=='field' and c['field']=='status' and c['value']=='Synthetic demo' and c['quote'] is None for c in refs)
    assert any(c['kind']=='passage' and c['quote'] in next(s['text'] for s in result['sources'] if s['reference_id']==c['reference_id']) for c in refs)
    assert sql(local,'SELECT count(*) FROM documents').scalar_one()==before
    assert sql(local,'SELECT count(*) FROM conversation_turns').scalar_one()==turns
    assert not sql(local,'SELECT 1 FROM connected_resources WHERE connection_id=:id',id=id).scalar()
    assert combined.allowed(viewer(),combined.AccessCheck(**result['access_check']))


def test_selected_source_outage_returns_only_authorized_stored_evidence(local,monkeypatch):
    doc=document(local);id=connection()
    def failed(*a,**k):raise HTTPException(503,dict(code='rate_limited',message='The source is rate limited. Try later.'))
    monkeypatch.setattr(connectors,'live',failed)
    result=combined.ask(viewer(),question(id,doc))
    assert result['partial'] and result['insufficient_evidence']
    assert all(s['origin']=='stored' for s in result['sources'])
    assert result['source_outcomes'][0]['code']=='rate_limited'


def test_foreign_source_is_rejected_before_any_read_or_model(local,monkeypatch):
    id=connection()
    monkeypatch.setattr(connectors,'live',lambda *a,**k:pytest.fail('No unauthorized read.'))
    monkeypatch.setattr(synthesis,'answer',lambda *a,**k:pytest.fail('No unauthorized model exposure.'))
    assert combined.available(viewer(OMAR))==[]
    with pytest.raises(HTTPException) as exc:combined.ask(viewer(OMAR),question(id))
    assert exc.value.status_code==404


def test_stored_source_revocation_hides_transient_evidence(local):
    doc=document(local)
    result=combined.ask(viewer(OMAR),combined.SourceQuestion(question='Why did the review move?',document_ids=[doc]))
    check=combined.AccessCheck(**result['access_check']);assert combined.allowed(viewer(OMAR),check)
    main.change_access(doc,main.AccessChange(visibility='private'),viewer())
    assert not combined.allowed(viewer(OMAR),check)


def test_retained_history_uses_exact_previous_and_current_revisions(local):
    doc=document(local)
    source(local,b'Fictional project DEMO: the current review date is Friday.',document=doc,enrichment_requested=False)
    assert processing.process_one()
    result=combined.ask(viewer(),combined.SourceQuestion(question='Compare the previous version with the current version.',document_ids=[doc]))
    assert {s['revision_role'] for s in result['sources']}=={'previous','current'}
    assert any('integration tests' in s['text'] for s in result['sources'])
    check=combined.AccessCheck(**result['access_check']);assert check.historical_dependencies and combined.allowed(viewer(),check)
    source(local,b'Fictional project DEMO: another later source revision.',document=doc,enrichment_requested=False)
    assert processing.process_one()
    assert not combined.allowed(viewer(),check)


def test_connection_generation_and_source_revision_revoke_transient_answer(local,monkeypatch):
    id=connection();state={'revision':'v1'};record=DemoProvider.record
    def current(self):
        value=record(self);value.revision=state['revision'];return value
    monkeypatch.setattr(DemoProvider,'record',current)
    result=combined.ask(viewer(),question(id));check=combined.AccessCheck(**result['access_check'])
    assert combined.allowed(viewer(),check)
    state['revision']='v2'
    assert not combined.allowed(viewer(),check)
    state['revision']='v1'
    with main.engine.connect() as conn:generation=connectors.owned(conn,viewer(),id).generation
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='disconnected',expected_generation=generation))
    assert not combined.allowed(viewer(),check)


def test_revocation_during_generation_does_not_deliver_or_save_an_answer(local,monkeypatch):
    id=connection()
    def answer(q,sources,scope,authorize):
        authorize()
        with main.engine.connect() as conn:generation=connectors.owned(conn,viewer(),id).generation
        connectors.change_mode(viewer(),id,connectors.ModeChange(mode='disconnected',expected_generation=generation))
        return SourceAnswer(statements=[],insufficient_evidence=True),'evidence_gap'
    monkeypatch.setattr(synthesis,'answer',answer)
    with pytest.raises(HTTPException) as exc:combined.ask(viewer(),question(id))
    assert exc.value.status_code==409


@pytest.mark.parametrize('text',['What was the issue status yesterday?','وش كانت الحالة أمس؟','Compare the previous version.'])
def test_past_state_never_substitutes_live_current_state(local,monkeypatch,text):
    id=connection();monkeypatch.setattr(connectors,'live',lambda *a,**k:pytest.fail('Current data is not history.'))
    result=combined.ask(viewer(),question(id,text=text))
    assert not result['statements'] and not result['sources']
    assert result['source_outcomes'][0]['code']=='history_unavailable'


def test_live_reference_identity_distinguishes_identical_content_and_does_not_fan_out(local,monkeypatch):
    ids=[connection() for _ in range(3)];calls=[];read=connectors.live
    def observe(viewer,id,body):calls.append(id);return read(viewer,id,body)
    monkeypatch.setattr(connectors,'live',observe)
    result=combined.ask(viewer(),combined.SourceQuestion(question='What is the current status of each selected resource?',live_resources=[dict(connection_id=id,native_id='demo-1') for id in ids[:2]]))
    assert calls==ids[:2]
    assert len({s['reference_id'] for s in result['sources']})==2
    assert all('config' not in c and 'credential_ref' not in c for c in combined.available(viewer()))


@pytest.mark.parametrize('payload',[
    dict(question='Question'),
    dict(question='Question',document_ids=[str(uuid4())]*2),
    dict(question='Question',live_resources=[dict(connection_id=str(uuid4()),native_id='A')]*2),
    dict(question='Question',live_resources=[dict(connection_id=str(uuid4()),native_id=str(i)) for i in range(3)]),
])
def test_source_scope_is_explicit_unique_and_bounded(payload):
    with pytest.raises(ValueError):combined.SourceQuestion(**payload)


@pytest.mark.parametrize('citation',[
    dict(reference_id='missing',kind='field',field='status',value='Blocked'),
    dict(reference_id='live',kind='field',field='status',value='Done'),
    dict(reference_id='live',kind='field',field='priority',value=1),
    dict(reference_id='live',kind='passage',quote='The issue is blocked.'),
])
def test_structured_fields_cannot_certify_fabricated_values_types_or_quotes(citation):
    sources=[dict(reference_id='live',kind='fields',fields=[dict(field='status',value='Blocked'),dict(field='priority',value=True)])]
    result=SourceAnswer(statements=[dict(text='Candidate',evidence=[citation])],insufficient_evidence=False)
    with pytest.raises(ValueError):synthesis.validate(result,sources)


def test_semantic_rejection_still_hides_exact_field_reference(monkeypatch):
    monkeypatch.setattr(providers,'configured',lambda:True);calls=[]
    sources=[dict(reference_id='live',kind='fields',fields=[dict(field='status',value='Blocked')],origin='live')]
    def structured(contract,system,payload,scope,operation,*a,**k):
        calls.append(operation)
        if operation=='answer':return SourceAnswer(statements=[dict(text='The project is cancelled.',evidence=[dict(reference_id='live',kind='field',field='status',value='Blocked')])],insufficient_evidence=False)
        return AnswerSupportVerdict(reviews=[dict(statement='The project is cancelled.',supported=False,unsupported_fragments=['cancelled'],temporal_scope_supported=True,authority_scope_supported=True,freshness_supported=True,reason='Blocked does not establish cancelled.')])
    monkeypatch.setattr(providers,'structured',structured)
    result,state=synthesis.answer('What is the status?',sources,{},lambda:None)
    assert not result.statements and state=='verification_failed'
    assert calls==['answer','answer_verification']


def test_mixed_source_answer_accepts_exact_passage_and_typed_field_support(monkeypatch):
    monkeypatch.setattr(providers,'configured',lambda:True);calls=[]
    sources=[dict(reference_id='saved',kind='passage',text='The review moved because tests were incomplete.',origin='stored'),
        dict(reference_id='live',kind='fields',fields=[dict(field='status',value='Blocked')],origin='live')]
    def structured(contract,system,payload,scope,operation,*a,**k):
        calls.append(operation)
        if operation=='answer':return SourceAnswer(statements=[
            dict(text='The saved note attributes the move to incomplete tests.',evidence=[dict(reference_id='saved',kind='passage',quote='tests were incomplete')]),
            dict(text='The observed issue status is Blocked.',evidence=[dict(reference_id='live',kind='field',field='status',value='Blocked')])],insufficient_evidence=False)
        assert {s['kind'] for s in payload['sources']}=={'passage','fields'}
        return AnswerSupportVerdict(reviews=[dict(statement=s['text'],supported=True,unsupported_fragments=[],temporal_scope_supported=True,authority_scope_supported=True,freshness_supported=True,reason='Explicit synthetic supported verdict.') for s in payload['statements']])
    monkeypatch.setattr(providers,'structured',structured)
    result,state=synthesis.answer('Why did it move, and what is the current issue status?',sources,{},lambda:None)
    assert len(result.statements)==2 and state=='answered' and calls==['answer','answer_verification']


def test_context_never_truncates_a_structured_value_to_fit():
    from app.query_limits import QueryLimits
    source=dict(reference_id='live',document_id='one',kind='fields',fields=[dict(field='status',value='Blocked'),dict(field='description',value='x'*12000)])
    items,size=combined.context([source],QueryLimits())
    assert items[0]['fields']==[dict(field='status',value='Blocked')] and size<=22000
    assert len(source['fields'])==2


@pytest.mark.parametrize('kind',['jira','confluence'])
def test_oauth_gateway_is_not_used_as_original_source_url(kind):
    spec=ConnectionSpec(kind=kind,name='Synthetic',site_url='https://fixture.atlassian.net',scope_id='RF' if kind=='jira' else '42',cloud_id='00000000-0000-4000-8000-000000000003',auth_method='oauth')
    provider=Provider(spec.model_copy(update=dict(credential_ref='RF4_OAUTH_'+'0'*32)))
    if kind=='jira':record=provider.jira(dict(id='1',key='RF-1',fields=dict(project={'key':'RF'},updated='2026-11-15T00:00:00Z')))
    else:
        record=provider.confluence(dict(id='8',spaceId='42',version=dict(number=1,createdAt='2026-11-15T00:00:00Z'),body={'storage':{'value':'<p>Original text.</p>'}}))
        provider.client.get=lambda *a,**k:dict(results=[])
        assert provider.page({})[2]
    assert record.original_url.startswith(spec.site_url+'/') and 'api.atlassian.com' not in record.original_url


@pytest.mark.parametrize('gateway_relative',[False,True])
def test_confluence_oauth_cursor_stays_on_the_verified_gateway_path(gateway_relative):
    spec=ConnectionSpec(kind='confluence',name='Synthetic',site_url='https://fixture.atlassian.net',scope_id='42',cloud_id='00000000-0000-4000-8000-000000000003',auth_method='oauth')
    provider=Provider(spec.model_copy(update=dict(credential_ref='RF4_OAUTH_'+'0'*32)))
    path='/wiki/api/v2/spaces/42/pages';prefix='/ex/confluence/'+spec.cloud_id
    calls=[]
    def page(url,*args):
        calls.append(url)
        return dict(results=[],_links={'next':(prefix if gateway_relative else '')+path+'?cursor=next'}) if len(calls)==1 else dict(results=[])
    provider.client.get=page
    records,cursor,complete=provider.page({});assert not complete
    assert provider.page(cursor)[2]
    assert all(url.startswith('https://api.atlassian.com'+prefix+path) for url in calls)
