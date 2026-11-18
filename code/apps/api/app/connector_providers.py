"""Source-specific, read-only native adapters and optional Atlassian MCP reads."""
import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Literal
from urllib.parse import parse_qs, quote, urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.connector_transport import ReadClient, ReadLimits, SourceFailure, AtlassianMCP, safe_url, active


NOTION_HOSTS = {'app.notion.com','www.notion.com','notion.com','www.notion.so','notion.so'}


def notion_page_id(url):
    parsed=urlsplit(url)
    host=parsed.hostname or ''
    if host not in NOTION_HOSTS and not host.endswith('.notion.site'):
        raise ValueError('Use a Notion page link.')
    try:safe_url(url,host)
    except SourceFailure:raise ValueError('Use a valid HTTPS Notion page link.') from None
    match=re.search(r'([a-f0-9]{32}|[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})/?$',parsed.path,re.I)
    if not match:raise ValueError('The Notion page link must include a page ID.')
    return UUID(match[1]).hex


class NotionPage(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1,max_length=240)
    url: str = Field(min_length=1,max_length=1000)


class ConnectionSpec(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['jira', 'confluence', 'onedrive', 'sharepoint', 'notion', 'custom_mcp']
    execution: Literal['mock','real'] = 'real'
    name: str = Field(min_length=1, max_length=120)
    site_url: str = ''
    scope_id: str = Field(min_length=1, max_length=150, pattern=r'^[A-Za-z0-9!_,.-]+$')
    drive_id: str = Field(default='', max_length=200, pattern=r'^[A-Za-z0-9!_,.-]*$')
    cloud_id: str = Field(default='', max_length=100, pattern=r'^[A-Za-z0-9-]*$')
    space_key: str = Field(default='',max_length=150,pattern=r'^[A-Za-z0-9_-]*$')
    transport: Literal['native', 'atlassian_mcp'] = 'native'
    auth_method: Literal['server','oauth'] = 'server'
    credential_ref: str = Field(default='RF4_UNCONFIGURED',pattern=r'^RF4_[A-Z0-9_]{1,100}$')
    mcp_credential_ref: str | None = Field(default=None, pattern=r'^RF4_[A-Z0-9_]{1,100}$')
    mcp_url: str = ''
    read_tool: str = Field(default='fetch_resource',pattern=r'^[A-Za-z][A-Za-z0-9_]{0,80}$')
    notion_pages: list[NotionPage] = Field(default_factory=list,max_length=6)

    @model_validator(mode='after')
    def valid(self):
        if any(ref and ref.startswith('RF4_OAUTH_') for ref in (self.credential_ref,self.mcp_credential_ref)):
            raise ValueError('OAuth credential bindings are generated on the server, not accepted in source configuration.')
        self.name=self.name.strip()
        if not self.name:raise ValueError('Enter a connection name.')
        for url in (self.site_url,self.mcp_url):
            if url:
                parsed=urlsplit(url)
                if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                    raise ValueError('Use an HTTPS source URL without credentials, query strings or fragments.')
        if self.execution=='mock':
            # Fixed labelled fixtures are the only synthetic content; URLs are optional
            # in demo setup and are never contacted.
            if self.site_url and not self.site_url.startswith('https://'): raise ValueError('Use HTTPS for a source URL.')
            return self
        if self.kind=='notion':
            if self.auth_method!='oauth' or self.transport!='native':
                raise ValueError('Notion uses secure sign-in to the official MCP service.')
            if not self.notion_pages:raise ValueError('Add at least one Notion handbook page.')
            ids=[notion_page_id(page.url) for page in self.notion_pages]
            if len(set(ids))!=len(ids):raise ValueError('Enter each Notion page only once.')
            if any(not page.title.strip() for page in self.notion_pages):
                raise ValueError('Enter a title for each Notion page.')
            self.scope_id=ids[0]
            return self
        if self.kind=='custom_mcp':
            if self.auth_method=='oauth':raise ValueError('Custom MCP uses its explicit server-managed authentication contract.')
            host=urlsplit(self.mcp_url).hostname or ''
            if not host or host in {'localhost','localhost.localdomain'} or not re.search(r'[A-Za-z]',host):
                raise ValueError('Use a public HTTPS MCP endpoint.')
            try: safe_url(self.mcp_url,host)
            except SourceFailure: raise ValueError('Use a valid HTTPS MCP endpoint.') from None
            return self
        if self.kind in {'jira', 'confluence'}:
            parsed = urlsplit(self.site_url)
            if not parsed.hostname or not re.fullmatch(r'[a-z0-9-]+\.atlassian\.net', parsed.hostname):
                raise ValueError('Use the exact HTTPS Atlassian Cloud site URL.')
            try: safe_url(self.site_url, parsed.hostname)
            except SourceFailure: raise ValueError('Use an HTTPS site origin without credentials.') from None
            if parsed.path not in ('', '/') or parsed.query: raise ValueError('Use a site origin, without a path or query.')
            if self.kind == 'jira' and not (self.auth_method=='oauth' and self.scope_id=='pending-scope') and not re.fullmatch(r'[A-Z][A-Z0-9_]{1,30}', self.scope_id):
                raise ValueError('Use one Jira project key.')
            if self.transport == 'atlassian_mcp' and (not self.cloud_id or not self.mcp_credential_ref):
                raise ValueError('MCP requires a cloud ID and its own token reference; native reads support sync.')
        elif (not self.drive_id and not (self.auth_method=='oauth' and self.scope_id=='pending-scope')) or self.transport != 'native':
            raise ValueError('Microsoft document scopes require a drive ID and native Graph transport.')
        if self.auth_method=='oauth' and self.transport!='native':raise ValueError('Native OAuth and MCP server authentication are separate connections.')
        self.site_url = self.site_url.rstrip('/')
        return self


@dataclass
class Record:
    native_id: str
    revision: str
    updated: datetime | None
    original_url: str
    filename: str
    content: bytes
    payload: dict
    fields: list
    display_title: str = ''


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None: raise ValueError()
        return result
    except (AttributeError, ValueError, TypeError): raise SourceFailure('source_time_missing') from None


def adf_text(node):
    if isinstance(node, str): return node
    if not isinstance(node, dict): return ''
    value = node.get('text', '')
    content = node.get('content', [])
    return value + ('\n' if node.get('type') in {'paragraph', 'heading', 'listItem'} else '') + ''.join(adf_text(n) for n in content)


class TextHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}: self.hidden += 1
        if tag in {'p', 'br', 'div', 'li', 'tr', 'h1', 'h2', 'h3'}: self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in {'script', 'style'}: self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)


