"""Durable owner-scoped collection runs on the existing PostgreSQL worker."""
from datetime import datetime, time, timedelta
import json
from types import SimpleNamespace
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError

from app import connectors
from app.connector_transport import ReadLimits, SourceFailure
from app.db import engine, sql


def supports(config):
    return config.get('kind') in {'jira','confluence','notion','onedrive','sharepoint'}


def event(conn,run,code,source=None):
    sql(conn,'INSERT INTO knowledge_sync_events(run_id,connection_id,code) VALUES(:run,:source,:code)',
        run=run,source=source,code=code)


def enqueue(conn,org,owner,trigger):
    sql(conn,'SELECT pg_advisory_xact_lock(hashtextextended(:key,0))',key=f'knowledge-sync:{org}:{owner}')
    current=sql(conn,'SELECT id,status FROM knowledge_sync_runs WHERE organization_id=:org AND owner_id=:owner AND finished_at IS NULL',
        org=org,owner=owner).mappings().first()
    if current:return dict(current)
    rows=sql(conn,"""SELECT c.id,c.config,s.name,c.generation FROM source_connections c JOIN source_instances s ON s.id=c.id
        WHERE c.organization_id=:org AND c.owner_id=:owner AND c.mode='sync' AND c.removed_at IS NULL ORDER BY c.id""",
        org=org,owner=owner).mappings().all()
    rows=[row for row in rows if supports(row.config)]
    if not rows:return None
    run=uuid4()
    sql(conn,'INSERT INTO knowledge_sync_runs(id,organization_id,owner_id,trigger) VALUES(:id,:org,:owner,:trigger)',
        id=run,org=org,owner=owner,trigger=trigger)
    for row in rows:
        sql(conn,'INSERT INTO knowledge_sync_tasks(run_id,connection_id,source_name,generation) VALUES(:run,:id,:name,:generation)',
            run=run,id=row.id,name=row.name,generation=row.generation)
    event(conn,run,'queued')
    return dict(id=run,status='queued')


def start(viewer):
    connectors.admin(viewer)
    with engine.begin() as conn:run=enqueue(conn,viewer.organization_id,viewer.id,'manual')
    if not run:raise HTTPException(409,'Enable Live + Sync on at least one eligible connection.')
    return run


class Schedule(BaseModel):
    model_config=ConfigDict(extra='forbid')
    enabled:bool
    time_of_day:time
    timezone:str=Field(max_length=80)


def next_slot(clock,zone):
    if clock.tzinfo or clock.second or clock.microsecond:raise ValueError('Use a local hour and minute.')
    local=datetime.now(ZoneInfo(zone))
    candidate=datetime.combine(local.date(),clock,local.tzinfo)
    if candidate<=local:candidate+=timedelta(days=1)
    return candidate


def schedule_due(conn):
    row=sql(conn,"""SELECT sc.* FROM knowledge_sync_schedules sc JOIN users u ON u.id=sc.owner_id
        AND u.organization_id=sc.organization_id WHERE u.role='admin' AND sc.enabled AND sc.next_run_at<=now()
        ORDER BY sc.next_run_at LIMIT 1 FOR UPDATE OF sc SKIP LOCKED""").mappings().first()
    if row:
        enqueue(conn,row.organization_id,row.owner_id,'scheduled')
        sql(conn,'UPDATE knowledge_sync_schedules SET next_run_at=:next WHERE organization_id=:org AND owner_id=:owner',
            next=next_slot(row.time_of_day,row.timezone),org=row.organization_id,owner=row.owner_id)


def finish_run(conn,run):
    sql(conn,'SELECT id FROM knowledge_sync_runs WHERE id=:run FOR UPDATE',run=run)
    states=sql(conn,'SELECT status FROM knowledge_sync_tasks WHERE run_id=:run',run=run).scalars().all()
    if any(state in {'queued','running','indexing'} for state in states):return
    final='completed' if all(state=='completed' for state in states) else 'failed' if all(state=='failed' for state in states) else 'partial'
    sql(conn,'UPDATE knowledge_sync_runs SET status=:status,finished_at=now() WHERE id=:run AND finished_at IS NULL',status=final,run=run)
    event(conn,run,final)


