"""Server-owned chat corpus boundary, independent of connector retention mode."""
from contextlib import contextmanager
from contextvars import ContextVar
import os
from fastapi import HTTPException
from app.db import sql

_scope=ContextVar('chat_source_scope',default=None)

def current():return (_scope.get() or {}).get('policy','combined')

@contextmanager
def scope(policy,selected=False):
    token=_scope.set(dict(policy=policy,selected=selected))
    try:yield
    finally:_scope.reset(token)

def knowledge_clause():
    value=_scope.get()
    if not value:return ''
    if value['policy']=='live':return ' AND FALSE'
    if value['selected']:return ''
    return ' AND v.dataset_id IS NULL'

def default(conn,viewer,documents=()):
    if os.getenv("LINKMIND_AUTO_CHAT")=="1":return "auto"
    if os.getenv('LINKMIND_AUTO_CHAT')=='1':return 'auto'
    if os.getenv('LINKMIND_AUTO_CHAT')=='1':return 'auto'
    if documents:return 'stored'
    real=sql(conn,"""SELECT 1 FROM source_connections WHERE organization_id=:org AND owner_id=:viewer
        AND removed_at IS NULL AND mode<>'disconnected' AND coalesce(config->>'execution','real')='real' LIMIT 1""",**viewer.access()).first()
    return 'live' if real else 'combined'

def compatible(policy,response,dependencies=()):
    if policy=='legacy':return False
    if policy=='live':
        return not dependencies and not response.get('source_matches') and all(p.get('live') for p in response.get('evidence',[])) and response.get('source_policy') in {None,'live'}
    if policy=='stored':return not response.get('live_dependencies') and not any(p.get('live') for p in response.get('evidence',[]))
    return True

def enforce(policy,response,dependencies=()):
    if not compatible(policy,response,dependencies):raise HTTPException(409,'The answer exceeded this conversation’s source scope. Start a new conversation with the sources you want.')
    response['source_policy']=policy
    return response

def demo_loading_allowed():
    return os.getenv('LINKMIND_ALLOW_DEMO_DATASETS')=='1' and os.getenv('LINKMIND_TEST_ENVIRONMENT')=='1' and os.getenv('AI_PROVIDER','mock')=='mock' and os.getenv('LINKMIND_CONNECTOR_NETWORK')!='1' and not os.getenv('BEDROCK_BUDGET_DATABASE_URL')

def require_demo_loading(conn):
    if not demo_loading_allowed() or sql(conn,"SELECT 1 FROM source_connections WHERE removed_at IS NULL AND coalesce(config->>'execution','real')='real' LIMIT 1").first():
        raise HTTPException(403,'Demo datasets can only be loaded in an explicitly enabled isolated mock environment.')


def annotate(conn,response):
    from uuid import UUID
    ids=[UUID(str(p['version_id'])) for p in response.get('evidence',[]) if p.get('version_id') and not p.get('live')]
    datasets={str(r.id):r.dataset_id for r in sql(conn,'SELECT id,dataset_id FROM document_versions WHERE id=ANY(:ids)',ids=ids).mappings()} if ids else {}
    for item in response.get('evidence',[]):
        item['origin']='live' if item.get('live') else 'stored'
        if not item.get('live'):
            item['dataset_id']=datasets.get(str(item.get('version_id')))
            item['synthetic']=bool(item['dataset_id'])
