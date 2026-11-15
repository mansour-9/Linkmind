# Linkmind — Main Implementation Roadmap

## Unified Company Repository, Retrieval First

Updated **2026-11-15**. This is the **single active roadmap**. RF1/RF2 are locally
implemented and validated. The user subsequently authorized finishing RF3 repairs and
continuing RF4 locally. The new isolated **5195** follow-up passed **315 API / 39 browser /
frontend build**, final **8 OAuth checks**, and **16/16 mock retrieval**. RF3's known
unsupported temporal/authority additions now have bounded Sonnet repair evidence;
three new answers passed source review. This does not establish independent company
quality acceptance. RF4's encrypted server-owned OAuth lifecycle and native scope
picker are implemented and tested offline; real consent/source trials remain explicitly
**deferred by the user**. See [current results](RF34_RESULTS.md),
[validation](RF34_VALIDATION.json) and [authentication runbook](RF4_OAUTH_RUNBOOK.md).

Current source requires schema **0018_connection_oauth** and policy v10. All older
previews remain unchanged. RF5/RF6 remain planned. No main/existing-preview cutover,
real source account, push/merge or AWS infrastructure deployment is included.

2026-11-14 testing preference: use real Sonnet for representative AI-quality/user trials
and mock/stubs for small deterministic checks that do not require inference. Real AI
answer testing can follow RF1 before RF2, preserving source-only ingestion. The user
will perform AWS login. Follow the [AI testing policy](AI_TESTING_POLICY.md); configure
the existing shared spend guard correctly before any separately scoped paid trial.
This preference does not start RF2, enable a provider or create another budget.

The user later explicitly approved RF2, with Arabic/answer-style enhancements deferred
to RF3. RF2's deterministic acceptance uses a new mock stack at 5191, zero paid calls,
and leaves RF1 Sonnet at 5189/main intact. Live evidence uses offline fixtures only.

Subsequent confirmed follow-up: **RF1 Sonnet preview enabled at port 5189**, directly
sharing the original USD 10 ledger/pacing. Full isolated API suite now **215 passed**;
the final selected-source Lantern summary passed real answer/semantic verification.
See [AI follow-up evidence](RF1_AI_PREVIEW.md), including two earlier safely rejected
probes. RF2 was subsequently approved and delivered as recorded above; RF3 later
entered the measured checkpoint at the top of this roadmap. RF4–RF6 implementation
remains planned. No new allowance or main-data rollout follows from these deliveries.

[Scope](PROJECT_SCOPE.md) owns requirements and open choices.
[Architecture](ARCHITECTURE_M2_M3.md) separates current code from target behavior.
[Decision/document review](RESTRUCTURE_REVIEW_2026_11_14.md) records rationale and review
coverage, not another backlog. The [prior roadmap](reference/pre_restructure_2026_11_14/IMPLEMENTATION_PLAN.md)
is preserved. Its next tasks and automatic-implementation wording are superseded.

## 1. Agreed outcome and hard boundaries

Linkmind durably collects selected company knowledge, organizes it lightly, and provides
intelligent search and evidence-based answers across stored and live sources. Original
provenance and field meaning stay intact. It is not only a transient search proxy.

- Core inputs already provide text: extractable PDFs, text/Markdown, existing DOCX,
  and MCP/native source text/structured records. OCR/conversion is upstream, outside
  the core. No Linkmind OCR or new microservice platform is part of this restructure.
- Default ingestion: retain → parse/map → index → available. **No automatic Sonnet
  entity/claim/relationship extraction, identity resolution or conflict assessment.**
- Embeddings are a separate measurable indexing cost. No default LLM summary or
  taxonomy pass, full-corpus extraction, or graph rebuilding is required.
- Relevant evidence is analyzed on demand. Missing graph facts must never block
  ingestion, search, metadata organization or cited answers.
- Persist selected synchronized scopes. Use live tools for relevant current fields;
  Live Only results do not automatically enter shared organizational knowledge.
- Preserve originals, revisions, citation IDs, current security boundaries, useful
  graph/review/history behavior, usage controls and the existing local Docker stack.
- Defer detailed enterprise groups/Space access design, native authoring, managed
  Spaces and advanced graph/conflict workflows. Adequate connector access and production
  authentication remain required before actual source/employee exposure.
