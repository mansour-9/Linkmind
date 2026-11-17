import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=async p=>JSON.parse(await fs.readFile(path.join(root,p),'utf8'));
const [issues,projects,employees,links,docs]=await Promise.all(['jira/seed-issues.json','organization/projects.json','organization/employees.json','jira/relationships.json','onedrive/documents.json'].map(read));
const byId=Object.fromEntries(issues.map(i=>[i.seed_id,i]));
const people=Object.fromEntries(employees.map(e=>[e.id,e.name]));
const excelDate=d=>(Date.parse(d+'T00:00:00Z')-Date.UTC(1899,11,30))/86400000;
const col=n=>{let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const checks=[];
await fs.mkdir(path.join(root,'validation','workbook-previews'),{recursive:true});

function table(wb,name,title,headers,rows,widths){
 const s=wb.worksheets.add(name);s.showGridLines=false;
 s.getRange('A2').values=[[title]];s.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:'#000000'};
 s.getRange('A3').values=[['As of November 16 2026']];s.getRange('A3').format.font={name:'Arial',size:10,italic:true,color:'#555555'};
 const end=col(headers.length-1),last=rows.length+5;
 s.getRange(`A5:${end}5`).values=[headers];
 if(rows.length)s.getRange(`A6:${end}${last}`).values=rows;
 s.getRange(`A5:${end}${last}`).format.font={name:'Arial',size:10,color:'#222222'};
 s.getRange(`A5:${end}${last}`).format.verticalAlignment='center';
 s.getRange(`A5:${end}5`).format={fill:'#243B53',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,rowHeight:34};
 s.getRange(`A6:${end}${last}`).format.rowHeight=35;
 s.getRange(`A6:${end}${last}`).format.wrapText=true;
 widths.forEach((w,i)=>s.getRange(`${col(i)}5:${col(i)}${last}`).format.columnWidth=w);
 s.getRange(`A5:${end}5`).format.borders={bottom:{style:'thin',color:'#D9D9D9'}};
 s.freezePanes.freezeRows(5);
 return s;
}
function dates(s,column,n){s.getRange(`${column}6:${column}${n+5}`).setNumberFormat('yyyy-mm-dd');}
function status(s,column,n){for(const text of ['Blocked','Red','Pending','Amber'])s.getRange(`${column}6:${column}${n+5}`).conditionalFormats.add('containsText',{text,format:{fill:text==='Red'||text==='Blocked'?'#FCE8E6':'#FFF2CC',font:{color:'#922222'}}});}

