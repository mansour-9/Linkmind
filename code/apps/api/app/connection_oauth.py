"""Server-owned delegated consent. No tokens, client secrets or PKCE verifiers leave this module."""
import hashlib
import json
import os
import re
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from uuid import UUID

import httpx
from authlib.integrations.httpx_client import OAuth2Client
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.db import engine, sql
from app.connector_transport import SourceFailure, ReadClient, ReadLimits

CALLBACK='/api/v1/connections/oauth/callback'
COOKIE='linkmind_source_consent'


def digest(value):return hashlib.sha256(value.encode()).hexdigest()


def cipher():
    configured=os.getenv('LINKMIND_CONNECTION_KEY_FILE')
    if not configured and os.getenv('COMPANY_BRAIN_LOCAL_DEMO')!='1':raise SourceFailure('oauth_not_configured')
    path=Path(configured or '/artifacts/connection-secrets/key')
    if not configured:
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        try:
            descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'wb') as stream:
                stream.write(Fernet.generate_key());stream.flush();os.fsync(stream.fileno())
        except FileExistsError:pass
    try:return Fernet(path.read_bytes().strip())
    except (OSError,ValueError):raise SourceFailure('oauth_not_configured') from None


def seal(payload):return cipher().encrypt(json.dumps(payload).encode()).decode()


def unseal(payload):
    try:return json.loads(cipher().decrypt(payload.encode()))
    except (InvalidToken,ValueError,TypeError):raise SourceFailure('credentials_invalid') from None


def origin():
    value=os.getenv('LINKMIND_PUBLIC_ORIGIN','').rstrip('/')
    p=urlsplit(value)
    local=os.getenv('COMPANY_BRAIN_LOCAL_DEMO')=='1' and p.hostname in {'127.0.0.1','localhost'}
    if not p.hostname or p.username or p.password or p.path or p.query or p.fragment or (p.scheme!='https' and not (local and p.scheme=='http')):
        raise SourceFailure('oauth_not_configured')
    return value


def settings(spec):
    if spec.kind=='custom_mcp' or spec.transport!='native':raise SourceFailure('oauth_not_configured')
    try:
        raw=json.loads(os.getenv('LINKMIND_OAUTH_PROVIDERS_JSON','{}'))[spec.kind]
        client_id=raw['client_id'];secret=raw['client_secret']
        if not all(isinstance(v,str) and 1<=len(v)<=4096 for v in (client_id,secret)):raise ValueError()
        if spec.kind in {'jira','confluence'}:
            scopes='offline_access '+('read:jira-work' if spec.kind=='jira' else 'read:confluence-content.all read:confluence-space.summary')
            return dict(client_id=client_id,client_secret=secret,scope=scopes,provider='atlassian',
                authorize_url='https://auth.atlassian.com/authorize',token_url='https://auth.atlassian.com/oauth/token')
        tenant=str(UUID(raw['tenant_id']))
        scopes='offline_access https://graph.microsoft.com/Files.Read' if spec.kind=='onedrive' else 'offline_access https://graph.microsoft.com/Files.Read.All https://graph.microsoft.com/Sites.Read.All'
        base=f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/'
        return dict(client_id=client_id,client_secret=secret,scope=scopes,provider='microsoft',authorize_url=base+'authorize',token_url=base+'token')
    except (KeyError,TypeError,ValueError):raise SourceFailure('oauth_not_configured') from None


def configured(spec):
    try:settings(spec);origin();return True
    except SourceFailure:return False


def network():
    if os.getenv('LINKMIND_CONNECTOR_NETWORK')!='1':raise SourceFailure('network_not_enabled')


def oauth_client(config):
    return OAuth2Client(client_id=config['client_id'],client_secret=config['client_secret'],
        scope=config['scope'],redirect_uri=origin()+CALLBACK,code_challenge_method='S256',
        token_endpoint_auth_method='client_secret_post',timeout=10,follow_redirects=False,trust_env=False)


def exchange(config, *, code=None, verifier=None, refresh=None):
    network()
    try:
        if config['provider']=='microsoft':
            with oauth_client(config) as client:
                result=(client.refresh_token(config['token_url'],refresh_token=refresh) if refresh else
                    client.fetch_token(config['token_url'],code=code,code_verifier=verifier))
        else:
            body=dict(client_id=config['client_id'],client_secret=config['client_secret'],
                grant_type='refresh_token' if refresh else 'authorization_code')
            body.update(dict(refresh_token=refresh) if refresh else dict(code=code,redirect_uri=origin()+CALLBACK))
            with httpx.Client(timeout=10,follow_redirects=False,trust_env=False) as client:
                response=client.post(config['token_url'],json=body)
                if response.status_code!=200 or len(response.content)>65536:raise SourceFailure('authentication_expired')
                result=response.json()
        token=dict(result)
        access=token.get('access_token');expiry=int(token.get('expires_in',3600))
        if not isinstance(access,str) or not 1<=len(access)<=24000 or any(c.isspace() for c in access) or token.get('token_type','Bearer').lower()!='bearer' or not 60<expiry<=86400:
            raise SourceFailure('credentials_invalid')
        return dict(access_token=access,refresh_token=token.get('refresh_token') or refresh,expires_at=time.time()+expiry)
    except SourceFailure:raise
    except Exception:
        # Provider/library errors may include secrets or raw token responses.
        raise SourceFailure('authentication_expired') from None


