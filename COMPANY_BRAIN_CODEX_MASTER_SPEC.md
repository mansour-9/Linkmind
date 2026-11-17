> **Historical original specification — superseded by the 2026-11-14 direction.**
> Its original body is preserved below. Mandatory seven-stage extraction, graph-first
> priority, enterprise-access delivery order, OCR extensions, Terraform choices and
> automatic-build instructions are not the active requirements or authorization.
> Use [current scope](docs/PROJECT_SCOPE.md), [architecture](docs/ARCHITECTURE_M2_M3.md)
> and the [single RF roadmap](docs/IMPLEMENTATION_PLAN.md): unified company repository,
> lightweight indexing, optional/default-off enrichment and bounded evidence-based AI.
> Native authoring/Spaces and advanced workflows remain later ambitions. Current work
> follows the later explicit RF1 implementation request only; this original spec does
> not authorize later RF work, paid model calls or deployment.

# Company Brain — Codex Master Build Specification
**Version:** 1.0 (MVP)  
**Status:** Implementation brief  
**Language:** English  
**Target:** Local-first development, AWS-ready production architecture

## 0. Instructions to the Codex Agent

You are the lead software engineer, AI engineer, cloud architect, and product-minded frontend engineer for **Company Brain**. Build a functioning, thoughtfully scoped MVP—not just wireframes, mock API responses, architecture diagrams, or a product plan.

1. Inspect the existing repository first. Preserve useful existing work and conventions. If it is empty, initialize the project as described below.
2. Start with a concise implementation plan and a task checklist in `docs/IMPLEMENTATION_PLAN.md`. Then **implement** each phase, run tests, and record what is complete.
3. Prioritize a genuinely functional **vertical slice**: import real/fixture content → normalize → extract structured knowledge → link entities → detect conflicting claims → persist → visualize graph/wiki → answer questions with source citations.
4. Make the entire project runnable locally with Docker Compose and seeded demo data, without AWS credentials. Use a deterministic mock AI provider when AWS is unavailable, and clearly label demo/AI modes in the UI.
5. Add Amazon Bedrock through a clean provider interface so actual AI extraction and answers work when credentials and a supported model are configured. Do not hardcode model IDs; use environment variables and validate model/region compatibility.
6. Implement **real permission checks** in backend queries, not only frontend hiding. Do not expose hidden claims through search results, graph edges, snippets, citations, page summaries, counts, autocomplete, logs, or caches.
7. Do not silently invent knowledge, source references, or resolutions. Show uncertainty and pending conflicts. Every factual generated output must be traceable to stored evidence.
8. Make the UI exceptionally polished, responsive, accessible, and interactive. The Knowledge Graph is a core product surface, not a decorative illustration.
9. Follow AWS security and least-privilege principles. Never commit credentials. Never provision billable AWS services or modify a live AWS account without explicit user approval; prepare Terraform and deployment guides first.
10. After each phase, run relevant tests, fix problems, and update the README. If blocked by missing credentials or external access, fully implement and test the local/demo path rather than stopping.
11. Prefer practical engineering decisions over overengineering. Do not add Kubernetes, Neptune, OpenSearch, or a microservice fleet in MVP unless a validated need arises.
12. Keep product copy and all documentation in English.

---

## 1. Product Vision

**Company Brain** is an AI-powered enterprise knowledge consolidation platform inspired conceptually by Glean (enterprise discovery), Obsidian (linked knowledge and wiki navigation), and knowledge graphs. It is **not** intended to copy their branding or interface.

Organizations have fragmented information across Jira, Slack, Confluence, OneDrive, GitLab, local documents, and other systems. Company Brain brings this information into a **unified, permission-aware knowledge layer** that can be explored visually, browsed as an automatically maintained wiki, and queried through an AI assistant.

**Core differentiator:** The system does not stop at indexing or answering questions. It detects and reconciles duplicate entities, extracts source-backed claims, builds inter-entity relationships, recognizes possible contradictions, maintains histories, and creates readable project/topic pages.

The LLM is an extraction and interpretation component, **not a source of truth**. Original source systems and their evidence remain authoritative according to explicit, attribute-specific source policies.

### Primary MVP user stories

