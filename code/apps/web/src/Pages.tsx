import { useRef, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowDownToLine, ArrowRight, Clock3, Database, FileText, Network, Plus, ShieldCheck, UploadCloud } from "lucide-react";
import { useGraph, useIngest, useJobs, useSession, useViewer } from "./session";

import { Button, Feedback, jobLabels, PageHeading, SearchField, Sheet, StatusBadge } from "./ui";
import { SourceControls } from "./SourceControls";
import type { Entity, Job, Visibility } from "./api";

const uploadDate = new Intl.DateTimeFormat("en", { dateStyle: "medium" });

export function Sources() {
  const { token, service } = useSession();
  const location = useLocation();
  const [filter, setFilter] = useState("");
  const jobs = useJobs();
  const ingest = useIngest();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [visibility, setVisibility] = useState<Visibility>("private");
  const [downloadError, setDownloadError] = useState("");
  const addButton = useRef<HTMLButtonElement>(null);
  const visible = jobs.isSuccess ? jobs.data : [];
  const filtered = visible.filter(j => j.filename.toLowerCase().includes(filter.toLowerCase()));
  const queued = visible.filter((job) => job.status === "queued").length;
  const ready = visible.filter((job) => job.status === "ready").length;

  function openUpload() {
    ingest.reset();
    setFile(null);
    setVisibility("private");
    setOpen(true);
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    if (file) ingest.mutate({ file, visibility }, { onSuccess: () => setOpen(false) });
  }
  async function download(job: Job) {
    setDownloadError("");
    try { await service.download(job.version_id, job.filename); }
    catch (error) { setDownloadError(error instanceof Error ? error.message : "Download failed."); }
  }
  const currentJob = visible.find((job) => job.id === ingest.data?.id) ?? ingest.data;
  return <div className="page">
    <PageHeading title={location.pathname.startsWith("/content") ? "Documents" : "Data Sources"} description="Your sources, their access, and the knowledge they contribute."
      action={<Button ref={addButton} onClick={openUpload}><Plus size={18} /> Add data source</Button>} />
    {jobs.isSuccess && <div className="source-summary" aria-label="Upload summary">
      <span><strong>{visible.length}</strong> uploads</span>
      <span><strong>{ready}</strong> ready</span>
      <span><strong>{queued}</strong> queued</span>
    </div>}
    <SearchField className="library-search source-search" aria-label="Find a document" placeholder="Find a document…" value={filter} onChange={e => setFilter(e.target.value)} />
    <div className="source-layout">
      <section className="source-table" aria-labelledby="uploads-title">
        <div className="panel-heading"><h2 id="uploads-title">Uploaded documents</h2></div>
        {jobs.isPending && <div className="panel-padding"><Feedback>Loading uploads…</Feedback></div>}
        {jobs.isError && <div className="panel-padding"><Feedback error>Uploads could not be loaded. <Button variant="outline" onClick={() => void jobs.refetch()}>Retry</Button></Feedback></div>}
        {jobs.isSuccess && !visible.length && <div className="panel-padding"><p className="muted">No uploads are visible in this workspace.</p></div>}
        {visible.length > 0 && !filtered.length && <Feedback>No documents match your search.</Feedback>}
        {visible.length > 0 && <ul className="upload-list">
          {filtered.map((job) => <li key={job.id}>
            <span className="tile-icon"><FileText size={18} /></span>
            <div className="file-details"><strong>{job.filename}</strong>
              <small>{job.visibility === "private" ? "Only me · owner access" : "My organization"}</small>{job.error && <details className="source-error"><summary>View processing error</summary><p>{job.error}</p><Link className="text-action" to="/admin/processing">Open Processing</Link></details>}
              <time className="job-date" dateTime={job.uploaded_at}>Uploaded {uploadDate.format(new Date(job.uploaded_at))}</time>
              <details className="source-management"><summary>Manage source</summary><SourceControls job={job} /></details>
            </div>
            <div className="source-state"><StatusBadge status={job.status} /><small>{job.current_version_id === job.version_id ? "Current revision" : job.processed_at ? "Historical revision" : "Not published"}</small></div>
            <Button variant="ghost" className="icon-button" aria-label={"Download " + job.filename}
              onClick={() => void download(job)}><ArrowDownToLine size={17} /></Button>
          </li>)}
        </ul>}
      </section>
      <details className="sample-documents"><summary>Try sample documents <span>Demo data</span></summary><section className="panel-padding" aria-labelledby="sample-title">
        <span className="tile-icon tile-teal"><UploadCloud size={21} /></span>
        <h2 className="mt-3" id="sample-title">Sample documents</h2>
        <p className="muted mt-2">Use demo documents to explore graph relationships and verify access.</p>
        <div className="mt-4 flex flex-col items-start gap-2">
          <Button variant="outline" disabled={ingest.isPending}
            onClick={() => ingest.mutate({ sample: "cloud-migration", visibility: "team" })}>Load Cloud Migration sample</Button>
          {token === "demo-amal" && <Button variant="outline" disabled={ingest.isPending}
            onClick={() => ingest.mutate({ sample: "private-review", visibility: "private" })}>Load restricted sample</Button>}
        </div>
      </section></details>
    </div>
    <div className="mt-4 space-y-2">
      {!open && ingest.isPending && <Feedback>Uploading document…</Feedback>}
      {!open && ingest.isError && <Feedback error>{ingest.error.message}</Feedback>}
      {!open && currentJob && <Feedback>{currentJob.filename} · {jobLabels[currentJob.status]}</Feedback>}
      {downloadError && <Feedback error>{downloadError}</Feedback>}
    </div>
    <Sheet title="Upload a document" description="Selectable-text PDF, DOCX, UTF-8 TXT or Markdown, up to 20 MiB."
      open={open} onOpenChange={setOpen} returnFocus={addButton}>
      <form className="upload-form" onSubmit={submit}>
        <label>File<input aria-label="Choose file" type="file" accept=".pdf,.docx,.txt,.md" required
          onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label>
        <label>Access<select value={visibility} onChange={(event) => setVisibility(event.target.value as Visibility)}>
          <option value="private">Only me</option><option value="team">My organization</option>
        </select></label>
        {ingest.isError && <Feedback error>{ingest.error.message}</Feedback>}
        <Button type="submit" disabled={!file || ingest.isPending}><UploadCloud size={18} />
          {ingest.isPending ? "Uploading…" : "Upload file"}</Button>
      </form>
    </Sheet>
  </div>;
}

export function SettingsPage() {
  const viewer = useViewer();
  return <div className="page">
    <PageHeading title="Settings" description="Your active workspace, identity, and access." />
    {viewer.isPending && <Feedback>Loading settings…</Feedback>}
    {viewer.isError && <Feedback error>Workspace settings could not be loaded. <Button variant="outline" onClick={() => void viewer.refetch()}>Retry</Button></Feedback>}
    {viewer.isSuccess && <section className="panel settings-panel">
      <div className="panel-heading"><ShieldCheck size={20} /><h2>Workspace access</h2></div>
      <dl><div><dt>Workspace</dt><dd>{viewer.data.organization}</dd></div>
        <div><dt>Active identity</dt><dd>{viewer.data.name}</dd></div>
        <div><dt>Mode</dt><dd>Local demo</dd></div>
      </dl>
    </section>}
  </div>;
}
