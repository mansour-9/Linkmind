import json,os
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from uuid import uuid4
from app.company_demo import ROOT
content=(ROOT/'atlas-handover-revision.md').read_bytes()
boundary=uuid4().hex
body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="atlas-handover-revision.md"\r\nContent-Type: text/markdown\r\n\r\n').encode()+content+f'\r\n--{boundary}--\r\n'.encode()
req=Request('http://api:8000/api/v1/documents/13edad97-3923-44f4-ab91-986bd07ea3c1/revisions',data=body,headers={'Authorization':'Bearer demo-amal','X-Preview-Proxy':os.getenv('COMPANY_BRAIN_PREVIEW_SECRET',''),'Content-Type':'multipart/form-data; boundary='+boundary})
try:
 with urlopen(req,timeout=30) as r: print(r.status,r.read().decode())
except HTTPError as r: print(r.code,r.read().decode())