- As an administrator, I can load sample data, upload documents, and connect one real external source (Jira, when configured).
- As an employee, I can search across accessible information in one place and see exactly where a result came from.
- As an employee, I can open an auto-generated project wiki page and inspect supporting sources.
- As an employee, I can open a beautiful interactive Knowledge Graph and follow relationships between projects, people, tasks, documents, decisions, and technologies.
- As an employee, I can ask a natural-language question and receive a grounded answer with citations and caveats.
- As a reviewer, I can review possible conflicts and approve a resolution or mark the case as not a conflict.
- As an administrator, I can see when sources were last synchronized, whether extraction failed, and which items need review.
- As an employee, I can never discover or retrieve information outside my permissions—not even through graph traversal or AI-generated content.

### Out of scope for v1

Enterprise-wide connector catalog; full Slack/OneDrive OAuth sync; enterprise SSO federation beyond a Cognito integration scaffold; advanced automatic multi-source writebacks; autonomous edits to Jira/Slack; complex custom RBAC policy designer; production-scale graph DB; multi-region HA; production billing/subscription; arbitrary browser/web crawling; exhaustive PDF OCR; mobile apps.

---

## 2. MVP Technology Stack

### Frontend
- React + TypeScript + Vite
- Tailwind CSS + shadcn/ui components
- React Flow (`@xyflow/react`) for interactive graph rendering
- TanStack Query for server-state fetching/caching
- React Router for navigation
- Lucide icons
- A small, consistent chart library only if needed for dashboard metrics
- Accessible keyboard navigation and light/dark theme (dark-first aesthetic, but readable light mode)

### Backend
- Python + FastAPI + Pydantic v2
- SQLAlchemy 2, Alembic migrations
- PostgreSQL with `pgvector` extension and built-in full-text search
- Background worker consuming a queue abstraction: in local Docker use Redis/RQ or a simple database-backed job queue; on AWS use SQS. Keep the processing logic backend-agnostic.
- S3-compatible storage interface, with local filesystem/MinIO option for development and S3 in AWS
- boto3-based Amazon Bedrock provider; configurable deterministic local mock provider
- Pytest for backend tests
- Docker Compose for local setup

### AWS target, after local MVP is proven
- ECS Fargate for API and processing worker
- Amazon RDS for PostgreSQL + pgvector
- S3 for raw versions and supported uploaded artifacts
- SQS with DLQ for processing jobs
- EventBridge Scheduler for periodic synchronization
- Bedrock for extraction and answer generation
- Cognito for authentication
- Secrets Manager for source credentials
- CloudWatch for metrics/logging
- Terraform for reproducible infrastructure

Use the **least expensive reasonable architecture** and avoid optional managed services until necessary. Do not infer pricing; document anticipated cost drivers. Provisioning requires explicit approval.

---

## 3. Architecture and Data Flow

```
Jira / Uploaded Files / Fixture Feeds (Slack, Confluence, GitLab)
                      |
               Source Connectors
                      |
     Raw Document Versions + Source Metadata + ACL
                      |
          Normalization / Text Segmentation
                      |
       Claim & Entity Extraction (Bedrock / Mock)
                      |
       Entity Resolution + Source-Linked Evidence
                      |
        Conflict Detection + Authority Policies
                      |
       Canonical Knowledge Layer (PostgreSQL)
                      |
       +--------------+---------------+
       |              |               |
    Graph API      Wiki Builder    Hybrid Search
       |              |               |
    Graph UI       Wiki UI       RAG AI Assistant
```

### Core design rules
1. Raw documents, claim assertions, canonical entity identities, and wiki presentations are **separate layers**.
2. Original documents are retained as immutable revisions; source deletions and ACL changes are represented and propagated.
3. `Claim` means **an attributed assertion**, not necessarily verified fact. Preserve `asserted_by`, `evidence`, timestamp, confidence, and verification state.
4. Do not merge similarly named entities without evidence. First use stable IDs/direct links, then aliases and metadata, then semantic assistance, and escalate uncertain matches.
5. Conflicts are **attribute-specific and time-aware**, not simply two different strings.
6. Wiki pages are generated views of the knowledge layer, not the master record of truth.
7. Graph nodes/edges must be based on persisted entities/relationships, not hallucinated at UI render time.
8. The system enforces source/user permissions before composing wiki pages, graph neighborhoods, retrieval context, and LLM answers.
9. Every query is tenant-scoped. Derivative objects must inherit restrictive access or be generated per authorized viewer.
10. Configurable AI providers, storage, and connector adapters must be replaceable independently.

