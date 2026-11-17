"""Back up/restore disposable legacy stacks; inspect the main stack read-only."""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import time

CODE=Path(__file__).resolve().parents[1]
PROJECTS=('linkmind-f13-rollout-legacy','linkmind-f13-rollout-candidate','linkmind-f13-rollout-rollback')
FINGERPRINT="""SELECT json_build_object(
 'schema',(SELECT version_num FROM alembic_version),
 'documents',(SELECT count(*) FROM documents),
 'versions',(SELECT count(*) FROM document_versions),
 'chunks',(SELECT count(*) FROM chunks),
 'entities',(SELECT count(*) FROM entities),
 'claims',(SELECT count(*) FROM claims),
 'relationships',(SELECT count(*) FROM relationships),
 'pointers',(SELECT md5(coalesce(string_agg(id::text||coalesce(current_version_id::text,'')||visibility||coalesce(deleted_at::text,''),',' ORDER BY id),'')) FROM documents),
 'evidence',(SELECT md5(coalesce(string_agg(id::text||version_id::text||md5(text)||locator::text,',' ORDER BY id),'')) FROM chunks),
 'facts',(SELECT md5(coalesce(string_agg(id::text||version_id::text||entity_id::text||chunk_id::text||predicate||value,',' ORDER BY id),'')) FROM claims))"""


def run(*args,input=None):
    result=subprocess.run(list(args),input=input,text=True,capture_output=True,cwd=CODE)
    if result.returncode:
        raise RuntimeError(result.stderr[-2500:])
    return result.stdout.strip()


def compose(project,image,*args):
    if project not in PROJECTS:
        raise RuntimeError('Only the three named disposable rehearsal projects may be mutated.')
    env={**os.environ,'BRAIN_BACKEND_IMAGE':image,'BRAIN_WEB_PORT':'5190'}
    result=subprocess.run(['docker','compose','-p',project,'-f','compose.yaml',*args],env=env,cwd=CODE,text=True,capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-2500:])


def db(project,statement):
    return run('docker','exec',project+'-db-1','psql','-v','ON_ERROR_STOP=1','-U','brain','-d','brain','-At','-c',statement)


def python(project,source):
    return run('docker','exec','-i',project+'-api-1','python','-',input=source)


def fingerprint(project):
    return json.loads(db(project,FINGERPRINT))


CONTEXT="""import json
from uuid import UUID
from app import main as api
v=api.Viewer(id='00000000-0000-4000-8000-000000000101',organization_id='00000000-0000-4000-8000-000000000001',name='Amal',organization='Test',role='admin')
assert api.health()['provider']=='mock'
"""


def job(project,id):
    return json.loads(python(project,CONTEXT+f"print(json.dumps(api.job(UUID('{id}'),v),default=str))"))


def wait(project,id):
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        row=job(project,id)
        if row['status'] not in {'queued','processing'}:
            if row['status']!='ready':
                raise RuntimeError('Synthetic rehearsal processing failed: '+str(row.get('error')))
            return row
        time.sleep(.5)
    raise TimeoutError('Synthetic processing exceeded its deadline.')


def artifacts(project):
    return json.loads(python(project,"""import hashlib,json
from pathlib import Path
root=Path('/artifacts')
print(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}))
"""))


def restore(project,image,folder):
    compose(project,image,'up','-d','--no-build','--wait','db')
    if db(project,"SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")!='0':
        raise RuntimeError('Restore target must be empty; refusing to overwrite any database.')
    run('docker','cp',str(folder/'database.dump'),project+'-db-1:/tmp/f13-rehearsal.dump')
    run('docker','exec',project+'-db-1','pg_restore','--exit-on-error','--no-owner','-U','brain','-d','brain','/tmp/f13-rehearsal.dump')
    volume=project+'_artifacts'
    run('docker','volume','create',volume)
    run('docker','run','--rm','--mount','type=volume,source='+volume+',target=/target',
        '--mount','type=bind,source='+str(folder)+',target=/backup,readonly',image,'python','-c',
        "import tarfile; tarfile.open('/backup/artifacts.tar.gz').extractall('/target',filter='data')")
    compose(project,image,'up','-d','--no-build','--wait','migrate','api','worker')


