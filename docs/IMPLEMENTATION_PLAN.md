# Linkmind — Main Implementation Roadmap

## Production-Quality Core Platform with Phased Feature Delivery

Updated 2026-11-13. This is the **single active roadmap**, restructuring the existing
M0–M7 plan. Product decisions are in [scope](PROJECT_SCOPE.md); current/target behavior
is in [architecture](ARCHITECTURE_M2_M3.md). The user subsequently requested F1.1
implementation on 2026-11-12. That slice is locally validated; all other unchecked
tasks remain planned and require their own implementation request.

Subsequent T1 authorization: the user requested the complete fictional-company test
experience and approved a US$10 cap for its Sonnet extraction/embedding/chat run.
This is a focused test/retrieval increment, not authorization to implement every
remaining roadmap milestone. See [T1 testing and evidence](COMPANY_TESTING.md).

2026-11-13 follow-up authorization: improve conversational help, approximate/topic
source discovery, clarification of similar matches, and contextual follow-ups for
user-uploaded data. This focused usability increment precedes F1.3; it does not
authorize F1.3 implementation or main-data rollout. Validation is isolated and mock;
manual Sonnet use retains the existing persistent USD 10 test allowance.

Subsequent 2026-11-13 authorization: implement **F1.3 and main-data rollout
preparation first**; the user explicitly selected this batch over continuing into F2.
Bounded Bedrock-backed checks are authorized within the existing persistent USD 10
run, without resetting/increasing it. Main cutover remains a separately reviewed step.

- [x] Implement bounded query understanding, catalog discovery, and source choices.
- [x] Recheck source metadata permissions/revisions in history and follow-ups.
- [x] Verify arbitrary uploads, typo/topic search, clarification, and frontend behavior.
- [x] Update the Sonnet preview without migrating the main app or spending on evaluation.

See [conversation tests and current operational limits](CONVERSATIONAL_TESTING.md).

## Status and evidence rules

- **Completed:** a bounded delivered feature/checkpoint with recorded evidence.
- **Partial:** useful implemented behavior exists, but target acceptance is not met.
- **Planned:** no verified implementation of that capability in the current application.
- **Deferred:** intentionally sequenced later, not deleted from product scope.

Completed local features do not imply production readiness. A synthetic test pass
does not establish real-model quality; a live lookup does not complete a connector.
Keep user visual acceptance, automated checks and representative quality review separate.

## Preserved checkpoint

M0/M1/M1.1 and M3.1 are completed. M2/M3 core local workflows are implemented, with
independent quality acceptance outstanding. The M3.1 UI/Graph/canvas checkpoint was
user-approved on 2026-11-12. M3.2A diagnostics and the bounded Gemma/Sonnet pilot are
complete. F1.1, the first M3.2B slice, is implemented and validated in an isolated
local stack; main-data rollout is pending. F1.2 implemented 2026-11-12; F1.3 locally
validated 2026-11-13. See
[F1.1 results](F1_1_RESULTS.md) and the unchanged historical checklists below.

Model decision (2026-11-12): use Sonnet only for ongoing model-backed work. Gemma is
unavailable per the user. The completed comparison remains historical evidence;
there is no active Gemma repair, comparison rerun or adoption task. Future processing
and quality work targets Sonnet. F1.1 preserves model settings and includes no paid
evaluation or model replacement.

Historical pre-F1.1 checks: 48 API tests, 20 browser workflows and frontend build passed
in M3.2A; 17 paid diagnostic attempts, with no production model/schema/data changes.
The older 12-document/30-question live benchmark predates final grounded-v3 tightening;
targeted checks are not a full rerun. Original private-PDF failed response bodies are
unavailable. These are historical results, not new tests run for this planning update.
Sources: [M3.2A](M3_2A_RESULTS.md), [M2/M3](M2_M3_VALIDATION.md),
[M3.1](M3_1_UI_REDESIGN.md), [Graph](GRAPH_EXPLORER_UPDATE.md).

## Phase map and dependencies

