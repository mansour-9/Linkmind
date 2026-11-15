"""Owner-bound read-only connectors; transactional checkpoints, no implicit inference."""
import hashlib
import json
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from app.db import engine, sql
from app.connector_providers import ConnectionSpec, Provider as NativeProvider
from app.connector_transport import ReadLimits, SourceFailure, active
from app.source_evidence import SourceEvidence, ResourceIdentity, FieldEvidence, EvidenceCoverage

MESSAGES = {
    'credentials_missing': 'Configure this connection’s credential reference on the local server.',
    'network_not_enabled': 'External reads are disabled in this local preview. Configure approved credentials and enable connector networking for a scoped trial.',
    'authentication_expired': 'Sign in again or renew this connection’s server-side credential.',
    'access_denied': 'Source access was denied. Verify the account and selected scope; retained evidence is hidden.',
    'resource_missing': 'This resource is no longer available from the source.',
    'rate_limited': 'The source is rate limited. Collection will back off; try again later.',
    'source_outage': 'The source is unavailable. Access could not be confirmed; retained evidence is hidden.',
    'scope_limit': 'This scope exceeds the local 25-resource limit. Choose a smaller project, space or folder.',
    'checkpoint_expired': 'The source checkpoint expired. Start a fresh collection; retained history is preserved.',
}


def now(): return datetime.now(timezone.utc)


class ModeChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['disconnected', 'live', 'sync']
    expected_generation: int = Field(ge=0)


class LiveRead(BaseModel):
    model_config = ConfigDict(extra='forbid')
    native_id: str = Field(min_length=1, max_length=200, pattern=r'^[A-Za-z0-9!_,.-]+$')
    question: str | None = Field(default=None, min_length=1, max_length=500)


PUBLIC = 'c.id,c.mode,c.health,c.error_code,c.generation,c.last_successful_sync_at,c.next_sync_at,s.kind,s.name,c.config,c.credential_ref'


def Provider(spec,limits=None,connection_id=None):
    spec=spec if isinstance(spec,ConnectionSpec) else ConnectionSpec(**spec)
    if spec.execution=='mock':
        from app.connector_demo import DemoProvider
        return DemoProvider(spec,limits)
    from app.connection_oauth import runtime_spec
    spec=runtime_spec(spec,connection_id)
    if spec.kind=='custom_mcp':
        from app.custom_mcp import CustomMCPProvider
        return CustomMCPProvider(spec,limits)
    return NativeProvider(spec,limits)


def admin(viewer):
    if viewer.role!='admin':raise HTTPException(403,'Only authorized administrators can manage source connections.')


def audit(conn,viewer,id,action):
    sql(conn,'''INSERT INTO audit_events(id,organization_id,actor_id,action,resource_id)
        VALUES(:event,:org,:actor,:action,:id)''',event=uuid4(),org=viewer.organization_id,actor=viewer.id,action=action,id=id)


def owned(conn, viewer, id, lock=False):
    row = sql(conn, '''SELECT c.*,s.kind,s.name FROM source_connections c JOIN source_instances s ON s.id=c.id
        WHERE c.id=:id AND c.organization_id=:org AND c.owner_id=:viewer AND c.removed_at IS NULL''' + (' FOR UPDATE OF c' if lock else ''),
        **viewer.access(), id=id).mappings().first()
    if row is None: raise HTTPException(404, 'Connection not found.')
    return row


