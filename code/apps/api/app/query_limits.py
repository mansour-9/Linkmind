"""Per-question limits, separate from the persistent shared dollar allowance."""
import json
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


class QueryLimitReached(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass
class QueryLimits:
    seconds: float = 90
    max_retrievals: int = 3
    max_model_calls: int = 7
    max_planner_calls: int = 1
    max_passages: int = 24
    max_context_characters: int = 22000
    max_request_bytes: int = 180000
    started: float = field(default_factory=time.monotonic)
    retrievals: int = 0
    model_calls: int = 0
    planner_calls: int = 0
    activity: list = field(default_factory=list)
    dependency_ids: set = field(default_factory=set)

    def remaining(self):
        return self.seconds - (time.monotonic() - self.started)

    def checkpoint(self, required_seconds=0):
        if self.remaining() <= required_seconds:
            raise QueryLimitReached('time_limit')

    def model(self, operation, request):
        self.checkpoint(6)
        if self.model_calls >= self.max_model_calls:
            raise QueryLimitReached('model_call_limit')
        if len(json.dumps(request, ensure_ascii=False, default=str).encode()) > self.max_request_bytes:
            raise QueryLimitReached('request_size_limit')
        if operation == 'query_understanding':
            if self.planner_calls >= self.max_planner_calls:
                raise QueryLimitReached('planning_limit')
            self.planner_calls += 1
        self.model_calls += 1

    def retrieve(self):
        self.checkpoint()
        if self.retrievals >= self.max_retrievals:
            raise QueryLimitReached('retrieval_limit')
        self.retrievals += 1

    def observed(self, operation, passages, *, mode='stored', semantic_status=None):
        self.checkpoint()
        self.dependency_ids.update(str(p['id']) for p in passages)
        self.activity.append(dict(operation=operation, mode=mode, returned_passages=len(passages),
            source_count=len({str(p['document_id']) for p in passages}), semantic_status=semantic_status))

    def context(self, passages):
        """Keep whole immutable passages, fairly across sources; never truncate quotations."""
        groups = {}
        for passage in passages:
            if str(passage['id']) not in {str(p['id']) for g in groups.values() for p in g}:
                groups.setdefault(str(passage['document_id']), []).append(passage)
        result, size = [], 0
        for position in range(max((len(g) for g in groups.values()), default=0)):
            for items in groups.values():
                if position < len(items):
                    item = items[position]
                    if len(result) < self.max_passages and size + len(item['text']) <= self.max_context_characters:
                        result.append(item)
                        size += len(item['text'])
        return result


_active = ContextVar('linkmind_query_limits', default=None)


def active():
    return _active.get()


@contextmanager
def question_limits(limits=None):
    limits = limits or QueryLimits()
    token = _active.set(limits)
    try:
        yield limits
    finally:
        _active.reset(token)