| Phase | Milestones | Status / dependency |
| --- | --- | --- |
| P1 — Reliable production foundations | F1 (M3.2B), F2 identity/access | Partial: F1.1–F1.3 locally implemented/validated, main-data cutover pending; F2 planned |
| P2 — Knowledge Hub and Spaces | K1 authoring, S1 Space experience | Planned; use F2 Space/access foundation and F1 content readiness |
| P3 — Retrieval intelligence | R1 (M3.3), R2 (M3.4), R3 bounded routing | Partial baseline; R1 uses F1; R2 builds on R1; R3 can be tested with adapters before live connector access |
| P4 — Enterprise connectors | C1 Jira live (M4.1), C2 Jira sync (M4.2), C3 Confluence, C4 GitLab | Planned; early identity/ACL feasibility in F2; C1 uses R3; C2 uses C1; C3 then C4 reuse proven contracts |
| P5 — Research and assisted work | W1 research/drafts, W2 approved actions | Planned; W1 builds on relevant P3/P4 sources; W2 follows explicit action authorization design |
| Cross-cutting production release | H1 hosted readiness (M5), H2 deployment/pilot (M6), L1 localization (M7) | Planned; security, quality and bilingual evaluation start early; H1 required before H2 |
| P6 — Advanced Conflict Resolution and Delegated Verification | D1 advanced review/resolution | Deferred; preserve essential safety and useful existing reviews throughout |

Phases describe delivery order, not reduced product quality. No requirement to finish
every graph improvement before investigating connector authorization. Native pages
use F2's minimal Space identity/authorization foundation; S1 delivers the full Space
experience after K1, avoiding a circular page/destination dependency. R3 supplies
the coordinator contract before C1; real cross-source acceptance follows C3/C4.

## Capability Acceptance Matrix

| Capability | Current state and evidence | Missing / improvement | Complete when | Owner milestone |
| --- | --- | --- | --- | --- |
| Uploads and evidence | Local ingestion, revisions, locators and retained originals; F1.1 independent search publication validated in an isolated stack | Main-data rollout; quote repair gaps; controlled reprocessing | Valid authorized text remains searchable despite failed enrichment; stable citations and safe revision transitions | F1 |
| Search | Partial target: implemented exact/text/vector/graph-assisted RRF in retrieval.py | Ranking, larger corpora, bilingual evaluation, new source filters | Relevant authorized resources found on held-out tasks within agreed load/latency targets | R1, L1, C2–C4 |
| Chat/RAG | Partial target: implemented cited answers, follow-ups, evidence dependencies and grounded-v3 | Space scope, live evidence, adaptive routing, improved interaction | Correct supported answers/abstention, scoped follow-ups, dated failures and end-to-end revocation | R1, R3, S1, C1 |
| Knowledge Graph | Completed bounded explorer and evidence display; partial target retrieval | Verified multi-hop answers, cross-source identity, measured path relevance | Useful paths support actual questions with evidence for every required connection; bounded and permission-safe | R2, C2–C4 |
| Native Knowledge Hub | Planned; current Knowledge.tsx is generated entity/claim display, not an editor | Rich authoring, publishing, organization, maintenance and revision UX | Full ordinary author/publisher/maintainer journeys work without approval bottlenecks; sources and attribution preserved | K1 |
| Spaces | Planned; current file scope and graph roots are not managed Spaces | Ownership, memberships, primary destinations, resource linking, contextual overview/chat | Project journey integrates curated and discovered knowledge without duplication or access expansion | F2, S1 |
| Identity and permissions | Partial target: org + owner/org-visible documents, demo tokens; review roles | Production sign-in, multi-group grants, delegated creation, narrowing page restrictions, source identity mapping | Full access matrix enforced before LLM and on all derived/history/cache surfaces; no demo impersonation hosted | F2, H1, C1–C4 |
| Contribution assistance | Planned | Destination/category/tag/related/duplicate suggestions | Useful authorized suggestions are optional; author is never inferred to be the actor described | K1, S1 |
| Connectors | Planned; no live Jira/Confluence/GitLab application integration | Authentication, live tools, modes, sync, ACLs, error lifecycle | Each source passes live and sync lifecycle gates; fixtures alone do not mark it complete | C1–C4 |
| Freshness and Updates | Partial foundation: revisions/timestamps exist; no connector change feed | Incremental sync, meaningful changes, live checks, simple indicators | Current requests use live source; dated fallback only if authorized; changed records refresh without full graph rebuild | R3, C2–C4 |
| Conflict safety | Basic local conflict storage/review; F1.1 search independence validated in isolation; partial target behavior | Main-data rollout; context-aware answer prioritization | Conflicting evidence retained, retrieved disagreements explained, existing useful review/history preserved | F1, R1 |
| Advanced conflict/delegated verification | Deferred; basic existing reviews are not this future capability | Detection/resolution policies, routing, queues, delegated fact review | Later approved scope and evaluation; no future-only machinery now | D1 |
| UI/UX | Completed M3.1 shell, source picker, evidence, graph/canvas, responsive checks | Complete authoring/Spaces/connectors UX, real progress/cancellation, RTL | Working end-to-end, accessible keyboard/mobile/error journeys; no empty navigation or simulated work | All, L1 |
| Operations/performance | Partial: leased jobs, bounded retries, independent usage, configured pacing | Load targets, interactive priority, backups, production monitoring/auth/deployment | Measured concurrent workloads, recovery, restore, security and cost acceptance; real infrastructure review | F1, F2, H1, H2 |
| Research/actions | Planned | Multi-source research/reports, assisted drafts, separately approved writes | Traceable useful outputs within budgets; authorized preview/approval and safe execution for writes | W1, W2 |