def create(viewer, spec):
    if viewer.role != 'admin': raise HTTPException(403, 'Only an administrator can configure a local connector.')
    id = uuid4()
    identity = json.dumps([str(viewer.id), spec.kind, spec.execution,spec.site_url,spec.mcp_url,spec.drive_id,spec.scope_id])
    key = hashlib.sha256(identity.encode()).hexdigest()
    config = spec.model_dump()
    with engine.begin() as conn:
        existing = sql(conn, '''SELECT c.id FROM source_instances s JOIN source_connections c ON c.id=s.id
            WHERE s.organization_id=:org AND s.kind=:kind AND s.instance_key=:key''',
            org=viewer.organization_id, kind=spec.kind, key=key).scalar()
        if existing:
            sql(conn,'DELETE FROM connection_oauth_grants WHERE connection_id=:id',id=existing)
            sql(conn,'DELETE FROM connection_oauth_states WHERE connection_id=:id',id=existing)
            sql(conn,'UPDATE source_instances SET name=:name WHERE id=:id',id=existing,name=spec.name)
            # Credential replacement preserves source identity but revokes old access/checkpoints.
            sql(conn, '''UPDATE source_connections SET credential_ref=:ref,config=CAST(:config AS jsonb),
                generation=generation+1,mode='disconnected',health='not_connected',cursor='{}',
                sync_requested=false,lease_token=NULL,lease_until=NULL,removed_at=NULL,
                auth_state='unconfigured',tested_generation=NULL,tested_at=NULL WHERE id=:id''',
                id=existing, ref=spec.credential_ref, config=json.dumps(config))
            sql(conn, 'UPDATE connected_resources SET access_until=NULL WHERE connection_id=:id', id=existing)
            audit(conn,viewer,existing,'connection_reconfigured')
            return dict(id=existing, reconnected=True)
        sql(conn, '''INSERT INTO source_instances(id,organization_id,kind,instance_key,name)
            VALUES(:id,:org,:kind,:key,:name)''', id=id, org=viewer.organization_id, kind=spec.kind, key=key, name=spec.name)
        sql(conn, '''INSERT INTO source_connections(id,organization_id,owner_id,config,credential_ref)
            VALUES(:id,:org,:owner,CAST(:config AS jsonb),:ref)''', id=id, org=viewer.organization_id,
            owner=viewer.id, config=json.dumps(config), ref=spec.credential_ref)
        audit(conn,viewer,id,'connection_created')
    return dict(id=id, reconnected=False)


def change_mode(viewer, id, body):
    admin(viewer)
    with engine.begin() as conn:
        row = owned(conn, viewer, id, True)
        if row.generation != body.expected_generation: raise HTTPException(409, 'Connection changed. Reload before saving.')
        if body.mode!='disconnected' and (row.tested_generation!=row.generation or not row.tested_at or row.tested_at<now()-timedelta(minutes=15)):
            raise HTTPException(409,'Authenticate and test this configuration before enabling it.')
        sql(conn, '''UPDATE source_connections SET mode=:mode,generation=generation+1,cursor='{}',
            health=:health,error_code=NULL,sync_requested=:sync,lease_token=NULL,lease_until=NULL,
            next_sync_at=CASE WHEN :sync THEN now() ELSE NULL END,
            tested_generation=CASE WHEN tested_generation=generation THEN generation+1 ELSE NULL END WHERE id=:id''', id=id,
            mode=body.mode, health='not_connected' if body.mode == 'disconnected' else 'awaiting_read', sync=body.mode == 'sync')
        sql(conn, 'UPDATE connected_resources SET access_until=NULL WHERE connection_id=:id', id=id)
        sql(conn,'UPDATE connection_oauth_grants SET generation=:generation WHERE connection_id=:id AND generation=:old',id=id,generation=row.generation+1,old=row.generation)
        audit(conn,viewer,id,'connection_mode_changed')
    return dict(mode=body.mode)


def list_connections(viewer):
    admin(viewer)
    with engine.connect() as conn:
        rows = [dict(r) for r in sql(conn, f'''SELECT {PUBLIC},c.auth_state,c.tested_generation,c.tested_at,
            (SELECT count(*) FROM connected_resources r WHERE r.connection_id=c.id AND NOT r.revoked
              AND r.access_until>now() AND r.generation=c.generation AND c.mode='sync') AS retained_resources
            FROM source_connections c JOIN source_instances s ON s.id=c.id
            WHERE c.organization_id=:org AND c.owner_id=:viewer AND c.removed_at IS NULL ORDER BY c.created_at,c.id''', **viewer.access()).mappings()]
    for row in rows:
        row['message'] = MESSAGES.get(row['error_code'], 'The source response could not be safely used. Test the selected scope and supported read interface.' if row['error_code'] else 'No source read has completed yet.' if row['health'] == 'awaiting_read' else None)
        row['scope'] = row['config']['scope_id']
        row['capabilities'] = dict(read_only=True, live=True, sync=True, resource_limit=25)
        row['execution']=row['config'].get('execution','real')
        from app.connection_oauth import configured
        row['oauth_ready']=configured(ConnectionSpec(**row['config'])) if row['execution']=='real' else False
    return rows