class Provider:
    def __init__(self, spec, limits=None):
        self.spec = spec if isinstance(spec, ConnectionSpec) else ConnectionSpec(**spec)
        self.limits = limits or active() or ReadLimits()
        self.host = urlsplit(self.spec.site_url).hostname if self.spec.kind in {'jira', 'confluence'} else 'graph.microsoft.com'
        self.client = ReadClient(self.spec.credential_ref, self.host, self.limits)
        self.base = self.spec.site_url if self.spec.kind in {'jira', 'confluence'} else 'https://graph.microsoft.com/v1.0'
        if self.spec.credential_ref.startswith('RF4_OAUTH_') and self.spec.kind in {'jira','confluence'}:
            self.host='api.atlassian.com'
            self.base=f'https://api.atlassian.com/ex/{self.spec.kind}/{self.spec.cloud_id}'
            self.client=ReadClient(self.spec.credential_ref,self.host,self.limits)

    def authorize(self, native_id):
        if self.spec.kind in {'jira', 'confluence'}:
            return self.get(native_id, mcp=self.spec.transport == 'atlassian_mcp')
        else:
            if not re.fullmatch(r'[A-Za-z0-9!_,.-]{1,200}', native_id): raise SourceFailure('invalid_resource_id')
            data = self.client.get(self.base + f'/drives/{quote(self.spec.drive_id)}/items/{quote(native_id)}')
            if data.get('id')!=native_id:raise SourceFailure('outside_scope')
            if 'deleted' in data: raise SourceFailure('resource_missing')
            self.in_folder(data)
            return data

    def mcp_client(self):
        # Reuse only protocol negotiation inside this bounded request. Every resource
        # access and reauthorization still performs a fresh source read.
        key = ('atlassian', self.spec.mcp_credential_ref,threading.get_ident())
        client = self.limits.mcp_sessions.get(key)
        if client is None:
            client = AtlassianMCP(self.spec.mcp_credential_ref, self.limits)
            self.limits.mcp_sessions[key] = client
        return client

    def search(self,query,limit=4):
        """Bounded, server-scoped discovery. Search snippets are never answer evidence."""
        tokens=re.findall(r'[^\W_]+',query,re.UNICODE)[:8]
        if not tokens:return []
        term=' '.join(tokens)[:150]
        s=self.spec;limit=max(1,min(limit,6))
        if s.kind=='jira':
            # A project-qualified question should search its issues, not require its
            # project name to occur inside every issue's prose.
            words=[t for t in tokens if t.upper()!=s.scope_id]
            jql=f'project = "{s.scope_id}"'
            exact=re.search(r'\b'+re.escape(s.scope_id)+r'-\d+\b',query,re.I)
            if exact:jql+=' AND key = '+json.dumps(exact[0].upper())
            elif words:jql+=' AND text ~ '+json.dumps(' '.join(words))
            jql+=' ORDER BY updated DESC'
            if s.transport=='atlassian_mcp':
                data=self.mcp_record(self.mcp_client().call('searchJiraIssuesUsingJql',dict(cloudId=s.cloud_id,jql=jql,maxResults=limit,view='compact')))
            else:data=self.client.get(self.base+'/rest/api/3/search/jql',dict(jql=jql,maxResults=limit,fields='summary,project'))
            items=data.get('issues')
            if not isinstance(items,list):raise SourceFailure('malformed_source')
            hits=[]
            for item in items[:limit]:
                key=item.get('key','')
                if not re.fullmatch(re.escape(s.scope_id)+r'-\d+',key):raise SourceFailure('outside_scope')
                hits.append(dict(native_id=key,title=item.get('fields',{}).get('summary',key)))
            return hits
        if s.kind=='confluence':
            # CQL space is a key, whereas v2 content authorization verifies its ID.
            key=s.space_key or (s.scope_id if not s.scope_id.isdigit() else '')
            if not key:raise SourceFailure('search_setup_required')
            from app.chat_retrieval import purpose,rank_hits
            kind=purpose(query)
            anchors=re.findall(r'\b[A-Z][A-Z0-9_]{1,30}\b',query)
            hints={'overview':['scope','overview','purpose'], 'ownership':['ownership','scope'],
                   'directory':['company and teams','directory','operating departments'],
                   'policy':['retention','policy','standard'], 'release':['release','readiness']}[kind]
            topic=' AND title ~ '+json.dumps(anchors[0]) if anchors and kind not in {'directory','policy'} else ''
            specific='('+ ' OR '.join('title ~ '+json.dumps(h) for h in hints)+')'+topic
            if kind=='policy':
                topical=[t for t in tokens if t.casefold() not in {'approved','policy','the','current','what','is','for','should','be','days','or','30','90'}]
                if topical:
                    specific='('+ ' OR '.join('title ~ '+json.dumps(t) for t in topical[:4])+')'
            def find(expression):
                cql='space = '+json.dumps(key)+' AND type = page AND '+expression
                if s.transport=='atlassian_mcp':
                    client=self.mcp_client()
                    name='searchConfluence' if 'searchConfluence' in client.tools else 'searchConfluenceUsingCql'
                    return self.mcp_record(client.call(name,dict(cloudId=s.cloud_id,cql=cql,limit=limit)))
                return self.client.get(self.base+'/wiki/rest/api/search',dict(cql=cql,limit=limit))
            hits={}
            # Title intent is only a ranking hint; source bodies must establish facts.
            for expression in [specific,'title ~ '+json.dumps(term),'text ~ '+json.dumps(term)]:
                data=find(expression);items=data.get('results')
                if not isinstance(items,list):raise SourceFailure('malformed_source')
                for item in items[:limit]:
                    content=item.get('content',item);native=str(content.get('id',''))
                    if not native.isdigit():raise SourceFailure('malformed_source')
                    hits[native]=dict(native_id=native,title=content.get('title','Page'))
                if len(hits)>=2:break
            return rank_hits(query,list(hits.values()))[:limit]
        if s.kind in {'onedrive','sharepoint'}:
            # https://learn.microsoft.com/graph/api/driveitem-search?view=graph-rest-1.0
            # Discover only within the configured folder, then verify every hit.
            literal=quote(term.replace("'", "''"),safe='')
            url=self.base+f"/drives/{quote(s.drive_id,safe='')}/items/{quote(s.scope_id,safe='')}/search(q='{literal}')"
            data=self.client.get(url,{'$top':limit})
            if not isinstance(data.get('value'),list):raise SourceFailure('malformed_source')
            hits=[]
            for item in data['value'][:limit]:
                if 'remoteItem' in item or 'file' not in item:continue
                if PurePosixPath(item.get('name','')).suffix.lower() not in {'.pdf','.docx','.md','.txt'}:continue
                self.in_folder(item)
                native=str(item.get('id',''))
                if not re.fullmatch(r'[A-Za-z0-9!_,.-]{1,200}',native):raise SourceFailure('malformed_source')
                hits.append(dict(native_id=native,title=item.get('name','Document')))
            return hits
        # Microsoft/custom search must have an explicit scoped implementation;
        # never fall back to an unscoped drive or generic MCP execution tool.
        raise SourceFailure('search_not_supported')

    def project_snapshot(self):
        """Verify one configured project via a visible native issue, without a model.

        Slim Rovo exposes issue search but no dedicated project-list tool. Never
        replace it with generic execution or expose unconfigured account projects.
        """
        if self.spec.kind!='jira':raise SourceFailure('search_not_supported')
        args=dict(cloudId=self.spec.cloud_id,jql=f'project = "{self.spec.scope_id}" ORDER BY updated DESC',maxResults=1,
            fields=['project','summary','status','updated'],view='full')
        if self.spec.transport=='atlassian_mcp':data=self.mcp_record(self.mcp_client().call('searchJiraIssuesUsingJql',args))
        else:data=self.client.get(self.base+'/rest/api/3/search/jql',dict(jql=args['jql'],maxResults=1,fields='project,summary,status,updated'))
        items=data.get('issues')
        if not isinstance(items,list):raise SourceFailure('malformed_source')
        if not items:return None
        return self.jira(items[0])

    @staticmethod
    def mcp_record(value):
        # Current Rovo tools wrap originals in data; older tools returned them flat.
        data = value.get('data', value)
        if not isinstance(data, dict): raise SourceFailure('malformed_source')
        return data

    def get(self, native_id, *, mcp=False):
        if not re.fullmatch(r'[A-Za-z0-9!_,.-]{1,200}', native_id): raise SourceFailure('invalid_resource_id')
        s = self.spec
        if s.kind == 'jira':
            raw = (self.mcp_client().call('getJiraIssue',
                {'cloudId': s.cloud_id, 'issueIdOrKey': native_id, 'view': 'full'}) if mcp and s.transport == 'atlassian_mcp'
                else self.client.get(self.base + '/rest/api/3/issue/' + quote(native_id), {'fields': 'summary,description,status,assignee,updated,project'}))
            data = self.mcp_record(raw) if mcp and s.transport == 'atlassian_mcp' else raw
            record=self.jira(data)
            record.payload=raw
            if native_id not in {record.native_id,data.get('key')}:raise SourceFailure('outside_scope')
            return record
        if s.kind == 'confluence':
            if mcp and s.transport == 'atlassian_mcp':
                client = self.mcp_client()
                raw = (client.call('getConfluenceContent', {'cloudId': s.cloud_id, 'content_id': native_id,
                    'detail': 'full', 'content_format': 'html'}) if 'getConfluenceContent' in client.tools else
                    client.call('getConfluencePage', {'cloudId': s.cloud_id, 'pageId': native_id, 'contentFormat': 'html'}))
                data = self.mcp_record(raw)
            else:
                raw = data = self.client.get(self.base + '/wiki/api/v2/pages/' + quote(native_id), {'body-format': 'storage'})
            record=self.confluence(data)
            record.payload=raw
            if record.native_id!=native_id:raise SourceFailure('outside_scope')
            return record
        data = self.client.get(self.base + f'/drives/{quote(s.drive_id)}/items/{quote(native_id)}')
        if data.get('id')!=native_id:raise SourceFailure('outside_scope')
        self.in_folder(data)
        return self.graph(data)

    def in_folder(self, item):
        current = item
        for _ in range(16):
            if current.get('id') == self.spec.scope_id: return
            parent = current.get('parentReference', {})
            if parent.get('driveId') != self.spec.drive_id or not parent.get('id'): break
            if parent['id'] == self.spec.scope_id: return
            current = self.client.get(self.base + f'/drives/{quote(self.spec.drive_id)}/items/{quote(parent["id"])}')
        raise SourceFailure('outside_scope')

    def jira(self, data):
        fields = data.get('fields', {})
        if fields.get('project', {}).get('key') != self.spec.scope_id: raise SourceFailure('outside_scope')
        key = data.get('key', '')
        if not re.fullmatch(re.escape(self.spec.scope_id) + r'-[0-9]+', key): raise SourceFailure('malformed_source')
        values = [dict(field='key', value=key), dict(field='summary', value=fields.get('summary', '')),
            dict(field='status', value=fields.get('status', {}).get('name')),
            dict(field='assignee', value=(fields.get('assignee') or {}).get('displayName')),
            dict(field='description', value=adf_text(fields.get('description')))]
        if fields.get('project',{}).get('name'):
            values.append(dict(field='project',value={k:fields['project'][k] for k in ('id','key','name') if k in fields['project']}))
        text = '\n'.join(v['field'] + ': ' + json.dumps(v['value'], ensure_ascii=False) for v in values)
        updated = timestamp(fields.get('updated'))
        return Record(str(data['id']), fields['updated'], updated, self.spec.site_url + '/browse/' + key,
            key + '.md', text.encode(), data, values,fields.get('summary') or key)

    def confluence(self, data):
        if str(data.get('spaceId')) != self.spec.scope_id: raise SourceFailure('outside_scope')
        html = data.get('body', {}).get('storage', {}).get('value')
        if html is None and data.get('body', {}).get('format') == 'html':
            html = data['body'].get('value')
        if not isinstance(html, str): raise SourceFailure('incomplete_record')
        parser = TextHTML(); parser.feed(html)
        text = ''.join(parser.parts).strip()
        if not text: raise SourceFailure('no_readable_text')
        version = data.get('version') or data.get('metadata', {}).get('version', {})
        updated = timestamp(version.get('createdAt'))
        id = str(data['id'])
        return Record(id, str(version['number']), updated, self.spec.site_url + '/wiki/pages/viewpage.action?pageId=' + quote(id),
            id + '.md', text.encode(), data, [],data.get('title') or '')

    def graph(self, data):
        if 'file' not in data: raise SourceFailure('unsupported_resource')
        name = PurePosixPath(data.get('name', '').replace('\\', '/')).name
        if PurePosixPath(name).suffix.lower() not in {'.pdf', '.docx', '.md', '.txt'}: raise SourceFailure('unsupported_format')
        original = data.get('webUrl', '')
        host = urlsplit(original).hostname or ''
        if not host.endswith('.sharepoint.com'): raise SourceFailure('source_link_invalid')
        safe_url(original, host)
        download = data.get('@microsoft.graph.downloadUrl')
        if not isinstance(download, str) or urlsplit(download).hostname != host:
            raise SourceFailure('download_url_unavailable')
        # Pre-authorized download URLs are not persisted, and never receive OAuth headers.
        content = ReadClient(self.spec.credential_ref, host, self.limits).request('GET', download, raw=True, authenticated=False)
        payload = {k: v for k, v in data.items() if k != '@microsoft.graph.downloadUrl'}
        return Record(str(data['id']), data['eTag'], timestamp(data.get('lastModifiedDateTime')),
            original, name, content, payload, [])

    def sync_page(self,cursor,since):
        """Use an MCP pagination contract when advertised, otherwise scoped native reads."""
        if self.spec.transport!='atlassian_mcp':return self.page(cursor,since=since)
        channel=cursor.get('channel')
        if channel!='native':
            try:
                records,next_cursor,done=self.mcp_page(cursor,since)
                return records,({**next_cursor,'channel':'mcp'} if not done else {}),done
            except SourceFailure as exc:
                if channel or exc.code not in {'sync_pagination_unavailable','mcp_tool_unavailable','mcp_schema_changed'}:raise
        if self.spec.credential_ref=='RF4_UNCONFIGURED':raise SourceFailure('sync_pagination_unavailable')
        records,next_cursor,done=self.page({k:v for k,v in cursor.items() if k!='channel'},since=since)
        return records,({**next_cursor,'channel':'native'} if not done else {}),done

    def jira_collection_query(self,since):
        base=f'project = "{self.spec.scope_id}"'
        if since:
            boundary=timestamp(since)-timedelta(days=1)
            base+=f' AND updated >= "{boundary.date().isoformat()}"'
        return base+' ORDER BY id ASC'

    def mcp_page(self,cursor,since):
        client=self.mcp_client()
        if self.spec.kind=='jira':
            tool='searchJiraIssuesUsingJql'
            if 'nextPageToken' not in client.tools.get(tool,{}).get('properties',{}):
                raise SourceFailure('sync_pagination_unavailable')
            args=dict(cloudId=self.spec.cloud_id,jql=self.jira_collection_query(since),maxResults=15,
                fields=['summary','description','status','assignee','updated','project'],view='full')
            if cursor.get('token'):args['nextPageToken']=cursor['token']
            data=self.mcp_record(client.call(tool,args))
            token=data.get('nextPageToken')
            if not isinstance(data.get('issues'),list) or (not token and data.get('isLast') is not True):
                raise SourceFailure('sync_pagination_unavailable')
            return [self.jira(item) for item in data['issues']],({'token':token} if token else {}),not token
        tool=next((name for name in ('searchConfluence','searchConfluenceUsingCql')
            if {'cursor','start'} & client.tools.get(name,{}).get('properties',{}).keys()),None)
        if not tool or not self.spec.space_key:raise SourceFailure('sync_pagination_unavailable')
        offset=cursor.get('start',0)
        uses_cursor='cursor' in client.tools[tool].get('properties',{})
        args=dict(cloudId=self.spec.cloud_id,
            cql='space = '+json.dumps(self.spec.space_key)+' AND type = page ORDER BY id ASC',limit=8)
        if uses_cursor:
            if cursor.get('confluence_cursor'):args['cursor']=cursor['confluence_cursor']
        else:args['start']=offset
        data=self.mcp_record(client.call(tool,args))
        items=data.get('results');total=data.get('totalSize',data.get('total'))
        if not isinstance(items,list) or not isinstance(total,int) or (not items and offset<total):
            raise SourceFailure('sync_pagination_unavailable')
        next_offset=offset+len(items)
        done=next_offset>=total
        next_state={'start':next_offset}
        if uses_cursor:
            # Resubmit only the opaque cursor to the same scoped MCP tool.
            # A provider-supplied pagination URL is never requested directly.
            next_link=data.get('_links',{}).get('next')
            token=parse_qs(urlsplit(next_link).query).get('cursor',[''])[0] if isinstance(next_link,str) else ''
            if token:
                if len(token)>4096 or token==cursor.get('confluence_cursor') or not items:
                    raise SourceFailure('incomplete_page')
                next_state['confluence_cursor']=token
                done=False
            elif not done or next_link:
                raise SourceFailure('incomplete_page')
        records=[]
        for item in items:
            native=str(item.get('content',item).get('id',''))
            if not native.isdigit():raise SourceFailure('malformed_source')
            records.append(self.get(native,mcp=True))
        return records,({} if done else next_state),done

    def page(self, cursor, *, since=None):
        """One page only. Cursor advances atomically with its retained records."""
        s = self.spec
        if s.kind == 'jira':
            params = {'jql': self.jira_collection_query(since), 'maxResults': 25,
                'fields': 'summary,description,status,assignee,updated,project'}
            if cursor.get('token'): params['nextPageToken'] = cursor['token']
            data = self.client.get(self.base + '/rest/api/3/search/jql', params)
            if not isinstance(data.get('issues'), list): raise SourceFailure('malformed_source')
            records = [self.jira(item) for item in data.get('issues', [])]
            token = data.get('nextPageToken')
            if data.get('isLast') is not True and not token: raise SourceFailure('incomplete_page')
            return records, ({'token': token} if token else {}), not token
        if s.kind == 'confluence':
            path = '/wiki/api/v2/spaces/' + quote(s.scope_id) + '/pages'
            url = cursor.get('next') or self.base + path
            safe_url(url, self.host, urlsplit(self.base).path+path)
            data = self.client.get(url, {'body-format': 'storage', 'limit': 25} if not cursor else None)
            if not isinstance(data.get('results'), list): raise SourceFailure('malformed_source')
            records = [self.confluence(item) for item in data.get('results', [])]
            next_url = data.get('_links', {}).get('next')
            if next_url:
                if next_url.startswith('/'):
                    prefix=urlsplit(self.base).path
                    next_url=('https://'+self.host+next_url if prefix and next_url.startswith(prefix+'/') else self.base+next_url)
                safe_url(next_url, self.host, urlsplit(self.base).path+path)
                if urlsplit(next_url).path != urlsplit(self.base).path+path: raise SourceFailure('unsafe_source_url')
            return records, ({'next': next_url} if next_url else {}), not next_url
        # Folder-only traversal avoids reading an entire drive to filter it later.
        pending = list(cursor.get('pending', [s.scope_id]))
        seen = list(cursor.get('seen', []))
        folder = pending.pop(0) if pending else None
        if not folder: return [], {}, True
        path = f'/v1.0/drives/{quote(s.drive_id)}/items/{quote(folder)}/children'
        url = cursor.get('next') or 'https://graph.microsoft.com' + path
        safe_url(url, self.host, path)
        data = self.client.get(url, {'$top': 25} if not cursor.get('next') else None)
        if not isinstance(data.get('value'), list): raise SourceFailure('malformed_source')
        records = []
        for item in data.get('value', []):
            if (item.get('parentReference', {}).get('id') != folder
                    or item.get('parentReference', {}).get('driveId') != s.drive_id): raise SourceFailure('outside_scope')
            if item.get('folder') is not None:
                if item['id'] not in seen and item['id'] not in pending: pending.append(item['id'])
            elif item.get('file') is not None:
                if getattr(self,'known_revisions',{}).get(str(item['id']))==item.get('eTag'):continue
                try: records.append(self.graph(item))
                except SourceFailure as exc:
                    if exc.code != 'unsupported_format': raise
        next_url = data.get('@odata.nextLink')
        if next_url:
            safe_url(next_url, self.host, path)
            if urlsplit(next_url).path != path: raise SourceFailure('unsafe_source_url')
            pending.insert(0, folder)
        else: seen.append(folder)
        if len(pending) + len(seen) > 100: raise SourceFailure('scope_limit')
        return records, ({'pending': pending, 'seen': seen, 'next': next_url} if pending else {}), not pending