## Milestone execution contracts

### T1 — Fictional-company testing and selected-source overviews

- [x] Prepare 24 clearly fictional source documents, five projects, shared people/
  teams, an owner-only budget, an unresolved ownership disagreement and a sample revision.
- [x] Provide 15 example questions with source mappings and hand-authored expected
  outcomes; preserve exact-byte fixture recognition and honest arbitrary-upload behavior.
- [x] Add working source loading/downloads, questions and addition/revision guidance
  to the existing Sources sample area; no new empty navigation.
- [x] Add bounded permission-checked selected-document context for vague overviews,
  partial-coverage disclosure, low-cost greeting/clarification and clear provider labels.
- [x] Implement persistent API/worker-shared conservative test-cost reservations and
  pause on unknown usage; do not change existing unbudgeted provider behavior.
- [x] Complete the capped Sonnet journeys after refreshing the expired AWS session.
  Run completed 2026-11-12. 14 of 15 questions answered (Q14 is revision-mode,
  handled in the revision stage). Revision stage passed (old answer suppressed,
  new deadline found). User addition: enrichment failed, text search-ready (expected
  F1.1 behavior). 9 questions fully pass; 2 content-pass (Q7 conflict, Q12 overview);
  5 original failures (Q4/Q5/Q9/Q10/Q11) confirmed as temporary empty-retrieval
  caused by vocabulary mismatch when semantic embeddings weren't yet indexed — all 5
  pass on retest. Budget: $1.587/$10 spent. See docs/company_demo/validation_summary.json.

Mock workflow implementation is validated. Full Sonnet run completed. 17 of 24
documents had enrichment failures (12 unsupported assertions, 5 identifier namespace
errors) — text remains search-ready for all; enrichment fix is F1.2 scope.
F1.2 implemented (contracts.py + providers.py, 2026-11-12). F1.3 locally validated
2026-11-13. The current F1.3 work leaves the main app and existing F1.1 preview untouched.

All milestones require focused implementation changes when separately requested,
compatible migrations where needed, preservation of existing behavior/data, and
recorded acceptance evidence. Paths below are existing reuse points, not mandates
for a new service per responsibility. Complexity is relative, not a time estimate.

### F1 — Search readiness and processing reliability (continues M3.2B)

Dependencies: completed M3.2A. Complexity: high due to publication/citation invariants.

- [x] **F1.1 first slice (isolated local validation; main-data rollout pending):** separate searchable-content readiness from enrichment;
  conflict/extraction failures cannot block valid authorized indexed content.
- [x] Keep current-content and enrichment-version selection explicit. Superseded
  relationships remain historical, not current facts while new enrichment is pending.
- [x] **F1.2:** implement bounded safe quote/schema repair and relationship-direction
  guards from the diagnosed cases; preserve exact original evidence.
  Implemented 2026-11-12. Two targeted fixes applied:
  (1) contracts.py: allow `project_key` namespace for `decision` entities — decisions
  legitimately reference project keys; previously all 5 decision documents failed.
  (2) providers.py: after one bounded repair attempt, prune unsupported assertions
  (entities/claims/relationships) instead of rejecting the entire extraction — supported
  knowledge is retained, unsupported claims are discarded. Cascading entity-key cleanup
  applied so claims/relationships referencing pruned entities are also removed.
  Regression: grounding, resolution, model_limits tests all pass. Pre-existing preview-auth
  403 failures in company-sonnet container are unchanged (not caused by these fixes).
- [x] **F1.3 (isolated local acceptance):** add versioned enrichment staging,
  verified atomic activation and failure rollback; preserve source search/evidence.
  Migration 0011 and the refresh journey are implemented. Main cutover remains pending.
- [ ] Improve structure-aware context and parent passages against held-out retrieval
  tests; do not treat a byte estimator as measured token usage or adopt fixed tuning blindly.
- [ ] Preserve useful conflict/identity functionality and history. Isolate cross-document
  conflict assessment from search publication rather than deleting the subsystem.

