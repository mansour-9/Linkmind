# Company Brain — Implementation Plan

M2/M3 core implementation is in place; independent acceptance work remains.
The UI checkpoint is implemented and validated. On 2026-11-12 the user approved
the current work and requested M3.2 planning plus a GitHub checkpoint before backend
implementation. Historical checkmarks distinguish implemented work from later
quality acceptance and pending upgrades.

## Active order — confirmed 2026-11-11

| Order | Milestone | Status |
| --- | --- | --- |
| 1 | M3.1 — Linkmind UI redesign and validation | Implemented and validated; user approved proceeding to M3.2 planning on 2026-11-12 |
| 2 | M3.2 — Baseline and document-processing reliability | A diagnostics/pilot complete; B proposal pending approval |
| 3 | M3.3 — Retrieval quality and entity resolution | Pending |
| 4 | M3.4 — Verified multi-hop GraphRAG | Pending |
| 5 | M4.1 — Read-only Jira integration | Pending local quality gates |
| 6 | M4.2 — Persistent sync, freshness and revocation | Pending source ACLs |
| 7 | M4.3 — Bounded orchestration | Adopt only with measured benefit |
| 8 | M4.4 — Additional sources | Later; Slack retained, other sources evaluated |
| 9 | M5 / M6 — Hosted readiness / approved AWS deployment | Later |
| 10 | M7 — Arabic and bilingual validation | After the English hosted pilot |

The next release is for local testing, prioritizes knowledge quality, and uses Jira
as its first external source. Update milestones and acceptance evidence as work
completes; do not start the backend upgrade ahead of the UI milestone.

## Delivery strategy
Build a substantial hosted MVP in demonstrable increments. Start with one complete
upload-to-knowledge flow, then expand intelligence, product surfaces, live sources,
and hosted operations. Keep permissions and provenance in the first slice.

Use the current scope and [frontend rules](FRONTEND_RULES.md) alongside the
original master specification. Ship frontend workflows in stages as their APIs
become available. Launch the hosted pilot in English and deliver Arabic in M7.

## M0 — Prepare the project
- [x] Read both original specification files completely.
- [x] Inspect the project: no existing application code.
- [x] Preserve the original master specification and engineering instructions.
- [x] Record the current scope, proposed defaults, open decisions, and milestones.
- [x] Confirm one internal team, English and Arabic content, core document formats,
  direct uploads, Jira Cloud, and selected public Slack channels.
- [x] Create the `code/` layout for the web app, API, worker, and Python CDK.
- [x] Verify Git in the moved project and check Node.js, npm, Python, and Compose.
- [x] Start Docker Desktop and verify the Linux engine. Verified Docker Engine
  29.6.2 and Docker Compose 5.3.1.

Exit: the scope, stack, and folders are in place, and the Docker engine is available
for the first local build.

## M1 — First working vertical slice
- [x] Initialize the React/TypeScript/Vite frontend, Python/FastAPI API, and Python
  worker with Docker Compose.
- [x] Add PostgreSQL/pgvector, migrations, a worker, and local artifact storage.
- [x] Implement organization scoping, local-only demo users, and document permissions.
- [x] Persist immutable documents, chunks, claims/evidence, entities, and relationships.
- [x] Build one upload route with validation, status, and idempotent processing.
- [x] Process recognized Cloud Migration fixture files through deterministic mock AI.
- [x] Add a real graph API and React Flow view with node details and source evidence.
- [x] Provide a truthful state for unrecognized files without a real AI provider.
- [x] Test repeat ingestion, restricted evidence, and worker retries against PostgreSQL.
- [x] Document and verify exact clean-checkout startup and seed commands.

Exit demo: upload a recognized fixture, wait for processing, open its persisted graph,
inspect a claim, and navigate to the original evidence. A second user cannot see
restricted information. The workflow survives restart.

Verified on 2026-11-11. A clean local Compose start ran the database migration.
Three PostgreSQL integration tests passed, and a browser run verified graph search,
citation navigation, download, and identity switching. A full Compose stop/start
preserved all nine sample entities and six relationships with their original IDs.

