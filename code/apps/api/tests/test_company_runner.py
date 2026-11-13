import io
import json
import runpy
import sys
from urllib.error import HTTPError
from urllib.request import Request
from unittest.mock import patch


class Response:
    def __init__(self,payload,status=200):
        self.status=status
        self.stream=io.BytesIO(json.dumps(payload).encode())
    def __enter__(self): return self
    def __iter__(self): return iter(self.stream)
    def __exit__(self,*args): pass
    def read(self,*args): return self.stream.read(*args)


def manifest():
    fixtures=[dict(key=key,filename=key+'.md',revision_of=None,visibility='team') for key in ['atlas-handover','beacon-private-budget']]
    keys=['atlas-charter','atlas-decision','beacon-charter','beacon-status','cedar-charter','cedar-status','company-leave-policy','company-onboarding','company-people','delta-handover','ember-handover','ember-private-budget']
    questions=[dict(question='Question '+str(i),sources=[keys[(i-1)%len(keys)]],expected='Deadline',mode='permissions' if i==15 else 'normal') for i in range(1,16)]
    return dict(fixtures=fixtures,questions=questions)


def run_runner(tmp_path,monkeypatch,fail_once=False,old_report=False):
    keys=['atlas-charter','atlas-decision','beacon-charter','beacon-status','cedar-charter','cedar-status','company-leave-policy','company-onboarding','company-people','delta-handover','ember-handover','ember-private-budget','atlas-handover','beacon-private-budget']
    jobs=[dict(id='job-'+str(i),document_id='doc-'+str(i),fixture_key=key,status='ready',search_status='ready') for i,key in enumerate(keys,1)]
    answers=[]
    failed=[fail_once]
    def call(url,body=None,token='demo-amal',method=None):
        path=url.split('/api/v1',1)[1]
        if path=='/runtime': return 200,{'provider':'bedrock','budget':{'id':'northstar-sonnet-2026-11-12','limit_usd':10,'paused':False}}
        if path=='/demo/company/load': return 202,{}
        if path=='/demo/company/status': return 200,{'total':24,'search_ready':24,'enriched':24,'jobs':jobs}
        if path=='/conversations' and token=='demo-omar': return 404,{'detail':'Not found'}
        if path=='/conversations': return 201,{'id':'conv-'+str(len(answers)+1)}
        if path.startswith('/conversations/') and path.endswith('/answers'):
            if failed[0]: failed[0]=False; return 503,{'detail':'simulated interruption'}
            answers.append(path); return 200,{'statements':[{'text':'Deadline','evidence':[]}],'evidence':[],'insufficient_evidence':False}
        if path.startswith('/jobs/'): return 200,{'id':'job-1','status':'ready','search_status':'ready','document_id':'doc-1'}
        if path.startswith('/conversations/'): return 200,{'turns':[{'suppressed':True}]}
        raise AssertionError(path)
    def upload(req,timeout):
        return Response({'id':'job-1','status':'ready','search_status':'ready','document_id':'doc-1'})
    def fake_open(req,timeout):
        if isinstance(req,Request) and req.full_url.endswith(('/revisions','/sources/upload')): return upload(req,timeout)
        code,payload=call(req.full_url,json.loads(req.data) if req.data else None) if req.data else call(req.full_url)
        return Response(payload,code)
    import scripts.company_live_check as runner
    monkeypatch.setattr(runner,'urlopen',fake_open)
    monkeypatch.setattr(runner.time,'sleep',lambda _:None)
    report=tmp_path/'report.json'
    if old_report: report.write_text(json.dumps({'schema_version':2,'status':'stopped','questions':[],'stage_checkpoints':{'ingestion':True},'ingestion':{'jobs':jobs}}))
    args=['company_live_check.py','--report',str(report)]+(['--resume'] if old_report else [])
    with patch.object(sys,'argv',args):
        result=runner.main()
    return result,json.loads(report.read_text()),answers


def test_runner_checkpoints_and_resumes_without_replaying_questions(tmp_path,monkeypatch):
    result,report,answers=run_runner(tmp_path,monkeypatch,fail_once=True)
    assert result==2
    assert report['status']=='stopped'
    result,report,answers=run_runner(tmp_path,monkeypatch,old_report=True)
    assert result==0
    assert len(report['questions'])==15
    assert report['checkpoint_complete']
    assert len(answers)==16


def test_runner_requires_explicit_resume(tmp_path,monkeypatch):
    report=tmp_path/'report.json'; report.write_text('{}')
    import scripts.company_live_check as runner
    with patch.object(sys,'argv',['runner','--report',str(report)]):
        import pytest
        with pytest.raises(SystemExit): runner.main()