Backend: processing.py, parsers.py, contracts.py, providers.py, retrieval.py,
conflict_detection.py, worker/main.py. Frontend: IntelligencePages.tsx Processing,
Sources/SourceControls and actual readiness/error displays. Data: F1.1 adds
search_ready_at; derived-generation changes remain F1.3 work as justified, existing
revision/chunk IDs unchanged.
Test: partial/failing extraction, parser failures, stale leases, concurrent revisions,
rollback/retry, mapped quotations, reversed edges, deletion/revocation and saved answers.
Exit: original citations still resolve, previous evidence is retained, supported new
text is searchable independently, and no stale/unsupported graph facts are promoted.
Detailed sequence: [M3.2B](M3_2B_PLAN.md).

#### F1 remaining delivery order — plan only, 2026-11-13

The user requested this plan after reporting that the conversational improvements
work, then authorized F1.3 implementation and rollout preparation. The reviewed
main-data cutover and F2 execution remain outside this batch.

1. **Checkpoint the current application.** Preserve the tested conversation/upload
   increment and its fixtures; prepare a scoped commit without sweeping unrelated
   changes into it. Retain the three reproduced baseline regression failures as
   explicit outstanding checks, not a fully passing-suite claim.
2. **F1.3 additive metadata.** Add `processing_jobs.staged_version_id` and
   `document_versions.activation_state` (`live`, `staged`, `rolled_back`) through
   an additive Alembic migration. Backfill existing records conservatively, retain
   source/revision lineage and original citation IDs, and extend job-status constraints
   for `enrichment_staged_failed` without destructive schema replacement. Confirm
   the distinction between immutable source revisions and derived enrichment
   generations before changing publication queries; add only metadata needed by
   the implemented staging boundary.
3. **F1.3 staging and verification.** Build candidate enrichment outside the live
   graph. Verify exact evidence, accepted assertions, relationship references and
   direction, and tenant/source dependencies before it becomes visible. Preserve
   current authorized text retrieval throughout reprocessing. The work uses the
   existing worker/modules; no new agent platform or infrastructure.
4. **F1.3 activation and failure.** Activate a verified candidate atomically, only
   when the expected source revision and job ownership/lease still match. A stale
   worker or older revision cannot replace a newer publication. If candidate
   verification fails, retain valid existing live enrichment, mark the candidate
   rolled back and the job `enrichment_staged_failed`, with an actionable reason.
   Same-revision reprocessing retains prior live facts; a newer source revision
   must still keep superseded old-revision facts historical under F1.1. Rollback
   must not label facts from obsolete text as current.
5. **F1.3 acceptance.** Test successful staged activation, failed verification and
   rollback, interrupted/stale workers, competing revisions, retry idempotency,
   uninterrupted search, historical citations, revoked access and saved-answer
   invalidation. Reflect the actual states in Processing/source controls and
   verify keyboard/mobile behavior. Validate migration/backfill and recovery in
   an isolated stack; record remaining quality limits. No new paid model evaluation
   or main-app migration is implied by these deterministic checks.
6. **F1.1 main-data rollout, separately authorized.** Freeze mutations/workers;
   preserve the old build; back up PostgreSQL and original artifacts; restore both
   into an isolated rehearsal stack. Preview actual readiness counts and pointers,
   apply the compatible migration chain in rehearsal, then verify permissions,
   search, graph freshness, citations/history and downloads. Prepare restore-based
   rollback and handling of post-backup writes before touching the original stack.
   Execute the reviewed rollout only after its own green light.

The remaining F1 context/ranking checks must use held-out questions and measured
results. They are not silently counted as completed by staging, and broad relevance
work retains its R1 gate. Historical M3.2A/F1.1 implementation is not repeated.

F1.3 acceptance and Bedrock evidence are in [F1.3 results](F1_3_RESULTS.md).
The [main-data rollout review](MAIN_DATA_ROLLOUT.md) includes the successful
synthetic backup/restore rehearsal and the observed main-stack inference-guard
configuration mismatch. Read-only inspection found the main database already at
0010; its next migration is 0011, rather than a repeat of readiness migration 0009.

### F2 — Organization identity, groups and access foundation

Dependencies: existing org/document permissions; can design/test alongside F1.
Complexity: high. Includes early source authorization feasibility, not a connector build.

- [ ] Replace demo-only auth for hosted operation; preserve local fixtures and plan
  enterprise IdP integration using the existing proposed Cognito boundary.
- [ ] Add multi-group membership and simple resource grants; centralize shared
  permission checks without per-claim/edge ACL administration.
- [ ] Establish Space identity, primary destination, owner and delegated Create Space;
  page restrictions narrow Space access, never broaden it. Define the general area.
