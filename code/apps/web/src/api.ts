import type { Passage } from "./contracts";
export type Visibility = "private" | "team";
export type Job = {
  id: string;
  version_id: string;
  filename: string;
  uploaded_at: string;
  visibility: Visibility;
  status: "queued" | "processing" | "ready" | "extraction_unavailable" | "failed" | "cancelled" | "enrichment_staged_failed";
  document_id: string; stage: string; processed_at: string | null; can_manage: boolean;
  search_ready_at: string | null; search_status: "ready" | "pending" | "failed" | "cancelled";
  enrichment_status: "ready" | "queued" | "processing" | "unavailable" | "failed" | "cancelled" | "enrichment_staged_failed"; can_retry: boolean;
  can_reprocess: boolean; staged_version_id: string | null; active_enrichment_version_id: string | null;
  preserved_enrichment: boolean; staged_activation_state: "live" | "staged" | "rolled_back" | null;
  current_version_id: string | null; extraction_provider: string | null; embedding_status: string;
  entity_count: number; claim_count: number; relationship_count: number;
  attempts: number;
  error: string | null;
};
export type Viewer = { id: string; name: string; organization: string; role: string };
export type Entity = { id: string; name: string; kind: string; version_id: string; filename: string; conflict_count?: number };
export type Relationship = { id: string; source: string; target: string; label: string; chunk_id: string; effective_from?: string | null; effective_to?: string | null };
export type GraphData = { nodes: Entity[]; edges: Relationship[] };
export type ExplorerNode = Entity & { incoming_count: number; outgoing_count: number; connection_count: number };
export type ExplorerGraph = Omit<GraphData, "nodes"> & { root: string; depth: number; nodes: ExplorerNode[];
  truncated: boolean; visible_node_count: number; visible_edge_count: number; root_connection_count: number };
export type ExplorerSearch = { nodes: ExplorerNode[]; total: number; offset: number; limit: number; has_more: boolean };
export type EntityOverview = { entity: ExplorerNode; graph: ExplorerGraph } | null;
export type Evidence = { id: string; filename: string; version_id: string; line_number: number; quote: string; locator?: Record<string, unknown> };
export type EntityDetails = Entity & {
  claims: { id: string; predicate: string; value: string; chunk_id: string; line_number: number; quote: string; filename: string; locator?: Record<string, unknown> }[];
};

export function api(token: string) {
  async function request(path: string, init?: RequestInit) {
    const response = await fetch("/api/v1" + path, {
      ...init,
      headers: { ...(typeof init?.body === "string" ? { "Content-Type": "application/json" } : {}), ...init?.headers, Authorization: "Bearer " + token },
    });
    if (!response.ok) {
      const error: { detail?: unknown } = await response.json().catch(() => ({}));
      throw new Error(typeof error.detail === "string" ? error.detail : "Request failed (" + response.status + ").");
    }
    return response;
  }
  return {
    json: <T,>(path: string, init?: RequestInit): Promise<T> => request(path, init).then((r) => r.json()),
    async search(params: string): Promise<{ passages: Passage[]; semantic_status: string }> {
      const response = await request("/search?" + params);
      return { passages: await response.json(), semantic_status: response.headers.get("X-Linkmind-Semantic-Status") ?? "unavailable" };
    },
    neighbors: (root: string) => request("/graph/neighborhood?root=" + root + "&limit=40").then((r): Promise<GraphData> => r.json()),
    me: () => request("/me").then((r): Promise<Viewer> => r.json()),
    jobs: () => request("/sources").then((r): Promise<Job[]> => r.json()),
    graph: () => request("/graph").then((r): Promise<GraphData> => r.json()),
    entity: (id: string) => request("/entities/" + id).then((r): Promise<EntityDetails> => r.json()),
    evidence: (id: string) => request("/evidence/" + id).then((r): Promise<Evidence> => r.json()),
    async upload(file: File, visibility: Visibility): Promise<Job> {
      const body = new FormData();
      body.set("file", file);
      body.set("visibility", visibility);
      return (await request("/sources/upload", { method: "POST", body })).json();
    },
    async sample(name: string, visibility: Visibility): Promise<Job> {
      const blob = await (await request("/demo/fixtures/" + name)).blob();
      return this.upload(new File([blob], name + ".md"), visibility);
    },
    async download(version: string, filename: string) {
      const blob = await (await request("/documents/" + version + "/download")).blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
    async companyFile(key: string, filename: string) {
      const blob = await (await request("/demo/company/files/" + encodeURIComponent(key))).blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = filename; anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  };
}
