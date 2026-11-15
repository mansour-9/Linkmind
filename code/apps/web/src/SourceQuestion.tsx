import { useState } from 'react';
import { useMutation,useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus,Trash2 } from 'lucide-react';
import { useSession,useViewer } from './session';
import { Button,Feedback,PageHeading,Sheet } from './ui';
import { FocusSources } from './FocusSources';
import './source-question.css';

type Connection={id:string;name:string;kind:string;scope:string;mode:string;execution:string};
type Resource={connection_id:string;native_id:string};
type Source={reference_id:string;name:string;kind:'passage'|'fields';origin:'stored'|'live';text:string|null;fields:{field:string;value:unknown}[];original_url:string|null;observed_at:string|null;source_updated_at:string|null;source_revision:string;synthetic:boolean;revision_role:string};
type Reference={reference_id:string;kind:'passage'|'field';quote:string|null;field:string|null;value:unknown};
type Result={statements:{text:string;evidence:Reference[]}[];sources:Source[];provider:string;partial:boolean;insufficient_evidence:boolean;message:string|null;access_check:unknown;source_outcomes:{connection_id:string;code:string;message:string}[];coverage:{partial:boolean;supplied_passages:number;total_passages:number}|null};

export default function SourceQuestion(){
 const {service}=useSession();const viewer=useViewer();
 const connections=useQuery({queryKey:['retrieval-connections'],queryFn:()=>service.json<Connection[]>('/retrieval/connections')});
 const [documents,setDocuments]=useState<string[]>([]);const [resources,setResources]=useState<Resource[]>([]);const [question,setQuestion]=useState('');
 const [result,setResult]=useState<Result|null>(null);const [asked,setAsked]=useState('');const [opened,setOpened]=useState<Source|null>(null);
 const request=useMutation({mutationFn:()=>service.json<Result>('/source-answers',{method:'POST',body:JSON.stringify({question,document_ids:documents,live_resources:resources})}),onSuccess:value=>{setAsked(question);setResult(value);}});
 const access=useQuery({queryKey:['source-answer-access',result?.access_check],enabled:!!result,queryFn:()=>service.json<{allowed:boolean}>('/source-answers/access',{method:'POST',body:JSON.stringify(result!.access_check)}),refetchInterval:30000,refetchOnWindowFocus:true});
 const visible=!!result&&access.isSuccess&&access.data.allowed;
 const reset=()=>{setResult(null);setOpened(null);request.reset();};
 const update=(index:number,change:Partial<Resource>)=>{reset();setResources(rows=>rows.map((row,i)=>i===index?{...row,...change}:row));};
 const numbers=new Map(result?.sources.map((s,i)=>[s.reference_id,i+1] as const));
 async function openSource(source:Source){const check=await access.refetch();if(check.data?.allowed)setOpened(source);else setOpened(null);}
 return <div className="page source-question-page">
 <Link to="/" className="muted">← Back to Assistant</Link>
 <PageHeading title="Ask across sources" description="Combine selected documents with a fresh reading from the connected resources you choose."/>
 <section className="source-question-selection" aria-label="Question sources">
 <h2>Stored documents</h2><FocusSources value={documents} onChange={ids=>{reset();setDocuments(ids);}} disabled={request.isPending} conversation={false} explicitOnly/>
 <h2>Connected resources</h2><p className="muted">Choose up to two resources. Only these resources will be read; adding a source does not import its content.</p>
 {connections.isPending&&<Feedback>Loading available connections…</Feedback>}{connections.isError&&<Feedback error>{connections.error.message}</Feedback>}
 {connections.isSuccess&&!connections.data.length&&<Feedback>No enabled connections are available to your identity. {viewer.data?.role==='admin'&&<Link to="/admin/connections">Manage connections</Link>}</Feedback>}
 {resources.map((resource,index)=><div className="source-question-resource" key={index}>
 <label>Connection {index+1}<select aria-label={'Connection '+(index+1)} value={resource.connection_id} disabled={request.isPending} onChange={event=>{const c=connections.data?.find(c=>c.id===event.target.value);update(index,{connection_id:event.target.value,native_id:c?.execution==='mock'?'demo-1':''});}}>{!connections.data?.some(c=>c.id===resource.connection_id)&&<option value={resource.connection_id}>Selected connection unavailable</option>}{connections.data?.map(c=><option key={c.id} value={c.id}>{c.name} · {c.scope}{c.execution==='mock'?' · Demo':''}</option>)}</select></label>
 <label>Issue key or resource ID<input aria-label={'Resource ID '+(index+1)} value={resource.native_id} disabled={request.isPending} maxLength={200} onChange={event=>update(index,{native_id:event.target.value})} placeholder="e.g. HB-42"/></label>
 <Button variant="ghost" aria-label={'Remove resource '+(index+1)} disabled={request.isPending} onClick={()=>{reset();setResources(rows=>rows.filter((_,i)=>i!==index));}}><Trash2 size={16}/></Button>
 {connections.data?.find(c=>c.id===resource.connection_id)?.execution==='mock'&&<p className="muted source-question-demo">Demo uses synthetic evidence. Resource ID: demo-1.</p>}
 </div>)}
 <Button variant="outline" disabled={request.isPending||resources.length>=2||!connections.data?.length} onClick={()=>{reset();const c=connections.data![0];setResources(rows=>[...rows,{connection_id:c.id,native_id:c.execution==='mock'?'demo-1':''}]);}}><Plus size={16}/>Add connected resource</Button>
 </section>
 <form className="source-question-form" onSubmit={event=>{event.preventDefault();setResult(null);setOpened(null);request.mutate();}}>
 <label>Your question<textarea aria-label="Cross-source question" value={question} maxLength={2000} disabled={request.isPending} onChange={event=>{reset();setQuestion(event.target.value);}} placeholder="Why did the delivery date change, and what is the current issue status?"/></label>
 <Button type="submit" disabled={request.isPending||question.trim().length<2||(!documents.length&&!resources.length)||resources.some(r=>!r.native_id.trim())}>{request.isPending?'Reading selected sources…':'Ask selected sources'}</Button>
 <p className="muted">This result is temporary. Live readings are not added to the repository or saved in conversation history.</p>
 </form>
 {request.isError&&<Feedback error>{request.error.message} Your question and selection are kept.</Feedback>}
 {result&&access.isPending&&<Feedback>Checking source access…</Feedback>}
 {result&&(access.isError||(access.isSuccess&&!access.data.allowed))&&<Feedback error>This result is hidden because source access, revisions or connection settings could not be confirmed. Ask again for current evidence.</Feedback>}
 {visible&&<section className="source-question-result" aria-label="Cross-source result"><h2 dir="auto">{asked}</h2>
 <p className="answer-provider">{result.provider==='bedrock'?'Sonnet · verified source answer':'Demo · verbatim excerpts and actual source fields'}</p>
 {result.provider!=='bedrock'&&<Feedback>Demo mode shows retrieved evidence. AI synthesis quality has not been evaluated by this result.</Feedback>}
 {result.message&&<Feedback>{result.message}</Feedback>}
 {(result.partial||result.insufficient_evidence)&&<Feedback>The selected evidence does not establish a complete answer to every part. Source failures and partial context are shown below.</Feedback>}
 {result.source_outcomes.filter(o=>o.code!=='observed').map((o,i)=><Feedback key={i}>{connections.data?.find(c=>c.id===o.connection_id)?.name??'Selected source'}: {o.message}</Feedback>)}
 {result.coverage?.partial&&<p className="muted">Stored context: {result.coverage.supplied_passages} of {result.coverage.total_passages} passages. This is a partial review.</p>}
 {result.statements.map((statement,i)=><article key={i}><p dir="auto" className="source-question-statement">{statement.text}</p><div className="evidence-row">{[...new Set(statement.evidence.map(e=>e.reference_id))].map(id=>{const source=result.sources.find(s=>s.reference_id===id);return source&&<Button key={id} variant="ghost" onClick={()=>void openSource(source)} aria-label={'Open source '+numbers.get(id)}>[{numbers.get(id)}] {source.name}</Button>;})}</div></article>)}
 <details><summary>Source observations · {result.sources.length}</summary><div className="source-question-observations">{result.sources.map(source=><div key={source.reference_id}><Button variant="ghost" onClick={()=>void openSource(source)}>[{numbers.get(source.reference_id)}] {source.name}</Button><p>{source.origin==='live'?'Live observation':'Saved evidence'}{source.revision_role==='previous'?' · Previous revision':''}{source.synthetic?' · Synthetic demo':''}</p><small>{source.observed_at?'Observed/received: '+new Date(source.observed_at).toLocaleString():'Observation time unavailable'}</small></div>)}</div></details>
 </section>}
 <Sheet title="Source evidence" description={opened?.name??''} open={!!opened&&visible} onOpenChange={open=>{if(!open)setOpened(null);}}>
 {opened&&<div className="source-question-evidence"><Feedback>{opened.origin==='live'?'Live resource observation':'Retained source evidence'}{opened.synthetic?' · Synthetic demonstration fixture':''}</Feedback>
 <p>Source revision: {opened.source_revision}</p>{opened.source_updated_at&&<p>Source updated: {new Date(opened.source_updated_at).toLocaleString()}</p>}{opened.observed_at&&<p>Observed/received: {new Date(opened.observed_at).toLocaleString()}</p>}
 {opened.kind==='passage'?<blockquote dir="auto">{opened.text}</blockquote>:<dl>{opened.fields.map(field=><div key={field.field}><dt>{field.field}</dt><dd dir="auto">{typeof field.value==='string'?field.value:JSON.stringify(field.value)}</dd></div>)}</dl>}
 {opened.original_url&&!opened.synthetic&&<a href={opened.original_url} target="_blank" rel="noopener noreferrer">Open original source</a>}
 </div>}</Sheet>
 </div>;
}