for(const item of docs.filter(d=>d.format==='xlsx')){
 const wb=Workbook.create();let sheet,expectation,verifyCell;
 if(item.seed_id==='project-tracker'){
  const rows=projects.map(p=>[p.key,people[p.technical_owner],excelDate(p.original_target),excelDate(p.current_target),null,p.risk,p.summary,byId[p.key.toLowerCase()+'-readiness']?.publication.key??byId['harbor-checklist'].publication.key]);
  sheet=table(wb,'Milestones',item.title,['Project','Technical owner','Original target','Current target','Slip days','Risk','Reason','Jira evidence'],rows,[14,22,16,16,12,12,62,19]);
  rows.forEach((r,i)=>sheet.getRange('E'+(i+6)).formulas=[['=D'+(i+6)+'-C'+(i+6)]]);dates(sheet,'C',3);dates(sheet,'D',3);status(sheet,'F',3);
  expectation=7;verifyCell='E6';
  const detail=issues.map(i=>[i.publication.key,i.project,i.summary,people[i.fictional_owner],i.business_state,excelDate(i.due_date),i.publication.url]);
  const s=table(wb,'Work records','Project work records',['Jira key','Project','Work item','Owner','Business state','Due date','Source URL'],detail,[18,14,62,22,18,16,65]);dates(s,'F',detail.length);status(s,'E',detail.length);
 }else if(item.seed_id==='dependency-tracker'){
  const rows=links.map(l=>[byId[l.inward_seed].publication.key,byId[l.inward_seed].project,l.type,byId[l.outward_seed].publication.key,byId[l.outward_seed].project,byId[l.inward_seed].business_state,byId[l.outward_seed].business_state,byId[l.inward_seed].publication.url]);
  sheet=table(wb,'Dependencies',item.title,['Upstream key','Upstream project','Relationship','Downstream key','Downstream project','Upstream state','Downstream state','Source URL'],rows,[18,19,16,19,21,19,20,64]);status(sheet,'G',rows.length);
  sheet.getRange('A29').values=[['Blocking relationships']];sheet.getRange('C29').formulas=[['=COUNTIFS(C6:C26,"Blocks")']];expectation=links.filter(l=>l.type==='Blocks').length;verifyCell='C29';
 }else if(item.seed_id==='risk-register'){
  const rows=[['R01','Identity contract incomplete','ATLAS',people.omar,4,5,null,'Open',excelDate('2026-11-18'),byId['atlas-claims'].publication.key],['R02','Events delay reporting pilot','BEACON',people.grace,4,4,null,'Open',excelDate('2026-11-20'),byId['atlas-event-api'].publication.key],['R03','Warehouse tenant partition','BEACON',people.noah,3,5,null,'Open',excelDate('2026-11-18'),byId['beacon-tenant-partition'].publication.key],['R04','Partner agreement unsigned','HARBOR',people.aisha,3,4,null,'Open',excelDate('2026-11-24'),byId['harbor-business-approval'].publication.key],['R05','Refresh replay regression','ATLAS',people.noah,1,5,null,'Mitigated',excelDate('2026-11-13'),byId['atlas-tenant-leak'].publication.key],['R06','Stale pilot communication','Portfolio',people.chloe,2,3,null,'Open',excelDate('2026-11-20'),byId['beacon-sales-pack'].publication.key]];
  sheet=table(wb,'Risks',item.title,['Risk ID','Risk','Project','Owner','Likelihood 1 to 5','Impact 1 to 5','Score','State','Review date','Jira evidence'],rows,[12,37,15,22,18,17,12,16,16,20]);
  rows.forEach((r,i)=>sheet.getRange('G'+(i+6)).formulas=[['=E'+(i+6)+'*F'+(i+6)]]);dates(sheet,'I',rows.length);
  sheet.getRange('E6:F11').dataValidation={rule:{type:'whole',operator:'between',formula1:1,formula2:5}};
  sheet.getRange('G6:G11').conditionalFormats.add('cellIs',{operator:'greaterThanOrEqual',formula:15,format:{fill:'#FCE8E6',font:{color:'#922222'}}});expectation=20;verifyCell='G6';
 }else if(item.seed_id==='resource-plan'){
  const allocation={maya:40,omar:48,priya:38,leo:44,elena:32,daniel:36,aisha:40,sofia:40,noah:42,yara:38,ben:40,ines:40,samir:38,grace:44,tomas:38,fatima:42,chloe:38,ethan:36};
  const rows=employees.map(e=>[e.name,e.team,e.role,40,allocation[e.id],null,[...new Set(issues.filter(i=>i.fictional_owner===e.id).map(i=>i.project))].join(', '),e.id==='leo'?byId['harbor-ownership'].publication.key:'Fictional capacity plan']);
  sheet=table(wb,'Capacity',item.title,['Employee','Team','Role','Capacity hours','Planned hours','Excess hours','Assigned projects','Basis'],rows,[23,21,31,17,17,17,29,27]);rows.forEach((r,i)=>sheet.getRange('F'+(i+6)).formulas=[['=MAX(0,E'+(i+6)+'-D'+(i+6)+')']]);
  sheet.getRange('F6:F23').conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0,format:{fill:'#FFF2CC',font:{color:'#8B4A00'}}});expectation=8;verifyCell='F7';
 }else if(item.seed_id==='atlas-tracker'){
  const list=issues.filter(i=>i.project==='ATLAS');const rows=list.map(i=>[i.publication.key,i.summary,people[i.fictional_owner],i.issue_type,i.business_state,i.priority,excelDate(i.due_date),i.publication.url]);
  sheet=table(wb,'ATLAS work',item.title,['Jira key','Work item','Owner','Type','Business state','Priority','Due date','Source URL'],rows,[17,62,22,16,19,16,16,65]);dates(sheet,'G',rows.length);status(sheet,'E',rows.length);
  sheet.getRange('A44').values=[['Blocked work items']];sheet.getRange('C44').formulas=[['=COUNTIFS(E6:E41,"Blocked")']];expectation=list.filter(i=>i.business_state==='Blocked').length;verifyCell='C44';
 }else{
  const rows=[['ATLAS','Technical','Blocked',people.omar,'Claims and event API incomplete',byId['atlas-readiness'].publication.key],['ATLAS','Security','Pending',people.sofia,'Consumer acceptance still open',byId['atlas-claims'].publication.key],['ATLAS','Business','Pending',people.elena,'Product acceptance not recorded',byId['atlas-approval'].publication.key],['BEACON','Technical','Blocked',people.grace,'Final event integration incomplete',byId['beacon-readiness'].publication.key],['BEACON','Security','Pending',people.yara,'Partition and privacy evidence open',byId['beacon-tenant-partition'].publication.key],['BEACON','Business','Pending',people.elena,'Reporting pilot approval not recorded',byId['beacon-approval'].publication.key],['HARBOR','Delivery subsystem','Complete',people.ben,'Webhook delivery accepted November 13',byId['harbor-technical-ready'].publication.key],['HARBOR','Authentication','Blocked',people.leo,'Claims v2 consumer acceptance open',byId['harbor-auth-integration'].publication.key],['HARBOR','Business','Blocked',people.aisha,'Agreement and Product approval open',byId['harbor-business-approval'].publication.key]];
  sheet=table(wb,'Release gates',item.title,['Project','Gate','State','Owner','Decision evidence','Jira evidence'],rows,[15,23,18,23,62,21]);status(sheet,'C',rows.length);
  sheet.getRange('A18:C18').values=[['Project','Open gates','Overall release']];sheet.getRange('A19:A21').values=[['ATLAS'],['BEACON'],['HARBOR']];
  for(let r=19;r<=21;r++){sheet.getRange('B'+r).formulas=[['=COUNTIFS(A6:A14,A'+r+',C6:C14,"<>Complete")']];sheet.getRange('C'+r).formulas=[['=IF(B'+r+'=0,"Ready","Blocked")']];}
  status(sheet,'C',16);expectation=2;verifyCell='B21';
 }
 wb.recalculate();
 const actual=sheet.getRange(verifyCell).values[0][0];if(actual!==expectation)throw Error(item.seed_id+' formula mismatch '+actual+' != '+expectation);
 const probes={
  'project-tracker':['D6',excelDate('2026-11-28'),8],
  'dependency-tracker':['C6','Relates',14],
  'risk-register':['E6',3,15],
  'resource-plan':['E7',50,10],
  'atlas-tracker':['E6','Blocked',4],
  'release-checklist':['C12','Pending',3],
 };
 const [inputCell,temporary,expectedChange]=probes[item.seed_id];
 const original=sheet.getRange(inputCell).values[0][0];sheet.getRange(inputCell).values=[[temporary]];wb.recalculate();
 const changed=sheet.getRange(verifyCell).values[0][0];if(changed!==expectedChange)throw Error(item.seed_id+' recalculation probe failed');
 sheet.getRange(inputCell).values=[[original]];wb.recalculate();
 if(sheet.getRange(verifyCell).values[0][0]!==expectation)throw Error(item.seed_id+' restoration failed');
 const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},maxChars:2000});
 const inspection=await wb.inspect({kind:'table',range:sheet.name+'!A5:F9',include:'values,formulas',tableMaxRows:5,tableMaxCols:6,maxChars:2000});
 const previews=[];
 for(const s of wb.worksheets.items){const blob=await wb.render({sheetName:s.name,range:'A1:'+ (s.name==='Milestones'?'H10':s.name==='Risks'?'J12':s.name==='Release gates'?'F21':s.name==='Capacity'?'H12':'H12'),scale:1,format:'png'});const filename=item.seed_id+'-'+s.name.replace(/[^a-z0-9]/gi,'-')+'.png';await fs.writeFile(path.join(root,'validation/workbook-previews',filename),new Uint8Array(await blob.arrayBuffer()));previews.push(filename);}
 const out=path.join(root,item.path);await fs.mkdir(path.dirname(out),{recursive:true});const blob=await SpreadsheetFile.exportXlsx(wb);await blob.save(out);
 checks.push({seed_id:item.seed_id,cell:verifyCell,expected:expectation,actual,formula_check:'passed',recalculation_probe:{input:inputCell,temporary,result:changed,expected:expectedChange,restored:true},error_scan:errors.ndjson,inspection:inspection.ndjson,previews});console.log(JSON.stringify({workbook:item.seed_id,formula:actual,recalculation:'passed',exported:true}));
}
await fs.writeFile(path.join(root,'validation/workbooks.json'),JSON.stringify(checks,null,2)+'\n');
