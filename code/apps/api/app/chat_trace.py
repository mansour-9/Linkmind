"""Request-scoped timings and truthful streaming activity, without source content."""
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass,field
from threading import Event,Lock

_active=ContextVar('chat_trace',default=None)

@dataclass
class Trace:
    emit:object=None
    cancelled:Event=field(default_factory=Event)
    started:float=field(default_factory=time.monotonic)
    stages:list=field(default_factory=list)
    counters:dict=field(default_factory=dict)
    events:list=field(default_factory=list)
    lock:Lock=field(default_factory=Lock)
    def activity(self,phase,**values):
        if self.emit:self.emit('activity',dict(phase=phase,**values))
    def count(self,key,amount=1):
        with self.lock:self.counters[key]=self.counters.get(key,0)+amount
    def summary(self):
        return dict(total_ms=round((time.monotonic()-self.started)*1000),stages=self.stages[-200:],counters=self.counters,events=self.events[-100:])

def event(kind,**metadata):
    """Callers supply identifiers/counts only, never credentials or source bodies."""
    trace=active()
    if trace:
        with trace.lock:trace.events.append(dict(kind=kind,at_ms=round((time.monotonic()-trace.started)*1000),**metadata))

def first_output(started,operation):
    trace=active()
    if trace:
        with trace.lock:
            trace.counters.setdefault('model_first_output_ms',round((time.monotonic()-trace.started)*1000))
        event('model_first_output',operation=operation,ms=round((time.monotonic()-started)*1000))

def active():return _active.get()

@contextmanager
def session(emit=None,cancelled=None):
    value=Trace(emit=emit,cancelled=cancelled or Event());token=_active.set(value)
    try:yield value
    finally:_active.reset(token)

@contextmanager
def stage(name):
    trace=active();started=time.monotonic()
    try:yield
    finally:
        if trace:
            with trace.lock:trace.stages.append(dict(stage=name,ms=round((time.monotonic()-started)*1000)))

def activity(phase,**values):
    trace=active()
    if trace:trace.activity(phase,**values)

def checkpoint():
    trace=active()
    if trace and trace.cancelled.is_set():
        from app.query_limits import QueryLimitReached
        raise QueryLimitReached('request_cancelled')
