"""Permission-checked reading of retained source records, independent of search passages."""

from fastapi import HTTPException

from app import connectors, content_domains as domains
from app.artifacts import resolve
from app.db import engine, sql
from app.graph_explorer import pattern
from app.source_access import ACCESS, CURRENT


RECORDS = """FROM documents d
    JOIN connected_resources r ON r.document_id=d.id
    JOIN source_connections c ON c.id=r.connection_id
    JOIN source_instances s ON s.id=c.id
    JOIN document_versions v ON v.document_id=d.id"""
SCOPE = """d.organization_id=:org AND c.organization_id=:org AND c.owner_id=:viewer
    AND c.mode='sync' AND c.removed_at IS NULL AND d.deleted_at IS NULL"""


def catalog(viewer, query, kind, offset, limit):
    if not domains.enabled():
        return dict(enabled=False, items=[], has_more=False)
    params = dict(**viewer.access(), query=pattern(query), kind=kind, offset=offset, limit=limit+1)
    with engine.connect() as conn:
        candidates = sql(conn, f"""SELECT d.id {RECORDS}
            WHERE {SCOPE}{domains.KNOWLEDGE} AND d.current_version_id=v.id
            AND (CAST(:kind AS text) IS NULL OR s.kind=:kind)
            AND (d.title ILIKE :query OR v.filename ILIKE :query OR r.native_id ILIKE :query)
            ORDER BY COALESCE(d.title,v.filename),d.id LIMIT :limit OFFSET :offset""", **params).scalars().all()
    ids = candidates[:limit]
    if not ids:
        return dict(enabled=True, items=[], has_more=False)
    connectors.refresh_access(viewer, ids, reuse_recent=True)
    with engine.connect() as conn:
        rows = sql(conn, f"""SELECT d.id, v.id AS version_id, COALESCE(d.title,v.filename) AS title, s.kind,
            s.name AS source_name, r.native_id, v.filename {RECORDS}
            WHERE {CURRENT} AND {SCOPE}{domains.KNOWLEDGE} AND d.id=ANY(:ids)
            ORDER BY COALESCE(d.title,v.filename),d.id""", **viewer.access(), ids=ids).mappings()
        return dict(enabled=True, items=[dict(row) for row in rows], has_more=len(candidates)>limit)


def read(viewer, document, version=None):
    connectors.refresh_access(viewer, [document])
    with engine.connect() as conn:
        selection = " AND v.id=:version" if version else " AND d.current_version_id=v.id" + domains.KNOWLEDGE
        row = sql(conn, f"""SELECT d.id, v.id AS version_id, v.filename, COALESCE(d.title,v.filename) AS title,
            s.kind,s.name AS source_name,r.native_id,v.artifact_key,
            (d.current_version_id=v.id AND revision.source_revision=r.source_revision) AS current,
            revision.original_url,revision.source_revision,revision.source_updated_at,
            CASE WHEN revision.source_revision=r.source_revision THEN r.observed_at ELSE revision.observed_at END AS synced_at,
            revision.fields,revision.payload,(c.config->>'execution'='mock') AS synthetic
            {RECORDS} JOIN connected_revisions revision ON revision.version_id=v.id
                AND revision.connection_id=r.connection_id AND revision.native_id=r.native_id
            WHERE {ACCESS} AND {SCOPE}{domains.SYNCED}{selection} AND d.id=:document
            ORDER BY (revision.source_revision=r.source_revision) DESC,revision.observed_at DESC,revision.id DESC LIMIT 1""",
            **viewer.access(), document=document, version=version).mappings().first()
        if not row:
            raise HTTPException(404, "Synchronized record not found or source access is unavailable.")
        relations = sql(conn, """SELECT DISTINCT a.canonical_id AS source_id,a.name AS source_name,a.kind AS source_kind,
            b.canonical_id AS target_id,b.name AS target_name,b.kind AS target_kind,r.predicate,r.chunk_id
            FROM live_relationships r JOIN live_entities a ON a.id=r.source_id JOIN live_entities b ON b.id=r.target_id
            WHERE r.version_id=:version ORDER BY r.predicate,a.name,b.name""", version=row.version_id).mappings().all() if row.current else []
        entity_id = sql(conn, """SELECT canonical_id FROM live_entities WHERE version_id=:version AND kind=:kind
            ORDER BY id LIMIT 1""", version=row.version_id, kind='task' if row.kind=='jira' else 'document').scalar() if row.current else None
    data = dict(row)
    payload = data.pop('payload')
    artifact = data.pop('artifact_key')
    fields = {item['field']: item['value'] for item in data.pop('fields')}
    data.update(body_format='text', relationships=[dict(relation) for relation in relations], entity_id=entity_id)
    if row.kind == 'jira' and 'description' in fields:
        data['body'] = fields.pop('description') or ''
        data['body_format'] = 'markdown' if isinstance(payload.get('fields', {}).get('description'), str) else 'text'
    elif row.kind == 'confluence':
        page = payload.get('data', payload)
        data['title'] = page.get('title') or data['title']
        body = page.get('body', {})
        html = body.get('storage', {}).get('value')
        if html is None and body.get('format') == 'html':
            html = body.get('value')
        if isinstance(html, str) and html.strip():
            data.update(body=html, body_format='html')
    if 'body' not in data:
        try:
            data['body'] = resolve(artifact).read_text(encoding='utf-8')
        except (OSError, UnicodeError, ValueError):
            raise HTTPException(503, "The retained source content is temporarily unavailable.") from None
        if row.kind == 'notion':
            # The snapshot export prepends the title, which the reader already displays.
            heading, separator, text = data['body'].partition('\n\n')
            if heading.startswith('# ') and separator:
                data.update(title=heading[2:], body=text)
            data['body_format'] = 'markdown'
    if row.kind == 'jira':
        data['issue_key'] = fields.pop('key', None)
        data['title'] = fields.pop('summary', None) or data['title']
    data['metadata'] = fields
    return data
