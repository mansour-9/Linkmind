"""Bounded metadata discovery and explicit scope selection; never document ingestion."""
import hashlib
import json
import re
from urllib.parse import quote, urlsplit

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.db import engine,sql
from app.connector_providers import ConnectionSpec
from app.connector_transport import ReadLimits,SourceFailure,active


class ScopeSelection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_generation:int=Field(ge=0)
    scope_id:str=Field(min_length=1,max_length=150,pattern=r'^[A-Za-z0-9!_,.-]+$')
    drive_id:str=Field(default='',max_length=200,pattern=r'^[A-Za-z0-9!_,.-]*$')


def discovery_failure(exc):
    raise HTTPException(409,dict(code=exc.code,message='Accessible scopes could not be read. Check sign-in, source permissions and the configured site. No documents were imported.')) from None


def discover(viewer,id,parent_id='',drive_id=''):
    from app.connectors import admin,owned,Provider
    admin(viewer)
    if any(value and not re.fullmatch(r'[A-Za-z0-9!_,.-]{1,200}',value) for value in (parent_id,drive_id)):
        raise HTTPException(422,'Use a valid folder or drive identifier.')
    with engine.connect() as conn:row=owned(conn,viewer,id)
    spec=ConnectionSpec(**row.config)
    if row.auth_state not in {'mock_authenticated','oauth_authenticated','server_credential'}:raise HTTPException(409,'Sign in before discovering accessible scopes.')
    if spec.execution=='mock':return dict(items=[dict(id='demo-scope',name='Demo scope — synthetic content only',kind='scope',drive_id='',selectable=True)],synthetic=True,truncated=False)
    if spec.kind=='custom_mcp' or spec.transport!='native':return dict(items=[dict(id=spec.scope_id,name='Explicitly configured MCP scope',kind='scope',drive_id='',selectable=True)],synthetic=False,truncated=False,manual=True)
    try:
        provider=Provider(spec,active() or ReadLimits(max_calls=5,seconds=20),row.id)
        client=provider.client;base=provider.base;items=[];truncated=False
        if spec.kind=='jira':
            data=client.get(base+'/rest/api/3/project/search',{'maxResults':25})
            items=[dict(id=p['key'],name=p['name'],kind='project',drive_id='',selectable=True) for p in data.get('values',[])[:25]]
            truncated=not data.get('isLast',True)
        elif spec.kind=='confluence':
            data=client.get(base+'/wiki/api/v2/spaces',{'limit':25})
            items=[dict(id=p['id'],name=p['name'],kind='space',drive_id='',selectable=True) for p in data.get('results',[])[:25]]
            truncated=bool(data.get('_links',{}).get('next'))
        elif spec.kind=='sharepoint' and not drive_id:
            site=urlsplit(spec.site_url)
            if not site.hostname or not site.hostname.endswith('.sharepoint.com'):raise SourceFailure('site_required')
            data=client.get(base+'/sites/'+site.hostname+':/'+quote(site.path.strip('/'),safe='/'))
            libraries=client.get(base+'/sites/'+quote(data['id'],safe=',')+'/drives',{'$top':25})
            items=[dict(id=p['id'],name=p['name'],kind='library',drive_id=p['id'],selectable=False) for p in libraries.get('value',[])[:25]]
            truncated=bool(libraries.get('@odata.nextLink'))
        else:
            folder=(base+'/drives/'+quote(drive_id)+'/items/'+quote(parent_id) if drive_id and parent_id else
                base+'/drives/'+quote(drive_id)+'/root' if drive_id else base+'/me/drive/root')
            current=client.get(folder)
            actual_drive=current.get('parentReference',{}).get('driveId') or drive_id
            if not actual_drive or 'folder' not in current:raise SourceFailure('outside_scope')
            children=client.get(base+'/drives/'+quote(actual_drive)+'/items/'+quote(current['id'])+'/children',{'$top':25,'$select':'id,name,folder,parentReference'})
            items=[dict(id=current['id'],name=current.get('name','Current folder')+' (this folder)',kind='folder',drive_id=actual_drive,selectable=True)]
            items += [dict(id=p['id'],name=p['name'],kind='folder',drive_id=actual_drive,selectable=True) for p in children.get('value',[])[:25] if 'folder' in p]
            truncated=bool(children.get('@odata.nextLink'))
        return dict(items=items,synthetic=False,truncated=truncated,notice='Only accessible scope metadata was read. No documents were imported.')
    except SourceFailure as exc:discovery_failure(exc)
    except (KeyError,TypeError,ValueError):discovery_failure(SourceFailure('malformed_source'))


