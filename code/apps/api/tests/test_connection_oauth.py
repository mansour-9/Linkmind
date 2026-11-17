import json
import time
import base64
import hashlib
from http.cookies import SimpleCookie
from urllib.parse import parse_qs,urlsplit
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException,Response
from starlette.requests import Request

from app import connection_oauth as oauth,connection_scopes as scopes,connectors,main
from app.connector_providers import ConnectionSpec
from app.connector_transport import authorization,SourceFailure
from app.db import sql
from test_search_readiness import workspace,viewer


@pytest.fixture
def local(workspace,monkeypatch,tmp_path):
    for module in (oauth,scopes,connectors):monkeypatch.setattr(module,'engine',main.engine)
    key=tmp_path/'key';key.write_bytes(Fernet.generate_key())
    monkeypatch.setenv('LINKMIND_CONNECTION_KEY_FILE',str(key))
    monkeypatch.setenv('LINKMIND_PUBLIC_ORIGIN','http://127.0.0.1:5195')
    monkeypatch.setenv('LINKMIND_CONNECTOR_NETWORK','1')
    providers={kind:dict(client_id='fictional-client',client_secret='fictional-client-secret',tenant_id='00000000-0000-4000-8000-000000000002') for kind in ('jira','confluence','onedrive','sharepoint')}
    monkeypatch.setenv('LINKMIND_OAUTH_PROVIDERS_JSON',json.dumps(providers))
    return workspace


def create(kind='jira'):
    spec=ConnectionSpec(kind=kind,execution='real',name='OAuth '+uuid4().hex,site_url='https://fixture.atlassian.net' if kind in {'jira','confluence'} else 'https://fixture.sharepoint.com/sites/test',scope_id='pending-scope',auth_method='oauth')
    return connectors.create(viewer(),spec)['id']


def begin(id):
    response=Response();data=oauth.start(viewer(),id,response)
    cookie=SimpleCookie(response.headers['set-cookie'])[oauth.COOKIE].value
    state=parse_qs(urlsplit(data['authorization_url']).query)['state'][0]
    assert 'fictional-client-secret' not in json.dumps(data) and 'verifier' not in json.dumps(data)
    assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=lax' in response.headers['set-cookie']
    return state,cookie,data


def callback(state,cookie,code='fictional-code',error=None):
    request=Request(dict(type='http',method='GET',path=oauth.CALLBACK,query_string=b'code=secret',headers=[(b'cookie',f'{oauth.COOKIE}={cookie}'.encode())]))
    response=oauth.callback(request,state,code,error)
    assert request.scope['query_string']==b''
    assert 'fictional-code' not in response.headers['location']
    assert response.headers['cache-control']=='no-store'
    return response.headers['location']


@pytest.fixture
def upstream(monkeypatch):
    calls=[];state=dict(refreshes=0,deny=False)
    def handle(request):
        calls.append(request)
        if request.method=='POST':
            if state['deny']:return httpx.Response(400,json={'error':'invalid_grant','error_description':'SECRET upstream message'})
            is_refresh=b'refresh_token' in request.content
            if is_refresh:state['refreshes']+=1
            return httpx.Response(200,json=dict(access_token='fictional-access-'+str(state['refreshes']),refresh_token='fictional-refresh-'+str(state['refreshes']),expires_in=3600,token_type='Bearer'))
        if request.url.path.endswith('accessible-resources'):return httpx.Response(200,json=[dict(id='00000000-0000-4000-8000-000000000003',url='https://fixture.atlassian.net')])
        if request.url.path.endswith('/project/search'):return httpx.Response(200,json=dict(values=[dict(key='RF',name='Fictional project')],isLast=True))
        if request.url.path.endswith('/project/RF'):return httpx.Response(200,json=dict(key='RF'))
        if request.url.path.endswith('/spaces'):return httpx.Response(200,json=dict(results=[dict(id='42',name='Fictional space')]))
        if request.url.path.endswith('/spaces/42'):return httpx.Response(200,json=dict(id='42'))
        if request.url.path.endswith('/drives'):return httpx.Response(200,json=dict(value=[dict(id='drive1',name='Knowledge library')]))
        if '/sites/' in request.url.path:return httpx.Response(200,json=dict(id='site1'))
        if request.url.path.endswith('/children'):return httpx.Response(200,json=dict(value=[dict(id='folder1',name='Team knowledge',folder={},parentReference={'driveId':'drive1'})]))
        return httpx.Response(200,json=dict(id='root1' if request.url.path.endswith(('/root','/root1')) else 'folder1',name='Root',folder={},parentReference={'driveId':'drive1'}))
    transport=httpx.MockTransport(handle);client=httpx.Client;oauth_client=oauth.OAuth2Client
    class TransportClient(client):
        def __init__(self,**kw):
            kw.setdefault('transport',transport)
            client.__init__(self,**kw)
    monkeypatch.setattr(httpx,'Client',TransportClient)
    monkeypatch.setattr(oauth,'OAuth2Client',lambda **kw:oauth_client(transport=transport,**kw))
    return state,calls


