import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Check, Copy, FileText, LoaderCircle, MessageSquarePlus, Network, Search } from "lucide-react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSession } from "./session";
import { Button, Feedback } from "./ui";
import { ChatSource } from "./ChatSource";

function sourceScope(params: URLSearchParams) { return [...new Set(params.getAll("scope"))].filter(id => /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(id)).slice(0, 30); }
import type { Answer, Conversation, History } from "./contracts";

function AnswerContent({ answer, onChoose, disabled }: { answer: Answer; onChoose?: (id: string, filename: string) => void; disabled: boolean }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const uniqueSources=(references:{passage_id:string;quote:string}[])=>{
    const seen=new Set<string>();
    return references.flatMap(reference=>{const source=answer.evidence.find(p=>p.id===reference.passage_id);
      if(!source)return [];const key=source.live?JSON.stringify([source.live.connection_id,source.live.native_id,source.live.revision]):source.id;
      if(seen.has(key))return [];seen.add(key);return [{source,quote:reference.quote}];});
  };
  const failures=Array.from(new Map([...(answer.source_failures??[]),...(answer.source_outcomes??[]).filter(s=>!['observed','discovered','no_matches','irrelevant_action'].includes(s.code))].map(s=>[s.name+'|'+s.code,s])).values());

  async function copy() {
    try { await navigator.clipboard.writeText([answer.message,...answer.statements.map(s => s.text)].filter(Boolean).join("\n\n")); setCopied(true); setCopyError(false); }
    catch { setCopyError(true); }
  }
  return <div className="answer-block">
    {answer.provider === "mock-extractive" && <p className="answer-provider">Demo · original source excerpts</p>}
    {answer.provider === 'source-excerpts' && <p className="answer-provider">Original excerpts · an answer could not be verified</p>}
    {answer.message && <p className="answer-message" dir="auto">{answer.message}</p>}
    {!!answer.source_matches?.length && <div className="source-choices" aria-label="Matching sources">{answer.source_matches.map(source =>
      <Button key={source.document_id} className="source-choice" variant="outline" disabled={disabled || !onChoose}
        onClick={() => onChoose?.(source.document_id, source.filename)} aria-label={"Use " + source.filename}>
        <FileText size={16} /><span dir="auto">{source.filename}<small>{!source.search_ready ? "Not search ready" : source.match === "similar_name" ? "Similar name" : source.match === "filename" ? "Filename match" : "Related source"}</small></span>
      </Button>)}</div>}
    {answer.search_notice && <Feedback>{answer.search_notice}</Feedback>}
    {answer.freshness_notice && <Feedback>{answer.freshness_notice}</Feedback>}
    {answer.coverage?.partial && <Feedback>{answer.coverage.mode === 'document_overview' ? 'This overview uses' : 'This context uses'} {answer.coverage.supplied_passages} of {answer.coverage.total_passages} passages from {answer.coverage.covered_sources} of {answer.coverage.selected_sources} selected sources. It covers only part of the content.</Feedback>}
    {failures.map((failure,i)=><Feedback error key={i}>{failure.name}: {['access_denied','authentication_expired','credentials_missing'].includes(failure.code)?'Source access could not be confirmed. Reconnect or check your permissions.':['source_limit','resource_limit'].includes(failure.code)?'The search reached its source limit. This answer covers the sources that were read.':'This source could not be read. The answer uses the sources that were available.'}</Feedback>)}
    <div className="answer-body">
      {answer.presentation?.kind==='projects'&&!!answer.presentation.items?.length?<div className="chat-table-scroll"><table className="chat-projects"><thead><tr><th>Project</th><th>Name</th><th>Source</th></tr></thead><tbody>{answer.presentation.items?.map(item=>{
        const source=answer.evidence.find(p=>p.id===item.source_id);
        return <tr key={item.source_id}><td><bdi>{item.key}</bdi></td><td dir="auto">{item.name}</td><td>{source&&<ChatSource source={source} quote={answer.statements.find(s=>s.evidence.some(e=>e.passage_id===source.id))?.evidence[0]?.quote}/>}</td></tr>;
      })}</tbody></table></div>:answer.statements.map((statement,i)=><div className="answer-statement" key={i}>
        {answer.presentation?.kind!=='source_links'&&<div className="markdown" dir="auto"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{a:props=><a {...props} target="_blank" rel="noopener noreferrer"/>}}>{statement.text}</Markdown></div>}
        <div className="answer-source-links" aria-label="Supporting sources">{uniqueSources(statement.evidence).map(({source,quote})=><ChatSource key={source.id} source={source} quote={quote} historical={answer.historical_dependencies?.find(d=>d.passage_id===source.id)}/>)}</div>
      </div>)}
    </div>
    <div className="answer-actions"><Button variant="ghost" aria-label="Copy answer" onClick={() => void copy()}>{copied ? <Check size={15} /> : <Copy size={15} />}{copied ? "Copied" : "Copy answer"}</Button></div>
    {copyError && <Feedback error>Copy is unavailable. Select the answer text to copy it.</Feedback>}
  </div>;
}

