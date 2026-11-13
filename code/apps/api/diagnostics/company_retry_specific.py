import json,os
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from app.db import engine,sql
ids=['26fb195a-0097-4479-bfa9-dab25276ece4','7833c4a9-c990-4267-9f12-92bb96bea3dc']
for id in ids:
 req=Request('http://api:8000/api/v1/jobs/'+id+'/retry',data=b'',method='POST',headers={'Authorization':'Bearer demo-amal','X-Preview-Proxy':os.getenv('COMPANY_BRAIN_PREVIEW_SECRET','')})
 try:
  with urlopen(req,timeout=30) as r: print(r.status,r.read().decode())
 except HTTPError as r: print(r.code,r.read().decode())
