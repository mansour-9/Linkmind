import { useEffect, useState } from "react";
import { IdentityReview, ConflictHistory } from "./IdentityReview";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Plus, RefreshCw, Activity } from "lucide-react";
import { useJobs, useSession, useViewer } from "./session";
import { Button, Feedback, PageHeading, SearchField, Sheet, ReadinessBadge } from "./ui";
import type { Job, EntityOverview } from "./api";
import { EntityOverviewCard } from "./GraphPanels";

import type { Conflict } from "./contracts";
type Usage = { operation: string; provider: string; model: string; region: string; status: string; calls: number;
 input_tokens: number | null; output_tokens: number | null; latency_ms: number; estimated_cost: string | null;
 unknown_cost_calls: number; currency: string | null; rate_date: string | null; retries: number };
function processingError(error: string) {
 if (/LoginRefreshRequired|ExpiredToken|SSOToken|credentials.*expired/i.test(error)) return "AWS sign-in has expired. Refresh the local AWS login, then retry processing. " + error;
 if (/quote|evidence|verification|validation/i.test(error)) return "The extracted evidence could not be validated. No unverified knowledge was published. " + error;
 return error;
}
const stageLabels: Record<string, string> = {
 queued_enrichment: "Refresh queued", verifying_staged_enrichment: "Verifying replacement",
 enrichment_staged_failed: "Refresh rolled back",
};
const pretty = (value: string) => stageLabels[value] ?? value.replaceAll("_", " ");
const date = (value: string | null) => value ? new Date(value).toLocaleString() : "Not recorded";
const location = (locator?: Record<string, unknown>) => !locator ? "Source passage" :
 Object.entries(locator).filter(([key]) => ["page", "paragraph", "table", "row", "line"].includes(key))
 .map(([key, value]) => key + " " + String(value)).join(" · ") || "Source passage";

export { EvidenceAction } from "./Evidence";
import { EvidenceAction } from "./Evidence";
function QueryState({ query }: { query: { isPending: boolean; isError: boolean; error: Error | null; refetch: () => unknown } }) {
 return query.isPending ? <Feedback>Loading workspace knowledge…</Feedback> : query.isError ?
 <Feedback error>{query.error?.message}<Button variant="outline" onClick={() => void query.refetch()}>Retry</Button></Feedback> : null;
}