def select(viewer,id,body):
    from app.connectors import admin,owned,audit,Provider
    admin(viewer)
    with engine.connect() as conn:row=owned(conn,viewer,id)
    if row.generation!=body.expected_generation:raise HTTPException(409,'Configuration changed. Reload the scopes.')
    if row.auth_state not in {'mock_authenticated','oauth_authenticated','server_credential'}:raise HTTPException(409,'Authenticate this source first.')
    old=ConnectionSpec(**row.config)
    try:spec=ConnectionSpec(**(row.config|dict(scope_id=body.scope_id,drive_id=body.drive_id or old.drive_id)))
    except ValueError:raise HTTPException(422,'Choose a valid scope for this source.') from None
    if spec.scope_id=='pending-scope':raise HTTPException(422,'Choose a scope before saving.')
    try:
        if spec.execution=='mock':
            if spec.scope_id!='demo-scope':raise SourceFailure('outside_scope')
        elif spec.kind=='custom_mcp' or spec.transport!='native':
            if spec.scope_id!=old.scope_id:raise SourceFailure('outside_scope')
        else:
            provider=Provider(spec,active() or ReadLimits(max_calls=5,seconds=20),row.id)
            if spec.kind=='jira':
                data=provider.client.get(provider.base+'/rest/api/3/project/'+quote(spec.scope_id))
                if data.get('key')!=spec.scope_id:raise SourceFailure('outside_scope')
            elif spec.kind=='confluence':
                data=provider.client.get(provider.base+'/wiki/api/v2/spaces/'+quote(spec.scope_id))
                if str(data.get('id'))!=spec.scope_id:raise SourceFailure('outside_scope')
            else:
                data=provider.client.get(provider.base+'/drives/'+quote(spec.drive_id)+'/items/'+quote(spec.scope_id))
                if data.get('id')!=spec.scope_id or 'folder' not in data or data.get('parentReference',{}).get('driveId',spec.drive_id)!=spec.drive_id:raise SourceFailure('outside_scope')
    except SourceFailure as exc:discovery_failure(exc)
    identity=json.dumps([str(viewer.id),spec.kind,spec.execution,spec.site_url,spec.mcp_url,spec.drive_id,spec.scope_id])
    key=hashlib.sha256(identity.encode()).hexdigest()
    with engine.begin() as conn:
        current=owned(conn,viewer,id,True)
        if current.generation!=row.generation:raise HTTPException(409,'Configuration changed during scope verification.')
        if spec.drive_id!=old.drive_id and sql(conn,'SELECT EXISTS(SELECT 1 FROM connected_resources WHERE connection_id=:id)',id=id).scalar():
            raise HTTPException(409,'Add a new source to change the library after retaining documents.')
        if sql(conn,'SELECT 1 FROM source_instances WHERE organization_id=:org AND kind=:kind AND instance_key=:key AND id<>:id',org=viewer.organization_id,kind=spec.kind,key=key,id=id).scalar():
            raise HTTPException(409,'That source scope is already configured.')
        sql(conn,'UPDATE source_instances SET instance_key=:key WHERE id=:id',key=key,id=id)
        sql(conn,'''UPDATE source_connections SET config=CAST(:config AS jsonb),generation=generation+1,mode='disconnected',
            health='not_connected',error_code=NULL,tested_generation=NULL,tested_at=NULL,cursor='{}',sync_requested=false,
            lease_token=NULL,lease_until=NULL WHERE id=:id''',id=id,config=spec.model_dump_json())
        sql(conn,'UPDATE connection_oauth_grants SET generation=:generation WHERE connection_id=:id AND generation=:old',id=id,generation=row.generation+1,old=row.generation)
        sql(conn,'DELETE FROM connection_oauth_states WHERE connection_id=:id',id=id)
        sql(conn,'UPDATE connected_resources SET access_until=NULL WHERE connection_id=:id',id=id)
        audit(conn,viewer,id,'connection_scope_selected')
    return dict(status='saved',requires_test=True,message='Scope saved. Test it before enabling access. No documents were imported.')