def main():
    global PROJECTS
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--legacy-image',default='company-brain-backend:local')
    parser.add_argument('--candidate-image',default='linkmind-f13-validation:local')
    parser.add_argument('--run-id',default='',help='Unique suffix for a fresh disposable rehearsal; never overwrites old runs')
    args=parser.parse_args()
    if args.run_id:
        if not re.fullmatch('[a-z0-9-]{1,20}',args.run_id):
            raise ValueError('Use a short lowercase alphanumeric rehearsal suffix.')
        PROJECTS=tuple(project+'-'+args.run_id for project in PROJECTS)
    output=args.output.resolve()
    if not output.is_relative_to((CODE.parent/'.local').resolve()) or output.exists():
        raise RuntimeError('Use a new output directory under the ignored repository .local directory.')
    for project in PROJECTS:
        if run('docker','ps','-aq','--filter','label=com.docker.compose.project='+project):
            raise RuntimeError('Rehearsal project already exists; refusing to overwrite it: '+project)
        if any(name.startswith(project+'_') for name in run('docker','volume','ls','--format','{{.Name}}').splitlines()):
            raise RuntimeError('Rehearsal volumes already exist; refusing to overwrite them.')
    output.mkdir(parents=True)
    report={'status':'started','main_mutated':False,'paid_calls':0}
    report['legacy_image_id']=json.loads(run('docker','image','inspect',args.legacy_image))[0]['Id']
    report['candidate_image_id']=json.loads(run('docker','image','inspect',args.candidate_image))[0]['Id']
    def save(step):
        report['step']=step
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(step,flush=True)
    try:
        report['main_inventory']=fingerprint('company-brain')
        report['main_backend_image']=json.loads(run('docker','inspect','company-brain-api-1'))[0]['Image']
        save('Read-only main inventory captured')
        legacy,candidate,rollback=PROJECTS
        compose(legacy,args.legacy_image,'up','-d','--no-build','--wait','db','migrate','api','worker')
        seed=json.loads(python(legacy,CONTEXT+"""from io import BytesIO
from pathlib import Path
from fastapi import UploadFile
r=api.upload(viewer=v,file=UploadFile(BytesIO(Path('/app/fixtures/cloud-migration.md').read_bytes()),filename='rollout-fixture.md'),visibility='team')
print(json.dumps(r,default=str))
"""))
        wait(legacy,seed['id'])
        saved=json.loads(python(legacy,CONTEXT+f"""c=api.create_conversation(api.NewConversation(document_ids=[UUID('{seed['document_id']}')]),v)
r=api.ask(c['id'],api.Question(question='Project Alpha'),v)
print(json.dumps(dict(conversation=str(c['id']),evidence=r['evidence'][0]['id'])))
"""))
        before=fingerprint(legacy)
        original_files=artifacts(legacy)
        report['legacy_before']=before
        report['seed']=seed
        report['saved_answer']=saved
        compose(legacy,args.legacy_image,'stop','api','worker')
        try:
            run('docker','exec',legacy+'-db-1','pg_dump','-U','brain','-d','brain','-Fc','-f','/tmp/f13-rehearsal.dump')
            run('docker','cp',legacy+'-db-1:/tmp/f13-rehearsal.dump',str(output/'database.dump'))
            run('docker','run','--rm','--mount','type=volume,source='+legacy+'_artifacts,target=/source,readonly',
                '--mount','type=bind,source='+str(output)+',target=/backup',args.legacy_image,'python','-c',
                "import tarfile; archive=tarfile.open('/backup/artifacts.tar.gz','w:gz'); archive.add('/source',arcname='.'); archive.close()")
        finally:
            compose(legacy,args.legacy_image,'start','api','worker')
        save('Synthetic database and originals backed up with writers stopped')
        restore(candidate,args.candidate_image,output)
        after=fingerprint(candidate)
        assert {k:v for k,v in before.items() if k!='schema'}=={k:v for k,v in after.items() if k!='schema'}
        assert original_files==artifacts(candidate)
        report['candidate_after_upgrade']=after
        assert after['schema']=='0011_staged_enrichment'
        checked=json.loads(python(candidate,CONTEXT+f"""assert api.evidence(UUID('{saved['evidence']}'),v)
assert api.history(UUID('{saved['conversation']}'),v)['turns'][0]['suppressed']
r=api.reprocess(UUID('{seed['id']}'),v)
print(json.dumps(dict(staged_version_id=str(r['staged_version_id']))))
"""))
        refreshed=wait(candidate,seed['id'])
        assert refreshed['active_enrichment_version_id']==checked['staged_version_id']
        assert fingerprint(candidate)['evidence']==before['evidence']
        save('Migration 0010 to 0011, citations, saved-answer policy and refresh verified')
        compose(candidate,args.candidate_image,'stop','api','worker')
        restore(rollback,args.legacy_image,output)
        assert fingerprint(rollback)==before
        assert artifacts(rollback)==original_files
        python(rollback,CONTEXT+f"assert api.evidence(UUID('{saved['evidence']}'),v)")
        report.update(status='passed',backup_restore_verified=True,legacy_rollback_verified=True,
            source_ids_and_files_preserved=True,main_after=fingerprint('company-brain'))
        assert report['main_after']==report['main_inventory']
        save('Legacy build restored from the reviewed snapshot; main remained unchanged')
    except Exception:
        report['status']='failed'
        save('Rehearsal stopped; retained artifacts require inspection')
        raise
    return 0


if __name__=='__main__':
    raise SystemExit(main())