export function SearchPage() {
 const { service } = useSession();
 const [params, setParams] = useSearchParams();
 const q = params.get("q") ?? "";
 const jobs = useJobs();
 const rawOffset = Number(params.get("offset") ?? "0");
 const offset = Number.isFinite(rawOffset) ? Math.min(200, Math.max(0, Math.floor(rawOffset / 20) * 20)) : 0;
 const resultQuery = new URLSearchParams(params); resultQuery.set("limit", "20"); resultQuery.set("offset", String(offset));
 function filter(key: string, value: string) { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); next.delete("offset"); setParams(next); }
 const [input, setInput] = useState(q);
 useEffect(() => setInput(q), [q]);
 const results = useQuery({ queryKey: ["search", params.toString()], queryFn: () => service.search(resultQuery.toString()), enabled: !!q, refetchOnWindowFocus: true });
 const passages = results.data?.passages ?? [];
 const overview = useQuery({ queryKey: ["search-overview", q], queryFn: () => service.json<EntityOverview>("/graph/overview?q=" + encodeURIComponent(q)), enabled: !!q && !params.get("document_id") && !params.get("kind") && !params.get("after") && !params.get("before") && offset === 0 });
 const entity = useQuery({ queryKey: ["entity", overview.data?.entity.id], queryFn: () => service.entity(overview.data!.entity.id), enabled: !!overview.data });
 return <div className="page reading-width"><PageHeading title="Search your workspace" description="Find evidence across the sources you can access." />
 <form className="intelligence-search" onSubmit={(e) => { e.preventDefault(); if (input.trim()) { const next = new URLSearchParams(params); next.set("q", input.trim()); next.delete("offset"); setParams(next); } }}>
 <SearchField className="library-search" aria-label="Search workspace" value={input} onChange={(e) => setInput(e.target.value)} maxLength={500} placeholder="Search projects, people, decisions…" />
 <Button type="submit" disabled={!input.trim()}>Search</Button></form>
 <div className="search-filters"><label>Source<select aria-label="Source" value={params.get("document_id") ?? ""} onChange={(e) => filter("document_id", e.target.value)}><option value="">All sources</option>
 {jobs.data?.filter((j) => j.current_version_id === j.version_id).map((j) => <option key={j.document_id} value={j.document_id}>{j.filename}</option>)}</select></label>
 <label>Entity type<select aria-label="Entity type" value={params.get("kind") ?? ""} onChange={(e) => filter("kind", e.target.value)}><option value="">All types</option>{["project", "person", "team", "task", "decision", "system", "technology", "event"].map((kind) => <option key={kind}>{kind}</option>)}</select></label>
 <label>Uploaded after<input type="date" value={params.get("after") ?? ""} onChange={(e) => filter("after", e.target.value)} /></label>
 <label>Uploaded before<input type="date" value={params.get("before") ?? ""} onChange={(e) => filter("before", e.target.value)} /></label></div>
 {!q && <Feedback>Enter a project name, identifier, or question to search your workspace.</Feedback>}
 {q && <><QueryState query={results} />
 {overview.isSuccess && overview.data && entity.isSuccess && <EntityOverviewCard entity={overview.data.entity} graph={overview.data.graph} claims={entity.data.claims} />}
 {results.isSuccess && <><div className="result-meta"><span>{passages.length} relevant passages</span>
 <Link className="text-action" to={"/?q=" + encodeURIComponent(q)}>Ask AI about this <ArrowRight size={14} /></Link></div>
 {results.data.semantic_status === "failed" && <Feedback>Semantic search is temporarily unavailable. Showing text matches.</Feedback>}
 {passages.some(p => p.embedding_status !== "ready") && <p className="muted">Some sources are searchable by text while their semantic index is unavailable.</p>}
 {!passages.length && <Feedback>No matching evidence. Try an exact project identifier or a different phrase.</Feedback>}
 <div className="knowledge-stack">{passages.map((p) => <article className="search-result" key={p.id}>
 <small className="eyebrow">{location(p.locator)}</small><h2>{p.filename}</h2><p className="passage-excerpt" dir="auto">{p.text}</p>
 <EvidenceAction id={p.id} title="Open source passage" /></article>)}</div>
 <div className="action-row"><Button variant="outline" disabled={offset === 0} onClick={() => { const next = new URLSearchParams(params); next.set("offset", String(Math.max(0, offset - 20))); setParams(next); }}>Previous</Button>
 <span className="muted">Page {Math.floor(offset / 20) + 1}</span><Button variant="outline" disabled={passages.length < 20 || offset >= 200} onClick={() => { const next = new URLSearchParams(params); next.set("offset", String(offset + 20)); setParams(next); }}>Next</Button></div></>}</>}
 </div>;
}