---

## 4. Knowledge Intelligence Engine — Seven Stages

### Stage A: Ingestion
- Implement a `Connector` interface: `list_changes(cursor)`, `fetch_item(id)`, `fetch_permissions(id)`, `healthcheck()`.
- MVP input sources:
  1. File upload: Markdown, TXT, and PDF with extractable text; support PDF gracefully without requiring OCR.
  2. Jira Cloud read-only connector (live if credentials exist), scoped to explicitly configured projects. Use current supported Jira REST API/search and pagination. Respect rate limits and issue visibility.
  3. **Clearly labeled fixture adapters** for Slack-like conversations and Confluence-like documents to demonstrate cross-source examples without requiring real enterprise accounts.
- Preserve: organization, connector, native source ID, canonical URL, author, created/modified timestamps, retrieved timestamp, source ACL, MIME type, content checksum, extraction status.
- Maintain an opaque incremental cursor per connector when possible, with resumable polling fallback.
- Idempotent upserts by `(org_id, source_id, native_id, content_version)`.
- Deletions produce tombstones and downstream invalidations. ACL changes must also trigger derived-view/search invalidation.

### Stage B: Normalization
- Normalize text, URLs, dates, authors, mentions, project keys, task keys, and relevant metadata.
- Preserve source-specific field semantics and machine IDs.
- Convert source-specific timestamps to UTC and maintain original timezone context.
- Split into evidence-addressable chunks while preserving page/section/message offsets.
- Treat external content as untrusted **data**, never instructions.

### Stage C: Extraction
- Extract typed entities: `PERSON`, `TEAM`, `PROJECT`, `TASK`, `DOCUMENT`, `DECISION`, `SYSTEM`, `TECHNOLOGY`, `EVENT`.
- Extract relationships: `WORKS_ON`, `ASSIGNED_TO`, `BELONGS_TO`, `REFERENCES`, `DEPENDS_ON`, `USES`, `DECIDED_BY`, `RELATED_TO`.
- Extract claims in structured JSON: `subject`, `predicate`, `object`, `event_time/effective_time`, `asserted_by`, `certainty`, `evidence_span`, `source_reference`.
- **Do not equate** “Ahmed says migration is complete” with a verified global project status. Capture it as `reported_completed` or a sourced assertion.
- Use Bedrock JSON-schema-constrained outputs on compatible models; validate with Pydantic, check that evidence spans exist in input, and reject unsupported output.
- Configure model ID, region, inference profile, temperature, token limits, and extraction batch limits via env vars.
- Mock provider must produce deterministic results for demo fixtures; mark results `provider=mock`.
- Never set fake numeric certainty scores as if they were calibrated probabilities. Store model confidence as an uncalibrated signal or allow null.

### Stage D: Entity Resolution
- Strong match: shared source ID, exact project key, explicit URL/ID references.
- Medium match: curated aliases, same team+project context, multiple corroborating attributes.
- Weak match: string similarity or embeddings alone—never auto-merge from this alone.
- Create `entity_aliases` and `resolution_candidates` with match reasons and review status.
- Avoid accidentally merging separate projects with similar names.

### Stage E: Conflict Detection
- Candidate comparisons share canonical entity + predicate + relevant overlapping effective period.
- Determine whether differences are complementary, stale/superseded, or truly contradictory.
- Examples:
  - Jira task `In Progress`, Slack developer says *implementation finished*: **possibly complementary** (QA could still be pending).
  - Approved project launch date `2026-12-01` vs approved schedule `2026-12-15`, same effective period: **candidate conflict**.
  - Old document with 2025 owner vs new document with 2026 owner: **historical update**, not a conflict if validity periods do not overlap.