- [ ] Cover owner delegation limits, link/move semantics and effective audience previews.
- [ ] Validate Jira Cloud user/source ACL and source-instance identity assumptions
  early using synthetic contracts, then an approved application connection when available.

Backend: main.py authentication/authorization boundary, retrieval.py, resolution.py,
graph_explorer.py; small reusable permission module as needed. Frontend: session.tsx,
admin/user/group screens and audience controls. Data: memberships/grants and Space
foundation with conservative backfill preserving existing owner/org audiences.
Test: multiple groups, narrowed pages, cross-org access, revoked membership, moves,
restricted names/counts, owner limits and source denial. Exit: permission matrix
works across API, search, graph, citations, history and caches; hosted demo auth disabled.

Suggested F2 delivery sequence, still planned:

1. Establish production sign-in/session contracts and an enterprise IdP path; keep
   the local demo explicitly isolated. Cognito remains the proposed hosted option,
   with configuration/cost review before any AWS resource provisioning.
2. Implement organization identity, multiple group memberships, resource grants
   and shared server-side permission checks with a conservative data backfill.
3. Deliver the Space/destination access foundation: delegated Create Space, owners,
   primary destination/general area, narrowing page restrictions, and safe links/moves.
   The complete Space UX remains S1; native authoring remains K1.
4. Verify the full access matrix across direct APIs, retrieval, graph, metadata,
   suggestions, citations, history and caches, including immediate revocation.
5. Validate Jira/source identity and ACL assumptions with synthetic contracts;
   use a real application connection only when separately authorized. This is
   feasibility for C1, not delivery of a live connector or synchronization.

### K1 — Production-quality native Knowledge Hub

Dependencies: F1 searchable content and F2 destination/access foundation. Complexity: high.

- [ ] Evaluate/reuse a maintained rich editor; deliver headings, lists, tables,
  links, code, appropriate attachments/media, autosave, preview and concurrent-edit protection.
- [ ] Deliver drafts without destination; direct authorized publication with suggested
  destination and visible audience; keep category/tag suggestions optional.
- [ ] Add revision browsing/comparison/restoration, archive and deliberate merge/redirect
  workflows preserving evidence and permission boundaries.
- [ ] Track author/editors, maintainer, described actors, AI provenance and references
  distinctly. Official designation is a separate authorized revision action, not a queue.
- [ ] Provide polished discovery, organization and authorized related/duplicate suggestions.

Backend: existing versions/artifacts/contracts and search publication; native content
module where needed. Frontend: Knowledge.tsx, shared ui.tsx/Evidence, editor and library
views. Data: native content/revisions, minimal lifecycle/maintainer/provenance fields;
reuse resource/evidence contracts, do not copy external pages into native records.
Test: save/reload, simultaneous edits, publication/access changes, restoration, duplicate
merge citations, safe rendering and keyboard/responsive UX. Exit: complete author,
reader and maintainer journeys; no compulsory ordinary approval; actor attribution correct.

### S1 — Complete Project Space experience

Dependencies: F2 Space foundation, K1 native content; integrate new sources as delivered.
Complexity: high across product UX and derived permissions.

- [ ] Deliver overview/objectives/owner/team, knowledge, connected resources, decisions,
  relationships, updates and contextual chat with honest empty/unavailable states.
- [ ] Support delegated self-service creation, accessible similar-Space suggestions,
  owner maintenance and a lightweight suggestion path for non-creators.
- [ ] Link a resource to multiple Spaces without copying or expanding access; suggestions
  and reliable auto-enrichment cannot overwrite approved content.
- [ ] Implement Hybrid Smart Scoping and clear audience/move controls; support teams
  and departments through the same model as their experiences are delivered.

Backend: Space queries/links using F2 permissions and existing entity/evidence/search
APIs. Frontend: Space navigation/overview/resources/chat; preserve People/Graph routes.
Data: Space-resource links and scoped conversation metadata; no separate knowledge store.
Test: private linked content, summaries with mixed permissions, duplicate names, moves,
revocation and context follow-ups. Exit: a useful cohesive project journey, not just a folder.

### R1 — Search relevance and grounded contextual answers (M3.3)

Dependencies: existing baseline; F1 enables index/context changes. Complexity: high.

- [ ] Improve identifier/entity linking, candidate ordering, hybrid ranking, context
  diversity and filters; compare reranking with baseline before adoption.
- [ ] Evaluate Arabic/English/mixed-language retrieval and answers from the beginning;
  expand independently reviewed real-company questions, not only synthetic fixtures.
