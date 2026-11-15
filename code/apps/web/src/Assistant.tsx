import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Check, Copy, FileText, LoaderCircle, MessageSquarePlus, Network, Search } from "lucide-react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSession } from "./session";
import { Button, Feedback } from "./ui";
import { EvidenceAction } from "./Evidence";
import { FocusSources } from "./FocusSources";

function sourceScope(params: URLSearchParams) { return [...new Set(params.getAll("scope"))].filter(id => /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(id)).slice(0, 30); }
import type { Answer, Conversation, History } from "./contracts";

function AnswerContent({ answer, onChoose, disabled }: { answer: Answer; onChoose?: (id: string, filename: string) => void; disabled: boolean }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const cited = new Set(answer.statements.flatMap(s => s.evidence.map(e => e.passage_id)));

  // Unique passage IDs in first-appearance order → citation number 1, 2, 3…
  const usedIds = [...new Set(answer.statements.flatMap(s => s.evidence.map(e => e.passage_id)))];
  const citationNum = new Map(usedIds.map((id, i) => [id, i + 1] as [string, number]));

  async function copy() {
    try { await navigator.clipboard.writeText(answer.message ?? answer.statements.map(s => s.text).join("\n\n")); setCopied(true); setCopyError(false); }
    catch { setCopyError(true); }
  }
  return <div className="answer-block">
    {!!answer.evidence.length && <details className="show-work"><summary>Show work <span>{answer.evidence.length} passages</span></summary>
      <div className="work-content"><p>Source passages supplied for this answer</p>
        <p className="muted">{answer.retrieval_activity?.length ? 'Completed retrieval operations and supplied source passages.' : 'These are retrieved passages, not a recorded search activity log.'}</p>
        {!!answer.retrieval_activity?.length && <ul className="retrieval-activity" aria-label="Retrieval activity">{answer.retrieval_activity.map((step, i) => <li key={i}>
          {({ indexed_search: 'Searched the stored index', adjacent_passages: 'Read adjacent source passages', selected_source_context: 'Read selected source context', retained_revision_context: 'Read retained source revisions' } as Record<string, string>)[step.operation] ?? 'Retrieved source evidence'}
          {' · '}{step.returned_passages} passages from {step.source_count} sources
        </li>)}</ul>}
        {[true, false].map(isCited => { const passages = answer.evidence.filter(p => cited.has(p.id) === isCited); return passages.length ? <section key={String(isCited)}>
          <h3>{isCited ? "Cited evidence" : "Additional context"}</h3><div className="evidence-row">{passages.map(p => <EvidenceAction key={p.id} id={p.id} title={p.filename} />)}</div>
        </section> : null; })}
      </div>
    </details>}
    {answer.provider === "mock-extractive" && <p className="answer-provider">Demo · verbatim evidence excerpts</p>}
    {answer.provider === "bedrock" && <p className="answer-provider">{answer.statements.length ? "Sonnet · cited source evidence" : ['verification_failed','citation_failed'].includes(answer.answer_state?.code ?? '') ? 'Sonnet · answer not verified' : "Sonnet · insufficient evidence"}</p>}
    {answer.message && <p className="answer-message" dir="auto">{answer.message}</p>}
    {!!answer.source_matches?.length && <div className="source-choices" aria-label="Matching sources">{answer.source_matches.map(source =>
      <Button key={source.document_id} className="source-choice" variant="outline" disabled={disabled || !onChoose}
        onClick={() => onChoose?.(source.document_id, source.filename)} aria-label={"Use " + source.filename}>
        <FileText size={16} /><span dir="auto">{source.filename}<small>{!source.search_ready ? "Not search ready" : source.match === "similar_name" ? "Similar name" : source.match === "filename" ? "Filename match" : "Related source"}</small></span>
      </Button>)}</div>}
    {answer.search_notice && <Feedback>{answer.search_notice}</Feedback>}
    {answer.freshness_notice && <Feedback>{answer.freshness_notice}</Feedback>}
    {answer.coverage?.partial && <Feedback>{answer.coverage.mode === 'document_overview' ? 'This overview uses' : 'This context uses'} {answer.coverage.supplied_passages} of {answer.coverage.total_passages} passages from {answer.coverage.covered_sources} of {answer.coverage.selected_sources} selected sources. It covers only part of the content.</Feedback>}
    {answer.insufficient_evidence && !answer.message && <Feedback>{answer.statements.length ? 'Only part of this request is supported by the supplied evidence.' : 'The supplied evidence did not establish a verified answer. Inspect the source context or narrow the question.'}</Feedback>}
    <div className="answer-body">
      {answer.statements.map((statement, i) => <div className="answer-statement" key={i}>
        <div className="markdown" dir="auto"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{ a: props => <a {...props} target="_blank" rel="noopener noreferrer" /> }}>{statement.text}</Markdown></div>
        {statement.evidence.length > 0 && <span className="answer-inline-cites" aria-label="Citations">
          {[...new Set(statement.evidence.map(e => e.passage_id))].map(pid => <EvidenceAction key={pid} id={pid}
            title={answer.evidence.find(p => p.id === pid)?.filename ?? "Source evidence"}
            citationNumber={citationNum.get(pid)} variant="cite" />)}
        </span>}
      </div>)}
    </div>
    {usedIds.length > 0 && <div className="answer-sources">
      <span className="sources-label">Sources</span>
      {usedIds.map(id => { const passage = answer.evidence.find(p => p.id === id); return <EvidenceAction key={id} id={id}
        title={passage?.filename ?? "Source evidence"} citationNumber={citationNum.get(id)} variant="source" />; })}
    </div>}
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
  const runtime = useQuery({ queryKey: ["runtime"], queryFn: () => service.json<{ provider: string; budget: { spent_usd: number; limit_usd: number; paused: boolean } | null }>("/runtime"), refetchInterval: 5000 });
  const cache = useQueryClient();
  const history = useQuery({ queryKey: ["conversation", conversationId], queryFn: () => service.json<History>("/conversations/" + conversationId), enabled: !!conversationId, refetchInterval: 5000 });
  const [question, setQuestion] = useState(params.get("q") ?? "");
  const [scope, setScope] = useState<string[]>(() => sourceScope(params));
  const [pending, setPending] = useState<{ conversation: string | null; question: string } | null>(null);
  const [error, setError] = useState("");
  const busy = useRef(false);
  const createdRoute = useRef<string | null>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const atBottom = useRef(true);
  const [showLatest, setShowLatest] = useState(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const activeScope = history.isSuccess ? history.data.document_ids : conversationId ? [] : scope;
  useLayoutEffect(() => { const el = textarea.current; if (el) { el.style.height = "auto"; el.style.height = Math.min(200, el.scrollHeight) + "px"; } }, [question]);
  useEffect(() => {
    // A fast failed answer can settle before navigation commits. Keep its draft/error.
    if (conversationId && createdRoute.current === conversationId) { createdRoute.current = null; return; }
    atBottom.current = true; setShowLatest(false); setError(""); setQuestion(params.get("q") ?? ""); setScope(sourceScope(params));
  }, [conversationId, params, location.key]);
  useLayoutEffect(() => { const el = scroller.current; if (el && atBottom.current) el.scrollTop = el.scrollHeight; }, [history.data, pending]);
  const visiblePending = pending && pending.conversation === (conversationId ?? null) ? pending : null;
  async function send(selection?: { id: string; filename: string }) {
    const text = selection ? "Tell me about " + selection.filename : question.trim();
    if (busy.current || text.length < 2 || text.length > 2000 || (conversationId && !history.isSuccess)) return;
    busy.current = true; setError(""); setPending({ conversation: conversationId ?? null, question: text });
    let current = conversationId;
    try {
      if (!current) {
        const created = await service.json<Conversation>("/conversations", { method: "POST", body: JSON.stringify({ title: text.slice(0, 100), document_ids: scope }) });
        current = created.id;
        if (!mounted.current) return;
        setPending({ conversation: current, question: text });
        // Keep this component mounted while moving from the home composer to the new chat.
        cache.setQueryData(["conversation", current], { ...created, turns: [] });
        createdRoute.current = current;
        navigate("/chat/" + current);
        void cache.invalidateQueries({ queryKey: ["conversations"] });
      }
      await service.json<Answer>("/conversations/" + current + "/answers", { method: "POST", body: JSON.stringify({ question: text, source_document_id: selection?.id }) });
      await cache.invalidateQueries({ queryKey: ["conversation", current] });
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
  function changeScope(ids: string[]) {
    if ([...ids].sort().join() === [...activeScope].sort().join()) return;
    const next = new URLSearchParams(question ? { q: question } : {});
    for (const id of ids) next.append("scope", id);
    setScope(ids);
    navigate("/" + (next.size ? "?" + next : ""), { replace: !conversationId });
  }
  const composer = <form className="assistant-composer" onSubmit={e => { e.preventDefault(); void send(); }} aria-label="Message composer">
    {runtime.isSuccess && <p className="answer-provider">{runtime.data.provider === "mock" ? "Demo mode · returns source excerpts. Select a document to explore its contents." : "Sonnet test mode · grounded answers"}
      {runtime.data.budget && <> · ${Number(runtime.data.budget.spent_usd).toFixed(2)} / ${Number(runtime.data.budget.limit_usd).toFixed(2)} estimated{runtime.data.budget.paused ? " · paused" : ""}</>}</p>}
    <textarea ref={textarea} aria-label="Ask a question" placeholder="Ask anything about your work…" maxLength={2000} value={question} disabled={!!pending}
      onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }} />
    <div className="composer-toolbar"><FocusSources value={activeScope} onChange={changeScope} conversation={!!conversationId} disabled={!!pending || (!!conversationId && !history.isSuccess)} /><Button className="send-button icon-button" type="submit" aria-label="Send question" disabled={question.trim().length < 2 || !!pending || (!!conversationId && !history.isSuccess)}>
      {pending ? <LoaderCircle size={19} className="spin" /> : <ArrowUp size={20} />}</Button></div>
  </form>;
  return <div className={"assistant-page" + (conversationId ? " has-conversation" : "")}>
    {conversationId ? <><header className="conversation-heading"><MessageSquarePlus size={18} /><h1>{history.isSuccess ? history.data.title : "Assistant"}</h1><Button variant="ghost" asChild><Link to="/">New conversation</Link></Button></header>
      <div className="conversation-scroll" ref={scroller} onScroll={e => { const el = e.currentTarget; atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100; setShowLatest(!atBottom.current); }}>
        <div className="conversation-reading">
          {history.isPending && <Feedback>Loading conversation…</Feedback>}
          {history.isError && <Feedback error>{history.error.message}<Button variant="outline" onClick={() => void history.refetch()}>Retry</Button><Link to="/">Start a new conversation</Link></Feedback>}
          {history.isSuccess && history.data.turns.map((turn, index) => <article className="chat-turn" key={turn.id}><div className="question-bubble" dir="auto">{turn.question}</div>
            {turn.suppressed ? <Feedback>This answer is hidden because its evidence, access, or validation policy changed. Ask again for current evidence.</Feedback> : turn.response && <AnswerContent answer={turn.response} disabled={!!pending}
              onChoose={index === history.data.turns.length - 1 ? (id, filename) => void send({ id, filename }) : undefined} />}
          </article>)}
          {visiblePending && <article className="chat-turn pending-turn"><div className="question-bubble" dir="auto">{visiblePending.question}</div><div className="answer-pending" role="status"><LoaderCircle size={17} className="spin" />Finding sources and preparing your response…</div></article>}
          {error && <Feedback error>{error}<span>Your question is kept below. Review the history, then send again to retry.</span></Feedback>}
        </div>
      </div>
      <div className="conversation-footer">{showLatest && <Button className="latest-button icon-button" variant="outline" aria-label="Scroll to latest" onClick={() => { atBottom.current = true; scroller.current?.scrollTo({ top: scroller.current.scrollHeight }); setShowLatest(false); }}><ArrowDown size={18} /></Button>}{composer}<p className="composer-note">Answers are grounded in the sources you can access.</p></div>
    </> : <div className="assistant-home"><h1>Ask Linkmind</h1>{composer}
      <div className="home-actions"><Link to="/search"><Search size={17} />Search knowledge</Link><Link to="/content"><FileText size={17} />Browse content</Link><Link to="/admin/sources"><FileText size={17} />Add documents</Link><Link to="/content/graph"><Network size={17} />Explore connections</Link></div>
      {pending && <Feedback>Starting your conversation…</Feedback>}{error && <Feedback error>{error}</Feedback>}
    </div>}
  </div>;
}
