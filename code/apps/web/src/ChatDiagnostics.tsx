import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useSession } from './session';
import { Feedback, PageHeading } from './ui';
import type { Conversation } from './contracts';
type Trace={id:string;question:string;diagnostics:{total_ms?:number;stages?:{stage:string;ms:number}[];counters?:Record<string,number>}};
export function ChatDiagnostics(){
 const {service}=useSession();const [selected,setSelected]=useState('');
 const conversations=useQuery({queryKey:['conversations'],queryFn:()=>service.json<Conversation[]>('/conversations')});
 const trace=useQuery({queryKey:['chat-diagnostics',selected],enabled:!!selected,queryFn:()=>service.json<Trace[]>('/conversations/'+selected+'/diagnostics')});
 return <div className="page reading-width"><PageHeading title="Chat diagnostics" description="Request timings and operation counts for your own conversations. Overlapping stages are not additive."/>
 <p><Link to="/admin/usage">Open AI usage and accounting</Link></p>
 <label>Conversation<select aria-label="Diagnostics conversation" value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Select a conversation</option>{conversations.data?.map(c=><option key={c.id} value={c.id}>{c.title}</option>)}</select></label>
 {trace.isError&&<Feedback error>{trace.error.message}</Feedback>}{trace.isFetching&&<Feedback>Loading timings…</Feedback>}
 {trace.data?.map(turn=><section className="diagnostic-turn" key={turn.id}><h2 dir="auto">{turn.question}</h2><p>Total: {turn.diagnostics.total_ms??'Not recorded'} ms</p><p>{Object.entries(turn.diagnostics.counters??{}).map(([key,value])=>key+': '+value).join(' · ')}</p>
 <table><thead><tr><th>Stage</th><th>Milliseconds</th></tr></thead><tbody>{turn.diagnostics.stages?.map((s,i)=><tr key={i}><td>{s.stage}</td><td>{s.ms}</td></tr>)}</tbody></table></section>)}
 </div>;
}
