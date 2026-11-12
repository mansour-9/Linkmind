import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, FileText } from "lucide-react";
import { useSession } from "./session";
import { Button, Feedback, Sheet, sourceLocation } from "./ui";
import type { Evidence } from "./api";

export function SourcePreview({ evidence }: { evidence: Evidence }) {
  const { service } = useSession();
  const download = useMutation({ mutationFn: () => service.download(evidence.version_id, evidence.filename) });
  return <div className="source-preview">
    <span className="source-file-icon"><FileText size={22} /></span>
    <h2>{evidence.filename}</h2>
    <p className="muted">{sourceLocation(evidence.locator, evidence.line_number)}</p>
    <blockquote className="source-quote" dir="auto">{evidence.quote}</blockquote>
    <Button variant="outline" disabled={download.isPending} onClick={() => download.mutate()}><Download size={16} />{download.isPending ? "Downloading…" : "Download original"}</Button>
    {download.isError && <Feedback error>{download.error.message}</Feedback>}
  </div>;
}

export function EvidenceAction({ id, title = "View evidence" }: { id: string; title?: string }) {
  const { service } = useSession();
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const evidence = useQuery({ queryKey: ["evidence", id], queryFn: () => service.evidence(id), enabled: open, refetchInterval: open ? 5000 : false });
  return <><Button ref={trigger} variant="ghost" className="citation-action" title={title} onClick={() => setOpen(true)}><FileText size={14} /><span>{title}</span></Button>
    <Sheet title="Source evidence" description="Original passage and source file." open={open} onOpenChange={setOpen} returnFocus={trigger}>
      {evidence.isPending && <Feedback>Loading evidence…</Feedback>}
      {evidence.isError && <Feedback error>{evidence.error.message}<Button variant="outline" onClick={() => void evidence.refetch()}>Retry</Button></Feedback>}
      {evidence.isSuccess && <SourcePreview evidence={evidence.data} />}
    </Sheet>
  </>;
}