def start(viewer,id,response):
    from app.connectors import admin,owned,audit
    from app.connector_providers import ConnectionSpec
    admin(viewer)
    with engine.connect() as conn:row=owned(conn,viewer,id)
    spec=ConnectionSpec(**row.config)
    if spec.execution!='real' or spec.auth_method!='oauth':raise HTTPException(409,'Choose real source OAuth authentication first.')
    try:
        config=settings(spec);public_origin=origin();network()
        state=secrets.token_urlsafe(32);binding=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
        encrypted=seal(dict(verifier=verifier,connection_id=str(id)))
    except SourceFailure as exc:raise HTTPException(409,dict(code=exc.code,message='Provider sign-in is not configured on this server yet. No external account was contacted.')) from None
    with engine.begin() as conn:
        current=owned(conn,viewer,id,True)
        if current.generation!=row.generation:raise HTTPException(409,'Configuration changed. Try sign-in again.')
        sql(conn,"DELETE FROM connection_oauth_states WHERE expires_at<now()-interval '1 day' OR connection_id=:id",id=id)
        sql(conn,'''UPDATE source_connections SET generation=generation+1,mode='disconnected',auth_state='sign_in_pending',
            tested_generation=NULL,tested_at=NULL,sync_requested=false,lease_token=NULL,lease_until=NULL WHERE id=:id''',id=id)
        sql(conn,'DELETE FROM connection_oauth_grants WHERE connection_id=:id',id=id)
        sql(conn,'UPDATE connected_resources SET access_until=NULL WHERE connection_id=:id',id=id)
        sql(conn,'''INSERT INTO connection_oauth_states(state_hash,connection_id,owner_id,organization_id,generation,cookie_hash,encrypted_verifier)
            VALUES(:state,:id,:owner,:org,:generation,:cookie,:verifier)''',state=digest(state),id=id,owner=viewer.id,
            org=viewer.organization_id,generation=row.generation+1,cookie=digest(binding),verifier=encrypted)
        audit(conn,viewer,id,'connection_sign_in_started')
    if config['provider']=='microsoft':
        with oauth_client(config) as client:url,_=client.create_authorization_url(config['authorize_url'],state=state,code_verifier=verifier)
    else:
        url=config['authorize_url']+'?'+urlencode(dict(audience='api.atlassian.com',client_id=config['client_id'],
            scope=config['scope'],redirect_uri=public_origin+CALLBACK,state=state,response_type='code',prompt='consent'))
    response.set_cookie(COOKIE,binding,max_age=600,httponly=True,secure=public_origin.startswith('https:'),samesite='lax',path=CALLBACK)
    response.headers['Cache-Control']='no-store'
    return dict(authorization_url=url,message='Continue sign-in with the source provider. Only selected Linkmind scopes can be enabled after testing.')


