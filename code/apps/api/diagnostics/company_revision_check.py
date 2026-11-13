import json,os,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from uuid import uuid4
from app.company_demo import ROOT
BASE='http://api:8000/api/v1'
HEAD={'Authorization':'Bearer demo-amal','X-Preview-Proxy':os.environ.get('COMPANY_BRAIN_PREVIEW_SECRET','')}
def call(path,body=None):
 h=dict(HEAD)
 if isinstance(body,dict): h['Content-Type']='application/json'; body=json.dumps(body).encode()
 try:
  with urlopen(Request(BASE+path,data=body,headers=h),timeout=240) as r: return r.status,json.load(r)
 except HTTPError as r: return r.code,json.load(r)
def upload(path,name):
 content=(ROOT/name).read_bytes(); boundary=uuid4().hex
 data=(f'--{boundary}\r\nContent-Disposition: form-data; name="visibility"\r\n\r\nprivate\r\n' if path.endswith('upload') else '')
 data=(data+f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n\r\n').encode()+content+f'\r\n--{boundary}--\r\n'.encode()
 h={**HEAD,'Content-Type':'multipart/form-data; boundary='+boundary}
 try:
  with urlopen(Request(BASE+path,data=data,headers=h),timeout=30) as r: return json.load(r)
 except HTTPError as r: return {'error':json.load(r),'status':r.code}
def wait(job):
 for _ in range(120):
  code,row=call('/jobs/'+job['id'])
  if row['status'] not in {'queued','processing'}: return row
  time.sleep(2)
 raise RuntimeError('job timeout')
_,jobs=call('/demo/company/status')
atlas=next(j for j in jobs['jobs'] if j and j['fixture_key']=='atlas-handover')
rev=upload('/documents/'+atlas['document_id']+'/revisions','atlas-handover-revision.md')
print(json.dumps({'revision_upload':rev},default=str),flush=True)
if rev.get('id'):
 rev=wait(rev)
 _,con=call('/conversations',{'document_ids':[atlas['document_id']]})
 code,answer=call('/conversations/'+con['id']+'/answers',{'question':'What is the deadline for task NS-ATLAS-01?'})
 print(json.dumps({'revision':rev,'http_status':code,'answer':answer},default=str),flush=True)
add=upload('/sources/upload','your-addition.txt')
print(json.dumps({'addition_upload':add},default=str),flush=True)
if add.get('id'):
 add=wait(add)
 _,con=call('/conversations',{'document_ids':[add['document_id']]})
 code,answer=call('/conversations/'+con['id']+'/answers',{'question':'When is the NS-ATLAS support drill?'})
 print(json.dumps({'addition':add,'http_status':code,'answer':answer},default=str),flush=True)