## M1.1 — Shared workspace and working local flows

- [x] Add the shared shell and routed Home, Knowledge Graph, Data Sources, and
  Settings pages. Settings shows the active workspace, identity, and demo mode.
- [x] Give Home a graph-node search using authorized graph data, shortcuts to
  Graph and Sources, and recently opened items that still pass authorization.
- [x] Redesign the graph and evidence inspector. Preserve search, filters, pan,
  zoom, fit, minimap, node and edge inspection, and original downloads.
- [x] Preserve sample loading, direct upload, access selection, and real job status
  in the Data Sources workflow.
- [x] Run the frontend build, PostgreSQL regressions, and browser checks at
  desktop, tablet, and mobile sizes. Check keyboard access, refresh, and direct links.

Exit demo: open Project Alpha from Home, inspect a node and a relationship, open
a citation, download the original, and upload a file in Sources. Switching from
Amal to Omar hides Project Cedar. Nour cannot see Engineering workspace data.

Verified on 2026-11-11. The frontend build and all three PostgreSQL regression
tests passed. Edge browser checks at 1440 px, 768 px, and 360 px covered navigation,
graph search and controls, direct-link refresh, keyboard focus, evidence and
downloads, upload validation, job status, and identity isolation.

The Royal Blue refresh is also verified. The shared theme controls colors and
typography, Graph opens around one project and expands authorized neighbors,
and Sources shows the stored upload date. The production build and three
PostgreSQL regressions passed. Browser and screenshot checks covered the four
pages at 1440 px, 1024 px, and 390 px. A temporary change to `--primary`
recolored the shared brand and primary actions, then the approved blue was restored.

## M2 — Real document intelligence and unified storage

- [x] Safely migrate canonical identities, aliases, uncertain matches, multiple evidence spans, effective dates, conflicts, review/processing history and usage.
- [x] Parse selectable-text PDF, DOCX, TXT and Markdown with original locators and bounded inputs.
- [x] Implement boto3 Bedrock structured extraction and semantic verification; retain deterministic exact-fixture processing locally.
- [x] Validate source IDs, exact quotations, evidence offsets, entity references and effective periods before publication.
- [x] Add one bounded model correction pass; never publish an unsupported result after validation fails.
- [x] Resolve strong identifiers conservatively; require human review for uncertain names and retain explicit merge history.
- [x] Compare same-entity attributes and overlapping periods. Preserve historical/complementary claims; use Bedrock semantic conflict assessment for live processing.
- [x] Add leased jobs, stages, attempts, bounded retries, errors and atomic current-version publication.
- [x] Add revisions, deletion, access changes and derived-view invalidation.
- [x] Ship Processing with authorized counts, versions, timestamps, errors, attempts, embedding status and working retry controls.
- [x] Record token/latency/model/status/retry/attempt usage independently of publication.
- [x] Support explicit dated model/region cost rates and show unavailable estimates honestly.
- [x] Coordinate API/worker request pacing against the verified local model quota.
- [x] Test PostgreSQL permissions, evidence, temporal conflicts, revisions, deletion, access revocation, independent accounting and retry rollback.
- [x] Run the 12-document/30-question live benchmark and record entity, claim, citation and answer-rubric results with diagnostic baselines.
- [ ] Independently review the draft expected answers and improve coverage using representative company documents.

Exit: two real documents sharing an explicit project ID produce connected, traceable knowledge and a genuine conflict. A live two-document Bedrock scenario has passed; expanded evaluation is recorded in [validation](M2_M3_VALIDATION.md).

## M3 — Retrieval, Wiki, Graph and chatbot

