"""Trusted corpus boundaries for the two repository surfaces."""
import os

from fastapi import HTTPException

MANUAL = " AND d.content_domain='manual_document'"
SYNCED = " AND d.content_domain='synced_knowledge'"
KNOWLEDGE = SYNCED + """ AND EXISTS (
    SELECT 1 FROM connected_resources kb_resource JOIN connected_revisions kb_revision
      ON kb_revision.connection_id=kb_resource.connection_id AND kb_revision.native_id=kb_resource.native_id
     AND kb_revision.source_revision=kb_resource.source_revision
    WHERE kb_resource.document_id=d.id AND kb_revision.version_id=v.id)"""
CHAT_DOCUMENTS = MANUAL + " AND lower(v.filename) ~ '[.](txt|pdf)$' AND v.dataset_id IS NULL"


def enabled():
    # The old corpus behavior is available only to the isolated legacy regression suite.
    return not (os.getenv('LINKMIND_TEST_ENVIRONMENT') == '1' and os.getenv('LINKMIND_LEGACY_CORPUS_TESTS') == '1'
        and os.getenv('AI_PROVIDER','mock') == 'mock' and os.getenv('LINKMIND_CONNECTOR_NETWORK') != '1'
        and not os.getenv('BEDROCK_BUDGET_DATABASE_URL'))


def manual():
    return MANUAL if enabled() else ''


def knowledge(*,current=True):
    return (KNOWLEDGE if current else SYNCED) if enabled() else ''


def require_admin(viewer):
    if enabled() and viewer.role != 'admin':
        raise HTTPException(403,'An administrator is required to manage content.')


def live_mcp(config):
    return config.get('transport')=='atlassian_mcp' or config.get('kind') in {'notion','custom_mcp'} or (
        config.get('execution') == 'mock' and os.getenv('LINKMIND_TEST_ENVIRONMENT') == '1'
        and os.getenv('LINKMIND_CONNECTOR_NETWORK') != '1')
