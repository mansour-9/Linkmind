"""Validate attachment references before exposing metadata, text or model context."""
from uuid import UUID
from fastapi import HTTPException
from app.db import sql
from app.retrieval import ACCESS


def accessible(conn, viewer, ids, ready=False):
    result=[]
    for id in dict.fromkeys(map(str, ids)):
        row=sql(conn, f"""SELECT d.id,d.filename,v.search_ready_at
            FROM documents d LEFT JOIN document_versions v ON v.id=d.current_version_id
            WHERE {ACCESS} AND d.id=:id""", **viewer.access(), id=UUID(id)).mappings().first()
        if row is None:
            raise HTTPException(404,'An attached document is no longer available. Remove it and try again.')
        if ready and not row.search_ready_at:
            raise HTTPException(409,dict(code='attachment_not_ready',message='An attached document is still being prepared or could not be read. Check Documents before sending.'))
        result.append(dict(document_id=str(row.id),filename=row.filename,search_ready=bool(row.search_ready_at)))
    return result