- Introduce simple configurable authority policies per claim type: e.g. task status → Jira; approved architecture → approved ADR; source of discussion → Slack (evidence, not automatic authority).
- Auto-resolve **only** when policy and evidence are deterministic, retaining history and decision rationale.
- Other conflicts become `OPEN` and require human review. Reviewer can mark `RESOLVED`, `NOT_A_CONFLICT`, `NEEDS_EVIDENCE`, and optionally choose an authoritative claim with rationale.
- A conflict never silently overwrites the original source records.

### Stage F: Consolidation
- Build canonical, source-backed knowledge entities with aliases, relationships, claim sets, historical versions, and review states.
- Maintain distinction between system-of-record status and narrative interpretation.
- Incrementally recompute derived projections on input change; do not reprocess entire corpus unnecessarily.

### Stage G: Publishing
- Update search chunks, embeddings if configured, graph relationships, project wiki projections, and summary statistics.
- Record processing state and cause of changes. Ensure eventual consistency is visible (e.g. “Syncing”, “Updated”, “Needs Review”).
- No generated wiki or graph view may leak data inaccessible to the current user.

---

## 5. Data Model (Relational First)

Use UUID primary keys. Include `organization_id` on all tenant data. Define migrations, constraints, indexes, and relationships.

**Identity and access**
- `organizations`
- `users`
- `groups`
- `group_memberships`
- `source_acl_entries`: per-source principal or group plus allowed actions; document inherited or item-level restrictions
- `user_source_identities`: mapping of authenticated user to source identities

**Ingestion and processing**
- `source_connections` (`type`, `config`, `status`, `sync_cursor`, `last_synced_at`; secrets referenced externally)
- `sync_runs` and `processing_jobs` (`status`, timestamps, failure reason, counts, retry history)
- `documents` (`source_connection_id`, `native_id`, `url`, `latest_version_id`, `visibility_state`)
- `document_versions` (`checksum`, `content_location`, `created_at`, `modified_at`, `retrieved_at`, `deleted`, `metadata`)
- `chunks` (`document_version_id`, `text`, `locator`, `embedding`, `tsvector`)

**Knowledge**
- `entities` (`type`, `canonical_name`, `summary`, `status`)
- `entity_aliases` and `resolution_candidates`
- `claims` (`entity_id`, `predicate`, `value_json`, `asserted_by`, `effective_from`, `effective_to`, `observed_at`, `verification_status`, `extraction_provider`)
- `claim_evidence` (`claim_id`, `document_version_id`, `chunk_id`, `span_start/end`, `quote`, `source_url`)
- `relationships` (`from_entity_id`, `to_entity_id`, `type`, `valid_from/to`)
- `relationship_evidence`
- `conflicts` (`entity_id`, `predicate`, `kind`, `status`, `severity`, `resolution`, `rationale`, timestamps)
- `conflict_claims` and `review_actions`
- `source_authority_policies` (`predicate`, source type/selector, policy priority)
- `wiki_page_versions` (generated output; source dependencies; visibility/authorization context)
- `audit_events`

If a slimmer schema is better for early implementation, preserve these conceptual boundaries and document mergers. `document_versions` and `claim_evidence` are especially important.

### Claim contract example

```json
{
  "subject": {"type": "TASK", "canonical_id": "task-db-123"},
  "predicate": "implementation_status",
  "value": {"status": "reported_completed"},
  "asserted_by": "Ahmed",
  "effective_at": "2026-11-10T14:00:00Z",
  "evidence": {
    "source_type": "slack_fixture",
    "native_id": "message-1002",
    "quote": "Database migration is complete; QA is next."
  },
  "verification_status": "unverified"
}
```

For durable external records use actual database UUIDs and source/native IDs; the example IDs here are illustrative.

---

## 6. Interactive Knowledge Graph — Top-Priority UX Feature

### Graph purpose
This must be an **explorable representation of real backend knowledge**—not a static marketing diagram. It should evoke a polished linked-thought/Obsidian-style exploration experience while remaining original in design.

