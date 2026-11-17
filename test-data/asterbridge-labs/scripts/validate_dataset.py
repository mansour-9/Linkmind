"""Validate authored records, confirmed readbacks, links, files, and evaluation grounding."""
from pathlib import Path
from collections import Counter
import hashlib, json, re, sys, os
from datetime import date
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from docx import Document
from openpyxl import load_workbook
from catalog import BUSINESS_EVIDENCE, TECHNICAL_EVIDENCE, AS_OF

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def save(p,v):(ROOT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
errors=[];count=0
def check(condition,message):
    global count
    count+=1
    if not condition:errors.append(message)
def norm(text):return re.sub(r'\s+',' ',str(text)).strip()

issues=read('jira/seed-issues.json');pages=read('confluence/pages.json');docs=read('onedrive/documents.json')
remote=read('jira/remote-map.json');page_map=read('confluence/remote-map.json');people=read('organization/employees.json')
links=read('jira/relationships.json');cases=read('test-cases/all-tests.json')
snapshots={p.stem:json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'jira/snapshots').glob('*.json')}
page_snapshot=read('confluence/space-snapshot.json')
native_pages={str(p['id']):p for p in page_snapshot['results']}
by_id={i['seed_id']:i for i in issues};by_doc={d['seed_id']:d for d in docs};by_page={p['seed_id']:p for p in pages}
check(len(issues)==108,'108 authored Jira issues required')
check(Counter(i['project'] for i in issues)==dict(ATLAS=36,BEACON=36,HARBOR=36),'Project issue distribution')
check(len(by_id)==len(issues),'Unique seed IDs')
check(len(people)==18 and len({p['id'] for p in people})==18,'18 unique fictional employees')
check(len({p['team'] for p in people})==6,'Six functional teams')
check(len(snapshots)==108 and len(remote)==108,'Complete Jira readback and map')
check(len(pages)==25 and len(page_map)==25,'25 published Confluence pages')
check(len(docs)==18 and Counter(d['format'] for d in docs)==dict(docx=12,xlsx=6),'18 actual business artifacts')
check(len(cases)==62 and len({c['id'] for c in cases})==62,'62 unique evaluation cases')
owner_ids={p['id'] for p in people}
for i in issues:
    seed=i['seed_id'];r=remote[seed];s=snapshots[r['key']];f=s['fields']
    check(s['id']==r['id'] and s['key']==r['key'],'Source identity '+seed)
    check(f['project']['key']==i['project'],'Native project '+seed)
    check(f['summary']==i['summary'],'Summary '+seed)
    check(f['issuetype']['name']==i['issue_type'],'Issue type '+seed)
    check(f['priority']['name']==i['priority'],'Priority '+seed)
    check(f['duedate']==i['due_date'],'Due date '+seed)
    check(i['fictional_owner'] in owner_ids,'Owner '+seed)
    expected='In Progress' if i['business_state']=='Blocked' else i['business_state']
    check(f['status']['name']==expected,'Native status '+seed)
    check(('abl-blocked' in f['labels'])==(i['business_state']=='Blocked'),'Blocked representation '+seed)
    check('asterbridge-labs-v1' in f['labels'] and 'abl-seed-'+seed in f['labels'],'Idempotency labels '+seed)
    check(f.get('assignee') is None,'No fictional native account '+seed)
    check(len(i['acceptance_criteria'])>=3,'Acceptance criteria '+seed)
    check(all(norm(c) in norm(f['description']) for c in i['acceptance_criteria']),'Published acceptance criteria '+seed)
    check('local seed' not in f['description'] and 'not published' not in f['description'],'Resolved Jira dependency references '+seed)
    if i['parent_seed']:check(f.get('parent',{}).get('key')==remote[i['parent_seed']]['key'],'Parent '+seed)
    comments=f.get('comment',{})
    check(comments.get('total')==1 and len(comments.get('comments',[]))==1,'Complete single history comment '+seed)
    check(any('ABL-HISTORY:'+seed+':v1' in str(c.get('body','')) for c in comments.get('comments',[])),'Comment seed marker '+seed)
    check(f.get('created') is not None and f.get('updated') is not None,'Actual source timestamps '+seed)
    check(date.fromisoformat(i['due_date'])<=date.fromisoformat(AS_OF) if i['business_state']=='Done' else True,'Completed narrative due date '+seed)

