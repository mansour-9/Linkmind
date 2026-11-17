import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, FileText, Plus } from 'lucide-react';
import { useSession } from './session';
import { Button, Feedback, PageHeading, SearchField, Sheet } from './ui';
import { EvidenceAction } from './Evidence';
import { DocumentUpload } from './DocumentUpload';
import { SourceControls } from './SourceControls';
import type { Job } from './api';

type Group = { id: string; name: string; kind: string; created_by_name: string; resource_count: number };
type Source = { id: string; name: string; kind: string; resource_count: number; searchable_count: number;
  last_received_at: string | null; capabilities: { indexed_search: boolean; live: boolean; history: boolean } };
type Resource = { document_id: string; version_id: string; filename: string; title: string; custom_title: string | null;
  source_name: string; source_instance_id: string; format: string; visibility: string; uploaded_at: string;
  search_ready_at: string | null; embedding_status: string; project_id: string | null; project_name: string | null;
  team_id: string | null; team_name: string | null; can_manage: boolean; metadata_revision: number; metadata_updated_at: string | null };
type Catalog = { items: Resource[]; total: number; has_more: boolean; offset: number; limit: number };
type Revision = { version_id: string; filename: string; uploaded_at: string; current: boolean; first_passage_id: string | null };
const date = (value: string | null) => value ? new Date(value).toLocaleString('en') : 'Not recorded';