- [x] Combine exact entity/identifier, PostgreSQL full text, compatible pgvector similarity and related graph claims using permission-filtered reciprocal-rank fusion.
- [x] Apply source/type/date filters before ranking and add bounded Search pagination.
- [x] Keep active embedding model/dimensions per versioned passage and exclude incompatible or outdated vectors.
- [x] Add grounded Bedrock answers with exact citations, separate semantic verification, explicit missing/contradictory evidence and truthful mock excerpts.
- [x] Persist per-user workspace/selected-file conversations and evidence dependencies; suppress saved answers after access or version invalidation.
- [x] Support follow-up context using current authorized evidence.
- [x] Add bounded server-backed graph neighborhoods and graph search, preserve positions and support expansion/collapse and provenance navigation.
- [x] Generate structured Wiki pages with attributed claims, conflict/uncertainty indicators, sources and version history.
- [x] Add authorized conflict review with rationale, stale-review protection and audit history.
- [x] Add explicit uncertain-identity review and preserve canonical/occurrence links after approved changes.
- [x] Connect Home to working Search, Ask AI, Graph and Wiki flows.
- [x] Expose internal operational Usage only to authorized reviewer/admin roles.
- [x] Preserve shared Royal Blue theme and original upload/download/evidence behavior.
- [x] Pass the upload → Processing → Graph → Wiki → question → citation browser journey and responsive checks at 1440, 1024 and 390.
- [x] Document live evaluation, measured accuracy limits and final-policy targeted checks.
- [ ] Perform a complete expanded benchmark rerun when the independently reviewed pilot dataset is available.

The latest approved benchmark scope is **12 documents / 30 questions**. The earlier proposed 60-question Rerank comparison is an optional later optimization, not an enabled dependency.
No Bedrock Knowledge Base, Neptune, S3, RDS, compute infrastructure, quota increase or CDK deployment has been provisioned.
See [architecture](ARCHITECTURE_M2_M3.md), [runbook](../code/README.md) and [validation](M2_M3_VALIDATION.md).

## M3.1 — Linkmind redesign and validation

The user approved the complete redesign plan on 2026-11-11: Linkmind identity,
Glean-inspired neutral/indigo design, English first and working features only.
The user also authorized completing independent work without waiting for manual
screen tests. User visual acceptance must still be recorded accurately.

- [x] Audit existing frontend, route/API contracts and supplied references.
- [x] Implement shared tokens, sidebar, recent conversations and profile/workspace UI.
- [x] Replace Home and Ask AI with the centered composer and reading-column chat.
- [x] Implement safe Markdown, source previews and honest evidence-based Show work.
- [x] Implement People, Content library/details, Documents and restyled Graph.
- [x] Group and redesign Sources, Processing, Conflicts, Usage and Settings.
- [x] Preserve legacy URLs, API contracts and role/owner permissions.
- [x] Complete automated build, workflow, permission and responsive validation.
- [x] Deliver visual comparison and validation report.
- [x] User approved the current checkpoint and requested M3.2 planning (2026-11-12).

See [UI redesign and validation](M3_1_UI_REDESIGN.md).

## M3.1 follow-up — focused Graph explorer and connected Search

- [x] Promote Graph to a primary `/graph` destination; preserve Content and legacy links.
- [x] Implement the light compact-node explorer, discovery, bounded expansion,
  relationship/type/depth filters, list view and separate evidence inspector.
- [x] Add permission-checked entity search, stable neighbor pagination, bounded
  one-to-three-hop traversal and truthful truncation/connection counts.
- [x] Supplement exact project/person/identifier searches with connected context
  while keeping ordinary document results and Chat as the daily workflows.
- [x] Pass frontend production build, **30 backend tests** and **17 Playwright tests**.
- [x] Review responsive screenshots and deploy locally without changing the
  existing database, documents or Bedrock configuration.
- [x] User approved the Graph/demo/canvas checkpoint and requested M3.2 planning (2026-11-12).

See [Graph explorer implementation and validation](GRAPH_EXPLORER_UPDATE.md).

## M3.2 — Architecture baseline and document-processing reliability

M3.2A completed on 2026-11-12: [findings](M3_2A_RESULTS.md), 48 API / 20 browser checks, 17 capped live attempts. [M3.2B proposal](M3_2B_PLAN.md) is not implemented; original private-PDF quotations remain unconfirmed.