- Ongoing model-backed reasoning is Sonnet-only; embeddings remain separately configured.
  Preserve `northstar-sonnet-2026-11-12` and its cumulative USD 10 ceiling/unknown
  reservations. No reset/clone/increase/unpause, Gemma rerun or new paid dispatch.

## 2. Current checkpoint — completed work is not reset

| Existing capability | Recorded state | Disposition |
| --- | --- | --- |
| M0/M1/M1.1 and M3.1 UI/Graph/canvas | Completed local checkpoints; M3.1 user-approved | Reuse; no repeated handoff/redesign |
| M2/M3 source/search/chat | Locally implemented; independent representative quality acceptance incomplete | Core foundation for RF1–RF3 |
| M3.2A pilot | Completed historical diagnostics | Preserve frozen evidence; no comparison rerun |
| F1.1 search-readiness separation | Locally validated | Reuse; default-off enrichment is new RF1 work |
| F1.2 and F1.3 staged enrichment | Implemented locally; isolated F1.3 acceptance; main cutover pending | Retain as optional safety/compatibility; not a core extraction gate |
| T1 Northstar previews/budget | Delivered test journeys with dated model outcomes | Reuse corpus/guard; no renewed paid allowance |
| Conversation discovery/persona | Implemented locally; compatible preview backport recorded | Preserve, extend to source routing |
| Lantern repair/diagnostics | Offline repairs exist; latest real extraction verifier failed alignment | Keep evidence/fixes; no mandatory extraction-repair rerun |
| Main/previews | Main last recorded 0010; RF1 Sonnet 0013; RF2 0014; RF3 0015; RF4 0017; new 5195/current source 0018 | Protected container IDs and RF1/RF2 source data preserved; main rollout excluded |
| Connectors/sync/adaptive live routing | Not implemented in application | RF2–RF5; Codex connections are not app credentials |
| Production sign-in/native authoring/managed Spaces | Not delivered | Release security in RF6; detailed F2/K1/S1 later |

RF1 changes ordinary processing to source-only by default in current code/new isolated
preview. Existing main/preview environments remain unchanged. Chat retains its current
answer verification; RF1 does not relax grounding rules.
No stronger answer accuracy, latency or savings claim follows from this plan. Latest
recorded real-model outcome: [Lantern identifier report](LANTERN_IDENTIFIER_REPAIR_RESULTS.md).
Historical reports/ledger figures are not observations of current runtime state.

## 3. Stages, dependencies and actual status

| Stage | Outcome | Dependency/status |
| --- | --- | --- |
| RF0 — Direction/documentation | Consistent scope, architecture, roadmap and history | Completed documentation alignment/checks |
| RF1 — Lightweight ingestion | Source-only indexing default; explicit optional enrichment | Completed isolated acceptance: 191 API / 29 browser / build; main rollout excluded |
| RF2 — Repository/catalog/evidence | Reliable resource identity, non-graph metadata and common evidence | Completed isolated acceptance: 231 API / 32 browser / build; live contract tested offline |
| RF3 — Retrieval and routing | Useful bilingual source-only answers; bounded index/live planning | Implemented; 264 API / 34 browser / build pass; real quality gate open after two reviewed failures |
| RF4 — Sources & MCP Connections | Admin lifecycle and local connector foundation for Jira, Confluence, OneDrive, SharePoint and Custom MCP | Implemented/validated locally at 5194; real auth, scopes and source acceptance pending |
| RF5 — Cross-source journey | Combined answers and light organization over accepted sources | Accepted RF4 lifecycles; graph optional |
| RF6 — Core release/rollout | Held-out quality, measured load/cost, production auth, tested recovery | Cross-cutting preparation; security before real employee use; separate rollout approval |
| Later capabilities | Rich authoring/Spaces, detailed enterprise design, advanced graph/research/actions | Separately requested; no implicit RF1–RF5 dependency |

No calendar commitments or guaranteed savings. RF6 measurement/safety preparation starts
early; full group/Space design does not move into RF1. First source/order/scopes remain
open. Jira is the prior candidate, while OneDrive/SharePoint collection is a core source
class. A fixed Jira → Confluence → GitLab sequence no longer blocks document-source value.

## 4. Capability acceptance matrix

