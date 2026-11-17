"""Bounded first-party read transports. Never follows credential-bearing redirects."""
import json
import os
import re
import time
import hashlib
from uuid import uuid4
from threading import RLock
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx
from app import chat_trace

_protocol_cache={}
_protocol_lock=RLock()


class SourceFailure(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass
class ReadLimits:
    max_calls: int = 40
    seconds: float = 35
    max_bytes: int = 20 * 1024 * 1024
    calls: int = 0
    received: int = 0
    started: float = field(default_factory=time.monotonic)
    mcp_sessions: dict = field(default_factory=dict, repr=False)
    lock: object = field(default_factory=RLock,repr=False)

    def check(self):
        if self.calls >= self.max_calls or time.monotonic() - self.started >= self.seconds:
            raise SourceFailure('source_limit')

    def reserve_call(self):
        with self.lock:
            self.check();self.calls+=1


_active = ContextVar('connector_read_limits', default=None)


def active(): return _active.get()


@contextmanager
def request_limits(seconds=35):
    token = _active.set(ReadLimits(seconds=seconds))
    try: yield
    finally: _active.reset(token)


def authorization(reference, host=None):
    if reference.startswith('RF4_OAUTH_'):
        from app.connection_oauth import token_authorization
        return token_authorization(reference,host)
    if not re.fullmatch(r'RF4_[A-Z0-9_]{1,100}', reference):
        raise SourceFailure('credential_reference_invalid')
    raw = os.getenv(reference)
    if not raw:
        raise SourceFailure('credentials_missing')
    try:
        secret=json.loads(raw)
        if host and host not in {'graph.microsoft.com','mcp.atlassian.com'} and not host.endswith('.atlassian.net') and secret.get('audience_host')!=host:
            raise SourceFailure('credential_audience_mismatch')
        value = secret['authorization']
        if not isinstance(value, str) or not value.startswith(('Bearer ', 'Basic ')) or '\n' in value or '\r' in value:
            raise ValueError()
        return value
    except (KeyError, ValueError, TypeError):
        raise SourceFailure('credentials_invalid') from None


def safe_url(url, host, prefix='/'):
    value = urlsplit(url)
    if (value.scheme != 'https' or value.hostname != host or value.port not in (None, 443)
            or value.username or value.password or value.fragment or not (value.path or '/').startswith(prefix)
            or any(part in value.path.lower() for part in ('%2f', '%5c', '..', '\\'))):
        raise SourceFailure('unsafe_source_url')
    return url


class ReadClient:
    def __init__(self, reference, host, limits=None):
        self.reference, self.host = reference, host
        self.limits = limits or active() or ReadLimits()

    def request(self, method, url, *, params=None, body=None, headers=None, raw=False, authenticated=True):
        started=time.monotonic();error=None;attempts=0
        try:
            # Only idempotent source reads retry, once, inside the same byte/call/
            # deadline guard. Never retry model calls, authorization failures or
            # generic MCP execution. Tool calls reaching this transport are allowlisted.
            retryable=method=='GET' or (body or {}).get('method')=='tools/call'
            for attempt in range(2 if retryable else 1):
                attempts+=1
                try:
                    with chat_trace.stage('source.'+str((body or {}).get('method',method))):
                        return self._request(method,url,params=params,body=body,headers=headers,raw=raw,authenticated=authenticated)
                except SourceFailure as exc:
                    if exc.code not in {'source_outage','source_timeout'} or attempt or self.limits.seconds-(time.monotonic()-self.limits.started)<2:raise
                    chat_trace.event('source_retry',code=exc.code,attempt=attempt+1)
        except SourceFailure as exc:
            error=exc.code
            raise
        finally:
            rpc=body or {};tool=rpc.get('params',{}).get('name') if rpc.get('method')=='tools/call' else None
            chat_trace.event('source_call',tool=tool,method=rpc.get('method',method),
                ms=round((time.monotonic()-started)*1000),error=error,retries=max(0,attempts-1))
            trace=chat_trace.active()
            if trace:
                trace.count('source_calls',attempts)
                rpc=body or {}
                if rpc.get('method')=='tools/call':
                    name=rpc.get('params',{}).get('name','unknown')
                    if re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,80}',name):trace.count('mcp.'+name,attempts)

    def _request(self, method, url, *, params=None, body=None, headers=None, raw=False, authenticated=True):
        if os.getenv('LINKMIND_CONNECTOR_NETWORK') != '1':
            raise SourceFailure('network_not_enabled')
        self.limits.reserve_call()
        safe_url(url, self.host)
        values = {'Accept': 'application/json', **(headers or {})}
        if self.host not in {'graph.microsoft.com','mcp.atlassian.com'} and not self.host.endswith(('.atlassian.net','.sharepoint.com')):
            import socket,ipaddress
            try:
                addresses=socket.getaddrinfo(self.host,443,type=socket.SOCK_STREAM)
                if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses): raise SourceFailure('unsafe_source_url')
            except OSError: raise SourceFailure('source_outage') from None
        if authenticated: values['Authorization'] = authorization(self.reference,self.host)
        remaining = self.limits.seconds - (time.monotonic() - self.limits.started)
        try:
            with httpx.Client(timeout=min(10, max(.1, remaining)), follow_redirects=False, trust_env=False) as client:
                with client.stream(method, url, params=params, json=body, headers=values) as response:
                    code = response.status_code
                    if code in (401, 403): raise SourceFailure('access_denied' if code == 403 else 'authentication_expired')
                    if code == 404: raise SourceFailure('resource_missing')
                    if code == 429: raise SourceFailure('rate_limited')
                    if code == 410: raise SourceFailure('checkpoint_expired')
                    if code >= 500: raise SourceFailure('source_outage')
                    if not 200 <= code < 300: raise SourceFailure('source_response_rejected')
                    chunks = []
                    for chunk in response.iter_bytes():
                        with self.limits.lock:
                            self.limits.received += len(chunk)
                            if self.limits.received > self.limits.max_bytes: raise SourceFailure('source_size_limit')
                        if time.monotonic() - self.limits.started > self.limits.seconds: raise SourceFailure('source_limit')
                        chunks.append(chunk)
                    data = b''.join(chunks)
                    if raw: return data
                    if response.headers.get('content-type', '').startswith('text/event-stream'):
                        messages = [json.loads(line[5:].strip()) for line in data.decode().splitlines() if line.startswith('data:')]
                        messages = [m for m in messages if m.get('id') == (body or {}).get('id')]
                        if len(messages) != 1: raise SourceFailure('malformed_source')
                        return messages[0], dict(response.headers)
                    return (json.loads(data) if data else {}), dict(response.headers)
        except SourceFailure:
            raise
        except httpx.TimeoutException:
            raise SourceFailure('source_timeout') from None
        except (httpx.HTTPError, UnicodeError, ValueError, KeyError, TypeError):
            raise SourceFailure('source_outage') from None

    def get(self, url, params=None):
        data, _ = self.request('GET', url, params=params)
        if not isinstance(data, dict): raise SourceFailure('malformed_source')
        return data


