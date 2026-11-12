import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession, useViewer } from "./session";
import { Button, Feedback, Sheet } from "./ui";

type Candidate = { id: string; source_name: string; candidate_name: string; reason: string; status: string };
export function IdentityReview() {
 const { service } = useSession();
 const viewer = useViewer();
 const cache = useQueryClient();
 const [selected, setSelected] = useState<Candidate | null>(null);
 const [action, setAction] = useState("reject");
 const [rationale, setRationale] = useState("");
 const candidates = useQuery({ queryKey: ["resolution-candidates"], queryFn: () => service.json<Candidate[]>("/resolution-candidates"), refetchInterval: 5000 });
 const review = useMutation({ mutationFn: () => service.json("/resolution-candidates/" + selected!.id + "/review", {
 method: "POST", body: JSON.stringify({ action, rationale }) }),
 onSuccess: () => { setSelected(null); void cache.invalidateQueries(); } });
 const open = candidates.data?.filter((c) => c.status === "open") ?? [];
 return <section className="mt-8"><h2 className="mb-4 text-lg font-semibold">Uncertain entity matches</h2>
 {candidates.isPending && <Feedback>Loading identity candidates…</Feedback>}
 {candidates.isError && <Feedback error>{candidates.error.message}</Feedback>}
 {candidates.isSuccess && !open.length && <p className="muted">No uncertain matches in your authorized current sources.</p>}
 <div className="knowledge-stack">{open.map((c) => <article className="panel knowledge-card" key={c.id}><h3>{c.source_name} ↔ {c.candidate_name}</h3><p className="muted">{c.reason}</p>
 {["admin", "reviewer"].includes(viewer.data?.role ?? "") && <Button variant="outline" onClick={() => { setSelected(c); setAction("reject"); setRationale(""); review.reset(); }}>Review identity</Button>}
 </article>)}</div>
 <Sheet title="Review entity identity" description="Names alone do not establish identity. Merge only when you can verify both records describe the same entity." open={!!selected} onOpenChange={(open) => { if (!open) setSelected(null); }}>
 <form className="upload-form" onSubmit={(e) => { e.preventDefault(); review.mutate(); }}><label>Decision<select value={action} onChange={(e) => setAction(e.target.value)}>
 <option value="reject">Keep these identities separate</option><option value="merge">Confirm they are the same entity</option></select></label>
 <label>Evidence and rationale<textarea required minLength={10} maxLength={2000} value={rationale} onChange={(e) => setRationale(e.target.value)} /></label>
 {review.isError && <Feedback error>{review.error.message}</Feedback>}<Button type="submit" disabled={review.isPending || rationale.trim().length < 10}>Save identity review</Button></form></Sheet></section>;
}

export function ConflictHistory({ id }: { id: string }) {
 const { service } = useSession();
 const [open, setOpen] = useState(false);
 const history = useQuery({ queryKey: ["conflict-history", id], queryFn: () => service.json<{ action: string; rationale: string; created_at: string }[]>("/conflicts/" + id + "/history"), enabled: open });
 return <details className="mt-4" onToggle={(e) => setOpen(e.currentTarget.open)}><summary className="text-action">Review history</summary>
 {history.isPending && open && <Feedback>Loading reviews…</Feedback>}{history.isError && <Feedback error>{history.error.message}</Feedback>}
 {history.data?.length === 0 && <p className="muted mt-2">No human reviews recorded.</p>}
 {history.data?.map((r, i) => <div key={i} className="mt-3"><strong>{r.action.replaceAll("_", " ")}</strong><small className="muted"> · {new Date(r.created_at).toLocaleString()}</small><p>{r.rationale}</p></div>)}</details>;
}
