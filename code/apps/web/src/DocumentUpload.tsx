import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, LoaderCircle, Paperclip, UploadCloud, X } from 'lucide-react';
import { useSession } from './session';
import { Button, Feedback } from './ui';
import type { Job } from './api';

export type UploadItem = { id: string; filename: string; uploading: boolean; job?: Job; error?: string };

export function DocumentUpload({ compact = false, onChange, dropped }: {
  compact?: boolean; onChange?: (items: UploadItem[]) => void; dropped?: File[];
}) {
  const { service } = useSession();
  const cache = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState<UploadItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const jobs = useQuery({ queryKey: ['document-upload-jobs'], queryFn: () => service.jobs(), enabled: rows.some(r => r.job), refetchInterval: query => rows.some(r => {const job=query.state.data?.find(j=>j.id===r.job?.id)??r.job;return r.uploading || job && !job.search_ready_at && ['queued','processing'].includes(job.status);}) ? 1500 : false });
  const onChangeRef = useRef(onChange); onChangeRef.current = onChange;
  const current = rows.map(r => ({ ...r, job: jobs.data?.find(j => j.id === r.job?.id) ?? r.job }));
  useEffect(() => { onChangeRef.current?.(rows.map(r => ({ ...r, job: jobs.data?.find(j => j.id === r.job?.id) ?? r.job }))); }, [rows, jobs.data]);
  async function upload(files: File[]) {
    const pending = files.slice(0, 30).map(file => ({ file, id: crypto.randomUUID() }));
    setRows(old => [...old, ...pending.map(p => ({ id: p.id, filename: p.file.name, uploading: true }))]);
    for (const item of pending) {
      try {
        if (!/\.(pdf|docx|md|txt)$/i.test(item.file.name)) throw new Error('Use a text PDF, DOCX, TXT or Markdown file.');
        if (item.file.size > 20 * 1024 * 1024) throw new Error('Each file must be 20 MiB or smaller.');
        const job = await service.upload(item.file, 'team');
        setRows(old => old.map(r => r.id === item.id ? { ...r, uploading: false, job } : r));
      } catch (error) { setRows(old => old.map(r => r.id === item.id ? { ...r, uploading: false, error: error instanceof Error ? error.message : 'Upload failed.' } : r)); }
    }
    await Promise.all([cache.invalidateQueries({ queryKey: ['repository-resources'] }), cache.invalidateQueries({ queryKey: ['repository-sources'] }), cache.invalidateQueries({ queryKey: ['jobs'] }), cache.invalidateQueries({ queryKey: ['document-upload-jobs'] })]);
  }
  const droppedRef = useRef<File[] | undefined>(undefined);
  useEffect(() => { if (dropped?.length && dropped !== droppedRef.current) { droppedRef.current = dropped; void upload(dropped); } }, [dropped]);
  return <div className={'document-uploader' + (compact ? ' compact' : '')}>
    <div className={'document-dropzone' + (dragging ? ' is-dragging' : '')} onDragOver={e => { if (e.dataTransfer.types.includes('Files')) { e.preventDefault(); setDragging(true); } }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); e.stopPropagation(); setDragging(false); void upload(Array.from(e.dataTransfer.files)); }}>
      <input ref={input} aria-label={compact ? 'Attach documents' : 'Upload documents'} type="file" accept=".pdf,.docx,.md,.txt" multiple hidden onChange={e => { void upload(Array.from(e.target.files ?? [])); e.target.value = ''; }} />
      {compact ? <Button variant="ghost" type="button" onClick={() => input.current?.click()}><Paperclip size={17} />Attach files</Button> : <><UploadCloud size={25} /><div><strong>Drop documents here</strong><p>Text PDF, DOCX, TXT or Markdown · up to 20 MiB each</p></div><Button type="button" onClick={() => input.current?.click()}>Choose files</Button></>}
    </div>
    <p className="muted document-sharing-note">Added to your organization's Documents. Your team can search and ask questions about these files.</p>
    {!!current.length && <ul className="document-upload-list" aria-label={compact ? 'Attachments' : 'Upload progress'}>{current.map(r => {
      const ready = !!r.job?.search_ready_at && r.job.current_version_id === r.job.version_id;
      const failed = r.error || r.job?.error || r.job && ['failed', 'cancelled', 'extraction_unavailable'].includes(r.job.status);
      return <li key={r.id}><FileText size={17} /><span><strong dir="auto">{r.filename}</strong><small role="status">{r.uploading ? 'Uploading…' : r.error ? r.error : ready ? 'Ready for search and answers' : failed ? r.job?.error ?? 'This file could not be prepared. Check Documents.' : 'Preparing for search…'}</small></span>{(r.uploading || !ready && !failed) && <LoaderCircle size={16} className="spin" />}<Button type="button" variant="ghost" disabled={r.uploading} aria-label={'Remove ' + r.filename} onClick={() => setRows(old => old.filter(x => x.id !== r.id))}><X size={15} /></Button></li>;
    })}</ul>}
    {jobs.isError && <Feedback error>File status could not be refreshed. <Button type="button" variant="ghost" onClick={() => void jobs.refetch()}>Retry</Button></Feedback>}
  </div>;
}