for l in links:
    a=remote[l['inward_seed']]['key'];b=remote[l['outward_seed']]['key']
    check(any(x['type']['name']==l['type'] and x.get('outwardIssue',{}).get('key')==b for x in snapshots[a]['fields'].get('issuelinks',[])),'Native link direction '+a+' '+l['type']+' '+b)
    check(any(x['type']['name']==l['type'] and x.get('inwardIssue',{}).get('key')==a for x in snapshots[b]['fields'].get('issuelinks',[])),'Native inverse link '+b)
check(sum(by_id[l['inward_seed']]['project']!=by_id[l['outward_seed']]['project'] for l in links)>=8,'Meaningful cross project dependencies')

def visit(seed,visiting,done):
    check(seed not in visiting,'No blocking cycle '+seed)
    if seed in visiting or seed in done:return
    visiting.add(seed)
    for l in links:
        if l['type']=='Blocks' and l['inward_seed']==seed:visit(l['outward_seed'],visiting,done)
    visiting.remove(seed);done.add(seed)
done=set()
for seed in by_id:visit(seed,set(),done)

for p in pages:
    r=page_map[p['seed_id']]
    check(r['status']=='published' and str(r['id']) in native_pages,'Confirmed page '+p['seed_id'])
    check(native_pages[str(r['id'])]['title']==p['title'],'Published page title '+p['seed_id'])
    check(len(p['body'].split())>=250,'Substantial page '+p['seed_id'])
    check('local seed' not in p['body'] and 'not published' not in p['body'],'Actual Jira references in page '+p['seed_id'])
    check(all(remote[id]['key'] in p['body'] for id in p['issue_seeds']),'Page issue traceability '+p['seed_id'])
    check(str(native_pages[str(r['id'])].get('spaceId',r['space_id']))=='262712','Dedicated test space '+p['seed_id'])

workbook_checks=read('validation/workbooks.json')
for w in workbook_checks:
    check(w['formula_check']=='passed' and w['actual']==w['expected'],'Workbook formula '+w['seed_id'])
    check(w['recalculation_probe']['restored'] and w['recalculation_probe']['result']==w['recalculation_probe']['expected'],'Workbook input response '+w['seed_id'])
    check('matched 0 entries' in w['error_scan'],'Formula error scan '+w['seed_id'])
    check(all((ROOT/'validation/workbook-previews'/p).exists() for p in w['previews']),'Workbook preview files '+w['seed_id'])