export function Assistant() {
  const { conversationId } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { service } = useSession();

  const cache = useQueryClient();
  const history = useQuery({ queryKey: ["conversation", conversationId], queryFn: () => service.json<History>("/conversations/" + conversationId), enabled: !!conversationId, refetchInterval: 30000 });
  const [question, setQuestion] = useState(params.get("q") ?? "");
  const [scope, setScope] = useState<string[]>(() => sourceScope(params));
  const [pending, setPending] = useState<{ conversation: string | null; question: string } | null>(null);
  const [error, setError] = useState("");
  const [activity,setActivity]=useState("Finding relevant sources…");
  const busy = useRef(false);
  const createdRoute = useRef<string | null>(null);
  const scopeRoutes = useRef(new Set<string>());
  const textarea = useRef<HTMLTextAreaElement>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const atBottom = useRef(true);
  const [showLatest, setShowLatest] = useState(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const activePolicy=history.isSuccess?history.data.source_policy:"auto";
  useLayoutEffect(() => { const el = textarea.current; if (el) { el.style.height = "auto"; el.style.height = Math.min(200, el.scrollHeight) + "px"; } }, [question]);
  useEffect(() => {
    // A fast failed answer can settle before navigation commits. Keep its draft/error.
    if (conversationId && createdRoute.current === conversationId) { createdRoute.current = null; scopeRoutes.current.clear(); return; }
    // Local source changes already set scope and preserve the draft. Their delayed
    // navigation effect must not erase a question typed after applying the selection.
    if (scopeRoutes.current.delete(location.pathname + location.search)) return;
    scopeRoutes.current.clear();
    atBottom.current = true; setShowLatest(false); setError(""); setQuestion(params.get("q") ?? ""); setScope(sourceScope(params));
  }, [conversationId, params, location.key]);
  useLayoutEffect(() => { const el = scroller.current; if (el && atBottom.current) el.scrollTop = el.scrollHeight; }, [history.data, pending]);
  const visiblePending = pending && pending.conversation === (conversationId ?? null) ? pending : null;
  async function send(selection?: { id: string; filename: string }) {
    const text = selection ? "Tell me about " + selection.filename : question.trim();
    if (activePolicy==="legacy") {setError("Start a new conversation. Earlier answers are preserved as history.");return;}
    if (busy.current || text.length < 2 || text.length > 2000 || (conversationId && !history.isSuccess)) return;
    busy.current = true; setActivity("Finding relevant sources…"); setError(""); setPending({ conversation: conversationId ?? null, question: text });
    let current = conversationId;
    try {
      if (!current) {
        const created = await service.json<Conversation>("/conversations", { method: "POST", body: JSON.stringify({ title: text.slice(0, 100), document_ids: scope, source_policy: activePolicy }) });
        current = created.id;
        if (!mounted.current) return;
        setPending({ conversation: current, question: text });
        // Keep this component mounted while moving from the home composer to the new chat.
        cache.setQueryData(["conversation", current], { ...created, turns: [] });
        createdRoute.current = current;
        navigate("/chat/" + current);
        void cache.invalidateQueries({ queryKey: ["conversations"] });
      }
      const result=await service.streamAnswer<Answer>(current,{question:text,source_document_id:selection?.id},phase=>{
        if(mounted.current)setActivity(({finding_sources:'Finding relevant sources…',searching_documents:'Searching Documents…',refining_search:'Checking what is still missing…',searching_onedrive:'Searching OneDrive…',searching_sharepoint:'Searching SharePoint…',searching_custom_mcp:'Searching connected sources…',searching_knowledge:'Searching company knowledge…',searching_jira:'Searching Jira…',searching_confluence:'Searching Confluence…',preparing_answer:'Preparing your answer…',checking_answer:'Checking supporting sources…',checking_access:'Checking source access…'} as Record<string,string>)[phase]??'Preparing your answer…');
      });
      cache.setQueryData<History>(['conversation',current],existing=>existing?{...existing,turns:[...existing.turns,{id:crypto.randomUUID(),question:text,suppressed:false,response:result}]}:existing);
      if (mounted.current) setQuestion("");
    } catch (cause) {
      // A timeout may happen after saving. Refresh history before offering a manual retry.
      if (current) await cache.invalidateQueries({ queryKey: ["conversation", current] });
      if (mounted.current) { setQuestion(text); setError(cause instanceof Error ? cause.message : "Answer unavailable. Please retry."); }
    } finally {
      busy.current = false;
      if (mounted.current) setPending(null);
    }
  }
  const composer = <form className="assistant-composer" onSubmit={e => { e.preventDefault(); void send(); }} aria-label="Message composer">
    <textarea ref={textarea} aria-label="Ask a question" dir="auto" placeholder="Ask anything about your work…" maxLength={2000} value={question} disabled={!!pending}
      onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }} />
    <div className="composer-toolbar"><span className="composer-source-note">Connected sources and your documents</span><Button className="send-button icon-button" type="submit" aria-label="Send question" disabled={question.trim().length < 2 || !!pending || (!!conversationId && !history.isSuccess)}>
      {pending ? <LoaderCircle size={19} className="spin" /> : <ArrowUp size={20} />}</Button></div>
  </form>;
  return <div className={"assistant-page" + (conversationId ? " has-conversation" : "")}>
    {conversationId ? <><header className="conversation-heading"><MessageSquarePlus size={18} /><h1>{history.isSuccess ? history.data.title : "Assistant"}</h1><Button variant="ghost" asChild><Link to="/">New conversation</Link></Button></header>
      <div className="conversation-scroll" ref={scroller} onScroll={e => { const el = e.currentTarget; atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100; setShowLatest(!atBottom.current); }}>
        <div className="conversation-reading">
          {history.isPending && <Feedback>Loading conversation…</Feedback>}
          {history.isError && <Feedback error>{history.error.message}<Button variant="outline" onClick={() => void history.refetch()}>Retry</Button><Link to="/">Start a new conversation</Link></Feedback>}
          {history.isSuccess&&history.data.source_policy==="legacy"&&<Feedback>This conversation used an earlier mixed-source policy. Its saved records are preserved. Start a new conversation to search connected sources and your documents automatically.</Feedback>}
          {history.isSuccess && history.data.turns.map((turn, index) => <article className="chat-turn" key={turn.id}><div className="question-bubble" dir="auto">{turn.question}</div>
            {turn.suppressed ? <Feedback>This answer is hidden because its evidence, access, or validation policy changed. Ask again for current evidence.</Feedback> : turn.response && <AnswerContent answer={turn.response} disabled={!!pending}
              onChoose={index === history.data.turns.length - 1 ? (id, filename) => void send({ id, filename }) : undefined} />}
          </article>)}
          {visiblePending && <article className="chat-turn pending-turn"><div className="question-bubble" dir="auto">{visiblePending.question}</div><div className="answer-pending" role="status"><LoaderCircle size={17} className="spin" />{activity}</div></article>}
          {error && <Feedback error>{error}<span>Your question is kept below. Review the history, then send again to retry.</span></Feedback>}
        </div>
      </div>
      <div className="conversation-footer">{showLatest && <Button className="latest-button icon-button" variant="outline" aria-label="Scroll to latest" onClick={() => { atBottom.current = true; scroller.current?.scrollTo({ top: scroller.current.scrollHeight }); setShowLatest(false); }}><ArrowDown size={18} /></Button>}{composer}<p className="composer-note">Answers are grounded in the sources you can access.</p></div>
    </> : <div className="assistant-home"><h1>Ask Linkmind</h1>{composer}
      <div className="home-actions"><Link to="/search"><Search size={17} />Search knowledge</Link><Link to="/content/documents"><FileText size={17} />Documents</Link><Link to="/content/graph"><Network size={17} />Explore connections</Link></div>
      {pending && <Feedback>Starting your conversation…</Feedback>}{error && <Feedback error>{error}</Feedback>}
    </div>}
  </div>;
}