### Required graph capabilities
- React Flow canvas with smooth pan, zoom, fit-view, minimap, optional background grid, and custom nodes.
- Differentiated node styles/icons for Projects, People, Teams, Tasks, Documents, Decisions, Technologies, and Systems.
- Directed labeled edges (`ASSIGNED_TO`, `USES`, `DECIDED_BY`, etc.).
- Search a node by title/alias; select and center on it.
- Click a node to open a **right-side details drawer** with description, verified/unverified claims, conflict markers, history, relationships, source citations, and a “Open Wiki Page” action.
- Double-click a node or click **Expand** to fetch 1-hop neighbors from the API. Offer 2-hop traversal on demand; lazy-load to avoid graph overload.
- Filter nodes by type, relationships by type, source, and conflicts.
- Toggle “Highlight conflicts” to color/mark unresolved-conflict nodes/edges.
- Breadcrumb/back navigation for exploration; zoom and layout reset.
- Connected-neighbor highlighting; fade irrelevant nodes on selection.
- Show a legend, selected count, node count, and loading/empty/error states.
- Read-only graph editing for v1: users cannot create factual relationships by simply dragging arrows.
- Optional layout algorithms (dagre/ELK) may be used; keep positions stable and smooth when expanding.
- Default max ~100–150 displayed nodes, paginate/batch neighborhoods. Performance should remain acceptable in sample data.
- **All graph endpoints must enforce tenant and item ACLs before returning nodes, edges, labels, and counts.**
- Graph data must come from `entities` and `relationships`, with supporting evidence accessible via detail endpoints.

### Visual direction
- Premium enterprise SaaS look: deep navy/charcoal surfaces, royal-blue accents, restrained emerald and amber for knowledge states, soft borders, excellent typography, clear whitespace.
- Dark mode first with complete light mode support.
- Left navigation rail, generous content area, contextual right drawer.
- No arbitrary glowing decorations, cluttered dashboards, or placeholder charts that pretend to be real data.
- Animations should feel smooth but respect reduced-motion preferences.
- Desktop-optimized; functional tablet/mobile with graph controls adapted to small screens.

### Navigation (v1)
1. **Overview** — status cards: sources, documents, entities, open conflicts, latest sync, recent knowledge changes.
2. **Sources** — connected sources, upload, start sync, sync history, errors.
3. **Knowledge Explorer** — searchable list of projects/entities, aliases, topic filters.
4. **Knowledge Graph** — primary interactive graph experience.
5. **Wiki** — generated pages with internal links, evidence references, revisions/last sync.
6. **Conflict Center** — review queue, before/after evidence comparisons, reviewer actions.
7. **Ask AI** — chat with grounded answers, citation chips, “explore in graph” links.
8. **Settings** — organization, active user context, policy summary, Bedrock/provider status, safe configuration.

---

## 7. Auto Wiki

- Generate page templates for at least Projects, People, Tasks, Decisions, and Systems.
- For project pages display: Overview, Current Status, Team, Tasks, Decisions, Architecture/Systems, Related Knowledge, Conflicts, Sources, Last Updated.
- Pages are **projections of canonical knowledge**, with links to claims and evidence; Markdown rendering is fine but not the canonical database.
- Generated summaries must avoid asserting unverified claims as settled truth.
- Clearly label contradictory information and unresolved reviews.
- Generate content using only items authorized for the requesting user; for v1 prefer per-request rendering with safe caching or no cache over insecure global precomputed summaries.
- Render a linked graph preview in wiki page (e.g. related entities side panel).
- Support backlinks and navigation between wiki pages.

---

## 8. Ask AI / Retrieval

- Hybrid retrieval: PostgreSQL full-text search plus pgvector similarity if configured; rerank in a constrained, cost-conscious manner.
- Apply authorization checks **before any evidence is passed to the LLM**. The answer, citation label, and linked entity must also be authorized.
- Keep the LLM context small: select relevant evidence and canonical claims with precise source metadata, not entire raw source documents.
- Cite individual source documents/messages/tasks and provide clickable evidence references.
- Acknowledge conflicting or unverified information rather than hiding it.
- If evidence is missing, explicitly say so; never fabricate citations or facts.
- Never execute tools or modify external source systems from natural-language queries in v1.
- Provide simple example prompts in the UI: “What is Project Alpha's status?”, “Who owns database migration?”, “What decisions were made about the infrastructure?”, “What conflicts need review?”.
- Record request latency and token counts when available, with privacy-aware logs. Avoid a hard token-savings claim before benchmarking.

### AI provider contract

