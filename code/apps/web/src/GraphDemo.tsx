import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { useSession } from "./session";
import { Button, Feedback } from "./ui";
import type { Job } from "./api";

type DemoStatus = { ready: boolean; source_count: number; entity_count: number;
  entity_occurrence_count: number; relationship_count: number; jobs: (Job | null)[] };

export function GraphDemoButton() {
  const { service } = useSession();
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const running = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function load() {
    if (running.current) return;
    running.current = true; setBusy(true); setError(""); setMessage("Loading two clearly labeled synthetic sources…");
    try {
      let status = await service.json<DemoStatus>("/demo/graph-dataset/load", { method: "POST" });
      const deadline = Date.now() + 180000;
      while (!status.ready) {
        if (!mounted.current) return;
        const failed = status.jobs.find(job => job && ["failed", "extraction_unavailable", "cancelled"].includes(job.status));
        if (failed) throw new Error(`${failed.filename}: ${failed.error ?? failed.status}. Open Processing to inspect or retry the job.`);
        if (status.jobs.length === 2 && status.jobs.every(job => job?.status === "ready")) throw new Error("The sources were processed, but the expected graph counts could not be verified.");
        if (Date.now() >= deadline) throw new Error("Demo processing is still pending. Check Processing; loading again will reuse the same uploads.");
        const active = status.jobs.find(job => job && job.status !== "ready");
        setMessage(active ? `${active.filename} · ${active.stage.replaceAll("_", " ")}` : "Verifying the synthetic graph…");
        await new Promise(resolve => setTimeout(resolve, 700));
        status = await service.json<DemoStatus>("/demo/graph-dataset/status");
      }
      await client.invalidateQueries();
      if (mounted.current) setMessage(`Graph demo ready: ${status.entity_count} entities and ${status.relationship_count} relationships · ${status.entity_occurrence_count} cited occurrences across ${status.source_count} synthetic sources.`);
    } catch (cause) {
      if (mounted.current) { setMessage(""); setError(cause instanceof Error ? cause.message : "The graph demo could not be loaded."); }
    } finally {
      running.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return <div className="graph-demo-control">
    <Button variant="outline" disabled={busy} onClick={() => void load()}><Sparkles size={15} />{busy ? "Loading demo…" : "Load graph demo"}</Button>
    {message && <span className="graph-demo-message" data-ready={!busy} role="status">{message}</span>}
    {error && <Feedback error>{error}<Link to="/admin/processing" className="text-action">Open Processing</Link></Feedback>}
  </div>;
}
