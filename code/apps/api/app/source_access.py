"""Shared source access and revision predicates; aliases d/v refer to existing rows."""

ACCESS = """d.organization_id=:org AND d.deleted_at IS NULL AND (d.owner_id=:viewer OR d.visibility='team')
 AND NOT EXISTS(SELECT 1 FROM connected_resources cr JOIN source_connections sc ON sc.id=cr.connection_id
   WHERE cr.document_id=d.id AND (sc.organization_id<>:org OR sc.owner_id<>:viewer OR sc.mode<>'sync'
     OR cr.generation<>sc.generation OR cr.revoked OR cr.access_until IS NULL OR cr.access_until<=clock_timestamp()))"""
CURRENT = ACCESS + " AND d.current_version_id=v.id"
PASSAGES = """FROM chunks k JOIN document_versions v ON v.id=k.version_id
 JOIN documents d ON d.id=v.document_id"""
# Never-published uploads can be browsed, but never replace a valid current revision.
CATALOG_VERSION = """v.source_version_id IS NULL AND (v.id=d.current_version_id OR (d.current_version_id IS NULL AND
    v.id=(SELECT latest.id FROM document_versions latest WHERE latest.document_id=d.id
          AND latest.source_version_id IS NULL ORDER BY latest.created_at DESC,latest.id DESC LIMIT 1)))"""