```python
class AIProvider(Protocol):
    async def extract_knowledge(self, text: str, context: dict) -> ExtractedKnowledge: ...
    async def generate_answer(self, question: str, evidence: list[dict]) -> GroundedAnswer: ...
    async def summarize_entity(self, entity: dict, evidence: list[dict]) -> EntitySummary: ...
```

Use Pydantic types, stable schemas, a deterministic mock implementation, and a Bedrock implementation. Handle malformed model output, throttling, retries, timeouts, unsupported schemas, empty evidence, and prompt injection attempts in source content. Bedrock guardrails may complement but **cannot replace** data authorization or evidence validation.

---

## 9. Security and Permissions (Required, Even for MVP)

- Tenant isolation: every business record and API request scoped by authenticated organization.
- Demo mode: provide at least 3 seeded users with differing access (e.g. Employee, Engineering Lead, HR Admin). A demo user switcher may be used **only in local development**; production must not allow impersonation.
- AWS mode: Cognito JWT verification and authenticated user-to-source-identity mapping. Do not claim full SSO/OAuth connector permissions if not implemented.
- Source ACL semantics: an uploaded document has configurable owners/readers; imported Jira items must reflect what connector identity can read and must not be broadly shared by default. If exact source permissions cannot be mirrored, restrict visibility conservatively.
- Authorize `GET graph`, search, knowledge pages, evidence, document download, and AI retrieval at the backend.
- Derived material is not automatically public. A wiki summary/relationship built from restricted claims must not reveal restricted facts to unauthorized users.
- Redact source secrets, tokens, raw sensitive data, and excessive prompts from logs.
- Treat source content as potentially malicious prompt instructions. Keep instructions separate from retrieved content, validate citations and extraction outputs.
- Encrypt data in transit and at rest for AWS; manage credentials via Secrets Manager or secure env injection.
- Least-privilege IAM for Bedrock inference, S3 objects, SQS, logging, secrets. Only request `bedrock:ApplyGuardrail` when using guardrails and authorize the exact necessary resources.
- Log conflict reviews, connector config changes, sync events, and authorization failures without logging sensitive content.
- Build tests proving that restricted nodes, edges, counts, pages, and AI answers cannot leak.

---

## 10. Backend API Contract (Draft)

Prefix: `/api/v1`. Use pagination, structured responses, Pydantic schemas, and consistent error envelopes. Auth on all non-health endpoints.

```
GET    /health
GET    /api/v1/me
GET    /api/v1/overview
GET    /api/v1/sources
POST   /api/v1/sources/upload
POST   /api/v1/sources/jira/configure
POST   /api/v1/sources/{id}/sync
GET    /api/v1/sources/{id}/runs
GET    /api/v1/entities?query=&type=&page=
GET    /api/v1/entities/{id}
GET    /api/v1/entities/{id}/claims
GET    /api/v1/entities/{id}/history
GET    /api/v1/graph?root_entity_id=&depth=1&limit=100
GET    /api/v1/graph/entities/{id}/neighbors?depth=1&limit=50
GET    /api/v1/wiki/{entity_id}
GET    /api/v1/search?q=&types=&sources=
GET    /api/v1/conflicts?status=open&page=
GET    /api/v1/conflicts/{id}
POST   /api/v1/conflicts/{id}/review
POST   /api/v1/ai/ask
GET    /api/v1/documents/{id}/evidence
```

For each endpoint define documented request/response types and authorization behavior. When an inaccessible resource is requested, return a safe response (often 404 to avoid confirming its existence). Do not return source content via unfiltered catch-all endpoints.

### Graph response example

```json
{
  "nodes": [
    {"id": "project-1", "type": "PROJECT", "label": "Cloud Migration", "has_conflicts": true},
    {"id": "person-1", "type": "PERSON", "label": "Ahmed", "has_conflicts": false}
  ],
  "edges": [
    {"id": "rel-1", "source": "person-1", "target": "project-1", "type": "WORKS_ON", "label": "Works on"}
  ],
  "has_more": false
}
```

IDs are illustrative, and actual APIs should use persisted UUIDs.

---

## 11. Seeded Demo Story (Must Be Persuasive and Testable)

Set up a realistic, source-linked, multi-step example centered on **Cloud Migration / Project Alpha**.

