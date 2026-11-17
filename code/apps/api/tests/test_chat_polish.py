import json,time
from dataclasses import replace
from datetime import datetime,timezone
from threading import Event
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app import chat_trace,structured_chat,providers,main
from app.connector_providers import Record
from app.connector_transport import ReadLimits,SourceFailure,AtlassianMCP,_protocol_cache
from app.query_limits import QueryLimitReached

def row(key='TEST'):
    return dict(id=uuid4(),kind='jira',name='Enabled '+key,generation=2,config=dict(scope_id=key))

def record(key='TEST'):
    return Record('100','v1',datetime.now(timezone.utc),'https://example.atlassian.net/browse/'+key+'-1','issue.md',b'',{},[
        dict(field='key',value=key+'-1'),dict(field='summary',value='Native issue title'),
        dict(field='project',value=dict(key=key,name='Source project '+key)),dict(field='status',value='In Progress'),dict(field='assignee',value=None)])

def test_project_list_has_no_model_or_retrieval_and_reads_only_enabled_scopes(monkeypatch):
    calls=[]
    class Provider:
        def __init__(self,config,*args):self.key=config['scope_id']
        def project_snapshot(self):calls.append(self.key);return record(self.key)
    monkeypatch.setattr(structured_chat.connectors,'Provider',Provider)
    monkeypatch.setattr(providers,'structured',lambda *a,**k:pytest.fail('No model for a project list.'))
    with chat_trace.session() as trace:result,deps=structured_chat.answer('What projects are available?',[row(),row('OTHER')],[])
    assert set(calls)=={'TEST','OTHER'} and deps==[]
    assert result['provider']=='structured' and len(result['statements'])==2
    assert result['presentation']['items'][0]['name']=='Source project TEST'
    assert not result['insufficient_evidence'] and 'model_calls' not in trace.counters

def test_native_issue_status_does_not_infer_project_business_readiness(monkeypatch):
    monkeypatch.setattr(structured_chat.connectors,'Provider',lambda *a:SimpleNamespace(get=lambda *a,**k:record()))
    result,_=structured_chat.answer('What is TEST-1 status?',[row()],[])
    assert 'In Progress' in result['statements'][0]['text']
    assert structured_chat.answer('What is the current status of TEST?',[row()],[]) is None
    assert structured_chat.answer('Who owns TEST delivery?',[row()],[]) is None

def test_empty_and_failed_project_reads_are_reported_not_complete(monkeypatch):
    monkeypatch.setattr(structured_chat.connectors,'Provider',lambda *a:SimpleNamespace(project_snapshot=lambda:None))
    result,_=structured_chat.answer('List projects',[row()],[])
    assert result['source_failures'][0]['code']=='no_visible_issue' and result['insufficient_evidence']
    def denied():raise SourceFailure('access_denied')
    monkeypatch.setattr(structured_chat.connectors,'Provider',lambda *a:SimpleNamespace(project_snapshot=denied))
    result,_=structured_chat.answer('List projects',[row()],[])
    assert result['source_failures'][0]['code']=='access_denied'

def test_citation_followup_dedupes_only_actually_cited_originals(monkeypatch):
    source,_=structured_chat.record_evidence(row(),record())
    source2=dict(source,id='second')
    previous=[dict(response=dict(statements=[dict(evidence=[dict(passage_id=source['id'])])],evidence=[source,source2,dict(source,id='uncited',original_url='https://example.com/uncited')]))]
    monkeypatch.setattr(providers,'structured',lambda *a:pytest.fail('No model for cited links.'))
    result,_=structured_chat.answer('Which Jira issues support this answer?',[],previous)
    assert len(result['evidence'])==1 and result['evidence'][0]['original_url']==record().original_url
    assert result['presentation']['kind']=='source_links'
    result,_=structured_chat.answer('Open the original source for this claim.',[],previous)
    assert len(result['statements'])==1

class Stream:
    def __init__(self,events):self.events=events;self.closed=False
    def __iter__(self):return iter(self.events)
    def close(self):self.closed=True

def test_bedrock_stream_drains_metadata_even_when_cancelled_and_never_emits_draft():
    cancelled=Event();cancelled.set();sent=[]
    stream=Stream([dict(contentBlockDelta=dict(delta=dict(text='{"unverified":true}'))),dict(messageStop=dict(stopReason='end_turn')),dict(metadata=dict(usage=dict(inputTokens=30,outputTokens=8)))])
    with chat_trace.session(lambda *args:sent.append(args),cancelled):
        response=providers.streamed_converse(SimpleNamespace(converse_stream=lambda **k:dict(stream=stream)),{}, {})
        with pytest.raises(QueryLimitReached):chat_trace.checkpoint()
    assert stream.closed and response['usage']['inputTokens']==30 and not sent

def test_stream_failure_keeps_usage_unknown_and_closes():
    stream=Stream([dict(modelStreamErrorException=dict(message='provider failure'))]);response={}
    with pytest.raises(providers.ModelResponseError):providers.streamed_converse(SimpleNamespace(converse_stream=lambda **k:dict(stream=stream)),{},response)
    assert stream.closed and 'usage' not in response

