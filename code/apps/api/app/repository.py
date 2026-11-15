"""Small source catalog and resource metadata, independent of extracted facts."""
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.db import sql
from app.source_access import ACCESS, CATALOG_VERSION


class ResourceFilters(BaseModel):
    source_instance_id: UUID | None = None
    format: Literal['pdf', 'docx', 'txt', 'md'] | None = None
    project_id: UUID | None = None
    team_id: UUID | None = None
    after: date | None = None
    before: date | None = None

    @model_validator(mode='after')
    def date_order(self):
        if self.after and self.before and self.after > self.before:
            raise ValueError('Uploaded after must not be later than uploaded before.')
        return self


class MetadataChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(ge=0)
    title: str | None = Field(default=None, max_length=240)
    project_id: UUID | None = None
    team_id: UUID | None = None

    @field_validator('title')
    @classmethod
    def clean_title(cls, value):
        return value.strip() or None if value is not None else None


class GroupCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['project', 'team']
    name: str = Field(min_length=1, max_length=120)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError('Enter a name.')
        return value.strip()


FORMAT = "lower(regexp_replace(v.filename,'^.*[.]',''))"
JOINS = """FROM documents d JOIN document_versions v ON v.document_id=d.id
    JOIN source_instances s ON s.id=d.source_instance_id AND s.organization_id=d.organization_id
    LEFT JOIN repository_groups pg ON pg.id=d.project_id AND pg.organization_id=d.organization_id
    LEFT JOIN repository_groups tg ON tg.id=d.team_id AND tg.organization_id=d.organization_id"""
FIELDS = f"""d.id AS document_id,v.id AS version_id,v.filename,coalesce(d.title,v.filename) AS title,
    d.title AS custom_title,d.visibility,v.created_at AS uploaded_at,v.search_ready_at,v.embedding_status,
    d.source_instance_id,d.native_id,s.name AS source_name,s.kind AS source_type,{FORMAT} AS format,
    d.project_id,pg.name AS project_name,d.team_id,tg.name AS team_name,d.metadata_revision,
    d.metadata_updated_at,d.metadata_updated_by,((d.owner_id=:viewer OR :admin)
      AND NOT EXISTS(SELECT 1 FROM connected_resources cr WHERE cr.document_id=d.id)) AS can_manage"""


def filter_clause(filters, params):
    """Only supported source metadata; this predicate is shared by all retrieval paths."""
    parts = []
    for key in ('source_instance_id', 'project_id', 'team_id'):
        if filters.get(key):
            parts.append(f'd.{key}=:{key}')
            params[key] = filters[key]
    if filters.get('format'):
        parts.append(FORMAT + '=:resource_format')
        params['resource_format'] = filters['format']
    for key, predicate in (('after', 'v.created_at>=CAST(:after AS date)'),
                           ('before', "v.created_at<CAST(:before AS date)+interval '1 day'")):
        if filters.get(key):
            parts.append(predicate)
            params[key] = filters[key]
    return ''.join(' AND ' + part for part in parts)


def resources(conn, viewer, *, query='', filters=None, limit=20, offset=0):
    params = {**viewer.access(), 'admin': viewer.role == 'admin', 'limit': limit, 'offset': offset}
    where = ACCESS + ' AND ' + CATALOG_VERSION + filter_clause(filters or {}, params)
    if query.strip():
        params['pattern'] = '%' + query.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        params['query'] = query.strip()
        where += """ AND (coalesce(d.title,v.filename) ILIKE :pattern OR v.filename ILIKE :pattern
            OR pg.name ILIKE :pattern OR tg.name ILIKE :pattern
            OR EXISTS(SELECT 1 FROM chunks k WHERE k.version_id=v.id AND
                (k.search_text@@websearch_to_tsquery('english',:query) OR k.text ILIKE :pattern)))"""
    total = sql(conn, f'SELECT count(*) {JOINS} WHERE {where}', **params).scalar_one()
    items = [dict(r) for r in sql(conn, f"""SELECT {FIELDS} {JOINS} WHERE {where}
        ORDER BY v.created_at DESC,d.id LIMIT :limit OFFSET :offset""", **params).mappings()]
    return dict(items=items, total=total, limit=limit, offset=offset, has_more=offset + len(items) < total)


GROUP_ACCESS = f"""g.organization_id=:org AND (g.created_by=:viewer OR EXISTS(
    SELECT 1 FROM documents d WHERE {ACCESS} AND (d.project_id=g.id OR d.team_id=g.id)))"""