def finish_indexing(conn):
    task=sql(conn,"""SELECT t.*,r.created_at FROM knowledge_sync_tasks t JOIN knowledge_sync_runs r ON r.id=t.run_id
        WHERE t.status='indexing' AND NOT EXISTS(SELECT 1 FROM knowledge_sync_items i
          JOIN processing_jobs j ON j.version_id=i.version_id WHERE i.run_id=t.run_id AND i.connection_id=t.connection_id
          AND j.status IN ('queued','processing')) ORDER BY r.created_at LIMIT 1 FOR UPDATE OF t SKIP LOCKED""").mappings().first()
    if not task:return False
    not_ready=sql(conn,"""SELECT count(*) FROM knowledge_sync_items i JOIN document_versions v ON v.id=i.version_id
        JOIN processing_jobs j ON j.version_id=i.version_id WHERE i.run_id=:run AND i.connection_id=:source
        AND (v.search_ready_at IS NULL OR j.status<>'ready')""",run=task.run_id,source=task.connection_id).scalar_one()
    config=sql(conn,'SELECT id FROM source_connections WHERE id=:id AND mode=\'sync\' AND generation=:generation FOR UPDATE',
        id=task.connection_id,generation=task.generation).scalar()
    error='connection_changed' if not config else 'indexing_failed' if not_ready else task.error_code
    status=('partial' if task.imported+task.updated+task.skipped else 'failed') if error else 'completed'
    sql(conn,"""UPDATE knowledge_sync_tasks SET status=:status,failed=failed+:count,error_code=:error
        WHERE run_id=:run AND connection_id=:source""",status=status,count=not_ready,error=error,run=task.run_id,source=task.connection_id)
    if not error:
        sql(conn,"""UPDATE source_connections SET last_successful_sync_at=now(),health='ready',error_code=NULL,
            knowledge_checkpoint=jsonb_build_object('generation',generation,'since',CAST(:since AS text))
            WHERE id=:source""",source=task.connection_id,since=task.created_at.isoformat())
    event(conn,task.run_id,error or 'source_completed',task.connection_id)
    finish_run(conn,task.run_id)
    return True


def claim(conn):
    task=sql(conn,"""SELECT t.*,c.config,c.organization_id,c.owner_id,c.mode,c.removed_at,c.generation AS current_generation,
        c.knowledge_checkpoint,r.created_at FROM knowledge_sync_tasks t JOIN source_connections c ON c.id=t.connection_id
        JOIN knowledge_sync_runs r ON r.id=t.run_id WHERE t.status IN ('queued','running')
        AND t.available_at<=now() AND (t.lease_until IS NULL OR t.lease_until<=now())
        ORDER BY t.available_at,r.created_at,t.connection_id LIMIT 1 FOR UPDATE OF t SKIP LOCKED""").mappings().first()
    if not task:return None,None
    token=uuid4()
    sql(conn,"""UPDATE knowledge_sync_tasks SET status='running',attempts=attempts+1,lease_token=:token,
        lease_until=now()+interval '90 seconds' WHERE run_id=:run AND connection_id=:source""",
        run=task.run_id,source=task.connection_id,token=token)
    sql(conn,"UPDATE knowledge_sync_runs SET status='running' WHERE id=:run AND status='queued'",run=task.run_id)
    if not task.cursor and not task.attempts:event(conn,task.run_id,'source_started',task.connection_id)
    return task,token