export function Processing() {
 const { service } = useSession();
 const cache = useQueryClient();
 const jobs = useJobs();
 const [selected, setSelected] = useState<string | null>(null);
 const details = useQuery({ queryKey: ["processing", selected], queryFn: () => service.json<Job & {
 attempt_history: { id: string; attempt: number; stage: string; status: string; error: string | null }[] }>("/jobs/" + selected), enabled: !!selected, refetchInterval: 3000 });
 const retry = useMutation({ mutationFn: (id: string) => service.json("/jobs/" + id + "/retry", { method: "POST" }),
 onSuccess: () => { void cache.invalidateQueries({ queryKey: ["jobs"] }); void cache.invalidateQueries({ queryKey: ["processing"] }); } });
 const conflicts = useQuery({ queryKey: ["conflicts"], queryFn: () => service.json<Conflict[]>("/conflicts") });
 const counts = jobs.data?.reduce((a, j) => ({ entities: a.entities + j.entity_count, claims: a.claims + j.claim_count, relationships: a.relationships + j.relationship_count }), { entities: 0, claims: 0, relationships: 0 });
 return <div className="page"><PageHeading title="Processing" description="Follow each document from upload to validated knowledge."
 action={<Button asChild><Link to="/admin/sources"><Plus size={16} />Upload a source</Link></Button>} />
 {counts && <div className="metric-grid">{[["Entities", counts.entities], ["Claims", counts.claims], ["Relationships", counts.relationships], ["Open conflicts", conflicts.data?.filter((c) => c.status === "open").length ?? "…"]].map(([label, value]) =>
 <div className="panel metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>}
 <QueryState query={jobs} />{retry.isError && <Feedback error>{retry.error.message}</Feedback>}
 {jobs.isSuccess && !jobs.data.length && <Feedback>No uploaded documents. Add a source to start processing.</Feedback>}
 <div className="knowledge-stack">{jobs.data?.map((j) => <article className="panel process-card" key={j.id}>
 <div className="process-heading"><div><h2>{j.filename}</h2><small className="muted">{j.visibility === "team" ? "Organization" : "Owner only"} · Version {j.version_id.slice(0, 8)}
 {j.current_version_id === j.version_id ? " · Current" : j.search_ready_at ? " · Historical" : ""}</small></div><div className="source-state"><ReadinessBadge job={j} /></div></div>
 <div className="process-stages"><span><Activity size={14} />{pretty(j.stage)}</span><span>{j.entity_count} entities</span><span>{j.claim_count} claims</span><span>{j.relationship_count} relationships</span><span>Semantic index: {j.embedding_status}</span></div>
 <p className="muted">Search ready: {date(j.search_ready_at)} · Knowledge enriched: {date(j.processed_at)} · {j.attempts} attempts</p>
 {j.error && <Feedback error>{processingError(j.error)}</Feedback>}
 {j.preserved_enrichment && <Feedback>{j.status === "enrichment_staged_failed" ? "The replacement did not pass. Previous verified knowledge is still available." : "A replacement is being prepared. Search and previous verified knowledge remain available."}</Feedback>}
 <div className="action-row"><Button variant="outline" onClick={() => setSelected(j.id)}>Processing details</Button>
 {j.can_manage && j.can_retry && <Button variant="outline" disabled={retry.isPending} onClick={() => retry.mutate(j.id)}><RefreshCw size={14} />{j.search_status === "ready" ? "Retry enrichment" : "Retry processing"}</Button>}</div>
 </article>)}</div>
 <Sheet title="Processing details" description="Version metadata, attempts and errors." open={!!selected} onOpenChange={(open) => { if (!open) setSelected(null); }}>
 <QueryState query={details} />{details.isSuccess && <div className="space-y-4"><h2>{details.data.filename}</h2><p className="muted">Provider: {details.data.extraction_provider ?? "Not extracted"}</p>
 <p>Search: {pretty(details.data.search_status)} · Enrichment: {pretty(details.data.enrichment_status)} · Semantic index: {details.data.embedding_status}</p>
 {details.data.attempt_history.map((a) => <div className="panel knowledge-card" key={a.id}><strong>Attempt {a.attempt} · {pretty(a.status)}</strong><p>{pretty(a.stage)}</p>{a.error && <p>{a.error}</p>}</div>)}
 {!details.data.attempt_history.length && <p className="muted">No new processing attempts recorded for this legacy upload.</p>}</div>}
 </Sheet></div>;
}

export function Conflicts() {
 const { service } = useSession();
 const viewer = useViewer();
 const cache = useQueryClient();
 const conflicts = useQuery({ queryKey: ["conflicts"], queryFn: () => service.json<Conflict[]>("/conflicts"), refetchInterval: 5000 });
 const [selected, setSelected] = useState<Conflict | null>(null);
 const [status, setStatus] = useState("needs_evidence");
 const [rationale, setRationale] = useState("");
 const review = useMutation({ mutationFn: () => service.json("/conflicts/" + selected!.id + "/review", { method: "POST",
 body: JSON.stringify({ expected_updated_at: selected!.updated_at, status: status.startsWith("resolved:") ? "resolved" : status, rationale,
 authoritative_claim_id: status.startsWith("resolved:") ? status.slice(9) : null }) }),
 onSuccess: () => { setSelected(null); void cache.invalidateQueries({ queryKey: ["conflicts"] }); } });
 return <div className="page reading-width"><PageHeading title="Conflict Resolution" description="Compare attributed evidence. Preserve disagreements until a reviewer decides." />
 <QueryState query={conflicts} />{conflicts.isSuccess && !conflicts.data.length && <Feedback>No reviewable conflicts in your authorized current sources.</Feedback>}
 <div className="knowledge-stack">{conflicts.data?.map((c) => <article className="panel knowledge-card" key={c.id}><div className="result-meta"><h2>{pretty(c.predicate)}</h2><span className="kind-pill">{pretty(c.status)}</span></div>
 <div className="conflict-sides"><div><small>Source claim A{c.authoritative_claim_id === c.left_claim_id ? " · Accepted by reviewer" : ""}</small><p>{c.left_value}</p><EvidenceAction id={c.left_chunk_id} /></div>
 <div><small>Source claim B{c.authoritative_claim_id === c.right_claim_id ? " · Accepted by reviewer" : ""}</small><p>{c.right_value}</p><EvidenceAction id={c.right_chunk_id} /></div></div>
 <p className="muted">{c.rationale}</p><div className="action-row"><Link className="text-action" to={"/content/" + c.canonical_id}>Open knowledge page</Link>
 {["admin", "reviewer"].includes(viewer.data?.role ?? "") && <Button variant="outline" onClick={() => { setSelected(c); setRationale(""); setStatus("needs_evidence"); review.reset(); }}>Review conflict</Button>}</div><ConflictHistory id={c.id} /></article>)}</div><IdentityReview />
 <Sheet title="Review conflict" description="Record a reasoned human decision. Original claims remain preserved." open={!!selected} onOpenChange={(open) => { if (!open) setSelected(null); }}>
 <form className="upload-form" onSubmit={(e) => { e.preventDefault(); review.mutate(); }}><label>Decision<select value={status} onChange={(e) => setStatus(e.target.value)}>
 <option value="needs_evidence">Request more evidence</option><option value="not_a_conflict">Complementary or historical statements</option>
 <option value={"resolved:" + selected?.left_claim_id}>Accept claim A as authoritative</option><option value={"resolved:" + selected?.right_claim_id}>Accept claim B as authoritative</option></select></label>
 <label>Rationale<textarea aria-label="Review rationale" required minLength={10} maxLength={2000} value={rationale} onChange={(e) => setRationale(e.target.value)} /></label>
 {review.isError && <Feedback error>{review.error.message}</Feedback>}<Button type="submit" disabled={rationale.trim().length < 10 || review.isPending}>Save review</Button></form>
 </Sheet></div>;
}

export function UsageDashboard() {
 const { service } = useSession();
 const usage = useQuery({ queryKey: ["usage"], queryFn: () => service.json<Usage[]>("/usage"), refetchInterval: 5000 });
 const rows = usage.data ?? [];
 const calls = rows.reduce((sum, row) => sum + row.calls, 0);
 const successes = rows.filter(row => row.status === "success").reduce((sum, row) => sum + row.calls, 0);
 const tokens = (key: "input_tokens" | "output_tokens") => rows.some(row => row[key] === null) ? "Incomplete" : rows.reduce((sum, row) => sum + (row[key] ?? 0), 0).toLocaleString("en");
 const meanLatency = calls ? Math.round(rows.reduce((sum, row) => sum + row.latency_ms * row.calls, 0) / calls) : null;
 return <div className="page"><PageHeading title="AI Usage" description="Recorded model activity across your organization." />
 <QueryState query={usage} />
 {usage.isSuccess && !rows.length && <Feedback>No model calls recorded. Demo processing does not consume model tokens.</Feedback>}
 {usage.isSuccess && rows.length > 0 && <><div className="metric-grid">
 {[["Requests", calls.toLocaleString("en")], ["Input tokens", tokens("input_tokens")], ["Output tokens", tokens("output_tokens")], ["Success rate", (successes / calls * 100).toFixed(1) + "%"]].map(([label,value]) => <div className="metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}
 </div><p className="muted mb-6">Mean latency: {meanLatency?.toLocaleString("en")} ms · Breakdown by operation, model, status, and configured rate.</p>
 <div className="usage-table-wrap" tabIndex={0} aria-label="AI usage breakdown"><table className="usage-table"><thead><tr><th>Operation / model</th><th>Status</th><th>Calls</th><th>Input / output</th><th>Mean latency</th><th>Cost estimate</th></tr></thead><tbody>
 {rows.map((u,i) => <tr key={i}><td><strong>{pretty(u.operation)}</strong><div className="model-name">{u.model}</div><small>{u.provider} · {u.region}</small></td><td>{pretty(u.status)}</td><td>{u.calls}<small>{u.retries} SDK retries</small></td><td>{u.input_tokens?.toLocaleString("en") ?? "Unknown"} / {u.output_tokens?.toLocaleString("en") ?? "Unknown"}</td><td>{u.latency_ms.toLocaleString("en")} ms</td><td>{u.estimated_cost === null ? "Unavailable" : u.estimated_cost + " " + u.currency}<small>{u.estimated_cost === null ? "No reliable rate configured" : "Rates effective " + u.rate_date}{u.estimated_cost !== null && u.unknown_cost_calls > 0 ? " · " + u.unknown_cost_calls + " calls have unknown cost" : ""}</small></td></tr>)}
 </tbody></table></div><p className="muted mt-4">Estimates cover recorded token calls only. No historical trend or total AWS bill is inferred.</p></>}
 </div>;
}
