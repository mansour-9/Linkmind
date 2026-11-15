import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowUpRight, BookOpen, FileText, Network, UserRound } from "lucide-react";
import { useSession } from "./session";
import { Button, Feedback, PageHeading, SearchField } from "./ui";
import { EvidenceAction } from "./Evidence";
import type { Entity } from "./api";
import type { Conflict, WikiPage } from "./contracts";

function Download({ version, filename }: { version: string; filename: string }) {
  const { service } = useSession();
  const download = useMutation({ mutationFn: () => service.download(version, filename) });
  return <><Button variant="ghost" disabled={download.isPending} onClick={() => download.mutate()}>Download</Button>{download.isError && <Feedback error>{download.error.message}</Feedback>}</>;
}

export function Knowledge({ people = false }: { people?: boolean }) {
  const { service } = useSession();
  const { entityId } = useParams();
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const kind = people ? "person" : params.get("kind") ?? "";
  const pages = useQuery({ queryKey: ["wiki"], queryFn: () => service.json<Entity[]>("/wiki"), refetchInterval: 5000 });
  const page = useQuery({ queryKey: ["wiki", entityId], queryFn: () => service.json<WikiPage>("/wiki/" + entityId), enabled: !!entityId, refetchInterval: 5000 });
  const conflicts = useQuery({ queryKey: ["conflicts"], queryFn: () => service.json<Conflict[]>("/conflicts"), enabled: !!entityId, refetchInterval: 5000 });
  const neighbors = useQuery({ queryKey: ["graph-neighborhood", entityId], queryFn: () => service.neighbors(entityId!), enabled: !!entityId, refetchInterval: 5000 });
  const [showSources, setShowSources] = useState(false);
  const items = pages.data?.filter(p => (!kind || p.kind === kind) && p.name.toLowerCase().includes(query.toLowerCase())) ?? [];
  const base = people ? "/people" : "/content";
  function filter(key: string, value: string) { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next, { replace: true }); }
  if (entityId) return <div className="page entity-reading">
    <Link className="back-link" to={base}><ArrowLeft size={16} />{people ? "All people" : "All knowledge"}</Link>
    {page.isPending && <Feedback>Loading knowledge…</Feedback>}
    {page.isError && <Feedback error>{page.error.message}<Button variant="outline" onClick={() => void page.refetch()}>Retry</Button></Feedback>}
    {page.isSuccess && <article><div className="entity-heading"><span className="entity-detail-icon">{page.data.kind === "person" ? <UserRound size={26} /> : <BookOpen size={26} />}</span><span className="kind-pill">{page.data.kind}</span><h1 className="wiki-title">{page.data.name}</h1><p className="muted">Knowledge linked to its original evidence.</p><Link className="text-action" to={"/graph?scope=" + entityId + "&node=" + entityId}><Network size={16} />Explore connections<ArrowUpRight size={14} /></Link></div>
      {page.data.uncertain_matches > 0 && <div className="review-banner">This entity has uncertain identity matches. <Link to="/admin/conflicts">Review possible matches</Link></div>}
      {conflicts.data?.some(c => c.canonical_id === entityId && c.status !== "not_a_conflict") && <div className="review-banner">Sources disagree about this entity. <Link to="/admin/conflicts">Inspect the evidence</Link></div>}
      {!page.data.claims.length && <section className="empty-claims"><h2>Evidence found, details still limited</h2><p className="muted">This entity appears in your sources, but no verified claims have been published. Read the original context or explore its connections.</p><div className="evidence-row">{page.data.entity_evidence.map(e => <EvidenceAction key={e.chunk_id} id={e.chunk_id} title={e.filename} />)}</div></section>}
      {page.data.claims.map(c => <section className="wiki-claim" key={c.id}><h2>{c.predicate.replaceAll("_", " ")}{conflicts.data?.some(f => f.status === "resolved" && f.authoritative_claim_id === c.id) ? " · Accepted by reviewer" : ""}</h2><p dir="auto">{c.value}</p><div className="evidence-row">{c.evidence.map(e => <EvidenceAction key={e.chunk_id + e.quote} id={e.chunk_id} title={e.filename} />)}</div><small className="muted">{c.provider === "fixture" ? "Demo extraction" : "Evidence validated"}</small></section>)}
      {neighbors.isSuccess && neighbors.data.nodes.some(n => n.id !== entityId) && <section className="related-knowledge"><h2>Connected knowledge</h2><div className="knowledge-directory">{neighbors.data.nodes.filter(n => n.id !== entityId).map(n => <Link key={n.id} className="knowledge-row" to={(n.kind === "person" ? "/people/" : "/content/") + n.id}><span className="knowledge-row-text"><strong>{n.name}</strong><small>{n.kind}</small></span><ArrowUpRight size={15} /></Link>)}</div></section>}
      <section className="source-history"><button className="text-action" aria-expanded={showSources} onClick={() => setShowSources(!showSources)}><FileText size={16} />Sources and version history ({page.data.sources.length})</button>{showSources && <ul>{page.data.sources.map(s => <li key={s.version_id}><div><strong>{s.filename}</strong><small>{new Date(s.created_at).toLocaleDateString("en")} · {s.current ? "Current" : "Historical"}</small></div><Download version={s.version_id} filename={s.filename} /></li>)}</ul>}</section>
    </article>}
  </div>;
  return <div className="page knowledge-library"><PageHeading title={people ? "People" : "Your company knowledge"} description={people ? "Find the people connected to your work." : "Explore the projects, decisions, and ideas in your sources."} />
    <div className="library-toolbar"><SearchField className="library-search" aria-label={people ? "Find a person" : "Find knowledge"} placeholder={people ? "Search people…" : "Search knowledge…"} value={query} onChange={e => filter("q", e.target.value)} />{!people && <select aria-label="Filter knowledge type" value={kind} onChange={e => filter("kind", e.target.value)}><option value="">All types</option>{[...new Set(pages.data?.map(p => p.kind) ?? [])].sort().map(k => <option key={k} value={k}>{k}</option>)}</select>}</div>
    {pages.isPending && <Feedback>Loading knowledge…</Feedback>}{pages.isError && <Feedback error>{pages.error.message}<Button variant="outline" onClick={() => void pages.refetch()}>Retry</Button></Feedback>}
    {pages.isSuccess && <><p className="library-count">{items.length} {people ? "people" : "knowledge pages"} in your available sources</p>{!items.length && <div className="knowledge-empty">{people ? <UserRound size={28} /> : <BookOpen size={28} />}<h2>{query || kind && !people ? "No matching knowledge" : people ? "People will appear here" : "Bring your knowledge together"}</h2><p>{people ? "People from optionally enriched sources appear here with supporting evidence." : "Optional enrichment adds connected knowledge here. Your indexed documents are already available for search and answers."}</p><Button variant="outline" asChild><Link to="/content/documents">Browse documents</Link></Button></div>}
      <div className={people ? "people-directory" : "knowledge-directory"}>{items.map(p => <Link className="knowledge-row" key={p.id} to={base + "/" + p.id}><span className={people ? "person-initial" : "knowledge-icon"}>{people ? p.name.slice(0,1) : <BookOpen size={20} />}</span><span className="knowledge-row-text"><strong>{p.name}</strong><small>{people ? p.filename : p.kind + " · " + p.filename}</small></span><ArrowUpRight className="row-arrow" size={17} /></Link>)}</div>
    </>}
  </div>;
}
