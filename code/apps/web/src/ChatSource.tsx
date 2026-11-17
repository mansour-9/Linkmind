import { useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ExternalLink, FileText, Info } from 'lucide-react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useSession, useViewer } from './session';
import { Button, Feedback, Sheet } from './ui';
import { SourcePreview } from './Evidence';
import type { Passage,RetainedDependency } from './contracts';

type LiveEvidence={source_revision:string;original_url:string;observed_at:string;source_updated_at:string;excerpt:string|null;fields:{field:string;value:unknown}[]};
function readable(value:unknown):string {
  if(value==null)return '';
  if(typeof value==='string'){try{const parsed=JSON.parse(value);if(typeof parsed==='string')return parsed;}catch{/* Plain source prose. */}return value;}
  if(typeof value==='object')return Object.entries(value).filter(([,v])=>v!=null).map(([key,v])=>key+': '+readable(v)).join(' · ');
  return String(value);
}
function canonical(value?:string){try{const url=new URL(value??'');return url.protocol==='https:'?url.href:null;}catch{return null;}}
export function sourceLabel(source:Passage){
  let key=source.source_key;
  if(!key&&source.original_url){try{const native=new URL(source.original_url).pathname.split('/').pop();if(/^[A-Z][A-Z0-9_]+-\d+$/.test(native??''))key=native;}catch{/* No derived URL. */}}
  return key&&!source.filename.startsWith(key)?key+' — '+source.filename:source.filename;
}
export function ChatSource({source,quote,historical}:{source:Passage;quote?:string;historical?:RetainedDependency}){
  const {service}=useSession();const [open,setOpen]=useState(false),[error,setError]=useState(''),[opening,setOpening]=useState(false);
  const viewer=useViewer();
  const trigger=useRef<HTMLButtonElement>(null);
  async function check(){const result=await service.json<{allowed:boolean}>('/source-answers/access',{method:'POST',body:JSON.stringify({passage_ids:source.live?[]:[source.id],historical_dependencies:historical?[historical]:[],live:source.live?[source.live]:[]})});if(!result.allowed)throw new Error('Source access or revision changed. Ask again for current evidence.');}
  const evidence=useQuery({queryKey:['chat-source',source.id,source.live],enabled:open,staleTime:0,refetchOnMount:'always',queryFn:async()=>{
    await check();
    if(!source.live)return {stored:await service.evidence(source.id)};
    const value=await service.json<{evidence:LiveEvidence}>('/connections/'+source.live.connection_id+'/live',{method:'POST',body:JSON.stringify({native_id:source.live.native_id})});
    if(value.evidence.source_revision!==source.live.revision)throw new Error('Source revision changed. Ask again for current evidence.');
    return {live:value.evidence};
  }});
  async function openOriginal(){
    setOpening(true);setError('');
    const popup=window.open('about:blank','_blank');if(popup)popup.opener=null;
    try{await check();const url=source.live?canonical(source.original_url):canonical((await service.evidence(source.id)).provenance?.original_url??undefined);
      if(!url){popup?.close();setOpen(true);return;}
      if(popup)popup.location.replace(url);else{setOpen(true);setError('Your browser blocked the new tab. Use Open original source in the preview.');}
    }catch(cause){popup?.close();setError(cause instanceof Error?cause.message:'Source unavailable.');}finally{setOpening(false);}
  }
  const live=evidence.data?.live;const fields=live?.fields??[];
  const metadata=fields.filter(f=>['status','assignee'].includes(f.field)&&f.value!=null&&readable(f.value).trim());
  const description=readable(fields.find(f=>f.field==='description')?.value);
  const evidenceQuote=quote?.replace(/^(description|project): /,'');
  const excerpt=evidenceQuote?readable((()=>{try{return JSON.parse(evidenceQuote);}catch{return evidenceQuote;}})()).slice(0,800):'';
  return <span className="chat-source-wrap">
    <span className="chat-source-actions"><button className="chat-source-link" onClick={()=>void openOriginal()} disabled={opening} title="Check access and open original source"><FileText size={13}/><bdi>{source.synthetic?"Demo · ":source.live?"Live · ":"Stored · "}{sourceLabel(source)}</bdi><ExternalLink size={11}/></button>
    <button ref={trigger} className="chat-source-preview" onClick={()=>setOpen(true)} aria-label={'Preview source: '+sourceLabel(source)}><Info size={14}/></button></span>
    {error&&!open&&<span role="alert" className="source-open-error">{error}</span>}
    <Sheet title={source.source_application??(source.live?'Connected source':'Source evidence')} description={sourceLabel(source)} open={open} onOpenChange={setOpen} returnFocus={trigger}>
      {evidence.isPending&&<Feedback>Checking source access…</Feedback>}{evidence.isError&&<Feedback error>{evidence.error.message}</Feedback>}
      {source.synthetic&&<Feedback>This document belongs to a synthetic test dataset.</Feedback>}
      {evidence.data?.stored&&<SourcePreview evidence={evidence.data.stored}/>}
      {live&&<div className="chat-source-detail"><h2 dir="auto">{sourceLabel(source)}</h2>
        {canonical(live.original_url)&&<a className="original-source-link" href={canonical(live.original_url)!} target="_blank" rel="noopener noreferrer"><ExternalLink size={15}/>Open original source</a>}
        {!!metadata.length&&<dl className="source-metadata">{metadata.map(f=><div key={f.field}><dt>{f.field==='status'?'Jira status':'Jira assignee'}</dt><dd dir="auto">{readable(f.value)}</dd></div>)}</dl>}
        <h3>Supporting excerpt</h3><blockquote dir="auto">{excerpt||live.excerpt||'See the structured source details for this reference.'}</blockquote>
        {live.source_updated_at&&<p className="muted">Updated {new Date(live.source_updated_at).toLocaleString()}</p>}
        <p className="muted">Retrieved {new Date(live.observed_at).toLocaleString()}</p>
        {(description||live.excerpt)&&<details><summary>View full details</summary><div className="markdown" dir="auto"><Markdown remarkPlugins={[remarkGfm]} skipHtml>{description||live.excerpt}</Markdown></div></details>}
        {['admin','reviewer'].includes(viewer.data?.role??'')&&<details className="developer-evidence"><summary>Developer evidence</summary><pre>{JSON.stringify(live,null,2)}</pre></details>}
      </div>}
      {error&&<Feedback error>{error}</Feedback>}
      <Button variant="outline" onClick={()=>setOpen(false)}>Close preview</Button>
    </Sheet>
  </span>;
}
