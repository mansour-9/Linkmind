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

/** variant="chip"   — existing chip button (Show work, default)
 *  variant="cite"   — compact superscript [n] button (inline after statement)
 *  variant="source" — [n] filename row in sources footer
 */
export function EvidenceAction({ id, title = "View evidence", citationNumber, variant = "chip" }: {
  id: string;
  title?: string;
  citationNumber?: number;
  variant?: "chip" | "cite" | "source";
}) {
  const { service } = useSession();
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const evidence = useQuery({ queryKey: ["evidence", id], queryFn: () => service.evidence(id), enabled: open, refetchInterval: open ? 5000 : false });

  const sheet = <Sheet title="Source evidence" description="Original passage and source file." open={open} onOpenChange={setOpen} returnFocus={trigger}>
    {evidence.isPending && <Feedback>Loading evidence…</Feedback>}
    {evidence.isError && <Feedback error>{evidence.error.message}<Button variant="outline" onClick={() => void evidence.refetch()}>Retry</Button></Feedback>}
    {evidence.isSuccess && <SourcePreview evidence={evidence.data} />}
  </Sheet>;

  if (variant === "cite" && citationNumber != null) {
    return <><button ref={trigger} className="cite-marker" onClick={() => setOpen(true)} aria-label={`Citation ${citationNumber}: ${title}`}>{citationNumber}</button>{sheet}</>;
  }

  if (variant === "source" && citationNumber != null) {
    return <><button ref={trigger} className="source-ref" onClick={() => setOpen(true)} title={title}>
      <span className="source-ref-num">{citationNumber}</span>
      <FileText size={11} className="source-ref-icon" aria-hidden />
      <span className="source-ref-name">{title}</span>
    </button>{sheet}</>;
  }

  return <><Button ref={trigger} variant="ghost" className="citation-action" title={title} onClick={() => setOpen(true)}><FileText size={14} /><span>{title}</span></Button>{sheet}</>;
}