- [ ] Implement flexible authority/relevance/time prioritization, optional scoped
  designations and semantic role distinctions; cite unresolved material disagreement.
- [ ] Evaluate proportionate semantic verification without weakening source checks;
  retain fail-safe abstention and Sonnet-only model use. No Gemma comparison or
  replacement work is required.
- [ ] Improve contextual follow-ups, source inspection, actual progress and supported
  cancellation; keep direct search independent of answer generation.

Backend: retrieval.py, providers.py, contracts.py, main.py conversations and tests.
Frontend: Assistant.tsx, IntelligencePages.tsx, FocusSources.tsx, Evidence.tsx.
Data: additive ranking/context/evidence metadata only if needed; version answer policy
when grounding rules change. Test: relevance, qualifiers, same-name entities, disagreements,
unsupported answers, bilingual queries and permission-safe history. Exit: held-out
quality/latency/cost targets met and regressions preserved; no invented target results.

### R2 — Evidence-backed multi-hop GraphRAG (M3.4)

Dependencies: R1, F1 source/version integrity. Complexity: high.

- [ ] Implement bounded path retrieval with cycle prevention and direction-aware traversal;
  the former three-hop default is a tuning starting point, not an intelligence ceiling.
- [ ] Retrieve evidence for every required edge; validate identity, dates and access;
  preserve explicit, inferred and uncertain distinctions.
- [ ] Measure path/ranking benefit against hybrid retrieval alone; retain useful graph
  exploration and do not extract every sentence or every possible relationship.
- [ ] Present supporting paths where useful and invalidate affected results on source changes.

Backend: graph_explorer.py, retrieval.py, contracts/evidence/resolution. Frontend:
GraphWorkspace/GraphPanels/ExplorerCanvas and evidence paths in chat. Data: reuse
relationships/evidence; source-qualified identity and additive metadata as needed.
Test: two/three-hop questions, reversed edges, missing evidence, ambiguous identity,
periods, cycles and revocation. Exit: useful cross-document answers with traceable
connections; failed paths produce partial/insufficient evidence, not fabricated links.

### R3 — Lightweight query routing and common evidence (continues M4.3)

Dependencies: R1; adapter contract can precede live C1; R2 enables graph routes.
Complexity: medium–high. No mandatory agent framework.

- [ ] Route stable, operational, historical and compound requests before retrieval;
  use relevant live source by default for current operational fields.
- [ ] Normalize local/live evidence identity, source/version, observed time, field/text
  support, authorization dependencies and coverage limitations.
- [ ] Bound tools, rounds, tokens, time and concurrency outside prompts; parallelize
  independent calls; broaden Space scope only when requested/enabled.
- [ ] Reauthorize retained live evidence/history and distinguish outage from source denial.

Backend: main.py ask path, contracts.py, providers.py, retrieval.py plus small coordinator/
adapter modules. Frontend: actual source activity, freshness, cancellation and partial
coverage in Assistant/Evidence. Data: minimal live evidence/dependency persistence under
retention; never automatically index Live Only history. Test routing with fixtures,
then real source gates in C1; simple questions incur no unnecessary planner call.

### C1 — Robust read-only Jira live integration (M4.1)

Dependencies: F2 source access/identity contract, R3 evidence/routing; approved app
credentials/project for live acceptance. Complexity: high.

- [ ] Implement approved MCP/native tools, user/source authorization, known endpoints,
  input validation, pagination, timeouts, bounded retries and source rate pacing.
- [ ] Expose connector/project modes and health; route current issue status/assignee/
  blockers live without equating assignee with project owner.
- [ ] Cite retained supporting response/excerpt and original Jira link with timestamps;
  do not use partial or user-filtered views as complete shared index records.
- [ ] Handle credential expiry, source denial, schema change, injection, outage and
  authorized dated fallback. No external writes.

Backend: connector adapter, coordinator, authorization/evidence. Frontend: Sources
connection/policy/health and source-labelled evidence throughout Chat/Search/Spaces.
Data: source instance, connection/scope policy, external identity and retained live evidence.
Test real approved access with two distinct source permissions plus mock fault cases.
Exit: complete live lifecycle, not one lookup. Jira integration is fully accepted
only with C2 synchronization lifecycle for Live + Sync scopes.

### C2 — Jira incremental sync, enrichment and Updates (M4.2)

Dependencies: C1, F1, F2; S1 for visible Space enrichment. Complexity: high.

- [ ] Synchronize approved scopes with checkpoints, recovery, deduplication, deletion
  and ACL reconciliation. Pick polling/webhooks from actual needs and source support.