def failure(id, generation, code, lease=None):
    with engine.begin() as conn:
        changed=sql(conn, '''UPDATE source_connections SET health='unavailable',error_code=:code,
            lease_token=NULL,lease_until=NULL,tested_generation=NULL,tested_at=NULL,next_sync_at=now()+interval '5 minutes'
            WHERE id=:id AND generation=:generation''' + (' AND lease_token=:lease' if lease else '') + ' RETURNING id',
            id=id, generation=generation, code=code, **({'lease':lease} if lease else {})).scalar()
        if not changed: return
        sql(conn, '''UPDATE connected_resources SET access_until=NULL WHERE connection_id=:id
            AND EXISTS(SELECT 1 FROM source_connections WHERE id=:id AND generation=:generation)''', id=id, generation=generation)


def live(viewer, id, body):
    with engine.connect() as conn: row = owned(conn, viewer, id)
    if row.mode == 'disconnected': raise HTTPException(409, 'Connect this scoped source before reading it.')
    limits = active() or ReadLimits()
    try:
        provider = Provider(row.config, limits, row.id)
        record = provider.get(body.native_id, mcp=True)
        identity = ResourceIdentity(organization_id=viewer.organization_id, source_instance_id=id,
            resource_type='issue' if row.kind == 'jira' else 'page' if row.kind == 'confluence' else 'document', native_id=record.native_id)
        from app.parsers import parse_document
        passages = parse_document(record.filename, record.content)
        text = '\n'.join(p.text for p in passages[:8])[:12000]
        evidence = SourceEvidence(reference_id='live-' + hashlib.sha256(record.content).hexdigest()[:24],
            synthetic=row.config.get('execution')=='mock',
            identity=identity, origin='live', original_url=record.original_url, source_revision=record.revision,
            source_updated_at=record.updated, observed_at=now(), access_dependencies=[identity],
            fields=[FieldEvidence(**v) for v in record.fields], excerpt=None if record.fields else text,
            coverage=EvidenceCoverage(complete=False, description='One bounded live resource observation; not complete source coverage.'))
        result = dict(evidence=evidence.model_dump(mode='json'), retained=False,synthetic=row.config.get('execution')=='mock')
        if body.question:
            from app import providers
            from app.query_limits import question_limits
            context = [dict(id=f'{evidence.reference_id}-{i}', text=p.text, filename=record.filename, locator=p.locator, observation_kind='live')
                for i, p in enumerate(passages[:8]) if sum(len(x.text) for x in passages[:i+1]) <= 12000]
            def authorize():
                with engine.connect() as conn:
                    current = owned(conn, viewer, id)
                    if current.generation != row.generation or current.mode == 'disconnected':
                        raise HTTPException(409, 'Connection changed during the read.')
                provider.authorize(record.native_id)
            with question_limits():
                answer = providers.answer(body.question, context, dict(org=viewer.organization_id, user=viewer.id), authorize=authorize)
                authorize()
            result.update(answer=answer.model_dump(), passages=context, provider='bedrock' if providers.configured() else 'mock-extractive')
        with engine.begin() as conn:
            current = owned(conn, viewer, id, True)
            if current.generation != row.generation or current.mode == 'disconnected': raise HTTPException(409, 'Connection changed during the read.')
            sql(conn, "UPDATE source_connections SET health='ready',error_code=NULL WHERE id=:id", id=id)
        return result
    except SourceFailure as exc:
        if exc.code not in {'resource_missing','outside_scope'}:failure(id, row.generation, exc.code)
        raise HTTPException(503, dict(code=exc.code, message=MESSAGES.get(exc.code, 'Source response could not be safely used. Check the configured scope.'))) from None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503,'The source answer is unavailable. No unverified answer or shared source record was saved.') from None