def groups(conn, viewer, *, kind=None, query='', limit=100, offset=0):
    params = {**viewer.access(), 'limit': limit, 'offset': offset}
    where = GROUP_ACCESS
    if kind:
        where += ' AND g.kind=:group_kind'
        params['group_kind'] = kind
    if query.strip():
        where += ' AND g.name ILIKE :pattern'
        params['pattern'] = '%' + query.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
    return [dict(r) for r in sql(conn, f"""SELECT g.id,g.kind,g.name,u.name AS created_by_name,
        (SELECT count(*) FROM documents d WHERE {ACCESS} AND (d.project_id=g.id OR d.team_id=g.id)) AS resource_count
        FROM repository_groups g JOIN users u ON u.id=g.created_by AND u.organization_id=g.organization_id
        WHERE {where} ORDER BY g.name,g.created_at,g.id LIMIT :limit OFFSET :offset""", **params).mappings()]


def source_catalog(conn, viewer):
    # Only sources with visible retained documents. No connector registry/credentials.
    rows = sql(conn, f"""SELECT s.id,s.name,s.kind,count(*) AS resource_count,
        count(*) FILTER(WHERE v.search_ready_at IS NOT NULL) AS searchable_count,
        max(v.created_at) AS last_received_at,max(v.search_ready_at) AS last_indexed_at
        {JOINS} WHERE {ACCESS} AND {CATALOG_VERSION}
        GROUP BY s.id,s.name,s.kind ORDER BY s.name,s.id""", **viewer.access()).mappings()
    result=[dict(**r, scope='Accessible uploaded documents' if r.kind=='upload' else 'Authorized retained source records', mode='stored',
                 capabilities=dict(indexed_search=True, live=False, history=True,
                                   operations=['browse', 'search', 'fetch_evidence', 'download', 'revisions']),
                 health='local', last_successful_sync_at=None) for r in rows]
    for item in result:
        if item['kind']=='upload':continue
        connection=sql(conn,'''SELECT mode,health,last_successful_sync_at,config FROM source_connections
            WHERE id=:id AND organization_id=:org AND owner_id=:viewer AND removed_at IS NULL''',
            **viewer.access(),id=item['id']).mappings().first()
        if connection:
            item.update(mode=connection.mode,health=connection.health,last_successful_sync_at=connection.last_successful_sync_at,
                synthetic=connection.config.get('execution')=='mock')
            item['capabilities'].update(live=True,sync=True)
    return result


def versions(conn, viewer, document, *, limit=20, offset=0):
    rows = [dict(r) for r in sql(conn, f"""SELECT v.id AS version_id,v.filename,v.created_at AS uploaded_at,
        v.search_ready_at,v.embedding_status,(d.current_version_id=v.id) AS current,
        v.byte_count,(SELECT k.id FROM chunks k WHERE k.version_id=v.id ORDER BY k.line_number,k.id LIMIT 1) AS first_passage_id
        FROM document_versions v JOIN documents d ON d.id=v.document_id
        WHERE {ACCESS} AND d.id=:document AND v.source_version_id IS NULL
        ORDER BY v.created_at DESC,v.id DESC LIMIT :limit OFFSET :offset""", **viewer.access(), document=document,limit=limit+1,offset=offset).mappings()]
    return dict(items=rows[:limit],has_more=len(rows)>limit,limit=limit,offset=offset)


def project_scope(conn, viewer, question):
    """Route only deliberate, unambiguous project associations; never merge labels."""
    projects=sql(conn,f"""SELECT g.id FROM repository_groups g WHERE {GROUP_ACCESS}
        AND g.kind='project' AND length(g.name)>=3 AND position(lower(g.name) in lower(:question))>0
        ORDER BY length(g.name) DESC,g.id LIMIT 2""",**viewer.access(),question=question).scalars().all()
    if len(projects)!=1:
        return dict(ambiguous=len(projects)>1,document_ids=None)
    documents=sql(conn,f"""SELECT d.id FROM documents d JOIN document_versions v ON v.id=d.current_version_id
        WHERE {ACCESS} AND d.project_id=:project ORDER BY v.created_at DESC,d.id LIMIT 31""",
        **viewer.access(),project=projects[0]).scalars().all()
    # A larger collection needs deliberate bounded selection rather than a silent subset.
    return dict(ambiguous=len(documents)>30,document_ids=documents if len(documents)<=30 else None)