- [ ] Refresh affected records from live observations without delaying answers;
  reject stale overwrites and incomplete replacement payloads; avoid unchanged embeddings.
- [ ] Auto-link reliable identities within sync scopes, preserve official content,
  and present basic meaningful change/freshness indicators without an event platform.
- [ ] Enforce Live Only/no-index and mode-transition removal from active retrieval;
  retained history still respects source access and retention.

Backend: existing worker/job patterns with appropriately scoped refresh jobs,
connector/search/Space queries. Frontend: sync status, recovery/errors and Space Updates.
Data: source revision/checkpoint and minimal change records justified by Updates.
Test duplicated/out-of-order/partial updates, source deletion vs not-found ambiguity,
permission revocation, missed polling cycles, mode changes and nonblocking refresh.
Exit: source changes appear once, old evidence remains attributable, active results
are permission-current, and only affected content/relationships are reprocessed.

### C3 / C4 — Confluence, then GitLab (expands M4.4)

Dependencies: proven C1/C2 contract; each needs its own approved connection and ACL tests.
Complexity: high per connector; no completion inherited from Jira.

- [ ] C3: Confluence live search/page retrieval, original identity/links, versions,
  restrictions, sync and revocation; complement native content without independent copies.
- [ ] C4: GitLab repositories/issues/merge requests/pipelines as approved, with live
  operational routing, membership/visibility, incremental sync and source limits.
- [ ] Reuse modes, evidence, connector UI and worker logic; implement source-specific
  permissions and error behavior explicitly rather than assuming identical APIs.
- [ ] Prove cross-source identities using explicit references; an issue mention is
  not proof that a merge request fixes it.

Data: reuse connector/resource models with only source-required metadata. Frontend:
complete source-specific configuration and unified results, not empty placeholders.
Test each full connector lifecycle and authorized cross-source questions, including
denial/expiry/rate limits/partial results. Exit: equivalent quality to Jira for supported
capabilities; unsupported source features are documented, not simulated.

### W1 / W2 — Research, assisted knowledge and authorized actions

Dependencies: R3 and relevant accepted connectors; W2 follows W1 and concrete action
design. Complexity: high; external writes require separate authorization.

- [ ] W1: complete multi-source research, project reports and handovers with source
  comparison, actual progress, cancellation, bounded cost and disclosed coverage.
- [ ] Prepare native-page additions as distinguishable drafts; a user explicitly
  publishes them. Keep tool results, conversation memory and organizational facts separate.
- [ ] W2: show exact target/payload preview, obtain explicit approval, reauthorize at
  execution, prevent duplicate writes, handle partial outcomes and retain audit evidence.
- [ ] Adopt specialist agents/frameworks only if measured task success or maintainability
  improves; do not add one agent per source.

Reuse coordinator, native editor, evidence and audit. Add execution/approval persistence
only when W2 is actually implemented; no future-only tables now. Test budget exhaustion,
prompt injection, evidence revocation, cancelled runs, retries and changed approval payloads.
Exit: useful reviewable outputs and safe approved actions, not unbounded autonomous work.

### H1 / H2 — Hosted readiness and approved deployment (M5 / M6)

Dependencies: F2 for real user access; each released capability's own gates. Complexity:
high. This is a cross-cutting release track, not deferred security cleanup.

- [ ] H1: production authentication, upload protection, least-privilege secrets,
  redacted diagnostics, monitoring, interactive/background scheduling, recovery and
  measured concurrency/latency/cost. Recheck actual model/source quotas; workers alone
  do not create throughput. Current nine-RPM pacing is configuration, not fresh quota proof.
- [ ] Establish backup/restore and retention/purge behavior; test tenant isolation and
  every derived surface under permission changes. Resolve critical findings.
- [ ] Prepare Python CDK deployment, HTTPS/frontend delivery/networking, state protections,
  current region-specific costs, synth/diff, restore/rollback and operator runbook.
- [ ] H2: only after explicit approval deploy the concrete reviewed AWS scope, validate
  hosted journeys/alerts/restore and run the measured pilot; no infrastructure in this task.

Reuse local Compose/runtime; target infrastructure is a proposal until reviewed. Tests
include load during ingestion/sync, failures/restarts, backup restoration and hosted auth.
No calendar commitment until representative volume, concurrency, budget and targets agree.

### L1 — Bilingual capability and localization (repositions M7)

Dependencies: evaluate content/query quality during F1/R1; localized UI follows each
working surface. Complexity: medium–high across authoring, evidence and navigation.