def callback(request,state,code=None,error=None):
    from app.connector_providers import ConnectionSpec
    from app.connectors import audit
    from types import SimpleNamespace
    # Prevent Uvicorn's response-time access log from recording provider codes/state.
    request.scope['query_string']=b''
    result='failed';row=None
    try:
        binding=request.cookies.get(COOKIE,'')
        if not state or len(state)>200 or not binding:raise SourceFailure('invalid_oauth_state')
        with engine.begin() as conn:
            row=sql(conn,'''SELECT s.*,c.config FROM connection_oauth_states s JOIN source_connections c ON c.id=s.connection_id
                JOIN users u ON u.id=s.owner_id AND u.organization_id=s.organization_id
                WHERE s.state_hash=:state AND s.expires_at>now() AND s.consumed_at IS NULL
                AND c.generation=s.generation AND c.owner_id=s.owner_id AND c.organization_id=s.organization_id
                AND c.removed_at IS NULL AND u.role='admin' FOR UPDATE OF s,c''',state=digest(state)).mappings().first()
            if row is None or not secrets.compare_digest(row.cookie_hash,digest(binding)):
                row=None
                raise SourceFailure('invalid_oauth_state')
            sql(conn,'UPDATE connection_oauth_states SET consumed_at=now() WHERE state_hash=:state',state=digest(state))
        if error or not code or len(code)>8192:raise SourceFailure('consent_denied')
        data=unseal(row.encrypted_verifier)
        if data.get('connection_id')!=str(row.connection_id):raise SourceFailure('invalid_oauth_state')
        spec=ConnectionSpec(**row.config);config=settings(spec)
        token=exchange(config,code=code,verifier=data['verifier'])
        if config['provider']=='atlassian':
            network()
            with httpx.Client(timeout=10,follow_redirects=False,trust_env=False) as client:
                response=client.get('https://api.atlassian.com/oauth/token/accessible-resources',headers={'Authorization':'Bearer '+token['access_token']})
                if response.status_code!=200 or len(response.content)>1048576:raise SourceFailure('access_denied')
                resources=response.json()
            selected=[r for r in resources if r.get('url','').rstrip('/')==spec.site_url and r.get('id')]
            if len(selected)!=1:raise SourceFailure('outside_scope')
            spec=spec.model_copy(update=dict(cloud_id=str(UUID(selected[0]['id']))))
        token.update(connection_id=str(row.connection_id),provider=config['provider'])
        with engine.begin() as conn:
            current=sql(conn,'SELECT generation FROM source_connections WHERE id=:id AND removed_at IS NULL FOR UPDATE',id=row.connection_id).scalar()
            if current!=row.generation:raise SourceFailure('configuration_changed')
            sql(conn,'''INSERT INTO connection_oauth_grants(connection_id,generation,encrypted_token) VALUES(:id,:generation,:token)
                ON CONFLICT(connection_id) DO UPDATE SET generation=EXCLUDED.generation,encrypted_token=EXCLUDED.encrypted_token,updated_at=now()''',
                id=row.connection_id,generation=row.generation,token=seal(token))
            sql(conn,"UPDATE source_connections SET config=CAST(:config AS jsonb),auth_state='oauth_authenticated',health='not_connected',error_code=NULL WHERE id=:id",
                id=row.connection_id,config=spec.model_dump_json())
            audit(conn,SimpleNamespace(id=row.owner_id,organization_id=row.organization_id),row.connection_id,'connection_sign_in_completed')
        result='connected'
    except Exception:
        # No raw upstream errors, codes or token material in responses/logs.
        if row:
            with engine.begin() as conn:
                sql(conn,"UPDATE source_connections SET auth_state='unconfigured',error_code='authentication_expired' WHERE id=:id AND generation=:generation AND auth_state='sign_in_pending'",id=row.connection_id,generation=row.generation)
    response=RedirectResponse('/admin/connections?auth='+result,status_code=303,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
    response.delete_cookie(COOKIE,path=CALLBACK)
    return response


def reference(id):return 'RF4_OAUTH_'+str(id).replace('-','').upper()


def token_authorization(ref,host):
    from app.connector_providers import ConnectionSpec
    if not re.fullmatch(r'RF4_OAUTH_[0-9A-F]{32}',ref):raise SourceFailure('credentials_missing')
    id=UUID(ref[len('RF4_OAUTH_'):])
    with engine.begin() as conn:
        row=sql(conn,'''SELECT g.*,c.config FROM connection_oauth_grants g JOIN source_connections c ON c.id=g.connection_id
            WHERE g.connection_id=:id AND g.generation=c.generation AND c.removed_at IS NULL
            AND c.auth_state='oauth_authenticated' FOR UPDATE OF g''',id=id).mappings().first()
        if row is None:raise SourceFailure('authentication_expired')
        spec=ConnectionSpec(**row.config)
        expected='api.atlassian.com' if spec.kind in {'jira','confluence'} else 'graph.microsoft.com'
        if host!=expected:raise SourceFailure('credential_audience_mismatch')
        token=unseal(row.encrypted_token)
        if token.get('connection_id')!=str(id):raise SourceFailure('credentials_invalid')
        if token.get('expires_at',0)<=time.time()+60:
            if not token.get('refresh_token'):raise SourceFailure('authentication_expired')
            refreshed=exchange(settings(spec),refresh=token['refresh_token'])
            token.update(refreshed)
            sql(conn,'UPDATE connection_oauth_grants SET encrypted_token=:token,updated_at=now() WHERE connection_id=:id',id=id,token=seal(token))
        return 'Bearer '+token['access_token']


def runtime_spec(spec,id):
    if spec.auth_method!='oauth':return spec
    if id is None:raise SourceFailure('credentials_missing')
    if spec.kind in {'jira','confluence'} and not spec.cloud_id:raise SourceFailure('authentication_expired')
    return spec.model_copy(update=dict(credential_ref=reference(id)))