doc_checks=[];all_urls={r['url'] for r in remote.values()}
for d in docs:
    target=ROOT/d['path'];check(target.is_file() and target.stat().st_size>0,'Nonempty business file '+d['path'])
    check((ROOT/d['editable_source']).exists(),'Editable source '+d['seed_id'])
    check(d['publication']['status']=='local_only' and d['publication']['id'] is None,'Honest upload state '+d['seed_id'])
    with ZipFile(target) as z:
        check(z.testzip() is None,'OOXML package integrity '+d['seed_id'])
        if d['format']=='docx':
            xml=ET.fromstring(z.read('word/document.xml'))
            text=' '.join(t.text or '' for t in xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
            check(d['title'] in text,'Word title '+d['seed_id'])
            check(all(norm(body) in norm(text) for heading,body in d['sections'] if heading!='Supporting work records'),'Word source fidelity '+d['seed_id'])
            check('local seed' not in text,'Word references resolved '+d['seed_id'])
            rels=ET.fromstring(z.read('word/_rels/document.xml.rels'))
            urls=[r.attrib['Target'] for r in rels if r.attrib.get('Type','').endswith('/hyperlink')]
            check(all(u in all_urls for u in urls),'Word hyperlink targets '+d['seed_id'])
            check(len(urls)==len(d['issue_seeds']),'Word hyperlink count '+d['seed_id'])
            doc_checks.append(dict(seed_id=d['seed_id'],structural_check='passed',hyperlinks=len(urls),render_status='blocked_missing_libreoffice',render_error='render_docx.py: FileNotFoundError: LibreOffice soffice.exe was not found on PATH',visual_review=False))
        else:
            wf=load_workbook(target,read_only=False,data_only=False);wv=load_workbook(target,read_only=True,data_only=True)
            check(all(c.data_type!='e' for s in wv for row in s for c in row),'Saved XLSX error cells '+d['seed_id'])
            proof=next(w for w in workbook_checks if w['seed_id']==d['seed_id'])
            check(wv.worksheets[0][proof['cell']].value==proof['expected'],'Exported formula cached value '+d['seed_id'])
            check(str(wf.worksheets[0][proof['cell']].value).startswith('='),'Exported native formula '+d['seed_id'])
            check(all(s.freeze_panes=='A6' for s in wf),'Workbook frozen headings '+d['seed_id'])
            wf.close();wv.close()

for fid,(did,detail) in BUSINESS_EVIDENCE.items():
    check(any(detail in b for h,b in by_doc[did]['sections']),'Business evidence in intended report '+fid)
    check(all(detail not in i['description'] for i in issues),'Business evidence absent from Jira '+fid)
    check(all(detail not in p['body'] for p in pages),'Business evidence absent from Confluence '+fid)
for fid,(pid,detail) in TECHNICAL_EVIDENCE.items():check(detail in by_page[pid]['body'],'Technical evidence '+fid)
for c in cases:
    check(c['execution_status']=='not_run','No unexecuted application pass '+c['id'])
    for source in c['supporting_sources']:
        check((ROOT/source['path']).exists(),'Evaluation source exists '+c['id']+' '+source['seed_id'])
    if c.get('required_source_types'):
        check(set(c['required_source_types'])<=set(s['source'] for s in c['supporting_sources']),'Required source coverage '+c['id'])
    if c.get('fact_id') and c['stage']=='C':check(set(c['required_contributions'])=={'jira','confluence','onedrive'},'Distinct Stage C evidence '+c['id'])

native_counts=Counter(s['fields']['status']['name'] for s in snapshots.values())
business_counts=Counter(i['business_state'] for i in issues)
summary=dict(status='passed' if not errors else 'failed',checks=count,errors=errors,counts=dict(employees=len(people),teams=6,jira_projects=3,jira_issues=len(issues),jira_snapshots=len(snapshots),jira_comments=sum(s['fields']['comment']['total'] for s in snapshots.values()),jira_relationships=len(links),cross_project_relationships=sum(by_id[l['inward_seed']]['project']!=by_id[l['outward_seed']]['project'] for l in links),confluence_authored_pages=len(pages),docx=12,xlsx=6,evaluation_cases=len(cases)),native_statuses=dict(native_counts),business_states=dict(business_counts),stages=dict(Counter(c['stage'] for c in cases)),workbook_visual_review='7 sheet previews reviewed',workbook_native_excel_trial='not_run',word_visual_review='blocked_missing_libreoffice',linkmind_application_evaluation='not_run',onedrive_connector_upload='not_performed',real_permission_acceptance='not_run')
save('validation/consistency.json',summary);save('validation/documents.json',doc_checks)
if errors:
    print(json.dumps(summary,ensure_ascii=False));sys.exit(1)

manifest=read('source-manifest.json')
for i in manifest['issues']:i['snapshot_path']='jira/snapshots/'+remote[i['seed_id']]['key']+'.json'
manifest['validation']='validation/consistency.json';manifest['counts']=summary['counts'];manifest['evaluation_status']='prepared_not_run'
manifest['confluence_layout']=dict(space_key='ABL',space_id='262712',logical_groups=['COMPANY','ENGINEERING','ATLAS','BEACON','HARBOR'],authored_pages=25,platform_generated_pages_excluded=3)
manifest['artifact_status']=dict(docx='generated_structurally_verified_render_blocked',xlsx='generated_formula_and_preview_verified',onedrive_upload='not_performed',intended_acl_metadata_is_not_enforcement=True)
save('source-manifest.json',manifest)
jira=read('jira/jira-manifest.json');jira['snapshot_count']=len(snapshots);jira['comments_confirmed']=108;jira['relationships_confirmed']=len(links);jira['native_statuses']=dict(native_counts);jira['business_states']=dict(business_counts);jira['readback_validation']='validation/consistency.json';save('jira/jira-manifest.json',jira)
inventory=[]
for current,dirs,files in os.walk(ROOT,followlinks=False):
    dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__'}]
    for name in sorted(files):
        p=Path(current)/name
        if p.name.endswith('.inspect.ndjson') or p.name=='content-hashes.json':continue
        inventory.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
save('validation/content-hashes.json',inventory)
print(json.dumps(summary,ensure_ascii=False))