| Capability | Current gap | Accepted target | Owner |
| --- | --- | --- | --- |
| Upload/revision | RF1 source-only default implemented locally | Arbitrary readable source searchable when extraction/conflict functions are forbidden | RF1 |
| Indexing | RF1 lexical-first publication and compatible same-document reuse implemented locally | Honest lexical/semantic readiness, stable citations and compatible changed-content reuse | RF1/RF3 |
| Repository | Selected owner-bound collection implemented locally; real-source acceptance pending | Source-qualified durable records, versions/provenance and selected scopes | RF2/RF4 |
| Discovery/metadata | RF2 metadata/content catalog and source/format/project/team/date filters delivered locally; entity-kind remains optional | Topic/source/type/project/date discovery without graph or exact filename knowledge | RF2/RF3 |
| Chat | Local evidence only; broad verification | Useful no-graph cited answers, identity/support safety, coverage and graceful abstention | RF3 |
| Routing | Intent routing only | Relevant sources, freshness/history routes, bounded expansion, no search-all default | RF3/RF5 |
| Live access | Native/MCP bounded reads implemented and validated offline; networking off by default | Actual authorized read-only evidence, links/times and fault handling | RF4 |
| Sync | Local ordinary-worker collection/checkpoints/revisions/access recovery implemented; real-source acceptance pending | Incremental checkpoints, restart recovery, idempotency, partial/version/access/deletion safety | RF4 |
| Cross-source reasoning | Uploaded local evidence only | Stored + live + historical evidence, without prebuilt edges | RF5 |
| Graph/links | Existing bounded explorer/legacy facts | Optional reliable links; zero-link resources fully usable; history preserved | RF2/RF5 |
| Security | Local tenant/owner/org boundaries and demo auth | Existing boundaries preserved, source checks per connector, production auth before employee exposure | All/RF6 |
| Cost/operations | Usage/pacing/test guard exist; representative limits open | Separate indexing/query/tool measurement, hard budgets, recovery and held-out acceptance | All/RF6 |
| Native Hub/Spaces | Planned | Prior complete journeys revisited when scheduled | Later K1/S1 |
| Advanced graph/conflict/delegation | Basic reviews retained; advanced behavior absent | Demonstrated benefit and separately agreed scope | Later R2/D1 |

## 5. RF1 — Default lightweight ingestion

Status: **implemented and validated in the isolated local stack**. Authorized by the user
on 2026-11-14. Reused `processing.py`, parsers, providers, existing jobs/version guards
and Processing/Sources UI. Delivery evidence: [RF1 results](RF1_RESULTS.md).

- [x] Audit upload/revision/retry/refresh/fixture/worker paths. Define one explicit
  default-off enrichment policy so alternate paths cannot silently invoke extraction.
- [x] Finish ordinary ingestion after source/index publication without extraction,
  extraction verification, model-based identity resolution or conflict assessment.
- [x] Keep deliberate optional enrichment with existing staging/lease/revision/access
  checks, compatible legacy jobs, supported retry semantics and retained attempt history.
- [x] Distinguish not-requested enrichment from failed/unavailable. Source-only content
  is successfully usable and must not appear broken or awaiting required graph repair.
- [x] Preserve lexical fallback; explicitly design/test lexical availability while
  embeddings are pending if adopted. Do not report semantic readiness prematurely.
- [x] Avoid reindexing/re-embedding unchanged content under compatible identity/model/
  policy rules. Metadata/access-only updates must still invalidate access correctly.
- [x] Preserve source/citation IDs and historical evidence. Source-only answer dependencies
  must not require unused graph generations; old turns are retained, not rewritten.
- [x] Keep explicit exact-byte graph fixtures working. Never fabricate extraction for
  arbitrary mock uploads. Retain optional-enrichment safety tests and useful legacy views.

Acceptance: ordinary readable uploads/revisions work with extraction/conflict functions
set to fail on invocation and with zero graph records. Verify lexical degradation,
citations/downloads/history, optional refresh, supersession/revocation/deletion, stale
workers/concurrent revisions, retry/UI states and policy invalidation in isolation.
Record zero extraction calls for default ingestion; embeddings remain separately measured.
Output: focused compatible implementation and documented isolated acceptance, not rollout.

## 6. RF2 — Repository metadata, source catalog and common evidence

Status: **implemented and validated locally**, in an isolated mock stack at 5191.
Full 231 API / 32 browser / build passed; final RF2 16 API / 3 browser follow-up passed.
See [RF2 results](RF2_RESULTS.md). RF1 Sonnet/main remain unchanged; no paid inference.

