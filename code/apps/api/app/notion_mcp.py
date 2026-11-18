"""Live reads from explicitly selected pages on Notion's hosted MCP server."""
import hashlib
import re
from urllib.parse import urlsplit

from app.chat_retrieval import rank_hits, terms
from app.connector_providers import Record, NOTION_HOSTS, notion_page_id, timestamp
from app.connector_transport import AtlassianMCP, ReadLimits, SourceFailure, active

ENDPOINT = 'https://mcp.notion.com/mcp'
READ_TOOLS = {'notion-fetch', 'fetch'}


class NotionProvider:
    def __init__(self, spec, limits=None):
        self.spec = spec
        self.limits = limits or active() or ReadLimits()
        self.pages = {notion_page_id(page.url):page for page in spec.notion_pages}
        self.mcp = None

    def search(self, query, limit=4):
        # Rank only the configured labels. Workspace-wide Notion search can include
        # personal pages and can depend on the workspace's Notion AI plan.
        topic = terms(query) - {'notion', 'handbook', 'our', 'how', 'many', 'have', 'responsible'}
        choices = [
            dict(native_id=key,title=page.title)
            for key,page in self.pages.items()
            if not topic or topic & terms(page.title)
        ]
        ranked = rank_hits(query,choices)
        return sorted(ranked,key=lambda hit:-len(topic & terms(hit['title'])))[:limit]

    def get(self, native_id, *, mcp=False):
        key = native_id.replace('-','').lower()
        if key not in self.pages:
            raise SourceFailure('outside_scope')
        if self.mcp is None:
            self.mcp = AtlassianMCP(self.spec.credential_ref,self.limits,endpoint=ENDPOINT,allowed=READ_TOOLS)
        tool = 'notion-fetch' if 'notion-fetch' in self.mcp.tools else 'fetch'
        result = self.mcp.call(tool,{'id':key})
        url,title,body = (result.get(field) for field in ('url','title','text'))
        metadata = result.get('metadata',{})
        if not (isinstance(metadata,dict) and metadata.get('type')=='page'
                and all(isinstance(value,str) and value.strip() for value in (url,title,body))):
            raise SourceFailure('malformed_source')
        try:
            if urlsplit(url).hostname not in NOTION_HOSTS or notion_page_id(url)!=key:
                raise SourceFailure('outside_scope')
        except ValueError:
            raise SourceFailure('source_link_invalid') from None
        content = re.search(r'<content>\s*(.*?)\s*</content>\s*</page>\s*$',body,re.S)
        if not content or not content[1].strip():
            raise SourceFailure('no_readable_text')
        text = ('# '+title.strip()+'\n\n'+content[1]).encode()
        revision = hashlib.sha256(text).hexdigest()
        updated = metadata.get('last_edited_time')
        return Record(key,revision,timestamp(updated) if isinstance(updated,str) else None,
                      url,key+'.md',text,{},[],title.strip())

    def authorize(self, native_id):
        return self.get(native_id)

    def page(self,cursor):
        keys=sorted(self.pages)
        index=cursor.get('index',0)
        if index>=len(keys):return [],{},True
        key=keys[index]
        records=[self.get(key)]
        done=index+1==len(keys)
        return records,{} if done else {'index':index+1},done
