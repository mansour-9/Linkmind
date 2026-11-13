import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useSession } from "./session";
import { Button, Feedback, Sheet } from "./ui";
import type { Job } from "./api";

export function SourceControls({ job }: { job: Job }) {
 const { service } = useSession();
 const cache = useQueryClient();
 const [action, setAction] = useState<"revision" | "delete" | "access" | "reprocess" | null>(null);
 const [file, setFile] = useState<File | null>(null);
 const change = useMutation({ mutationFn: async () => {
   const path = "/documents/" + job.document_id;
   if (action === "reprocess") return service.json("/jobs/" + job.id + "/reprocess", { method: "POST" });
   if (action === "revision") {
     const body = new FormData(); body.set("file", file!);
     return service.json(path + "/revisions", { method: "POST", body });
   }
   if (action === "delete") return service.json(path, { method: "DELETE" });
   return service.json(path + "/access", { method: "PATCH", body: JSON.stringify({ visibility: job.visibility === "team" ? "private" : "team" }) });
 }, onSuccess: () => { setAction(null); void cache.invalidateQueries(); } });
 return <div className="source-controls"><Button variant="ghost" asChild><Link to="/admin/processing">Processing</Link></Button>
 {job.can_manage && <><Button variant="ghost" onClick={() => { setAction("revision"); setFile(null); change.reset(); }}>New revision</Button>
 {job.can_reprocess && <Button variant="ghost" onClick={() => { setAction("reprocess"); change.reset(); }}>Refresh knowledge</Button>}
 <Button variant="ghost" onClick={() => { setAction("access"); change.reset(); }}>Change access</Button>
 <Button variant="ghost" onClick={() => { setAction("delete"); change.reset(); }}>Delete</Button></>}
 <Sheet title={action === "revision" ? "Upload revision" : action === "reprocess" ? "Refresh knowledge" : action === "access" ? "Change source access" : "Delete source"}
 description={job.filename} open={!!action} onOpenChange={(open) => { if (!open) setAction(null); }}>
 <form className="upload-form" onSubmit={(event) => { event.preventDefault(); change.mutate(); }}>
 {action === "revision" ? <><p>The current source stays available until the new text is search ready. Previous relationships then become historical while the new revision is enriched.</p>
 <label>New file<input type="file" required accept=".pdf,.docx,.txt,.md" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label></> :
 action === "reprocess" ? <p>Build and verify knowledge from the same source. Search stays available. {job.processed_at ? "Existing knowledge remains active until the replacement passes verification." : "New knowledge becomes available only after verification."} In Sonnet mode, this uses your remaining test allowance.</p> :
 action === "access" ? <p>{job.visibility === "team" ? "Restrict this source and its derived knowledge to its owner. Saved answers depending on it will be hidden from other users." :
 "Share this source and its derived knowledge with everyone in your organization."}</p> :
 <p>Remove this source from Search, Graph, Wiki and AI evidence. Saved answers that depend on it will be hidden. Original files remain in retained storage.</p>}
 {change.isError && <Feedback error>{change.error.message}</Feedback>}
 <Button type="submit" variant={action === "delete" ? "destructive" : "primary"} disabled={change.isPending || action === "revision" && !file}>
 {change.isPending ? "Saving…" : action === "revision" ? "Upload revision" : action === "reprocess" ? "Start refresh" : action === "delete" ? "Delete source" : "Confirm access change"}</Button>
 </form></Sheet></div>;
}
