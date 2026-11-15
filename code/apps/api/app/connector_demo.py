"""Fixed, explicitly labelled fixtures for the admin lifecycle; no simulated real access."""
import json
from datetime import datetime, timezone
from app.connector_providers import Record
from app.connector_transport import SourceFailure


class DemoProvider:
    def __init__(self,spec,limits=None): self.spec=spec
    def record(self):
        text=('SYNTHETIC LINKMIND CONNECTOR DEMO\n'
              'This fixture demonstrates source-only retrieval and scoped collection.\n'
              'It contains no information from your company or configured source URL.\n'
              'The fictional demo review is scheduled for Thursday.')
        fields=[{'field':'status','value':'Synthetic demo'}] if self.spec.kind=='jira' else []
        return Record('demo-1','demo-v1',datetime(2026,11,15,tzinfo=timezone.utc),
            'https://fixtures.linkmind.invalid/connector-demo/'+self.spec.kind,'connector-demo-'+self.spec.kind+'.md',
            text.encode(),{'synthetic':True,'fixture':'linkmind-connector-demo-v1','kind':self.spec.kind},fields)
    def get(self,native_id,**kwargs):
        if native_id!='demo-1': raise SourceFailure('resource_missing')
        return self.record()
    def authorize(self,native_id): self.get(native_id)
    def page(self,cursor): return [self.record()],{},True