def test_parallel_read_limit_cannot_oversubscribe():
    from concurrent.futures import ThreadPoolExecutor
    limits=ReadLimits(max_calls=3)
    def call(_):
        try:limits.reserve_call();return True
        except SourceFailure:return False
    with ThreadPoolExecutor(max_workers=8) as pool:assert sum(pool.map(call,range(20)))==3

def test_diagnostics_require_reviewer_before_any_database_read():
    with pytest.raises(HTTPException) as exc:main.chat_diagnostics(uuid4(),SimpleNamespace(role='member'))
    assert exc.value.status_code==403

def test_protocol_cache_is_credential_bound_and_does_not_cache_source_calls(monkeypatch):
    import app.connector_transport as transport
    _protocol_cache.clear();monkeypatch.setenv('LINKMIND_MCP_DISCOVERY_CACHE','1')
    monkeypatch.setattr(transport,'authorization',lambda ref,*a:'Bearer '+ref)
    negotiations=[];calls=[]
    def negotiate(self,hint):negotiations.append(self.client.reference);self.tools={'read':{}}
    monkeypatch.setattr(AtlassianMCP,'_negotiate',negotiate)
    monkeypatch.setattr(AtlassianMCP,'rpc',lambda self,method,args:(calls.append(args) or {'structuredContent':{'fresh':len(calls)}},{}))
    # Discovering schemas may be reused; actual resources are fetched every time.
    for token in ('RF4_ONE','RF4_ONE','RF4_TWO'):
        client=AtlassianMCP(token,ReadLimits(),endpoint='https://mcp.atlassian.com/v1/mcp',allowed={'read'})
        assert client.call('read',{})['fresh']==len(calls)
    assert len(negotiations)==2 and len(calls)==3

def test_project_reads_are_concurrent_but_bounded(monkeypatch):
    from threading import Barrier,Lock
    barrier=Barrier(3);lock=Lock();state=dict(active=0,peak=0)
    class Provider:
        def __init__(self,config,*args):self.key=config['scope_id']
        def project_snapshot(self):
            with lock:state['active']+=1;state['peak']=max(state['peak'],state['active'])
            barrier.wait(timeout=3)
            with lock:state['active']-=1
            return record(self.key)
    monkeypatch.setattr(structured_chat.connectors,'Provider',Provider)
    result,_=structured_chat.answer('List projects',[row(str(i)+'TEST') for i in range(6)],[])
    assert len(result['statements'])==6 and state['peak']==3

def test_cached_mcp_sessions_never_reuse_rpc_ids_across_clients(monkeypatch):
    import app.connector_transport as transport
    monkeypatch.setenv('LINKMIND_MCP_DISCOVERY_CACHE','1');seen=[]
    def request(self,method,url,**kwargs):
        body=kwargs['body'];seen.append(body['id']);return dict(id=body['id'],result={'value':body['params']}),{}
    monkeypatch.setattr(transport.ReadClient,'request',request)
    clients=[]
    for _ in range(2):
        client=object.__new__(AtlassianMCP);client.sequence=0;client.headers={};client.client=transport.ReadClient('RF4_TEST','mcp.atlassian.com');clients.append(client)
    assert clients[0].rpc('tools/call',{'a':1})[0]['value']=={'a':1}
    assert clients[1].rpc('tools/call',{'a':2})[0]['value']=={'a':2}
    assert len(set(seen))==2

def test_stream_endpoint_emits_activity_then_only_approved_result(monkeypatch):
    from contextlib import contextmanager
    from fastapi.testclient import TestClient
    class Engine:
        @contextmanager
        def connect(self):yield None
    monkeypatch.setattr(main,'engine',Engine())
    monkeypatch.setitem(main.app.dependency_overrides,main.authenticate,lambda:SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(main,'conversation',lambda *a:dict(id=a[-1]))
    def approved(*args):
        chat_trace.activity('checking_answer')
        return dict(statements=[dict(text='Approved source fact',evidence=[])],evidence=[])
    monkeypatch.setattr(main,'ask',approved)
    response=TestClient(main.app).post('/api/v1/conversations/'+str(uuid4())+'/answers/stream',headers={'Authorization':'Bearer demo-amal'},json={'question':'Test question'})
    assert response.status_code==200 and response.headers['content-type'].startswith('text/event-stream')
    assert response.text.index('checking_answer')<response.text.index('Approved source fact')
    assert 'event: done' in response.text

def test_stream_endpoint_reports_error_without_draft(monkeypatch):
    from contextlib import contextmanager
    from fastapi.testclient import TestClient
    class Engine:
        @contextmanager
        def connect(self):yield None
    monkeypatch.setattr(main,'engine',Engine());monkeypatch.setattr(main,'conversation',lambda *a:None)
    monkeypatch.setitem(main.app.dependency_overrides,main.authenticate,lambda:SimpleNamespace(id=uuid4()))
    def failure(*a):raise ValueError('private provider details')
    monkeypatch.setattr(main,'ask',failure)
    response=TestClient(main.app).post('/api/v1/conversations/'+str(uuid4())+'/answers/stream',headers={'Authorization':'Bearer demo-amal'},json={'question':'Test question'})
    assert 'event: error' in response.text and 'private provider details' not in response.text and 'event: answer' not in response.text
