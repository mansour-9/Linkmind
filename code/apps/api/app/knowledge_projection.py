"""Project explicitly recorded facts from an immutable synchronized revision."""
import json
import re
from urllib.parse import urlsplit

from app.contracts import Extraction
from app.db import sql


def project(conn,job,passages):
    record=sql(conn,"""SELECT r.fields,r.payload,r.original_url,s.kind,d.title FROM connected_revisions r
        JOIN source_instances s ON s.id=r.connection_id JOIN documents d ON d.id=:document
        WHERE r.version_id=:version ORDER BY r.observed_at DESC,r.id DESC LIMIT 1""",
        document=job.document_id,version=job.version_id).mappings().first()
    result=dict(entities=[],claims=[],relationships=[])
    if not record:return Extraction(**result)
    job.knowledge_host=urlsplit(record.original_url).hostname or ''
    job.knowledge_source_ids={}

    def cite(quote):
        return [dict(passage_id=p['id'],quote=quote) for p in passages if quote in p['text']][:1]

    def entity(key,kind,name,evidence,identifier=None):
        if name and evidence and not any(row['key']==key for row in result['entities']):
            result['entities'].append(dict(key=key,kind=kind,name=name,evidence=evidence,
                identifiers=[dict(namespace=identifier[0],value=identifier[1])] if identifier else []))

    def link(left,right,predicate,evidence):
        known={row['key'] for row in result['entities']}
        if evidence and left in known and right in known and not any(
            (r['source_key'],r['target_key'],r['predicate'])==(left,right,predicate) for r in result['relationships']):
            result['relationships'].append(dict(source_key=left,target_key=right,predicate=predicate,evidence=evidence))

    if record.kind=='jira':
        fields={item['field']:item['value'] for item in record.fields}
        issue=fields.get('key')
        if isinstance(issue,str):
            entity('issue','task',issue+' — '+(fields.get('summary') or issue),cite(issue),('issue_key',issue))
        project=fields.get('project')
        if isinstance(project,dict) and isinstance(project.get('key'),str):
            key=project['key'];proof=cite('project: '+json.dumps(project,ensure_ascii=False)) or cite('"'+key+'"')
            entity('project','project',project.get('name') or key,proof,('project_key',key))
            link('issue','project','belongs_to_project',proof)
        assignee=fields.get('assignee')
        if isinstance(assignee,str):
            proof=cite('assignee: '+json.dumps(assignee,ensure_ascii=False))
            entity('assignee','person',assignee,proof)
            raw=record.payload.get('fields',{}).get('assignee') or {}
            account=raw.get('accountId') if isinstance(raw,dict) else None
            if isinstance(account,str) and account.strip() and job.knowledge_host:
                job.knowledge_source_ids['assignee']=job.knowledge_host+':'+account
            link('issue','assignee','assigned_to',proof)
    else:
        first=next((p['text'].strip().splitlines()[0] for p in passages if p['text'].strip()),'')
        if first:entity('document','document',record.title or job.filename,cite(first))
        for passage in passages:
            owner=re.fullmatch(r'Owner:\s+([^.;\n]{2,90})',passage['text'].strip())
            if owner:
                proof=cite(owner[0])
                entity('page_owner','person',owner[1].strip(),proof)
                link('page_owner','document','owns_document',proof)
            for match in re.finditer(r'\b([A-Z][A-Z0-9_]{2,20}) (product|technical|delivery accountable) owner:\s+([^.;\n]{2,90})',passage['text']):
                if len(result['entities'])>=95:break
                key,role,name=match.groups()
                proof=cite(match[0]);person='person:'+key+':'+role
                entity('project:'+key,'project',key,proof,('project_key',key))
                entity(person,'person',name.strip(),proof)
                link(person,'project:'+key,role.replace(' ','_')+'_owner_of',proof)
    return Extraction.model_validate(result)