Use the [M3.2 plan](M3_2_PLAN.md): **one milestone, two sequential checkpoints** (A: reproduction/baseline; B: implementation/validation). Backend implementation has not started.

Preparation completed: [baseline manifest](M3_2_BASELINE.json) freezes backend/test/fixture hashes and separates existing live results from current mock regressions. This is preparation, not acceptance of the full milestone.

Local testing first; improve knowledge quality before expanding external sources.

- [ ] Audit the actual code/schema and record the custom-vs-managed retrieval,
  orchestration and integration decisions using current official documentation.
  Compare Managed Knowledge Bases without provisioning or migrating automatically.
- [ ] Freeze a reproducible baseline and agree quality, latency and cost targets
  before evaluating changes. Independently review expected answers; carry forward
  the outstanding M2/M3 representative-document acceptance work.
- [ ] Reproduce the remaining PDF exact-quote failure and add a regression case
  using authorized content or a representative synthetic reproduction.
- [ ] Improve text normalization with mappings to original source locations and
  add bounded repair for recoverable extraction/schema/quote errors. Keep exact
  evidence validation and reject unsupported facts after the repair limit.
- [ ] Introduce token-aware, structure-aware chunks with measured overlap and
  parent context; preserve headings, paragraphs, tables and original page/line locators.
- [ ] Version processing/index generations. Backfill alongside the current index,
  validate and switch deliberately; preserve source versions, citations and rollback.
- [ ] Record a document format/size matrix and test malformed, scanned, unsupported,
  empty and large files with truthful errors. OCR remains outside this upgrade.
- [ ] Add per-stage tracing and measure ingestion time, extraction/relationship
  quality, token usage and available cost estimates against the baseline.

Exit: the PDF regression is resolved without weakening grounding; versioned
reprocessing preserves old evidence, and the agreed document test matrix passes.

## M3.3 — Retrieval quality and conservative entity resolution

- [ ] Improve question-to-entity linking using explicit identifiers, aliases and
  context. Namespace external IDs by source instance and project/repository.
- [ ] Use contextual/semantic similarity to propose uncertain identity matches;
  keep unsupported automatic merges disabled and preserve human review/history.
- [ ] Improve cross-section extraction and link suitable attributed claims to
  evidence-backed relationships without converting every value into a graph edge.
- [ ] Improve exact/keyword candidate ordering, tune hybrid fusion and compare a
  reranker against the same held-out questions. Adopt it only if quality and
  latency/cost targets justify it; do not add new infrastructure by default.
- [ ] Select evidence with parent context, diversity and a token budget while
  retaining every required supporting passage. Keep source scope and ACL filtering.
- [ ] Report retrieval recall/ranking, identity-match and relationship precision/recall,
  grounded answers, abstention, citations and permission regressions separately.

Exit: held-out comparisons meet the agreed retrieval/identity targets without
permission regressions; ambiguous same-name entities remain distinguishable.

## M3.4 — Verified multi-hop GraphRAG on uploaded documents

- [ ] Implement bounded PostgreSQL traversal with three hops by default,
  bidirectional navigation, cycle detection and explicit node/edge/path budgets.
  Preserve predicate direction and meaning when navigating backward.
- [ ] Link the question to canonical entities, decompose a complex question when
  necessary, rank candidate paths and retrieve source evidence for every edge.
- [ ] Verify identity, relationship meaning, applicable dates and access across the
  complete path. Distinguish explicit facts, supported conclusions and unconfirmed
  hypotheses; hypotheses must not become trusted graph facts automatically.
- [ ] Keep simple questions on a direct retrieval path. Bound any extra retrieval
  rounds by configured call/token/time limits and return partial or insufficient
  evidence when a path cannot be established.
- [ ] Recheck all source dependencies before generation, saving and history display;
  include paths, caches, labels and counts in revocation/deletion tests.
- [ ] Preserve existing API behavior and add evidence-path metadata additively;
  show authorized supporting paths through the UI accepted in M3.1.