- Jira fixture `DB-123`: task **Migrate database to AWS RDS**, assignee Ahmed, status `In Progress`.
- Slack fixture message from Ahmed: “Migration implementation is complete; QA will start tomorrow.”
- Confluence fixture page: project is in QA phase; Sarah owns test sign-off.
- Architecture document: RDS Postgres is selected for the database.
- A separate, clearly labeled conflict: two *approved* documents disagree about the **same upcoming deployment date** for the same project and effective period; this creates an OPEN conflict.
- A second historical document shows the deployment date was legitimately revised last month; this should be categorized as **superseded**, not a live contradiction.
- An HR/private file and restricted graph relationship exist and are visible only to authorized demo users.
- A second project with a similar name tests entity-resolution false merges.
- A later Jira fixture update changes task status to Done and should update source history and projected wiki/graph information without deleting the Slack evidence.

The UI should show the end-to-end story with clear source provenance, one unresolved conflict, at least one resolved/superseded case, and permission differences between seeded users.

The mock AI may produce deterministic outputs **only for seeded fixture data**. For unrecognized uploaded files without Bedrock available, use truthful status messaging (e.g., “Imported; AI extraction unavailable”) rather than pretending extraction succeeded.

---

## 12. Frontend UX Quality Bar

- Cohesive design system, loading skeletons, toasts, error messages, empty states, search, responsive layouts.
- Real live API data on all primary pages; no static chart data presented as live metrics.
- Overview cards link to filtered views.
- Sources page shows last successful sync and failed runs, with user-controlled Retry.
- Knowledge Explorer offers list + relationship preview + source evidence.
- Graph has functional node search, filters, lazy expansion, minimap, drawer, and conflict highlights.
- Wiki pages offer internal links and visible sources.
- Conflict Center shows side-by-side assertions, timestamps, source authority policy, and working reviewer actions.
- AI interface supports citations and “Open in Graph/Wiki” navigation.
- Use semantic HTML and accessible dialogs; no critical information conveyed by color alone.
- Display Demo Mode clearly; do not mimic success statuses for unavailable Bedrock/Jira integrations.

---

## 13. Tests and Acceptance Criteria

### Backend tests
1. Idempotent re-ingestion: repeated sync of unchanged source does not duplicate claims or document versions.
2. Source revision creates a new version and updates current claim projections correctly.
3. Same entity under aliases merges only when supported by strong evidence.
4. Similar names without adequate evidence **do not merge**.
5. Complementary implementation/QA claims are **not** incorrectly labeled contradictory.
6. Overlapping approved dates create a conflict and preserve all evidence.
7. Historical superseded dates are not presented as live conflicts.
8. Reviewer action persists with reviewer, rationale, and audit event.
9. Search and graph results are consistent with persisted entities, claims, and edges.
10. Unprivileged users cannot access restricted document text, claims, graph nodes/edges, citation metadata, wiki snippets, or AI contexts.
11. Input injection in a source document cannot cause arbitrary instructions to be executed.
12. Worker retries and error handling do not create duplicate processing outcomes.
13. Deleting or restricting a source invalidates derived searchable/visible information.
14. Bedrock errors produce honest, recoverable state without fake success.

### Frontend / end-to-end tests
1. Launch with Docker Compose, sign in via demo mode, load seeded content, and navigate all pages.
2. Search for Cloud Migration and open its wiki page.
3. Open graph, center on Cloud Migration, expand neighbors, inspect Ahmed, filter to Tasks, and see a conflict-highlighted node.
4. Open conflict, inspect both evidences, submit review, and confirm state changes.
5. Ask AI “What is the migration status?” and receive sourced answer with unresolved caveat.
6. Switch to unauthorized demo user and confirm the private HR document is absent across **all** surfaces.
7. Simulate a Jira update and see updated history, wiki, and graph after processing.

### Definition of Done
- The full vertical slice works locally from a clean checkout.
- All central pages load real backend data.
- There is a working graph explorer and conflict-review flow.
- External references and original evidence are traceable.
- User-level permissions are enforced and tested.
- Integration tests pass; unresolved issues are documented.
- README gives exact startup commands, env vars, demo identities, and how to enable Bedrock/Jira.
- Terraform skeleton and AWS deployment plan exist; no live infrastructure was provisioned without approval.

---