- [x] Define minimal stable external identity: organization/source instance/type/native
  ID; keep source instance distinct from replaceable connection credentials.
- [x] Add metadata/filtering independent of entity extraction: source/type/times and
  reliable project/team references. Unknown remains unknown; names alone do not merge.
- [x] Describe configured scopes and actual source operations/live/index/history/health
  in a small catalog, without building an exhaustive company ontology.
- [x] Define local/live evidence with original link, excerpt/locator or typed field/value,
  revision/observation times, access dependencies and coverage. Keep existing passage IDs.
- [x] Support reliable project/resource association without managed Spaces/native pages.
  Distinguish explicit source/human links from uncertain suggestions.
- [x] Add persistence only for delivered capabilities; no universal fact-store rewrite,
  new event platform, future-only permissions schema or mandatory generation overhaul.

Acceptance: non-graph metadata/topic discovery, safe reconnect and native-ID collisions,
source-qualified identity, permission-safe titles/counts/history, inspectable local/live
fixture citations, and no fabricated verbatim quotes for structured fields.
Output: minimal compatible catalog/evidence contracts and working supported filters.
Local acceptance passed. Native identity/reconnection and live structured-field checks
are offline contract fixtures, not actual connector authentication or synchronization.
Only uploads are active; projects/teams are deliberate associations, not inferred facts.

## 7. RF3 — Retrieval quality and bounded routing

Status: **local implementation and bounded grounding repair validated**. The original
RF3 5192/5193 stacks and eight-prompt failed outputs remain preserved. The new 5195
follow-up uses policy v10 and passed 315 API / 39 browser / build, with deterministic
retrieval 16/16. Three new Sonnet answers passed source review; six distinct verifier
controls have expected outcomes after a preserved false rejection and targeted fix.
See [repair evidence and limits](RF34_RESULTS.md). Broader independent representative
company acceptance remains a release gate, not a claim from synthetic cases.

- [x] Establish reviewed source-only questions: policies, project facts, same-name
  ambiguity, history, disagreement, missing evidence and Arabic/English/mixed wording.
  Measure baseline; improve structure-aware context/diversity/ranking only with evidence.
- [x] Route clear selected-source/ID requests directly. Use bounded Sonnet planning for
  ambiguity/composition only where useful; preserve question qualifiers and scope.
- [x] Select indexed/live/historical/combined sources from actual capabilities (offline
  registered-adapter contract; real live access remains RF4). Expand
  a failed initial route to another relevant source within budget; no search-all fan-out.
- [x] Enforce tool/round/context/model/output/time limits and bounded concurrency in
  code. Numeric defaults are proposed until tested against workloads/provider limits.
- [x] Provide bounded question/partial-context coverage and evidence-gap behavior.
  Clarify ambiguity, retain actual values/source disagreements and distinguish missing
  evidence from tool/provider failure. Each requested part still needs representative acceptance.
- [x] Treat broad summaries as a separate coverage-aware workload; do not imply complete
  review from top passages or promise all long-document questions are cheap.
- [x] Keep mandatory grounding/access checks and existing semantic answer verification
  initially. Any selective-verification change needs measured held-out regression and
  a policy bump when trust rules change; do not weaken checks to pass expected answers.
- [x] Show actual activity/citations/limits and genuine cancellation where supported.
  Preserve persona; no fake tools, integrations, reasoning traces or empty navigation.

Acceptance: useful no-graph factual answers and cross-document synthesis; no irrelevant
source calls on clear routes; bounded expansion; unsupported identity/content/injection
fails safely. Denial, outage, empty search and exhausted budget remain distinguishable.
Output: retrieval/routing implementation, measured isolated baseline/comparison, UI/source
inspection and separately reviewable live-evaluation scope. Mock tests are not AI quality.

The measured temporal/authority/freshness repairs are implemented and have bounded
real-model regression evidence. Preserve both the original failures and the later
false rejection. The authored corpus is not independent held-out acceptance. No paid
corpus rerun is authorized automatically. Representative company question/summary
coverage and long-document workloads still require independent release acceptance.

## 8. RF4 — Read-only connectors, live and persistent

User steering, 2026-11-15: real-server MCP/connector tests are deferred until later.
Keep real consent, discovery/permission and source acceptance open; local OAuth/scope implementation is now validated offline.

