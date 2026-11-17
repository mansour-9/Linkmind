import re
"""Explicit bounded remote-MCP read contract, without arbitrary model tool execution."""
from urllib.parse import urlsplit
from app.connector_providers import Record, timestamp
from app.connector_transport import AtlassianMCP, SourceFailure, safe_url


class CustomMCPProvider:
    def __init__(self,spec,limits=None):
        self.spec=spec
        self.mcp=AtlassianMCP(spec.credential_ref,limits,endpoint=spec.mcp_url,
            allowed={spec.read_tool,'list_resources'},require_read_hint=True)
    def record(self,item):
        if item.get('scope_id')!=self.spec.scope_id:raise SourceFailure('outside_scope')
        text=item.get('text')
        if not isinstance(text,str) or not text.strip() or len(text)>12000:raise SourceFailure('incomplete_record')
        safe_url(item.get('url',''),urlsplit(self.spec.mcp_url).hostname)
        return Record(str(item['resource_id']),str(item['revision']),timestamp(item['updated_at']),item['url'],
            'mcp-resource.md',text.encode(),item,[])
    def get(self,native_id,**kwargs):
        result=self.mcp.call(self.spec.read_tool,{'resource_id':native_id,'scope_id':self.spec.scope_id})
        record=self.record(result)
        if record.native_id!=native_id:raise SourceFailure('outside_scope')
        return record
    def search(self,query,limit=4):
        # The installed custom MCP contract exposes bounded scope enumeration,
        # not an unrestricted tool executor. Filter its first validated page.
        records,_,_=self.page({})
        words=set(re.findall(r'[^\W_]+',query.casefold()))
        ranked=sorted(records,key=lambda r:-sum(w in (r.filename+' '+r.content.decode('utf8',errors='replace')).casefold() for w in words))
        return [dict(native_id=r.native_id,title=r.filename) for r in ranked
                if any(w in (r.filename+' '+r.content.decode('utf8',errors='replace')).casefold() for w in words)][:min(limit,6)]
    def authorize(self,native_id):return self.get(native_id)
    def page(self,cursor):
        data=self.mcp.call('list_resources',{'scope_id':self.spec.scope_id,'cursor':cursor.get('token')})
        if not isinstance(data.get('records'),list) or len(data['records'])>25 or not isinstance(data.get('complete'),bool):raise SourceFailure('incomplete_page')
        records=[self.record(r) for r in data['records']]
        if not data['complete'] and not data.get('next_cursor'):raise SourceFailure('incomplete_page')
        return records,({'token':data['next_cursor']} if not data['complete'] else {}),data['complete']
