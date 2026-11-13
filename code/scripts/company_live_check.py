"""Run and safely resume the approved isolated fictional-company test.

This runner is local-only. It never replays a recorded answer, and it records
permission and processing failures instead of silently replacing them.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',default='http://127.0.0.1:5175')
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--resume',action='store_true',help='Resume this exact checkpoint without replaying recorded answers')
    args=parser.parse_args()
    if urlparse(args.base).hostname not in {'127.0.0.1','localhost'}:
        parser.error('Local preview only')
    manifest_path=Path(__file__).resolve().parents[1]/'fixtures/company_demo/manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    report={'schema_version':2,'dataset_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'status':'starting','questions':[],'checkpoint_complete':False,'stage_checkpoints':{}}
    if args.report.exists():
        if not args.resume:
            parser.error('Use --resume to continue this exact checkpoint')
        report=json.loads(args.report.read_text(encoding='utf-8'))
        if report.get('schema_version') != 2 or not isinstance(report.get('questions'),list):
            parser.error('Unrecognized checkpoint; refusing to repeat paid work')
    args.report.parent.mkdir(parents=True,exist_ok=True)

    def save():
        temp=args.report.with_suffix('.tmp')
        temp.write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
        temp.replace(args.report)

    def checkpoint(name):
        report['stage_checkpoints'][name]=True
        save()

    def call(path,body=None,token='demo-amal',method=None):
        headers={'Authorization':'Bearer '+token}
        if os.getenv('COMPANY_BRAIN_COMPANY_PREVIEW')=='1':
            headers['X-Preview-Proxy']=os.environ.get('COMPANY_BRAIN_PREVIEW_SECRET','')
        if isinstance(body,dict):
            headers['Content-Type']='application/json'
            body=json.dumps(body).encode()
        request=Request(args.base+'/api/v1'+path,headers=headers,data=body,method=method)
        try:
            with urlopen(request,timeout=240) as response:
                return response.status,json.load(response)
        except HTTPError as response:
            return response.code,json.load(response)

    def upload_revision(job,key,revision=True):
        content=(manifest_path.parent/(key+'.md' if revision else 'your-addition.txt')).read_bytes()
        boundary=uuid4().hex
        filename=key+'.md' if revision else 'your-addition.txt'
        prefix='' if revision else f'--{boundary}\r\nContent-Disposition: form-data; name="visibility"\r\n\r\nprivate\r\n'
        data=(prefix+f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n\r\n').encode()+content+f'\r\n--{boundary}--\r\n'.encode()
        path='/documents/'+job['document_id']+'/revisions' if revision else '/sources/upload'
        request=Request(args.base+'/api/v1'+path,data=data,headers={'Authorization':'Bearer demo-amal','X-Preview-Proxy':os.environ.get('COMPANY_BRAIN_PREVIEW_SECRET',''),'Content-Type':'multipart/form-data; boundary='+boundary})
        try:
            with urlopen(request,timeout=30) as response:
                return json.load(response)
        except HTTPError as response:
            return {'status':'failed','search_status':'failed','http_status':response.code,'error':json.load(response)}

    def wait_job(job):
        if not job.get('id'):
            return job
        deadline=time.monotonic()+240
        while time.monotonic()<deadline:
            _,row=call('/jobs/'+job['id'])
            if row['status'] not in {'queued','processing'}:
                return row
            time.sleep(2)
        raise RuntimeError('Test job exceeded its bounded deadline')

    try:
        _,runtime=call('/runtime')
        budget=runtime.get('budget') or {}
        if runtime.get('provider')!='bedrock' or budget.get('id')!='northstar-sonnet-2026-11-12' or float(budget.get('limit_usd',0))!=10:
            raise RuntimeError('The expected isolated Sonnet budget is not configured')
        report['runtime_start']=runtime
        report['status']='ingesting'; save()
        if not report['stage_checkpoints'].get('ingestion'):
            code,status=call('/demo/company/load',{})
            if code!=202:
                raise RuntimeError('Company dataset loading was rejected')
            deadline=time.monotonic()+1200
            while time.monotonic()<deadline:
                _,status=call('/demo/company/status')
                print(json.dumps({'search_ready':status['search_ready'],'enriched':status['enriched'],'total':status['total']}),flush=True)
                if all(j and j['status'] not in {'queued','processing'} for j in status['jobs']):
                    break
                time.sleep(3)
            else:
                raise RuntimeError('Company ingestion exceeded its bounded deadline')
            required={key for item in manifest['questions'] if item.get('mode')!='revision' for key in item['sources']}
            available={j['fixture_key'] for j in status['jobs'] if j and j['search_status']=='ready'}
            if not required.issubset(available):
                raise RuntimeError('Required documents are not searchable: '+','.join(sorted(required-available)))
            report['ingestion']=status
            checkpoint('ingestion')
        status=report['ingestion']
        jobs={j['fixture_key']:j for j in status['jobs'] if j}
        report['status']='questions'; save()
        for index,item in enumerate(manifest['questions']):
            if item.get('mode')=='revision' or any(q['number']==index+1 and q.get('http_status')==200 for q in report['questions']):
                continue
            selected=[jobs[key]['document_id'] for key in item['sources']]
            code,conversation=call('/conversations',{'title':'Northstar live test '+str(index+1),'document_ids':selected})
            if code!=201:
                raise RuntimeError('Test conversation creation failed')
            started=time.monotonic()
            code,response=call('/conversations/'+conversation['id']+'/answers',{'question':item['question']})
            row=dict(number=index+1,question=item['question'],expected=item['expected'],http_status=code,
                     response=response,latency_seconds=round(time.monotonic()-started,3),conversation=conversation['id'])
            if code==200:
                texts=' '.join(s['text'] for s in response['statements'])
                row['has_supported_output']=bool(response['statements'])
                row['exact_source_quotes']=all(c['quote'] in next(p['text'] for p in response['evidence'] if p['id']==c['passage_id']) for s in response['statements'] for c in s['evidence'])
                row['expected_literal_present']=item['expected'].casefold() in texts.casefold()
                if item.get('mode')=='missing-evidence':
                    row['expected_abstention']=response['insufficient_evidence']
                if item.get('mode')=='permissions':
                    denied,_=call('/conversations',{'document_ids':selected},token='demo-omar')
                    row['other_user_denied']=denied==404
            report['questions']=[q for q in report['questions'] if q['number']!=index+1]
            report['questions'].append(row)
            report['questions'].sort(key=lambda q:q['number'])
            checkpoint('question_'+str(index+1))
            print(json.dumps({'question':index+1,'http_status':code,'statements':len(response.get('statements',[]))}),flush=True)
            _,runtime=call('/runtime')
            if runtime['budget']['paused']:
                raise RuntimeError('Budget paused; uncertain usage is preserved for review')
        if not report['stage_checkpoints'].get('questions'):
            checkpoint('questions')

        if 'revision' not in report:
            atlas=jobs['atlas-handover']
            before=next(q for q in report['questions'] if q['number']==12)
            if before.get('http_status')!=200:
                raise RuntimeError('Question 12 is not successful; cannot validate old-answer suppression')
            revised=wait_job(upload_revision(atlas,'atlas-handover-revision'))
            _,history=call('/conversations/'+before['conversation'])
            report['revision']=dict(status=revised['status'],search_status=revised['search_status'],
                                    old_answer_suppressed=history['turns'][0]['suppressed'])
            old=before['response'].get('evidence',[])
            report['revision']['old_evidence_accessible']=bool(old) and call('/evidence/'+old[0]['id'])[0]==200
            _,conversation=call('/conversations',{'document_ids':[atlas['document_id']]})
            code,response=call('/conversations/'+conversation['id']+'/answers',{'question':'What is the deadline for task NS-ATLAS-01?'})
            report['revision']['answer']=response
            report['revision']['new_deadline_found']=code==200 and any('2026-12-08' in p['text'] for p in response.get('evidence',[]))
            checkpoint('revision')
        if 'user_addition' not in report:
            addition=wait_job(upload_revision(None,'your-addition',revision=False))
            report['user_addition']=dict(job_status=addition['status'],search_status=addition['search_status'])
            if addition.get('id'):
                _,conversation=call('/conversations',{'document_ids':[addition['document_id']]})
                if conversation.get('id'):
                    code,response=call('/conversations/'+conversation['id']+'/answers',{'question':'When is the NS-ATLAS support drill?'})
                    report['user_addition'].update(http_status=code,response=response)
            checkpoint('user_addition')
        report['status']='completed'
        report['checkpoint_complete']=True
    except Exception as exc:
        report['status']='stopped'
        report['stop_reason']=type(exc).__name__+': '+str(exc)
    finally:
        try: report['runtime_end']=call('/runtime')[1]
        except Exception: pass
        save()
    print(json.dumps({'status':report['status'],'questions':len(report['questions']),'budget':report.get('runtime_end',{}).get('budget')}),flush=True)
    return 0 if report['status']=='completed' else 2


if __name__=='__main__':
    sys.exit(main())