Status: **local management, connector, delegated OAuth and scope-selection foundation
implemented/validated; real-source acceptance deferred**. Five labelled demos are at
5195. Server-owned encrypted consent/token/refresh state and bounded metadata discovery
are functional, tested with offline native provider transports. Default networking stays
off. Actual provider registration, consent, scope permissions and live/sync lifecycle
acceptance remain outstanding. See [current results](RF34_RESULTS.md),
[runbook](RF4_OAUTH_RUNBOOK.md) and [prior RF4 plan](RF4_PLAN.md).

- [x] Deliver Admin Settings → Sources & MCP Connections for all five types, persisted
  configuration, labelled Demo/Real environments, authentication status, test-before-enable,
  explicit scopes, editing/removal, three modes, health/errors and collection status.
- [x] Validate the local lifecycle, native/MCP transport contracts and source-only
  collection/recovery/access invariants with offline fixtures and real browser/API checks.

- [x] Implement and offline-test owner/cookie/generation-bound single-use consent,
  encrypted tokens/refresh rotation, audience binding and native scope selection.
  Keep Custom MCP's explicit server-managed authentication contract distinct.

The gates below remain real-source acceptance requirements; local mocks do not complete them.

- [ ] Select bounded scopes per source; verify real MCP/native capabilities, app credentials,
  identity and permission semantics before broad implementation. Codex access is not app auth.
- [ ] Implement bounded search/fetch/current fields and supported history, with original
  URLs, actual field semantics, retained evidence and source/observed times. No writes.
- [ ] Provide practical Live Only / Live + Sync / Not Connected policies, health,
  last-successful-sync and actionable source errors.
- [ ] Persist selected scopes with versions/checksums, cursor/checkpoint, resumability,
  pagination, deduplication and bounded retries/backoff. No routine extraction/graph pass.
- [ ] Reconcile changes/deletion/access for rarely queried resources too. Reject stale
  overwrites and partial/user-filtered replacements; missing search hits do not prove deletion.
- [ ] Answer live without waiting for safe background refresh. Avoid unchanged embeddings;
  access-only changes must still revoke derived/history/cache visibility.
- [ ] Prove mode/scope removal, expiry/denial, outages/rate limits, malformed/partial
  payloads, duplicate/out-of-order updates, missed cycles and dependency reauthorization.

Acceptance has separate live and sync gates; a single API call is insufficient. Live Only
creates no shared index records. Live + Sync persists selected records through restart
and safe update recovery. Dated fallback requires valid access; cached status is never
presented as newly live-confirmed. Deliver necessary source checks without full F2 design.
Output: staged accepted source lifecycles for the four planned systems. Real connector/model acceptance needs its separately
authorized access/budget; this plan does not connect accounts or run imports.

## 9. RF5 — Cross-source company journey and light organization

Status: **planned**. Use complementary accepted sources by employee value/access,
for example Jira + OneDrive/SharePoint, after their RF4 lifecycle gates. Additional
systems beyond RF4's four planned sources remain separately selected.

- [ ] Reuse accepted evidence/live/sync contracts, proving each participating source's own
  permission, pagination, history and failure lifecycle.
- [ ] Demonstrate a project with stored documents/records, current live state, original
  references and reliable optional project/repository/document associations.
- [ ] Answer why a date changed and where work stands now using retained reasons plus
  live fields, without prebuilt relationships or automatic persistence of AI conclusions.
- [ ] Support dated/historical questions without substituting today's result for missing
  history. Explain partial coverage and unresolved material disagreements.
- [ ] Keep graph exploration optional and existing graph/review/history behavior usable.

Acceptance: independently reviewed coverage/citations for each question part, no guessed
identity joins, no all-source default, and honest partial results during a source outage.
Output: complete company-repository/assistant journey with measured cost/latency. Advanced
GraphRAG is a later experiment only if it adds value over the accepted hybrid baseline.

## 10. RF6 — Core release and separately reviewed rollout

Status: **planned; cross-cutting preparation, no deployment authorization**.

- [ ] Agree corpus/questions, source scopes, concurrency, quality/freshness thresholds,
  p50/p95 latency and indexing/query cost targets. Employee count is not concurrency.
- [ ] Measure embeddings, planning, answers/verification and source tools separately;
  test interactive workload during sync and actual quotas. More workers do not create quota.
- [ ] Deliver adequate production sign-in/session and source access before real employee
  use; preserve isolation/revocation on all surfaces. Detailed groups/Space delegation is later.