def retain(conn, connection, record):
    from app.main import add_version, Viewer
    viewer = Viewer(id=connection.owner_id, organization_id=connection.organization_id, role='admin', name='Collector', organization='Local')
    row = sql(conn, '''SELECT r.*,v.checksum,v.id AS version_id FROM connected_resources r JOIN documents d ON d.id=r.document_id
        LEFT JOIN document_versions v ON v.id=d.current_version_id WHERE r.connection_id=:id AND r.native_id=:native FOR UPDATE OF r''',
        id=connection.id, native=record.native_id).mappings().first()
    if row and record.updated < row.source_updated_at: return
    checksum = hashlib.sha256(record.content).hexdigest()
    if row and record.updated == row.source_updated_at and record.revision != row.source_revision:
        raise SourceFailure('source_version_ambiguous')
    if not row:
        count = sql(conn, 'SELECT count(*) FROM connected_resources WHERE connection_id=:id', id=connection.id).scalar_one()
        if count >= 25: raise SourceFailure('scope_limit')
        did = uuid4()
        sql(conn, '''INSERT INTO documents(id,organization_id,owner_id,filename,visibility,source_instance_id,native_id)
            VALUES(:id,:org,:owner,:filename,'private',:source,:native)''', id=did, org=connection.organization_id,
            owner=connection.owner_id, filename=record.filename, source=connection.id, native=record.native_id)
        sql(conn, '''INSERT INTO connected_resources(connection_id,native_id,document_id,source_revision,source_updated_at,observed_at,
            original_url,generation,access_until) VALUES(:id,:native,:doc,:revision,:updated,now(),:url,:generation,now()+interval '2 minutes')''',
            id=connection.id, native=record.native_id, doc=did, revision=record.revision, updated=record.updated,
            url=record.original_url, generation=connection.generation)
        version = add_version(conn, viewer, did, record.filename, record.content, checksum)['version_id']
    else:
        did = row.document_id
        # A queued unchanged revision is also reused across worker/page retries.
        latest = sql(conn, '''SELECT id,checksum FROM document_versions WHERE document_id=:id
            AND source_version_id IS NULL ORDER BY created_at DESC,id DESC LIMIT 1''', id=did).mappings().first()
        version = latest.id if latest and latest.checksum == checksum else None
        if row.checksum != checksum and version is None:
            version = add_version(conn, viewer, did, record.filename, record.content, checksum)['version_id']
        version = version or row.version_id
        if not version: raise SourceFailure('publication_pending')
        sql(conn, '''UPDATE connected_resources SET source_revision=:revision,source_updated_at=:updated,observed_at=now(),
            original_url=:url,generation=:generation,access_until=now()+interval '2 minutes',revoked=false
            WHERE connection_id=:id AND native_id=:native''', id=connection.id, native=record.native_id,
            revision=record.revision, updated=record.updated, url=record.original_url, generation=connection.generation)
    payload = json.dumps(record.payload, ensure_ascii=False, sort_keys=True)
    previous = sql(conn, '''SELECT payload FROM connected_revisions WHERE connection_id=:id AND native_id=:native
        AND source_revision=:revision ORDER BY observed_at DESC LIMIT 1''', id=connection.id, native=record.native_id, revision=record.revision).scalar()
    if previous is not None and previous != record.payload: raise SourceFailure('source_revision_conflict')
    if previous is None:
        sql(conn, '''INSERT INTO connected_revisions(id,version_id,connection_id,native_id,source_revision,source_updated_at,original_url,payload,fields)
            VALUES(:id,:version,:source,:native,:revision,:updated,:url,CAST(:payload AS jsonb),CAST(:fields AS jsonb))''',
            id=uuid4(), version=version, source=connection.id, native=record.native_id, revision=record.revision,
            updated=record.updated, url=record.original_url, payload=payload, fields=json.dumps(record.fields))