export function RepositoryFilters({ params, onChange }: { params: URLSearchParams; onChange: (key: string, value: string) => void }) {
  const { service } = useSession();
  const sources = useQuery({ queryKey: ['repository-sources'], queryFn: () => service.json<Source[]>('/repository/sources'), refetchInterval: 5000 });
  const [groupQuery, setGroupQuery] = useState('');
  const groups = useQuery({ queryKey: ['repository-groups', groupQuery], queryFn: () => service.json<Group[]>('/repository/groups?q=' + encodeURIComponent(groupQuery)), refetchInterval: 5000 });
  return <><div className="search-filters repository-filters">
    <label>Source system<select aria-label="Source system" value={params.get('source_instance_id') ?? ''} onChange={e => onChange('source_instance_id', e.target.value)}>
      <option value="">All source systems</option>{sources.isSuccess && sources.data.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
      {params.get('source_instance_id') && !sources.data?.some(s => s.id === params.get('source_instance_id')) && <option value={params.get('source_instance_id')!}>Selected source</option>}
    </select></label>
    <label>Find project or team<SearchField className="library-search" aria-label="Find project or team" value={groupQuery} maxLength={120} onChange={e => setGroupQuery(e.target.value)} placeholder="Search groups…" /></label>
    <label>File type<select aria-label="File type" value={params.get('format') ?? ''} onChange={e => onChange('format', e.target.value)}>
      <option value="">All file types</option>{['pdf', 'docx', 'md', 'txt'].map(f => <option key={f} value={f}>{f.toUpperCase()}</option>)}
    </select></label>
    {(['project', 'team'] as const).map(kind => <label key={kind}>{kind === 'project' ? 'Project' : 'Team'}
      <select aria-label={kind === 'project' ? 'Project' : 'Team'} value={params.get(kind + '_id') ?? ''} onChange={e => onChange(kind + '_id', e.target.value)}>
        <option value="">{kind === 'project' ? 'All projects' : 'All teams'}</option>
        {params.get(kind + '_id') && !groups.data?.some(g => g.id === params.get(kind + '_id')) && <option value={params.get(kind + '_id')!}>Selected {kind}</option>}
        {groups.isSuccess && groups.data.filter(g => g.kind === kind).map(g => <option key={g.id} value={g.id}>{g.name} · {g.created_by_name}</option>)}
      </select></label>)}
    <label>Uploaded after<input aria-label="Uploaded after" type="date" value={params.get('after') ?? ''} onChange={e => onChange('after', e.target.value)} /></label>
    <label>Uploaded before<input aria-label="Uploaded before" type="date" value={params.get('before') ?? ''} onChange={e => onChange('before', e.target.value)} /></label>
  </div>{groups.isSuccess && groups.data.length === 100 && <p className="muted">Showing the first 100 matching projects and teams. Narrow the choices to find another group.</p>}{(sources.isError || groups.isError) && <Feedback error>Source filters could not be loaded. <Button variant="outline" onClick={() => { void sources.refetch(); void groups.refetch(); }}>Retry filters</Button></Feedback>}</>;
}

function GroupPicker({ kind, value, name, onChange }: { kind: 'project' | 'team'; value: string; name: string | null; onChange: (id: string) => void }) {
  const { service } = useSession();
  const cache = useQueryClient();
  const [query, setQuery] = useState('');
  const [created, setCreated] = useState<Group | null>(null);
  const label = kind === 'project' ? 'Project' : 'Team';
  const groups = useQuery({ queryKey: ['repository-group-picker', kind, query], queryFn: () => service.json<Group[]>('/repository/groups?' + new URLSearchParams({ kind, q: query })) });
  const create = useMutation({ mutationFn: () => service.json<Group>('/repository/groups', { method: 'POST', body: JSON.stringify({ kind, name: query.trim() }) }),
    onSuccess: group => { setCreated(group); onChange(group.id); setQuery(''); void cache.invalidateQueries({ queryKey: ['repository-groups'] }); void cache.invalidateQueries({ queryKey: ['repository-group-picker'] }); } });
  const options = groups.isSuccess ? groups.data : [];
  return <fieldset className="repository-group-picker"><legend>{label}</legend>
    <SearchField className="library-search" aria-label={'Find ' + kind} placeholder={'Find a ' + kind + '…'} value={query} maxLength={120} onChange={e => setQuery(e.target.value)} />
    <select aria-label={'Assign ' + kind} value={value} onChange={e => onChange(e.target.value)}>
      <option value="">Not assigned</option>
      {!!value && !options.some(g => g.id === value) && <option value={value}>{created?.id === value ? created.name : name ?? 'Selected ' + kind}</option>}
      {options.map(g => <option key={g.id} value={g.id}>{g.name} · {g.created_by_name}</option>)}
    </select>
    {query.trim() && <Button variant="outline" disabled={create.isPending} onClick={() => create.mutate()}>Create {kind} “{query.trim()}”</Button>}
    {groups.isError && <Feedback error>{groups.error.message}<Button variant="outline" onClick={() => void groups.refetch()}>Retry</Button></Feedback>}
    {create.isError && <Feedback error>{create.error.message}</Feedback>}
    {groups.isPending && <p className="muted">Loading {kind}s…</p>}
  </fieldset>;
}

function MetadataEditor({ document, done }: { document: Resource; done: () => void }) {
  const { service } = useSession();
  const cache = useQueryClient();
  const [title, setTitle] = useState(document.custom_title ?? '');
  const [project, setProject] = useState(document.project_id ?? '');
  const [team, setTeam] = useState(document.team_id ?? '');
  const [expectedRevision] = useState(document.metadata_revision);
  const save = useMutation({ mutationFn: () => service.json('/documents/' + document.document_id + '/metadata', {
    method: 'PATCH', body: JSON.stringify({ expected_revision: expectedRevision, title: title.trim() || null, project_id: project || null, team_id: team || null }),
  }), onSuccess: () => { void cache.invalidateQueries(); done(); } });
  return <form className="upload-form" onSubmit={e => { e.preventDefault(); save.mutate(); }}>
    <p className="muted">Organize this document without changing its original content. Project and team associations are assigned explicitly.</p>
    <label>Display title<input type="text" aria-label="Display title" value={title} maxLength={240} placeholder={document.filename} onChange={e => setTitle(e.target.value)} /></label>
    <GroupPicker kind="project" value={project} name={document.project_name} onChange={setProject} />
    <GroupPicker kind="team" value={team} name={document.team_name} onChange={setTeam} />
    {save.isError && <Feedback error>{save.error.message} <Button variant="outline" onClick={() => { void cache.invalidateQueries(); done(); }}>Reload details</Button></Feedback>}
    <div className="action-row"><Button type="submit" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save details'}</Button><Button variant="outline" onClick={done}>Cancel</Button></div>
  </form>;
}

function RevisionDownload({ revision }: { revision: Revision }) {
  const { service } = useSession();
  const download = useMutation({ mutationFn: () => service.download(revision.version_id, revision.filename) });
  return <><Button variant="ghost" disabled={download.isPending} onClick={() => download.mutate()}>Download original</Button>{download.isError && <Feedback error>{download.error.message}</Feedback>}</>;
}

function DocumentDetails({ id }: { id: string }) {
  const { service } = useSession();
  const [editing, setEditing] = useState(false);
  const [offset, setOffset] = useState(0);
  const document = useQuery({ queryKey: ['document-metadata', id], queryFn: () => service.json<Resource>('/documents/' + id + '/metadata'), refetchInterval: 5000 });
  const jobs=useQuery({queryKey:['jobs'],queryFn:()=>service.jobs()});
  const job=jobs.data?.find((j:Job)=>j.document_id===id && j.current_version_id===j.version_id);
  const versions = useQuery({ queryKey: ['document-versions', id, offset], queryFn: () => service.json<{ items: Revision[]; has_more: boolean }>('/documents/' + id + '/versions?limit=20&offset=' + offset), refetchInterval: 5000, enabled: document.isSuccess });
  if (document.isPending) return <Feedback>Loading document details…</Feedback>;
  if (document.isError) return <Feedback error>{document.error.message}<Button variant="outline" onClick={() => void document.refetch()}>Retry</Button></Feedback>;
  const d = document.data;
  return <div className="repository-detail">{job && <SourceControls job={job}/>}<h2>{d.title}</h2><p className="muted">{d.filename}</p>
    {editing && d.can_manage ? <MetadataEditor document={d} done={() => setEditing(false)} /> : <>
      <dl className="repository-metadata">
        <div><dt>Source</dt><dd>{d.source_name}</dd></div><div><dt>File type</dt><dd>{d.format.toUpperCase()}</dd></div>
        <div><dt>Project</dt><dd>{d.project_name ?? 'Not assigned'}</dd></div><div><dt>Team</dt><dd>{d.team_name ?? 'Not assigned'}</dd></div>
        <div><dt>Received</dt><dd>{date(d.uploaded_at)}</dd></div><div><dt>Source updated</dt><dd>Not provided by the upload</dd></div>
        <div><dt>Access</dt><dd>{d.visibility === 'team' ? 'My organization' : 'Only the owner'}</dd></div>
        <div><dt>Search</dt><dd>{d.search_ready_at ? 'Ready for search and answers' : 'Not search ready'}</dd></div>
        <div><dt>Semantic index</dt><dd>{d.embedding_status.replaceAll('_', ' ')}</dd></div>
        {d.metadata_updated_at && <div><dt>Details updated</dt><dd>{date(d.metadata_updated_at)}</dd></div>}
      </dl>
      <div className="action-row">{d.can_manage && <><Button variant="outline" onClick={() => setEditing(true)}>Edit details</Button><Button variant="outline" asChild><Link to={'/admin/sources?document_id=' + d.document_id}>Manage source</Link></Button></>}
        {d.search_ready_at && <Button asChild><Link to={'/?scope=' + d.document_id}>Ask about this document</Link></Button>}</div>
    </>}
    <section className="repository-history"><h3>Original files and revisions</h3>
      {versions.isPending && <Feedback>Loading revisions…</Feedback>}
      {versions.isError && <Feedback error>{versions.error.message}<Button variant="outline" onClick={() => void versions.refetch()}>Retry</Button></Feedback>}
      {versions.isSuccess && <><ul>{versions.data.items.map(v => <li key={v.version_id}><strong>{v.filename}</strong>
        <small>{v.current ? 'Current revision' : 'Earlier or unpublished revision'} · Received {date(v.uploaded_at)}</small>
        <div className="action-row">{v.first_passage_id && <EvidenceAction id={v.first_passage_id} title="Open original passage" />}<RevisionDownload revision={v} /></div></li>)}</ul>
        <div className="action-row"><Button variant="outline" disabled={!offset} onClick={() => setOffset(x => Math.max(0, x - 20))}>Earlier page</Button><Button variant="outline" disabled={!versions.data.has_more} onClick={() => setOffset(x => x + 20)}>More revisions</Button></div></>}
    </section>
  </div>;
}

export function Repository() {
  const { service } = useSession();
  const [params, setParams] = useSearchParams();
  const [input, setInput] = useState(params.get('q') ?? '');
  useEffect(() => setInput(params.get('q') ?? ''), [params]);
  const [selected, setSelected] = useState<string | null>(null);
  const [uploadOpen,setUploadOpen]=useState(false);
  const addDocumentButton=useRef<HTMLButtonElement>(null);
  const offset = Math.max(0, Math.min(100000, Number(params.get('offset')) || 0));
  const query = new URLSearchParams(params); query.set('offset', String(offset)); query.set('limit', '20');
  const catalog = useQuery({ queryKey: ['repository-resources', query.toString()], queryFn: () => service.json<Catalog>('/repository/resources?' + query), refetchInterval: 5000 });
  const sources = useQuery({ queryKey: ['repository-sources'], queryFn: () => service.json<Source[]>('/repository/sources'), refetchInterval: 5000 });
  function filter(key: string, value: string) { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); next.delete('offset'); setParams(next); }
  function page(value: number) { const next = new URLSearchParams(params); next.set('offset', String(value)); setParams(next); }
  return <div className="page repository-page"><PageHeading title="Documents" description="Upload files, find information and ask questions with supporting sources."
    action={<Button ref={addDocumentButton} type="button" onClick={()=>setUploadOpen(true)}><Plus size={18}/>Add document</Button>} />
    <Sheet title="Add documents" description="Upload files to your organization's Documents." side="center" open={uploadOpen} onOpenChange={setUploadOpen} returnFocus={addDocumentButton}>
      <DocumentUpload/>
    </Sheet>
    <form className="intelligence-search" onSubmit={e => { e.preventDefault(); filter('q', input.trim()); }}>
      <SearchField className="library-search" aria-label="Find stored knowledge" placeholder="Search content, title, project or team…" value={input} maxLength={500} onChange={e => setInput(e.target.value)} /><Button type="submit">Search documents</Button>
    </form><RepositoryFilters params={params} onChange={filter} />
    {!!params.toString() && <Button variant="ghost" onClick={() => { setParams({}); setInput(''); }}>Clear filters</Button>}
    {catalog.isPending && <Feedback>Loading stored knowledge…</Feedback>}
    {catalog.isError && <Feedback error>{catalog.error.message}<Button variant="outline" onClick={() => void catalog.refetch()}>Retry</Button></Feedback>}
    {catalog.isSuccess && <><p className="library-count">{catalog.data.total} {catalog.data.total === 1 ? 'document' : 'documents'} available</p>
      {!catalog.data.items.length && <div className="knowledge-empty"><FileText size={28} /><h2>No matching documents</h2><p>Try another search or add a readable document.</p></div>}
      <div className="repository-list">{catalog.data.items.map(d => <article className="repository-row" key={d.document_id}>
        <FileText size={22} /><div><h2><button className="repository-title" onClick={() => setSelected(d.document_id)}>{d.title}</button></h2>
          {d.title !== d.filename && <p className="muted">{d.filename}</p>}
          <small>{d.source_name} · {d.format.toUpperCase()} · {d.visibility === 'team' ? 'My organization' : 'Only me'}</small>
          {(d.project_name || d.team_name) && <p className="repository-associations">{[d.project_name && 'Project: ' + d.project_name, d.team_name && 'Team: ' + d.team_name].filter(Boolean).join(' · ')}</p>}
          <small>Received {date(d.uploaded_at)} · {d.search_ready_at ? 'Search ready' : 'Not search ready'}</small>
        </div><div className="repository-row-actions"><Button variant="outline" onClick={() => setSelected(d.document_id)}>Details</Button>
          {d.search_ready_at && <Link className="text-action" to={'/?scope=' + d.document_id}>Ask AI<ArrowRight size={14} /></Link>}</div>
      </article>)}</div>
      <div className="action-row repository-pagination"><Button variant="outline" disabled={!offset} onClick={() => page(Math.max(0, offset - 20))}>Previous</Button><span className="muted">Page {Math.floor(offset / 20) + 1}</span><Button variant="outline" disabled={!catalog.data.has_more} onClick={() => page(offset + 20)}>Next</Button></div>
    </>}
    <details className="repository-source-catalog"><summary>Sources in this repository</summary>
      {sources.isSuccess && sources.data.map(s => <div key={s.id}><strong>{s.name}</strong><p>{s.resource_count} accessible documents · {s.searchable_count} search ready</p>
        <small>Stored knowledge · Indexed search · Revision history</small><p className="muted">Last received {date(s.last_received_at)}</p></div>)}
      {sources.isSuccess && !sources.data.length && <p>No stored sources are available yet.</p>}
    </details>
    <Sheet title="Document details" description="Organization, source information and original revisions." open={!!selected} onOpenChange={open => { if (!open) setSelected(null); }}>
      {selected && <DocumentDetails key={selected} id={selected} />}
    </Sheet>
  </div>;
}