- [ ] Test two- and three-hop cross-document answers, ambiguous identities,
  cycles, reversed predicates, conflicting periods, missing edges and revoked evidence.

Exit demo: two documents support Project Alpha -> uses -> Billing Service ->
maintained by -> Omar. The answer cites both edges. Removing or revoking either
source prevents an unsupported answer and suppresses dependent saved evidence.

## M4 — External sources, synchronization and bounded orchestration

Jira is the first external source, after the local document-quality milestones.
Connections in Codex are not application credentials. A real project and the
application's own authorized connection are required for live-source acceptance.

### M4.1 — One read-only Jira integration

See [Jira knowledge discussion](JIRA_KNOWLEDGE_NEXT_STEPS.md) for the confirmed source and proposed reference/saved-view tasks; the additional user chat is pending.

- [ ] Build a typed connector boundary supporting direct MCP for live tools and
  native APIs/webhooks where synchronization capabilities require them. Keep
  uploaded-document tools internal rather than wrapping them in MCP unnecessarily.
- [ ] Register approved endpoints/tools, discover capabilities, check health and
  enforce read-only allowlists, timeouts, bounded retries and sanitized responses.
  Prevent source content or the model from choosing identities or arbitrary endpoints.
- [ ] Map application users to validated Jira identities and source permissions.
  Do not translate a service account's broad access into organization sharing;
  deny unverified access and isolate credentials, sessions and cached results.
- [ ] Normalize source-qualified IDs, URLs, version/update times, retrieval times,
  evidence and authorization context. Label live results separately from cached facts.
- [ ] Compare direct MCP with AgentCore Gateway/Identity for the hosted target;
  keep the local integration independent of new billable AWS infrastructure.
- [ ] Demonstrate one approved Jira project plus uploaded-document evidence. A
  reference to an issue is not proof that a merge request or change fixes it.
- [ ] Test denied/expired credentials, unavailable tools, prompt injection,
  tool-schema changes, rate limits and cross-user/organization isolation.

Exit: a real read-only Jira query returns current, attributed information only to
an authorized user. Fixtures remain clearly labelled; unavailable credentials are
reported as a live-validation dependency, never as a completed integration.

### M4.2 — Persistent synchronization, freshness and revocation

- [ ] Route authorized connector records through the versioned ingestion pipeline
  only after source ACLs and identity mapping are established.
- [ ] Implement incremental checkpoints, idempotency, pagination, bounded retries,
  rate limiting and recovery; choose polling/webhooks from verified source capabilities.
- [ ] Reconcile updates, deletions and permissions, preserving source versions and
  invalidating affected graph paths, search, caches and saved answers.
- [ ] Define freshness and access-verification expiry rules; fail closed when access
  cannot be verified. Distinguish unavailable sources from an empty result and do
  not present stale status as current.
- [ ] Expose actual sync runs, checkpoints, last-success time, freshness and errors
  through compatible APIs and matching source-management UI.
- [ ] Test duplicate/out-of-order events, interrupted sync, deletion/revocation,
  source outages and resumption without duplicate publications.

Exit: a Jira update appears once, stale facts are superseded, and revoked/deleted
records stop contributing to every dependent surface within the agreed policy.

### M4.3 — Bounded agentic retrieval and orchestration (measured adoption)

- [ ] Start with one typed Python workflow and deterministic knowledge/Jira tools.
  Add planning or specialist LLM agents only when paired tests show a benefit.
- [ ] Compare custom orchestration, Strands Agents-as-Tools and LangGraph against
  actual needs, including durable execution, streaming and future approval workflows.
- [ ] Enforce tool, iteration, concurrency, token and time budgets outside prompts;
  support cancellation and honest partial answers with visible evidence limitations.
- [ ] Trace source/tool calls, retrieved evidence, permission decisions and usage
  with sensitive-data redaction. Conversation memory is not organizational truth.
- [ ] Compare answer quality, p50/p95 latency, token/model usage and available
  costs with the direct retrieval baseline before enabling extra orchestration.