- [ ] Evaluate Arabic, English and mixed-language source/query combinations throughout.
- [ ] Deliver language selection and RTL layouts across Hub, Spaces, Search, Chat,
  Graph, source management and evidence; preserve original source identifiers/text.
- [ ] Test desktop/mobile, keyboard, mixed-direction editor content and English regression.

Data: language/locale metadata only where useful; no separate knowledge stores. Exit:
an Arabic-speaking employee can complete the same accepted knowledge journeys; current
English UI does not count as localization completion. Release coverage must be explicit.

### D1 — Advanced Conflict Resolution and Delegated Verification

Status: deferred. Do not add new conflict engines, queues, ownership routing, resolution
automation, verification services or speculative tables now. Preserve existing basic
conflict/identity review and history; do not remove useful working features merely
because this phase is later. Future design can attach decisions to stable attributed
claims/evidence. Reassess scope and acceptance with real usage before implementation.

## Cross-cutting acceptance and rollout

Before each capability is called complete: test ordinary workflows, permissions and
revocation, concurrency/version races, degraded/error recovery, responsive/keyboard UX,
and measured quality/latency/cost appropriate to the change. Preserve original data and
citations with additive migrations and tested rollback/backfill; destructive replacement
is not authorized. Run relevant API/build/browser regressions in disposable environments.

Build a held-out employee-question set covering policies, ownership, same-name projects,
history, source disagreement, graph paths, operational status and Jira/GitLab research.
Review gold answers independently. Compare hybrid baseline vs graph/reranking/planning
increments; report retrieval, semantic support, abstention, latency, source/model calls
and costs separately. Never infer factual truth from exact-quote matching alone.

Numeric targets and workload are open decisions: previous 20 users/50–200 documents
were pilot assumptions, not capacity requirements; 100–200 employees is not measured
concurrency. Agree corpus, simultaneous queries, source quotas, freshness/ACL windows,
retention and budget before claiming enterprise-scale readiness. Paid evaluation needs
a new explicit budget; historical M3.2A approval is not a standing allowance.

## Legacy milestone mapping and retained scope

| Earlier plan | Current location / reason |
| --- | --- |
| M0–M3.1 completed checklists | Preserved verbatim below; new requirements do not reset progress |
| M3.2A | Completed findings retained; no repeated pilot implied |
| M3.2B | F1, split into reviewable readiness/repair/reprocessing slices |
| M3.3 / M3.4 | R1 / R2; graph capability preserved and measured |
| M4.1 / M4.2 / M4.3 | C1 / C2 / R3 and W1; live-first routing is not only an empty-KB fallback |
| M4.4 | C3 Confluence then C4 GitLab committed; Slack retained below |
| M5 / M6 | H1 / H2; production auth/security start early, deployment still requires approval |
| M7 last | L1 cross-cutting evaluation/localization; no false claim of existing Arabic support |
| New native Hub and Spaces | F2, K1 and S1; full capabilities, not merely renamed generated Wiki |
| Extensive new conflict workflows | D1 deferred; essential safety and existing useful functionality retained |

Retained extension backlog (not implicitly authorized or deleted): selected public
Slack channels/readable replies with verified membership; named saved graph views/layouts
that store view state without copying knowledge; SharePoint/OneDrive; OCR/images/Excel;
private Slack/DMs; customer onboarding. Existing explicit source/data authorizations
remain valid within their scope; additional access needs its own authorization. No new
dates or feature removal are inferred from this order.

## Recommended next development task — when explicitly requested

**Review the prepared main-data rollout.** F1.1/F1.2, the conversational increment
and F1.3 are implemented locally; F1.3 has isolated acceptance and a bounded Sonnet
probe. The original main stack has not been changed by this work. Resolve the
observed main API/worker budget mismatch in the concrete rollout review; the proposed
first cutover keeps inference disabled instead of creating another test allowance.
F2 remains the next implementation milestone after the separately approved rollout.

F1 main-data rollout remains a separate tracked step. The main database is observed
at migration 0010; rehearse its actual snapshot and migration 0011, with reviewed
backups and rollback, before cutover. Historical isolated F1.1 evidence remains in
[F1.1 results](F1_1_RESULTS.md); current procedures are in
[main-data rollout review](MAIN_DATA_ROLLOUT.md).

Do not rerun completed M3.1 handoff, M3.2A or F1.1 implementation merely because an old
paragraph said to do so. Later slices require a new implementation request.

## Historical completed milestones and validation

The following original M0–M3.1 record is retained verbatim. Its dated wording and
old delivery assumptions describe past work; active order and requirements are above.
Outstanding M2/M3 quality acceptance is carried into R1 and cross-cutting acceptance.

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