## 14. Development Plan and Priority Order

### Phase 0 — Repository and documentation
Create a clean monorepo, Docker Compose, env examples, README, implementation checklist, API contract, and initial architecture documentation. Verify dev containers start.

### Phase 1 — Knowledge backbone
Build PostgreSQL schemas/migrations, tenant/access model, document upload and fixture ingestion, immutable versions, claims/evidence, entities/relationships, and deterministic conflict detection. Add backend tests.

### Phase 2 — Real user-facing MVP
Build React app shell, Overview, Sources, Explorer, interactive Graph, Wiki, Conflict Center, and Ask AI UI, all wired to real API endpoints. Seed rich sample data and finish critical interaction flows.

### Phase 3 — Intelligence and retrieval
Implement AI provider adapter with Bedrock plus deterministic mock, extraction/validation, guided entity matching, full-text retrieval, pgvector when available, authorization-aware RAG answers, citations, and incremental processing. Add end-to-end tests.

### Phase 4 — Real Jira connector
Build read-only Jira Cloud sync for configured projects; handle auth, pagination, rate limits, updates, deletions where possible, and conservative permissions. Document limitations. Keep fixture connectors for repeatable demonstrations.

### Phase 5 — AWS readiness
Prepare Terraform for ECS Fargate, RDS/pgvector, S3, SQS/DLQ, EventBridge schedules, Cognito, IAM, Secrets Manager, and CloudWatch. Include deployment guide and cost/security caveats. **Do not deploy until explicitly authorized.**

Where a phase can be split into smaller deliverables, prioritize working end-to-end paths over breadth. Continuously update implementation status.

---

## 15. Suggested Monorepo Layout

```
company-brain/
├── apps/
│   ├── web/                    # React + TS application
│   └── api/                    # FastAPI application
│       ├── app/
│       │   ├── api/
│       │   ├── auth/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── connectors/
│       │   ├── ingestion/
│       │   ├── intelligence/   # extraction, identity, conflicts, consolidation
│       │   ├── retrieval/
│       │   ├── graph/
│       │   ├── wiki/
│       │   ├── providers/      # mock and Bedrock
│       │   └── workers/
│       ├── alembic/
│       └── tests/
├── infrastructure/
│   └── terraform/
├── fixtures/
│   ├── jira/
│   ├── slack/
│   ├── confluence/
│   └── documents/
├── docs/
│   ├── IMPLEMENTATION_PLAN.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── SECURITY.md
│   ├── AWS_DEPLOYMENT.md
│   └── API.md
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

You may improve this structure with justification; avoid premature fragmentation.

---

## 16. Explicit Nonfunctional Requirements

- **Reliability:** idempotency, bounded retries, dead-letter behavior, observable sync failures.
- **Privacy:** full authorization on all surfaces, no secrets in repos/logs, tenant-aware storage, delete/ACL invalidation.
- **Observability:** ingestion counts/errors, conflicts opened/resolved, extraction jobs, model usage where available, processing durations.
- **Performance:** graph lazy loading and pagination; sensible batch processing; use indexes. Benchmark rather than claim unmeasured SLAs.
- **Cost:** fixed concurrency and token controls; avoid embedding or summarizing unchanged content; do not force AWS resources during local development.
- **Maintainability:** type hints, API validation, migrations, tests, documented environment configuration.
- **UX integrity:** no fake real-time badges, fabricated conflict resolutions, or demo metrics presented as production data.

## 17. First Task for Codex

**Begin immediately by checking the repository and implementing Phase 0 and the first demonstrable Phase 1 vertical slice.** Build a running frontend and backend with seeded Cloud Migration data, persisted entities/claims/relationships, a graph API, and a functional React Flow graph. Then continue through the remaining phases as capacity allows. If a phase is incomplete, state precisely what is done and what is not—do not falsely mark it complete. Do not ask broad design questions already resolved here. Make reasonable decisions, document them, and write code.

## 18. Official References

- Amazon Bedrock structured outputs: https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html
- Amazon RDS PostgreSQL releases / pgvector: https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-versions.html
- React Flow: https://reactflow.dev/
- Jira Cloud REST API: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/
- Amazon Bedrock Guardrails: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-how.html

**End of master specification.**
