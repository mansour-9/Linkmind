import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, Library, Search, SlidersHorizontal, X } from "lucide-react";
import { useSession } from "./session";
import { Button, Feedback, Sheet, sourceLocation } from "./ui";
import type { Passage } from "./contracts";

export type FocusDocument = { document_id: string; version_id: string; filename: string; visibility: string; uploaded_at: string; dataset_id?: string|null };
type Match = FocusDocument & { excerpt?: string; locator?: Record<string, unknown> };
const MAX_SOURCES = 30;

export function FocusSources({ value, onChange, disabled, conversation, explicitOnly=false, allLabel="All sources" }: {
  value: string[]; onChange: (ids: string[]) => void; disabled: boolean; conversation: boolean; explicitOnly?:boolean; allLabel?:string;
}) {
  const { service } = useSession();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const trigger = useRef<HTMLButtonElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const ids = [...value].sort();
  const selected = useQuery({ queryKey: ["focus-documents", ids], queryFn: () => service.json<FocusDocument[]>("/documents?chat_eligible=true&" + ids.map(id => "id=" + encodeURIComponent(id)).join("&")), enabled: !!ids.length, refetchInterval: ids.length ? 5000 : false });
  const results = useQuery({ queryKey: ["focus-discovery", query, offset], enabled: open,
    queryFn: async (): Promise<Match[]> => {
      if (!query) return service.json<FocusDocument[]>("/documents?chat_eligible=true&limit=20&offset=" + offset);
      // Search is submitted deliberately: typing must not trigger embedding calls on every keystroke.
      const [passages, filenames] = await Promise.all([
        service.json<Passage[]>("/documents/search?" + new URLSearchParams({ q: query, limit: "40" })),
        service.json<FocusDocument[]>("/documents?" + new URLSearchParams({ q: query, limit: "20", chat_eligible: "true" })),
      ]);
      const found = new Map<string, Match>();
      for (const p of passages) if (!found.has(p.document_id)) found.set(p.document_id, { document_id: p.document_id, version_id: p.version_id, filename: p.filename, visibility: "", uploaded_at: "", excerpt: p.text, locator: p.locator, dataset_id:p.dataset_id });
      for (const p of filenames) if (!found.has(p.document_id)) found.set(p.document_id, p);
      return [...found.values()];
    },
  });
  function showPicker() { setDraft([...value]); setInput(""); setQuery(""); setOffset(0); setOpen(true); }
  function apply(ids: string[]) { onChange(ids); setOpen(false); }
  function toggle(id: string) { setDraft(current => current.includes(id) ? current.filter(x => x !== id) : current.length < MAX_SOURCES ? [...current, id] : current); }
  const names = selected.isSuccess ? selected.data : [];
  return <div className="focus-sources">
    <div className="focus-toolbar"><span className="scope-status"><Library size={16} />{value.length ? "Selected sources" : explicitOnly ? "No stored documents selected" : allLabel}</span>
      <Button ref={trigger} variant="ghost" className="focus-trigger" disabled={disabled} onClick={showPicker}><SlidersHorizontal size={15} />Focus sources</Button>
      {!!value.length && <Button variant="ghost" className="scope-clear" disabled={disabled} onClick={() => onChange([])}>{explicitOnly ? 'Clear stored selection' : 'Clear document selection'}</Button>}
    </div>
    {!!value.length && <div className="selected-source-chips" aria-label="Selected sources">{value.map(id => {
      const name = names.find(d => d.document_id === id)?.filename ?? (selected.isPending ? "Loading source…" : "Source unavailable");
      return <span className="selected-source-chip" key={id} title={name}><FileText size={13} /><span>{name}</span><button type="button" aria-label={"Remove " + name} disabled={disabled} onClick={() => onChange(value.filter(x => x !== id))}><X size={13} /></button></span>;
    })}</div>}
    <Sheet title="Focus your sources" description="Find documents by project, topic, or filename. Select the ones you want Linkmind to use." side="center" open={open} onOpenChange={setOpen} returnFocus={trigger} initialFocus={searchInput}>
      <div className="source-picker">
        <form className="source-picker-search" onSubmit={e => { e.preventDefault(); e.stopPropagation(); setQuery(input.trim()); setOffset(0); if (query === input.trim()) void results.refetch(); }}>
          <label className="source-picker-input"><Search size={18} /><input ref={searchInput} aria-label="Find sources by topic" maxLength={500} placeholder="Describe what you need, e.g. Project Alpha launch plan" value={input} onChange={e => setInput(e.target.value)} /></label>
          <Button type="submit" variant="secondary">Search</Button>
        </form>
        <div className="source-picker-context"><span>{query ? "Relevant documents" : "Recent available documents"}</span>{query && <button type="button" onClick={() => { setInput(""); setQuery(""); setOffset(0); }}>Clear search</button>}</div>
        <div className="source-picker-results" aria-busy={results.isFetching}>
          {results.isFetching && <Feedback>Finding sources…</Feedback>}
          {results.isError && <Feedback error>Sources could not be searched. Your selection is kept.<Button variant="outline" onClick={() => void results.refetch()}>Retry</Button></Feedback>}
          {results.isSuccess && !results.data.length && <div className="source-picker-empty"><Search size={26} /><h3>No matching sources</h3><p>Try a project name, person, or a few important words from the information you need.</p></div>}
          {results.isSuccess && results.data.map(doc => <label className={"source-picker-result" + (draft.includes(doc.document_id) ? " is-selected" : "")} key={doc.document_id}>
            <input type="checkbox" checked={draft.includes(doc.document_id)} disabled={!draft.includes(doc.document_id) && draft.length >= MAX_SOURCES} onChange={() => toggle(doc.document_id)} aria-label={"Select " + doc.filename} />
            <span className="picker-file-icon"><FileText size={18} /></span><span className="picker-result-text"><strong>{doc.filename}</strong>{doc.dataset_id&&<small>Demo dataset · included only when selected</small>}
              {doc.excerpt ? <><small className="match-label">Content match · {sourceLocation(doc.locator)}</small><span className="picker-excerpt" dir="auto">{doc.excerpt}</span></> : <small>{query ? "Filename match" : (doc.visibility === "private" ? "Only me" : "My organization")}</small>}
            </span>
          </label>)}
        </div>
        {!query && results.isSuccess && <div className="picker-pagination"><Button variant="ghost" disabled={offset === 0 || results.isFetching} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous</Button><span>Page {offset / 20 + 1}</span><Button variant="ghost" disabled={results.data.length < 20 || results.isFetching} onClick={() => setOffset(offset + 20)}>Next</Button></div>}
        <footer className="source-picker-footer"><p>{draft.length ? `${draft.length} selected · up to ${MAX_SOURCES}` : explicitOnly ? "Only explicitly selected documents are used" : "Let Linkmind choose relevant sources"}{conversation && <small>Changing sources starts a new conversation.</small>}</p><div><Button variant="ghost" onClick={() => apply([])}>{explicitOnly ? 'Clear stored selection' : 'Clear document selection'}</Button><Button onClick={() => apply(draft)}>{draft.length ? "Apply selection" : "Done"}</Button></div></footer>
      </div>
    </Sheet>
  </div>;
}
