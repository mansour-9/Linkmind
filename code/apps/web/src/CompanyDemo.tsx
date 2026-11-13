import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "./session";
import { Button, Feedback } from "./ui";
import type { Job } from "./api";
import { useState } from "react";

type Dataset = { name: string; description: string; can_load: boolean; provider: string;
  files: { key: string; filename: string; title: string; visibility: string; revision_of: string | null }[];
  questions: { question: string; expected: string; sources: string[]; mode?: string }[] };
type Status = { total: number; search_ready: number; enriched: number; jobs: (Job & { fixture_key: string } | null)[] };

export function CompanyDemo() {
  const { service } = useSession();
  const cache = useQueryClient();
  const [downloadError, setDownloadError] = useState("");
  const info = useQuery({ queryKey: ["company-demo"], queryFn: () => service.json<Dataset>("/demo/company") });
  const status = useQuery({ queryKey: ["company-demo-status"], queryFn: () => service.json<Status>("/demo/company/status"),
    refetchInterval: query => query.state.data?.jobs.some(j => j && ["queued", "processing"].includes(j.status)) ? 1500 : 5000 });
  const load = useMutation({ mutationFn: () => service.json<Status>("/demo/company/load", { method: "POST" }), onSuccess: () => { void cache.invalidateQueries(); } });
  async function download(key: string, filename: string) {
    setDownloadError("");
    try { await service.companyFile(key, filename); } catch (e) { setDownloadError(e instanceof Error ? e.message : "Download unavailable."); }
  }
  const active = status.data?.jobs.some(j => j && ["queued", "processing"].includes(j.status));
  return <section className="panel-padding" aria-label="Fictional company testing">
    <h3>Northstar Labs test company</h3>
    <p className="muted mt-2">24 fictional documents across five projects, with people, policies, an ownership disagreement and a private budget.</p>
    {info.isSuccess && <p className="muted mt-2">{info.data.provider === "mock" ? "Mock mode: predefined graph relationships and verbatim chat excerpts. Your own uploads remain searchable." : "Sonnet mode: real extraction, semantic retrieval and cited answers use the configured test budget."}</p>}
    {info.isError && <Feedback error>{info.error.message}</Feedback>}
    {info.data?.can_load && <Button className="mt-3" variant="outline" disabled={load.isPending || !!active || !status.isSuccess}
      onClick={() => load.mutate()}>{load.isPending ? "Adding documents…" : active ? "Processing company documents…" : "Load fictional company"}</Button>}
    {load.isError && <Feedback error>{load.error.message}</Feedback>}
    {status.isError && <Feedback error>{status.error.message}</Feedback>}
    {status.isSuccess && <p className="muted mt-2" role="status">{status.data.search_ready} / {status.data.total} search ready · {status.data.enriched} enriched</p>}
    {!!status.data?.jobs.some(j => j && ["failed", "extraction_unavailable"].includes(j.status)) && <p className="muted">Some enrichment is unavailable. Open Processing for errors and retry; searchable source text remains available.</p>}
    <p className="mt-2"><Link className="text-action" to="/admin/processing">Open Processing</Link></p>
    <details className="mt-3"><summary>Example questions and expected results</summary>
      {info.data?.questions.map(item => {
        const selected = status.data?.jobs.filter((j): j is Job & { fixture_key: string } => !!j && item.sources.includes(j.fixture_key)) ?? [];
        const params = new URLSearchParams({ q: item.question });
        selected.forEach(j => params.append("scope", j.document_id));
        return <div className="mt-3" key={item.question}>
          {selected.length === item.sources.length ? <Link className="text-action" to={"/?" + params.toString()}>{item.question}</Link> : <p>{item.question} · load the company first</p>}
          <details><summary>Expected result</summary><p className="muted">{item.expected}</p></details>
        </div>;
      })}
    </details>
    <details className="mt-3"><summary>Add information or test a revision</summary>
      <p className="muted mt-2">Upload your own text through Add data source. In mock mode it becomes searchable without invented graph facts. Sonnet mode can enrich new content.</p>
      <Button variant="ghost" onClick={() => void download("your-addition", "your-addition.txt")}>Download an addition to upload</Button>
      <Button variant="ghost" onClick={() => void download("atlas-handover-revision", "atlas-handover-revision.md")}>Download Atlas handover revision</Button>
      <p className="muted">Upload the revision through Manage source → New revision on atlas-handover.md. Its task deadline changes to December 8; old evidence remains historical.</p>
    </details>
    <details className="mt-3"><summary>Download fictional source files</summary>
      {info.data?.files.filter(f => !f.revision_of).map(f => <div key={f.key}><Button variant="ghost" onClick={() => void download(f.key, f.filename)}>{f.title}{f.visibility === "private" ? " · owner only" : ""}</Button></div>)}
    </details>
    {downloadError && <Feedback error>{downloadError}</Feedback>}
  </section>;
}
