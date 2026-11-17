"""Explicit tenant content purge; never removes accounts, connections or spend records."""
import argparse
import hashlib
import json
from pathlib import Path
from uuid import UUID,uuid4
from app.db import engine,sql

CONTENT_TABLES=('review_actions','conflicts','claim_evidence','relationship_evidence','entity_evidence',
    'entity_resolution_reviews','resolution_candidates','entity_aliases','entity_identifiers','canonical_redirects',
    'relationships','claims','entities','processing_attempts','processing_jobs','chunks','connected_revisions',
    'connected_resources','document_versions','documents','canonical_entities','repository_groups')


def inventory(conn,org):
    existing=set(sql(conn,"SELECT tablename FROM pg_tables WHERE schemaname='public'").scalars())
    counts={table:sql(conn,f'SELECT count(*) FROM {table} WHERE organization_id=:org',org=org).scalar()
        for table in CONTENT_TABLES if table in existing and table not in {'connected_resources','connected_revisions'}}
    return dict(counts=counts,connections=sql(conn,"SELECT md5(string_agg(id::text||config::text||mode||generation::text||auth_state,',' ORDER BY id)) FROM source_connections").scalar(),
        other_organizations=[dict(r) for r in sql(conn,'SELECT organization_id,count(*) AS documents FROM documents WHERE organization_id<>:org GROUP BY organization_id ORDER BY organization_id',org=org).mappings()],
        usage=sql(conn,"SELECT md5(string_agg(id::text||operation||coalesce(estimated_cost::text,'')||status,',' ORDER BY id)) FROM ai_usage").scalar(),
        active_chats=sql(conn,'SELECT count(*) FROM conversations WHERE organization_id=:org AND archived_at IS NULL',org=org).scalar())


def purge(conn,org):
    before=inventory(conn,org)
    sql(conn,'UPDATE conversations SET archived_at=coalesce(archived_at,now()) WHERE organization_id=:org',org=org)
    sql(conn,'UPDATE ai_usage SET version_id=NULL,processing_attempt_id=NULL WHERE organization_id=:org',org=org)
    sql(conn,'UPDATE documents SET current_version_id=NULL WHERE organization_id=:org',org=org)
    sql(conn,'UPDATE document_versions SET active_enrichment_version_id=NULL WHERE organization_id=:org',org=org)
    for table in CONTENT_TABLES:
        if table=='connected_revisions':
            sql(conn,'DELETE FROM connected_revisions WHERE version_id IN (SELECT id FROM document_versions WHERE organization_id=:org)',org=org)
        elif table=='connected_resources':
            sql(conn,'DELETE FROM connected_resources WHERE document_id IN (SELECT id FROM documents WHERE organization_id=:org)',org=org)
        else:sql(conn,f'DELETE FROM {table} WHERE organization_id=:org',org=org)
    after=inventory(conn,org)
    assert not any(after['counts'].values()) and after['active_chats']==0
    assert all(before[key]==after[key] for key in ('connections','other_organizations','usage'))
    sql(conn,"INSERT INTO audit_events(id,organization_id,action,resource_id) VALUES(:id,:org,'workspace_content_reset',:org)",id=uuid4(),org=org)
    return dict(before=before,after=after)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--organization',type=UUID,required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--expected-documents',type=int)
    args=parser.parse_args()
    with engine.begin() as conn:
        current=inventory(conn,args.organization)
        if args.apply:
            if args.expected_documents is None or args.expected_documents!=current['counts']['documents']:
                raise RuntimeError('Content changed or expected count was not supplied; no cleanup performed.')
            result=purge(conn,args.organization)
        else:result=current
    print(json.dumps(result,default=str))


if __name__=='__main__':main()
