import type { EntityDetails } from "./api";

export type Passage = { id: string; filename: string; text: string; version_id: string; document_id: string; locator: Record<string, unknown>;
  embedding_status?: string; semantic_status?: "ready" | "failed" | "unavailable" | "not_requested" };
export type ClaimEvidence = { chunk_id: string; quote: string; filename: string; locator: Record<string, unknown>; version_id: string };
export type WikiPage = Omit<EntityDetails, "claims"> & {
  sources: { version_id: string; filename: string; created_at: string; current: boolean }[];
  uncertain_matches: number; entity_evidence: ClaimEvidence[];
  claims: (EntityDetails["claims"][number] & { evidence: ClaimEvidence[]; provider: string })[];
};
export type Answer = { statements: { text: string; evidence: { passage_id: string; quote: string }[] }[]; insufficient_evidence: boolean; provider: string; evidence: Passage[];
  message?: string; clarification?: boolean; search_notice?: string;
  source_matches?: { document_id: string; version_id: string; filename: string; search_ready: boolean; match: string }[];
  coverage?: { mode: string; selected_sources: number; covered_sources: number; supplied_passages: number; total_passages: number; partial: boolean } };
export type Conversation = { id: string; title: string; document_ids: string[] };
export type History = Conversation & { turns: { id: string; question: string; suppressed: boolean; response: Answer | null }[] };
export type Conflict = { id: string; canonical_id: string; predicate: string; status: string; rationale: string; authoritative_claim_id: string | null;
  updated_at: string; left_claim_id: string; right_claim_id: string; left_value: string; right_value: string; left_chunk_id: string; right_chunk_id: string };
