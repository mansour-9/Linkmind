"""Bounded ordinary Python coordination; real adapters remain a separate RF4 gate."""
from dataclasses import dataclass
from typing import Callable

from app import retrieval
from app.query_language import historical_question, operational_question, normalize
from app.query_limits import active, QueryLimits
from app.source_evidence import SourceEvidence
from uuid import UUID


@dataclass(frozen=True)
class SourceAdapter:
    """An already authorized/registered capability, not a model-invented tool."""
    id: str
    mode: str
    keys: tuple[str, ...]
    fetch: Callable


def choose_adapters(question, adapters, selected=()):
    """Offline-testable source policy; production registers only delivered capabilities."""
    text = normalize(question)
    eligible = [a for a in adapters if (not selected or a.id in selected)]
    relevant_live = [a for a in eligible if a.mode == 'live' and any(normalize(k) in text for k in a.keys)]
    history = [a for a in eligible if a.mode == 'history']
    stored = [a for a in eligible if a.mode == 'stored']
    if historical_question(question) and history:
        return history[:1]
    if operational_question(question) and relevant_live:
        # The second candidate is a bounded fallback, not unconditional fan-out.
        return relevant_live[:1] + stored[:1]
    return stored[:1]


def retrieve_adapters(question, adapters, authorize, organization_id, selected=(), limits=None):
    """Contract harness for fake/live adapters; not an application connector endpoint."""
    limits = limits or active() or QueryLimits()
    result = []
    for adapter in choose_adapters(question, adapters, selected):
        limits.retrieve()
        authorize(adapter.id)
        items=[]
        characters=0
        for raw in adapter.fetch(question):
            item=SourceEvidence.model_validate(raw)
            characters+=len(item.model_dump_json())
            if len(items)>=limits.max_passages or characters>limits.max_context_characters:
                raise ValueError('Adapter evidence exceeded its context bound.')
            if item.origin!=('live' if adapter.mode=='live' else 'stored'):
                raise ValueError('Adapter observation mode did not match its registered capability.')
            items.append(item)
        if any(item.identity.organization_id!=UUID(str(organization_id)) or str(item.identity.source_instance_id)!=adapter.id for item in items):
            raise ValueError('Adapter evidence did not match the authorized source identity.')
        authorize(adapter.id)
        result.extend(items)
        if items:
            break
    return result


class QuestionRetriever:
    def __init__(self, viewer, search):
        self.viewer = viewer
        self.index = search
        self.limits = active() or QueryLimits()

    def search(self, question, document_ids=None, diagnostics=None, neighbors=True):
        self.limits.retrieve()
        diagnostics = diagnostics if diagnostics is not None else {}
        items = self.index(self.viewer, question, document_ids, diagnostics=diagnostics)
        self.limits.observed('indexed_search', items, semantic_status=diagnostics.get('semantic_status'))
        if items and neighbors and self.limits.retrievals < self.limits.max_retrievals:
            self.limits.retrieve()
            adjacent = retrieval.adjacent_context(self.viewer, items)
            self.limits.observed('adjacent_passages', adjacent)
            items = items + adjacent
        return self.limits.context(items)

    def context(self, document_ids, question=None):
        self.limits.retrieve()
        items, coverage = retrieval.selected_context(self.viewer, document_ids, question=question,
            limit=self.limits.max_passages, max_characters=self.limits.max_context_characters)
        if question:
            coverage['mode']='selected_source_context'
        self.limits.observed('selected_source_context', items)
        return items, coverage

    def history(self, document_ids, question):
        self.limits.retrieve()
        items, coverage, dependencies = retrieval.historical_context(self.viewer, document_ids,
            question=question, limit=self.limits.max_passages, max_characters=self.limits.max_context_characters)
        self.limits.observed('retained_revision_context', items, mode='history')
        return items, coverage, dependencies