Exit: complex authorized questions improve against the agreed baseline while
simple questions retain their direct path. A framework with no measured benefit
is documented as deferred rather than adopted to satisfy an agent count.

### M4.4 — Additional sources after the Jira proof

- [ ] Retain approved public Slack channels and readable replies in the later
  hosted-pilot scope, with verified membership and the same sync/revocation guarantees.
- [ ] Evaluate Confluence and GitLab as subsequent source candidates; do not add
  them to the next local release automatically. Confirm their order and approved scope.
- [ ] Reuse connector contracts and preserve namespace-qualified identities,
  evidence, permissions and predicate meanings across every source.

Exit: each adopted source passes its own live authorization and synchronization
checks before contributing to cross-source answers. Broader source adoption is
separate from completion of the next local knowledge-quality release.

## M5 — Hosted readiness and verification
- [ ] Add verified Cognito authentication and disable all demo impersonation in hosted mode.
- [ ] Test cross-tenant isolation and restricted nodes, edges, labels, counts, snippets,
  citations, original downloads, wiki content, AI context, and cache invalidation.
- [ ] Test malicious source instructions, unsafe uploads, stale jobs, and concurrent changes.
- [ ] Add structured operational metrics, redacted logs, audit visibility, and failure recovery.
- [ ] Measure graph performance, ingestion throughput, retrieval quality, and model usage
  on the agreed pilot dataset; set explicit acceptance targets before evaluating it.
- [ ] Prepare an AWS CDK v2 app in Python with pinned dependencies, secrets and IAM,
  HTTPS ingress, frontend delivery, networking, backups, and an operator runbook.
- [ ] Synthesize and review CloudFormation templates, including protections for
  stateful resources. Prepare the target-specific CDK diff, restore and rollback
  procedures, and bootstrap requirements for review before deployment.
- [ ] Prepare a region-specific cost estimate including compute, database, storage,
  model calls, networking, logs, backups, and frontend delivery. No invented prices.
- [ ] Present exact resources, access model, projected cost, and known limitations for review.

Exit: acceptance tests pass, remaining limitations are documented, and the proposed
deployment is concrete and reviewable. No cloud resources are provisioned in this milestone.

## M6 — AWS deployment and pilot
- [ ] Obtain explicit user approval for the concrete billable deployment.
- [ ] Confirm the approved account and region. Bootstrap the CDK environment if
  required, review `cdk diff`, then deploy the approved stacks with `cdk deploy`.
- [ ] Validate hosted login, uploads, processing, graph, wiki, search, reviews, and citations.
- [ ] Verify backup restoration, rollback, alerts, and access restrictions in the hosted environment.
- [ ] Run a limited pilot, collect feedback, and resolve critical findings before expanding.
- [ ] Deliver operating instructions, exact run/deploy commands, and a measured limitation report.

Exit: pilot users can securely use the hosted product with their approved data.

## M7 — Arabic support (final milestone)

- [ ] Localize UI copy and add right-to-left layouts for navigation, controls,
  graph inspection, wiki, search, evidence, and conversations.
- [ ] Validate Arabic and mixed-language document extraction, retrieval, and
  answers, including Arabic questions against English evidence.
- [ ] Review Arabic citation accuracy, source links, and permissions. Run
  desktop, mobile, keyboard, and English regression checks.

Exit demo: an Arabic-speaking user can upload and explore Arabic and mixed-language
knowledge, ask a question, and follow the answer back to authorized evidence.

## Planning estimates

The previous 4-8 week local-MVP and 10-14 week hosted-pilot ranges predated this
UI revision and advanced GraphRAG scope; they are not commitments for this update.
Re-estimate after M3.1 locks the UI scope and M3.2 establishes the quality baseline,
using representative documents, model quotas and authorized source access.
Record effort, dependencies and acceptance evidence per milestone. Hosting and
additional-source estimates remain separate from the next local release.

## Next implementation task, when requested

Finish M3.1 automated validation and visual handoff. Prepare independent M3.2
baseline work while preserving the knowledge layer; representative-data quality
acceptance and user visual acceptance must not be claimed automatically.