def process_one():
    with engine.begin() as conn:
        row = sql(conn, '''SELECT c.*,s.kind,s.name FROM source_connections c JOIN source_instances s ON s.id=c.id
            WHERE c.mode='sync' AND c.removed_at IS NULL AND (c.sync_requested OR c.next_sync_at<=now())
            AND (c.lease_until IS NULL OR c.lease_until<now()) ORDER BY c.next_sync_at NULLS FIRST,c.id
            LIMIT 1 FOR UPDATE OF c SKIP LOCKED''').mappings().first()
        if not row: return False
        lease = uuid4()
        sql(conn, "UPDATE source_connections SET lease_token=:lease,lease_until=now()+interval '1 minute',sync_requested=false WHERE id=:id", id=row.id, lease=lease)
    try:
        provider = Provider(row.config, ReadLimits(), row.id)
        with engine.connect() as conn:
            provider.known_revisions=dict(sql(conn,'SELECT native_id,source_revision FROM connected_resources WHERE connection_id=:id',id=row.id).all())
        records, cursor, complete = provider.page(row.cursor)
        if len(records) > 25 or cursor == row.cursor and not complete: raise SourceFailure('incomplete_page')
        # Absence from a list is never a deletion. Recheck retained records individually.
        checks = []
        if complete:
            with engine.connect() as conn:
                retained = sql(conn, 'SELECT native_id FROM connected_resources WHERE connection_id=:id', id=row.id).scalars().all()
            for native in retained:
                try:
                    provider.authorize(native); checks.append((native, True))
                except SourceFailure as exc:
                    if exc.code not in {'resource_missing', 'access_denied', 'outside_scope'}: raise
                    checks.append((native, False))
        with engine.begin() as conn:
            current = sql(conn, 'SELECT * FROM source_connections WHERE id=:id FOR UPDATE', id=row.id).mappings().one()
            if current.generation != row.generation or current.mode != 'sync' or current.lease_token != lease or current.lease_until < now():
                return True
            connection = SimpleNamespace(**dict(row))
            for record in records: retain(conn, connection, record)
            for native, allowed in checks:
                sql(conn, '''UPDATE connected_resources SET revoked=:revoked,access_until=CASE WHEN :allowed THEN now()+interval '2 minutes' ELSE NULL END,
                    generation=:generation WHERE connection_id=:id AND native_id=:native''',
                    id=row.id, native=native, revoked=not allowed, allowed=allowed, generation=row.generation)
            sql(conn, '''UPDATE source_connections SET cursor=CAST(:cursor AS jsonb),lease_token=NULL,lease_until=NULL,
                next_sync_at=now()+CASE WHEN :complete THEN interval '5 minutes' ELSE interval '1 second' END,
                health=:health,error_code=NULL,last_successful_sync_at=CASE WHEN :complete THEN now() ELSE last_successful_sync_at END
                WHERE id=:id''', id=row.id, cursor=json.dumps(cursor), complete=complete, health='ready' if complete else 'collecting')
    except SourceFailure as exc:
        failure(row.id, row.generation, exc.code, lease)
    except Exception:
        failure(row.id, row.generation, 'malformed_source', lease)
    return True