@pytest.mark.parametrize('kind',['jira','confluence','onedrive','sharepoint'])
def test_server_owned_consent_scope_selection_and_encrypted_refresh(local,upstream,kind):
    id=create(kind);state,cookie,data=begin(id)
    if kind in {'onedrive','sharepoint'}:
        params=parse_qs(urlsplit(data['authorization_url']).query)
        assert params['code_challenge_method']==['S256'] and params.get('code_challenge')
    assert callback(state,cookie).endswith('auth=connected')
    if kind in {'onedrive','sharepoint'}:
        sent=parse_qs(next(r for r in upstream[1] if r.method=='POST').content.decode())
        challenge=base64.urlsafe_b64encode(hashlib.sha256(sent['code_verifier'][0].encode()).digest()).rstrip(b'=').decode()
        assert challenge==params['code_challenge'][0]
    grant=sql(local,'SELECT * FROM connection_oauth_grants WHERE connection_id=:id',id=id).mappings().one()
    assert 'fictional-access' not in grant.encrypted_token and 'fictional-refresh' not in grant.encrypted_token
    assert callback(state,cookie).endswith('auth=failed') # single use
    listing=connectors.list_connections(viewer());row=next(r for r in listing if r['id']==id)
    assert row['auth_state']=='oauth_authenticated' and row['mode']=='disconnected'
    assert all(secret not in json.dumps(listing,default=str) for secret in ('fictional-access','fictional-refresh','fictional-client-secret'))
    with pytest.raises(HTTPException) as exc:connectors.test_connection(viewer(),id)
    assert exc.value.status_code==409
    choices=scopes.discover(viewer(),id)
    item=choices['items'][0]
    if kind=='sharepoint':
        assert item['kind']=='library' and not item['selectable']
        item=scopes.discover(viewer(),id,drive_id=item['drive_id'])['items'][0]
    scopes.select(viewer(),id,scopes.ScopeSelection(expected_generation=row['generation'],scope_id=item['id'],drive_id=item['drive_id']))
    current=sql(local,'SELECT generation FROM source_connections WHERE id=:id',id=id).scalar_one()
    assert sql(local,'SELECT generation FROM connection_oauth_grants WHERE connection_id=:id',id=id).scalar_one()==current
    host='api.atlassian.com' if kind in {'jira','confluence'} else 'graph.microsoft.com'
    ref=oauth.reference(id)
    assert authorization(ref,host)=='Bearer fictional-access-0'
    token=oauth.unseal(grant.encrypted_token);token['expires_at']=time.time()-1
    sql(local,'UPDATE connection_oauth_grants SET encrypted_token=:token WHERE connection_id=:id',id=id,token=oauth.seal(token))
    assert authorization(ref,host)=='Bearer fictional-access-1'
    assert upstream[0]['refreshes']==1
    # A successful read-only test is already covered separately. Here verify that
    # enabling/disabling a tested generation preserves its same server-owned grant.
    sql(local,'UPDATE source_connections SET tested_generation=generation,tested_at=now() WHERE id=:id',id=id)
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='live',expected_generation=current))
    assert authorization(ref,host)=='Bearer fictional-access-1'
    connectors.change_mode(viewer(),id,connectors.ModeChange(mode='disconnected',expected_generation=current+1))
    with pytest.raises(SourceFailure,match='audience'):authorization(ref,'attacker.example')
    assert not sql(local,'SELECT 1 FROM connected_resources WHERE connection_id=:id',id=id).scalar()
    connectors.remove(viewer(),id,current+2)
    with pytest.raises(SourceFailure,match='expired'):authorization(ref,host)