def read_batch(task):
    if task.removed_at or task.mode!='sync' or task.generation!=task.current_generation:raise SourceFailure('connection_changed')
    provider=connectors.Provider(task.config,ReadLimits(seconds=35),task.connection_id)
    if task.cursor.get('phase')=='verify':
        with engine.connect() as conn:
            ids=sql(conn,"""SELECT native_id FROM connected_resources WHERE connection_id=:id AND native_id>:after
                ORDER BY native_id LIMIT 9""",id=task.connection_id,after=task.cursor.get('after','')).scalars().all()
        checks=[]
        for native in ids[:8]:
            try:provider.authorize(native);checks.append((native,True))
            except SourceFailure as exc:
                if exc.code not in {'resource_missing','access_denied','outside_scope'}:raise
                checks.append((native,False))
        return [],checks,({'phase':'verify','after':ids[7]} if len(ids)>8 else {}),len(ids)<=8
    checkpoint=task.knowledge_checkpoint
    since=checkpoint.get('since') if checkpoint.get('generation')==task.generation else None
    collect=getattr(provider,'sync_page',None)
    records,cursor,done=collect(task.cursor,since) if collect else provider.page(task.cursor)
    if len(records)>25 or (not done and cursor==task.cursor):raise SourceFailure('incomplete_page')
    return records,[],({'phase':'verify'} if done else cursor),False


def process_one():
    with engine.begin() as conn:
        schedule_due(conn)
        if finish_indexing(conn):return True
        task,token=claim(conn)
    if not task:return False
    error=None
    try:
        records,checks,cursor,done=read_batch(task)
    except SourceFailure as exc:error=exc.code
    except Exception:error='source_unavailable'
    with engine.begin() as conn:
        current=sql(conn,"""SELECT c.mode,c.generation,c.removed_at,t.lease_until>now() AS leased FROM knowledge_sync_tasks t
            JOIN source_connections c ON c.id=t.connection_id WHERE t.run_id=:run AND t.connection_id=:source
            AND t.lease_token=:token FOR UPDATE OF t,c""",run=task.run_id,source=task.connection_id,token=token).mappings().first()
        if not current or not current.leased:return True
        if current.generation!=task.generation or current.removed_at or current.mode!='sync':error='connection_changed'
        values=dict(run=task.run_id,source=task.connection_id)
        if error:
            retry=task.attempts<2 and error in {'source_outage','source_timeout','rate_limited','source_unavailable','source_limit'}
            sql(conn,"""UPDATE knowledge_sync_tasks SET status=:status,error_code=:error,lease_token=NULL,lease_until=NULL,
                failed=failed+:failed,available_at=now()+interval '5 seconds' WHERE run_id=:run AND connection_id=:source""",
                **values,status='queued' if retry else 'indexing',error=error,failed=0 if retry else 1)
            if error!='connection_changed':
                sql(conn,"UPDATE source_connections SET health='unavailable',error_code=:error WHERE id=:source",source=task.connection_id,error=error)
                sql(conn,'UPDATE connected_resources SET access_until=NULL WHERE connection_id=:source',source=task.connection_id)
            event(conn,task.run_id,error,task.connection_id)
            return True
        connection=SimpleNamespace(id=task.connection_id,owner_id=task.owner_id,organization_id=task.organization_id,generation=task.generation)
        counts=dict(imported=0,updated=0,skipped=0,failed=0)
        for record in records:
            try:
                with conn.begin_nested():
                    action,version=connectors.retain(conn,connection,record)
                    if version:
                        sql(conn,"INSERT INTO knowledge_sync_items(run_id,connection_id,version_id) VALUES(:run,:source,:version) ON CONFLICT DO NOTHING",
                            **values,version=version)
                counts[action]+=1
            except SourceFailure as exc:
                counts['failed']+=1
                event(conn,task.run_id,exc.code,task.connection_id)
            except IntegrityError:
                counts['failed']+=1
                event(conn,task.run_id,'record_conflict',task.connection_id)
        for native,allowed in checks:
            sql(conn,"""UPDATE connected_resources SET revoked=:revoked,generation=:generation,
                access_until=CASE WHEN :revoked THEN NULL ELSE now()+interval '2 minutes' END
                WHERE connection_id=:source AND native_id=:native""",source=task.connection_id,native=native,revoked=not allowed,generation=task.generation)
        sql(conn,"""UPDATE knowledge_sync_tasks SET status=:status,cursor=CAST(:cursor AS jsonb),
            lease_token=NULL,lease_until=NULL,attempts=0,available_at=now(),
            error_code=CASE WHEN failed+:failed>0 THEN 'record_failed' ELSE NULL END,
            imported=imported+:imported,updated=updated+:updated,skipped=skipped+:skipped,failed=failed+:failed
            WHERE run_id=:run AND connection_id=:source""",**values,**counts,status='indexing' if done else 'queued',cursor=json.dumps(cursor))
        event(conn,task.run_id,'indexing' if done else 'page_processed',task.connection_id)
    return True