- [ ] Prepare backup/restore, retention/deletion decisions, secrets, redacted diagnostics,
  health/recovery and actual build/schema inventory. Resolve known main inference-accounting
  mismatch explicitly; never create a cloned USD 10 ledger to enable main paid calls.
- [ ] Prepare the RF cutover candidate with compatible migrations including 0012 if
  required. Reuse safety procedures in MAIN_DATA_ROLLOUT.md, not its obsolete 0011-only
  enrichment acceptance sequence. No destructive rewrite of retained data/migrations.
- [ ] Freeze actual-data writers; back up DB and originals together; restore/rehearse
  separately; compare citation/history/review fingerprints and test backfill/rollback.
  Decide how post-snapshot writes are preserved before any restoration is authorized.
- [ ] Present concrete local/main rollout separately. AWS hosting also needs Python CDK,
  current regional costs, HTTPS/network/security review and explicit deployment approval.

Completion requires relevant deterministic and separately authorized held-out/live evidence,
actual recovery checks and release security. User visual/localization acceptance remains
separate. English UI exists; Arabic/English retrieval quality is cross-cutting and full
Arabic/RTL release coverage remains explicit. No production readiness is claimed now.

## 11. Deferred capabilities and retained requirements

| Previous capability / ID | Treatment |
| --- | --- |
| F2 detailed groups/delegation/Space grants | Deferred design; current boundaries and minimum RF4/RF6 security remain mandatory |
| K1 rich native Knowledge Hub | Later complete author/editor/maintainer journeys; ingestion does not wait for it |
| S1 managed Spaces | Later workspace; metadata grouping can exist independently |
| R2 advanced multi-hop GraphRAG | Optional later measured benefit; keep current explorer |
| D1 conflict/delegated verification | Deferred; useful reviews/evidence and answer disagreement safety retained |
| W1 research/reports, W2 actions/agents | Later requested scope; no writes/agent-per-source infrastructure now |
| L1 full Arabic/RTL | Retained; bilingual retrieval/answers evaluated in RF3 |
| Saved graph layouts, private Slack/DMs, onboarding | Retained extension backlog, not current authorization |
| OCR/image interpretation/conversion services | Upstream/outside core text contract |
| Archival export/legal retention and model training | Illustrative future uses, not newly requested features |

The [prior scope](reference/pre_restructure_2026_11_14/PROJECT_SCOPE.md) and
[prior roadmap](reference/pre_restructure_2026_11_14/IMPLEMENTATION_PLAN.md) retain detailed
later requirements. Do not implement their future editor/permissions/conflict schema now.

## 12. Legacy mapping and next task

| Earlier work/sequence | Active disposition |
| --- | --- |
| M0–M3.1 | Completed record below; no repeated implementation |
| M3.2A/T1 | Historical evidence and corpus/guard; no renewed paid allowance |
| F1.1/F1.2/F1.3/Lantern | Existing foundation/optional safety; RF1 changes the default |
| R1/M3.3 | RF2/RF3 evidence and source-only relevance |
| R3/M4.3 | RF2/RF3 catalog/coordinator; RF5 real combined proof |
| C1/C2/M4.1/M4.2 | RF4 live + sync lifecycle; source choice reopened |
| C3/C4/M4.4 and other sources | RF5 and later accepted adapters; no mandatory Confluence-before-document-source order |
| F2 → K1 → S1 before retrieval | Superseded ordering; detailed capabilities deferred |
| Mandatory GraphRAG before connectors | Superseded; graph optional and measured |
| H1/H2/M5/M6 | RF6 release gates plus separately approved hosting |

**RF1/RF2 are complete locally. RF3 deterministic checks pass, but two real-model
grounding failures remain open. Next: bounded RF3 quality repair/regression; RF4 planning
was requested on 2026-11-15 for Jira, Confluence, OneDrive and SharePoint, with exact
account/resource scopes still to choose.** See the
[RF4 planning draft](RF4_PLAN.md). Main rollout and connector implementation remain
separately scoped.
Do not resume old extraction repair, repeat completed work, execute the old main cutover,
run a paid comparison or start F2 because an archived handoff says so. Documentation
verification does not authorize implementation automatically.

## Historical completed milestones and validation

Original M0–M3.1 records follow. Their old assumptions/checkmarks describe past work,
not active requirements or RF completion. Independent quality gaps carry into RF3/RF6.

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