class AtlassianMCP:
    """Explicit read-tool allowlist over negotiated Streamable HTTP; no model-selected writes."""
    endpoint = 'https://mcp.atlassian.com/v2/mcp'
    allowed = {'getJiraIssue', 'searchJiraIssuesUsingJql', 'getConfluencePage', 'searchConfluenceUsingCql',
               'getConfluenceContent', 'searchConfluence'}

    def __init__(self, reference, limits=None, *, endpoint=None, allowed=None, require_read_hint=False):
        if endpoint: self.endpoint=endpoint
        if allowed is not None:self.allowed=set(allowed)
        self.client = ReadClient(reference, urlsplit(self.endpoint).hostname, limits)
        self.headers = {'Accept': 'application/json, text/event-stream'}
        self.sequence = 0
        enabled=os.getenv('LINKMIND_MCP_DISCOVERY_CACHE')=='1'
        if enabled:
            secret=authorization(reference,urlsplit(self.endpoint).hostname)
            cache_key=(self.endpoint,hashlib.sha256(secret.encode()).hexdigest(),tuple(sorted(self.allowed)),require_read_hint)
            with _protocol_lock:
                cached=_protocol_cache.get(cache_key)
                if cached and cached[0]>time.monotonic():
                    self.headers.update(cached[1]);self.tools=cached[2]
                    trace=chat_trace.active()
                    if trace:trace.count('protocol_cache_hits')
                    return
                self._negotiate(require_read_hint)
                if len(_protocol_cache)>=32:_protocol_cache.clear()
                _protocol_cache[cache_key]=(time.monotonic()+120,dict(self.headers),dict(self.tools))
                return
        self._negotiate(require_read_hint)

    def _negotiate(self,require_read_hint):
        result, headers = self.rpc('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {},
            'clientInfo': {'name': 'Linkmind-readonly', 'version': '1'}})
        protocol = result.get('protocolVersion')
        if protocol not in {'2025-03-26', '2025-06-18', '2025-11-25'}:
            raise SourceFailure('mcp_protocol_unsupported')
        self.headers['MCP-Protocol-Version'] = protocol
        if headers.get('mcp-session-id'): self.headers['Mcp-Session-Id'] = headers['mcp-session-id']
        self.client.request('POST', self.endpoint, body={'jsonrpc': '2.0', 'method': 'notifications/initialized'}, headers=self.headers)
        self.tools = {}
        cursor = None
        for _ in range(5):
            page, _ = self.rpc('tools/list', {'cursor': cursor} if cursor else {})
            for tool in page.get('tools', []):
                if tool.get('name') in self.allowed and (not require_read_hint or tool.get('annotations',{}).get('readOnlyHint') is True):
                    self.tools[tool['name']] = tool.get('inputSchema', {})
            cursor = page.get('nextCursor')
            if not cursor: break
        if cursor: raise SourceFailure('mcp_discovery_limit')

    def rpc(self, method, params):
        self.sequence += 1
        request_id='linkmind-'+uuid4().hex if os.getenv('LINKMIND_MCP_DISCOVERY_CACHE')=='1' else self.sequence
        data, headers = self.client.request('POST', self.endpoint,
            body={'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params}, headers=self.headers)
        if data.get('id') != request_id or 'error' in data or 'result' not in data:
            raise SourceFailure('mcp_request_rejected')
        return data['result'], headers

    def call(self, tool, arguments):
        if tool not in self.allowed or tool not in self.tools: raise SourceFailure('mcp_tool_unavailable')
        schema = self.tools[tool]
        if set(schema.get('required', [])) - arguments.keys(): raise SourceFailure('mcp_schema_changed')
        if schema.get('additionalProperties') is False and arguments.keys() - schema.get('properties', {}).keys():
            raise SourceFailure('mcp_schema_changed')
        result, _ = self.rpc('tools/call', {'name': tool, 'arguments': arguments})
        if result.get('isError'):
            chat_trace.event('source_tool_error',tool=tool,code='mcp_tool_failed')
            raise SourceFailure('mcp_tool_failed')
        value = result.get('structuredContent')
        if value is None:
            try: value = json.loads(''.join(c.get('text', '') for c in result.get('content', []) if c.get('type') == 'text'))
            except (ValueError, TypeError): raise SourceFailure('malformed_source') from None
        if not isinstance(value, dict): raise SourceFailure('malformed_source')
        return value