def test_state_cookie_expiry_configuration_change_and_denial_are_safe(local,upstream):
    id=create();state,cookie,_=begin(id)
    assert callback(state,'wrong-cookie').endswith('auth=failed')
    assert not upstream[1]
    assert sql(local,'SELECT consumed_at FROM connection_oauth_states WHERE state_hash=:state',state=oauth.digest(state)).scalar() is None
    assert callback(state,cookie,error='access_denied').endswith('auth=failed')
    assert not upstream[1]
    state,cookie,_=begin(id)
    sql(local,"UPDATE connection_oauth_states SET expires_at=now()-interval '1 second' WHERE connection_id=:id",id=id)
    assert callback(state,cookie).endswith('auth=failed')
    state,cookie,_=begin(id)
    sql(local,'UPDATE source_connections SET generation=generation+1 WHERE id=:id',id=id)
    assert callback(state,cookie).endswith('auth=failed')
    assert not upstream[1]


def test_grant_cannot_move_to_another_connection_or_be_bound_by_browser(local,upstream):
    first=create();second=create('confluence');state,cookie,_=begin(first);callback(state,cookie)
    grant=sql(local,'SELECT * FROM connection_oauth_grants WHERE connection_id=:id',id=first).mappings().one()
    sql(local,"UPDATE source_connections SET auth_state='oauth_authenticated' WHERE id=:id",id=second)
    sql(local,'INSERT INTO connection_oauth_grants(connection_id,generation,encrypted_token) VALUES(:id,0,:token)',id=second,token=grant.encrypted_token)
    with pytest.raises(SourceFailure,match='invalid'):authorization(oauth.reference(second),'api.atlassian.com')
    with pytest.raises(ValueError):ConnectionSpec(kind='jira',execution='mock',name='Forged',scope_id='demo-scope',credential_ref=oauth.reference(first))


def test_missing_setup_and_member_cannot_start_sign_in(local,monkeypatch,upstream):
    id=create();monkeypatch.delenv('LINKMIND_OAUTH_PROVIDERS_JSON')
    with pytest.raises(HTTPException) as exc:oauth.start(viewer(),id,Response())
    assert exc.value.status_code==409 and not upstream[1]
    member=viewer();member.role='member'
    with pytest.raises(HTTPException) as exc:oauth.start(member,id,Response())
    assert exc.value.status_code==403


def test_refresh_denial_and_lost_key_do_not_expose_or_reuse_tokens(local,upstream,tmp_path):
    id=create();state,cookie,_=begin(id);callback(state,cookie)
    grant=sql(local,'SELECT encrypted_token FROM connection_oauth_grants WHERE connection_id=:id',id=id).scalar_one()
    token=oauth.unseal(grant);token['expires_at']=0
    sql(local,'UPDATE connection_oauth_grants SET encrypted_token=:token WHERE connection_id=:id',id=id,token=oauth.seal(token))
    upstream[0]['deny']=True
    with pytest.raises(SourceFailure,match='expired'):authorization(oauth.reference(id),'api.atlassian.com')
    (tmp_path/'key').write_bytes(Fernet.generate_key())
    with pytest.raises(SourceFailure,match='invalid'):authorization(oauth.reference(id),'api.atlassian.com')