def refresh_access(viewer, documents=None, query=None):
    """Relevant local candidate IDs first; bounded original-source authorization before exposure."""
    params = viewer.access()
    where = ''
    if documents is not None:
        if not documents: return
        where = ' AND d.id=ANY(:documents)'; params['documents'] = [UUID(str(x)) for x in documents]
    elif query:
        where = ''' AND EXISTS(SELECT 1 FROM chunks k JOIN document_versions v ON v.id=k.version_id
            WHERE v.document_id=d.id AND v.id=d.current_version_id AND
            (k.search_text@@websearch_to_tsquery('english',:query) OR k.search_simple@@websearch_to_tsquery('simple',:query)))'''
        params['query'] = query
    with engine.connect() as conn:
        rows = sql(conn, '''SELECT c.id,c.config,c.generation,r.native_id,r.document_id FROM connected_resources r
            JOIN source_connections c ON c.id=r.connection_id JOIN documents d ON d.id=r.document_id
            WHERE c.owner_id=:viewer AND c.organization_id=:org AND c.mode='sync' AND d.deleted_at IS NULL''' + where +
            ' ORDER BY r.access_until NULLS FIRST,r.document_id LIMIT 30', **params).mappings().all()
    limits = active() or ReadLimits(max_calls=40, seconds=25)
    for row in rows:
        try:
            Provider(row.config, limits, row.id).authorize(row.native_id)
            with engine.begin() as conn:
                sql(conn, '''UPDATE connected_resources SET revoked=false,access_until=now()+interval '2 minutes',generation=:generation
                    WHERE document_id=:document AND EXISTS(SELECT 1 FROM source_connections WHERE id=:id
                    AND generation=:generation AND mode='sync')''', id=row.id, document=row.document_id, generation=row.generation)
        except SourceFailure as exc:
            with engine.begin() as conn:
                sql(conn, 'UPDATE connected_resources SET access_until=NULL WHERE document_id=:id', id=row.document_id)
            failure(row.id, row.generation, exc.code)


def refresh_request(viewer, request):
    """Refresh relevant metadata/download surfaces before their ordinary access predicates."""
    if request.method != 'GET' or request.url.path.startswith('/api/v1/connections'):
        return
    path = request.url.path
    if not path.startswith('/api/v1/') or path in {'/api/v1/me', '/api/v1/runtime', '/api/v1/usage'}: return
    import re
    ids = re.findall(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}', str(request.url))
    if ids:
        with engine.connect() as conn:
            documents = sql(conn, '''SELECT DISTINCT d.id FROM documents d LEFT JOIN document_versions v ON v.document_id=d.id
                LEFT JOIN chunks k ON k.version_id=v.id LEFT JOIN processing_jobs j ON j.version_id=v.id
                WHERE d.organization_id=:org AND d.owner_id=:viewer
                AND (d.id=ANY(:ids) OR v.id=ANY(:ids) OR k.id=ANY(:ids) OR j.id=ANY(:ids))''',
                **viewer.access(), ids=[UUID(x) for x in ids]).scalars().all()
        refresh_access(viewer, documents)
    elif request.query_params.get('q'):
        refresh_access(viewer, query=request.query_params['q'])
    elif path in {'/api/v1/documents', '/api/v1/sources', '/api/v1/processing', '/api/v1/repository/resources', '/api/v1/repository/sources'}:
        refresh_access(viewer)


