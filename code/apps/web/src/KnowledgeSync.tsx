import { useEffect, useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useSession, useViewer } from './session';
import { Button, Feedback, PageHeading } from './ui';

type Run = { id: string; status: string; trigger: string; created_at: string; finished_at: string | null };
type Source = { connection_id: string; source_name: string; status: string; imported: number; updated: number; skipped: number; failed: number; error_code: string | null };
type Schedule = { enabled: boolean; time_of_day: string; timezone: string; next_run_at: string | null };
type Event = { id: number; connection_id: string | null; created_at: string; code: string };

const running = (value?: Run) => !!value && !value.finished_at;
const date = (value: string) => new Date(value).toLocaleString();
const labels: Record<string, string> = {
  queued: 'Queued', running: 'Collecting', indexing: 'Indexing', completed: 'Completed', partial: 'Partially completed', failed: 'Failed',
  source_started: 'Collection started', page_processed: 'Batch processed', source_completed: 'Source completed',
  authentication_expired: 'Source sign-in expired', credentials_missing: 'Source credential is missing',
  sync_pagination_unavailable: 'Scoped collection is unavailable', connection_changed: 'Connection settings changed',
  source_unavailable: 'Source is unavailable', indexing_failed: 'Some records could not be indexed', record_failed: 'Some records could not be retained',
};
const label = (value: string) => labels[value] ?? value.replaceAll('_', ' ');

export default function KnowledgeSync() {
  const { service } = useSession();
  const viewer = useViewer();
  const cache = useQueryClient();
  const enabled = viewer.data?.role === 'admin';
  const [selected, setSelected] = useState<string>();
  const [draft, setDraft] = useState<Schedule>();
  const [eventPage, setEventPage] = useState(0);
  const prefix = '/knowledge-sync';
  const history = useQuery({ queryKey: ['knowledge-sync', 'runs'], enabled,
    queryFn: () => service.json<Run[]>(prefix + '/runs'),
    refetchInterval: query => query.state.data?.some(running) ? 2000 : 15000 });
  const schedule = useQuery({ queryKey: ['knowledge-sync', 'schedule'], enabled,
    queryFn: () => service.json<Schedule>(prefix + '/schedule') });
  useEffect(() => { if (schedule.data) setDraft(schedule.data); }, [schedule.data]);
  const id = selected ?? history.data?.[0]?.id;
  const detail = useQuery({ queryKey: ['knowledge-sync', id], enabled: enabled && !!id,
    queryFn: () => service.json<Run & { sources: Source[] }>(prefix + '/runs/' + id),
    refetchInterval: query => running(query.state.data) ? 2000 : false });
  const events = useQuery({ queryKey: ['knowledge-sync', id, 'events', eventPage], enabled: enabled && !!id,
    queryFn: () => service.json<Event[]>(prefix + '/runs/' + id + '/events?after=' + eventPage),
    refetchInterval: running(detail.data) ? 2000 : false });
  const sync = useMutation({ mutationFn: () => service.json<{ id: string }>(prefix + '/runs', { method: 'POST' }),
    onSuccess: run => { setSelected(run.id); setEventPage(0); void cache.invalidateQueries({ queryKey: ['knowledge-sync'] }); } });
  const save = useMutation({ mutationFn: (value: Schedule) => service.json<Schedule>(prefix + '/schedule', { method: 'PUT',
    body: JSON.stringify({ enabled: value.enabled, time_of_day: value.time_of_day.slice(0, 5), timezone: value.timezone }) }),
    onSuccess: value => cache.setQueryData(['knowledge-sync', 'schedule'], value) });
  function submit(event: FormEvent) { event.preventDefault(); if (draft) save.mutate(draft); }
  const active = history.data?.some(running) || running(detail.data);
  if (!enabled) return <div className="page"><PageHeading title="Knowledge Sync" description="Manage background collection." /><Feedback>{viewer.isPending ? 'Checking access…' : 'Knowledge Sync requires an administrator.'}</Feedback></div>;

  return <div className="page reading-width">
    <PageHeading title="Knowledge Sync" description="Collect and index content from connections enabled for Live + Sync."
      action={<Button onClick={() => sync.mutate()} disabled={sync.isPending || active}>Sync All Now</Button>} />
    {sync.isError && <Feedback error>{sync.error.message} <Link to="/admin/connections">Manage connections</Link></Feedback>}
    <section className="panel process-card"><h2>Automatic schedule</h2>
      {schedule.isError && <Feedback error>{schedule.error.message}</Feedback>}
      {draft && <form className="upload-form" onSubmit={submit}>
        <label><input type="checkbox" checked={draft.enabled} onChange={e => setDraft({ ...draft, enabled: e.target.checked })} /> Run daily</label>
        <label>Time<input type="time" required value={draft.time_of_day.slice(0, 5)} onChange={e => setDraft({ ...draft, time_of_day: e.target.value })} /></label>
        <label>Time zone<input required value={draft.timezone} onChange={e => setDraft({ ...draft, timezone: e.target.value })} placeholder="Asia/Riyadh" /></label>
        <div className="action-row"><Button type="submit" variant="outline" disabled={save.isPending}>Save schedule</Button>
          {schedule.data?.next_run_at && <small>Next run {date(schedule.data.next_run_at)}</small>}
          {save.isSuccess && <small role="status">Schedule saved</small>}</div>
        {save.isError && <Feedback error>{save.error.message}</Feedback>}
      </form>}
    </section>
    <section className="panel process-card"><h2>Run history</h2>
      {history.isError && <Feedback error>{history.error.message}</Feedback>}
      {history.isSuccess && !history.data.length && <Feedback>No sync activity yet. Enable Live + Sync on a connection to get started.</Feedback>}
      {!!history.data?.length && <label>Run <select value={id} onChange={e => { setSelected(e.target.value); setEventPage(0); }}>
        {history.data.map(run => <option key={run.id} value={run.id}>{date(run.created_at)} · {label(run.status)} · {label(run.trigger)}</option>)}
      </select></label>}
      {detail.isError && <Feedback error>{detail.error.message}</Feedback>}
      {detail.data && <><p role="status">{label(detail.data.status)}</p><div className="chat-table-scroll"><table className="chat-projects">
        <thead><tr><th>Source</th><th>Status</th><th>Imported</th><th>Updated</th><th>Skipped</th><th>Failed</th></tr></thead>
        <tbody>{detail.data.sources.map(source => <tr key={source.connection_id}><td>{source.source_name}</td><td>{label(source.status)}
          {source.error_code && <div>{label(source.error_code)}</div>}</td><td>{source.imported}</td><td>{source.updated}</td><td>{source.skipped}</td><td>{source.failed}</td></tr>)}</tbody>
      </table></div></>}
      {events.isError && <Feedback error>{events.error.message}</Feedback>}
      {!!events.data?.length && <details><summary>Execution log</summary><ul>
        {events.data.map(event => <li key={event.id}>{date(event.created_at)} · {detail.data?.sources.find(source => source.connection_id === event.connection_id)?.source_name ?? 'Run'} · {label(event.code)}</li>)}
      </ul><div className="action-row">{eventPage > 0 && <Button variant="outline" onClick={() => setEventPage(0)}>First events</Button>}
        {events.data.length === 100 && <Button variant="outline" onClick={() => setEventPage(events.data!.at(-1)!.id)}>Next events</Button>}</div></details>}
    </section>
  </div>;
}