def install(app,Identity):
    path='/api/v1/knowledge-sync'

    @app.post(path+'/runs',status_code=202)
    def sync_all(viewer:Identity):return start(viewer)

    @app.get(path+'/runs')
    def runs(viewer:Identity):
        connectors.admin(viewer)
        with engine.connect() as conn:
            return [dict(r) for r in sql(conn,"""SELECT id,trigger,status,created_at,finished_at FROM knowledge_sync_runs
                WHERE organization_id=:org AND owner_id=:viewer ORDER BY created_at DESC,id LIMIT 30""",**viewer.access()).mappings()]

    @app.get(path+'/runs/{id}')
    def detail(id:UUID,viewer:Identity):
        connectors.admin(viewer)
        with engine.connect() as conn:
            run=sql(conn,'SELECT id,trigger,status,created_at,finished_at FROM knowledge_sync_runs WHERE id=:id AND organization_id=:org AND owner_id=:viewer',
                **viewer.access(),id=id).mappings().first()
            if not run:raise HTTPException(404,'Sync run not found.')
            sources=sql(conn,"""SELECT connection_id,source_name,status,imported,updated,skipped,failed,error_code
                FROM knowledge_sync_tasks WHERE run_id=:id ORDER BY source_name,connection_id""",id=id).mappings().all()
            return dict(**run,sources=[dict(r) for r in sources])

    @app.get(path+'/runs/{id}/events')
    def events(id:UUID,viewer:Identity,after:int=Query(0,ge=0)):
        detail(id,viewer)
        with engine.connect() as conn:
            return [dict(r) for r in sql(conn,"""SELECT id,connection_id,code,created_at FROM knowledge_sync_events
                WHERE run_id=:run AND id>:after ORDER BY id LIMIT 100""",run=id,after=after).mappings()]

    @app.get(path+'/schedule')
    def get_schedule(viewer:Identity):
        connectors.admin(viewer)
        with engine.connect() as conn:
            row=sql(conn,'SELECT enabled,time_of_day,timezone,next_run_at FROM knowledge_sync_schedules WHERE organization_id=:org AND owner_id=:viewer',
                **viewer.access()).mappings().first()
        return dict(row) if row else dict(enabled=False,time_of_day='02:00',timezone='Asia/Riyadh',next_run_at=None)

    @app.put(path+'/schedule')
    def put_schedule(body:Schedule,viewer:Identity):
        connectors.admin(viewer)
        try:next_run=next_slot(body.time_of_day,body.timezone)
        except (ValueError,ZoneInfoNotFoundError):raise HTTPException(422,'Enter a valid time and IANA timezone.') from None
        with engine.begin() as conn:
            sql(conn,"""INSERT INTO knowledge_sync_schedules(organization_id,owner_id,enabled,time_of_day,timezone,next_run_at)
                VALUES(:org,:viewer,:enabled,:clock,:zone,:next) ON CONFLICT(organization_id,owner_id) DO UPDATE
                SET enabled=excluded.enabled,time_of_day=excluded.time_of_day,timezone=excluded.timezone,next_run_at=excluded.next_run_at""",
                **viewer.access(),enabled=body.enabled,clock=body.time_of_day,zone=body.timezone,next=next_run if body.enabled else None)
        return get_schedule(viewer)