class ConfigurationEdit(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_generation:int=Field(ge=0)
    configuration:ConnectionSpec


def edit(viewer,id,body):
    admin(viewer)
    with engine.begin() as conn:
        row=owned(conn,viewer,id,True)
        if row.generation!=body.expected_generation:raise HTTPException(409,'Configuration changed. Reload before editing.')
        old=ConnectionSpec(**row.config);new=body.configuration
        if old.kind!=new.kind:raise HTTPException(409,'Create another source to change the source system.')
        has_records=sql(conn,'SELECT EXISTS(SELECT 1 FROM connected_resources WHERE connection_id=:id)',id=id).scalar()
        if has_records and any(getattr(old,k)!=getattr(new,k) for k in ('site_url','mcp_url','drive_id','execution')):
            raise HTTPException(409,'This change identifies another source. Add a new source to preserve existing provenance.')
        identity=json.dumps([str(viewer.id),new.kind,new.execution,new.site_url,new.mcp_url,new.drive_id,new.scope_id])
        key=hashlib.sha256(identity.encode()).hexdigest()
        if sql(conn,'SELECT 1 FROM source_instances WHERE organization_id=:org AND kind=:kind AND instance_key=:key AND id<>:id',
               org=viewer.organization_id,kind=new.kind,key=key,id=id).scalar():raise HTTPException(409,'That source scope is already configured.')
        sql(conn,'UPDATE source_instances SET name=:name,instance_key=:key WHERE id=:id',id=id,name=new.name,key=key)
        sql(conn,'''UPDATE source_connections SET config=CAST(:config AS jsonb),credential_ref=:ref,generation=generation+1,
            mode='disconnected',health='not_connected',auth_state='unconfigured',tested_generation=NULL,tested_at=NULL,
            cursor='{}',sync_requested=false,lease_token=NULL,lease_until=NULL WHERE id=:id''',
            id=id,config=new.model_dump_json(),ref=new.credential_ref)
        sql(conn,'UPDATE connected_resources SET access_until=NULL WHERE connection_id=:id',id=id)
        sql(conn,'DELETE FROM connection_oauth_grants WHERE connection_id=:id',id=id)
        sql(conn,'DELETE FROM connection_oauth_states WHERE connection_id=:id',id=id)
        audit(conn,viewer,id,'connection_edited')
    return dict(status='saved',requires_test=True)


def authenticate_connection(viewer,id):
    admin(viewer)
    with engine.connect() as conn:row=owned(conn,viewer,id)
    spec=ConnectionSpec(**row.config)
    if spec.execution=='mock':state='mock_authenticated'
    else:
        if spec.auth_method=='oauth':raise HTTPException(409,dict(code='oauth_sign_in_required',message='Use secure provider sign-in for this source.'))
        from app.connector_transport import authorization
        try:
            host='graph.microsoft.com' if spec.kind in {'onedrive','sharepoint'} else urlsplit(spec.mcp_url or spec.site_url).hostname
            authorization(spec.credential_ref,host)
            if spec.transport=='atlassian_mcp':authorization(spec.mcp_credential_ref,'mcp.atlassian.com')
        except SourceFailure:
            raise HTTPException(409,dict(code='provider_setup_required',message='Provider sign-in is not configured for this source yet. Use Demo mode now; a server-owned authentication provider is required to activate the real source. No secret is sent to the browser.')) from None
        state='server_credential'
    with engine.begin() as conn:
        sql(conn,'''UPDATE source_connections SET auth_state=:state,tested_generation=NULL,tested_at=NULL
            WHERE id=:id AND generation=:generation''',id=id,generation=row.generation,state=state)
        audit(conn,viewer,id,'connection_authentication_configured')
    return dict(auth_state=state,synthetic=spec.execution=='mock',message='Demo authentication completed; no external account was contacted.' if spec.execution=='mock' else 'Server credential available. Test the source before enabling it.')


def test_connection(viewer,id,native_id=None):
    admin(viewer)
    with engine.connect() as conn:row=owned(conn,viewer,id)
    if row.auth_state=='unconfigured':raise HTTPException(409,'Authenticate this source before testing it.')
    spec=ConnectionSpec(**row.config)
    if spec.scope_id=='pending-scope':raise HTTPException(409,'Choose an accessible project, space, folder or library before testing.')
    try:
        provider=Provider(spec,active() or ReadLimits(),row.id)
        if native_id:
            records=[provider.get(native_id,mcp=True)]
        elif spec.transport=='atlassian_mcp':
            raise SourceFailure('test_resource_required')
        else:
            records,_,_=provider.page({})
        for record in records:
            from app.parsers import parse_document
            parse_document(record.filename,record.content)
        with engine.begin() as conn:
            current=owned(conn,viewer,id,True)
            if current.generation!=row.generation:raise HTTPException(409,'Configuration changed during its test.')
            sql(conn,"UPDATE source_connections SET tested_generation=generation,tested_at=now(),health='tested',error_code=NULL WHERE id=:id",id=id)
            audit(conn,viewer,id,'connection_tested')
        return dict(status='passed',synthetic=spec.execution=='mock',observed_resources=len(records),retained=False,
            message='Demo connector test passed. No external source was contacted.' if spec.execution=='mock' else 'Read access tested for this scope. No content was retained.')
    except SourceFailure as exc:
        failure(id,row.generation,exc.code)
        raise HTTPException(503,dict(code=exc.code,message=MESSAGES.get(exc.code,'The source test did not pass. Check its scope, resource ID and supported read interface.'))) from None


def remove(viewer,id,generation):
    admin(viewer)
    with engine.begin() as conn:
        row=owned(conn,viewer,id,True)
        if row.generation!=generation:raise HTTPException(409,'Connection changed. Reload before removing it.')
        sql(conn,'''UPDATE source_connections SET removed_at=now(),mode='disconnected',generation=generation+1,
            health='removed',auth_state='unconfigured',tested_generation=NULL,tested_at=NULL,sync_requested=false,
            lease_token=NULL,lease_until=NULL WHERE id=:id''',id=id)
        sql(conn,'UPDATE connected_resources SET access_until=NULL WHERE connection_id=:id',id=id)
        sql(conn,'DELETE FROM connection_oauth_grants WHERE connection_id=:id',id=id)
        sql(conn,'DELETE FROM connection_oauth_states WHERE connection_id=:id',id=id)
        audit(conn,viewer,id,'connection_removed')
    return dict(status='removed',retained_history=True)


def install(app, Identity):
    from fastapi import Request,Response
    from app import connection_oauth,connection_scopes

    @app.get('/api/v1/connections/oauth/callback')
    def oauth_callback(request:Request,state:str='',code:str|None=None,error:str|None=None):
        return connection_oauth.callback(request,state,code,error)

    @app.post('/api/v1/connections/{id}/oauth/start')
    def oauth_start(id:UUID,response:Response,viewer:Identity):return connection_oauth.start(viewer,id,response)

    @app.get('/api/v1/connections/{id}/scopes')
    def scope_listing(id:UUID,viewer:Identity,parent_id:str='',drive_id:str=''):
        return connection_scopes.discover(viewer,id,parent_id,drive_id)

    @app.post('/api/v1/connections/{id}/scope')
    def scope_selection(id:UUID,body:connection_scopes.ScopeSelection,viewer:Identity):
        return connection_scopes.select(viewer,id,body)

    @app.get('/api/v1/connection-options')
    def options(viewer:Identity):
        admin(viewer)
        return [dict(kind=kind,name=name,mock_scopes=[dict(id='demo-scope',name='Demo scope — synthetic content only')],
            auth_methods=['mock','server_owned']+([] if kind=='custom_mcp' else ['oauth']),read_only=True) for kind,name in [('jira','Jira'),('confluence','Confluence'),
            ('onedrive','OneDrive'),('sharepoint','SharePoint'),('custom_mcp','Custom MCP Server')]]

    @app.get('/api/v1/connections')
    def listing(viewer: Identity): return list_connections(viewer)

    @app.post('/api/v1/connections', status_code=201)
    def creation(body: ConnectionSpec, viewer: Identity): return create(viewer, body)

    @app.patch('/api/v1/connections/{id}')
    def editing(id:UUID,body:ConfigurationEdit,viewer:Identity):return edit(viewer,id,body)

    @app.post('/api/v1/connections/{id}/authenticate')
    def authentication(id:UUID,viewer:Identity):return authenticate_connection(viewer,id)

    @app.post('/api/v1/connections/{id}/test')
    def testing(id:UUID,viewer:Identity,body:dict|None=None):return test_connection(viewer,id,(body or {}).get('native_id'))

    @app.delete('/api/v1/connections/{id}')
    def removal(id:UUID,expected_generation:int,viewer:Identity):return remove(viewer,id,expected_generation)

    @app.patch('/api/v1/connections/{id}/mode')
    def mode(id: UUID, body: ModeChange, viewer: Identity): return change_mode(viewer, id, body)

    @app.post('/api/v1/connections/{id}/sync', status_code=202)
    def sync(id: UUID, viewer: Identity):
        admin(viewer)
        with engine.begin() as conn:
            row = owned(conn, viewer, id, True)
            if row.mode != 'sync': raise HTTPException(409, 'Choose Live + Sync before collecting.')
            sql(conn, "UPDATE source_connections SET sync_requested=true,next_sync_at=now(),cursor=CASE WHEN error_code='checkpoint_expired' THEN '{}'::jsonb ELSE cursor END WHERE id=:id", id=id)
        return dict(status='queued')

    @app.post('/api/v1/connections/{id}/live')
    def read(id: UUID, body: LiveRead, viewer: Identity): return live(viewer, id, body)
