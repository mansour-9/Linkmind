# Linkmind Restructure — Decision and Document Review

> **Subsequent RF1 delivery:** after this documentation-only checkpoint, the user
> requested RF1 implementation. It is now implemented/validated in a new isolated local
> stack; see [RF1 results](RF1_RESULTS.md). This record preserves the earlier review,
> its authorization boundary and dated documentation checks; it is not current RF status.

Date: **2026-11-14**. Status: documentation alignment completed; RF implementation
is not started. This is a decision/audit record, not a second roadmap. Use
[scope](PROJECT_SCOPE.md), [architecture](ARCHITECTURE_M2_M3.md) and the
[single implementation plan](IMPLEMENTATION_PLAN.md) for active requirements/work.

## Authorization and outcome

The user requested stepping back from implementation, then agreed a simpler company
repository and AI direction, and explicitly requested a complete restructuring plan
and updates to conflicting project documentation. Inputs are guaranteed to provide
readable text/extractable PDFs or source text/records. OCR/conversion is handled upstream
if needed; it must not drive new Linkmind services or complexity in this core plan.

Only project documentation was edited. No source/configuration/fixture, database,
service, external account or AWS state was changed. No model/embedding/tool-source call,
paid evaluation, ledger operation, migration, build, deployment, commit or push occurred.
Read-only source inspection and local documentation checks do not establish RF behavior.

## Agreed decisions

| Decision | Product/architecture consequence |
| --- | --- |
| Unified durable company repository | Persist selected uploaded/synchronized knowledge, versions and provenance; do not deliver only a transient live-search proxy |
| Lightweight ingestion | Retain, parse/map, index and make available; no default Sonnet entity/claim/relationship extraction or conflict scan |
| Graph is optional | Preserve useful existing views/links; missing graph never blocks ingestion, discovery or answers |
| Metadata and retrieval are core | Use source fields, reliable project references, text/semantic search and a small capability catalog |
| Reason on demand | Analyze retrieved evidence at question time; do not automatically publish AI interpretation as shared truth |
| Stored and live sources cooperate | Stable knowledge uses the index, current fields use relevant tools, historical questions use dated evidence; bounded combined retrieval |
| Selective durable collection | Selected Live + Sync scopes persist; Live Only results do not silently become shared index/graph knowledge |
| Readable text boundary | No core OCR/conversion requirement, new microservice platform or image interpretation work |
| Preserve security | Existing tenant/item/source/history/cache boundaries stay; detailed enterprise group/Space design deferred |
| Preserve completed work | Retain original records, passage/citation IDs, reviews, facts, migrations and optional enrichment safeguards |
| Prioritize the core | Native authoring, managed Spaces, advanced GraphRAG/conflict/delegation and action/agent workflows remain later |
| Future examples stay examples | Training and archival export/legal retention are not newly authorized features |

Embeddings still cost processing and model usage; removing routine Sonnet extraction is
not a claim of free ingestion. Broad summaries can need more evidence than ordinary
questions. No zero-failure guarantee, savings percentage or unmeasured SLA was agreed.

## Proposed defaults and open choices

The RF sequence is the plan, not implementation authorization. RF1 is the next candidate
only if requested. First connector, actual accounts/scopes and connector order remain
open; Jira is the prior candidate and OneDrive/SharePoint collection is a core source
class. This replaces mandatory Jira → Confluence → GitLab prerequisites, without claiming
any connector exists. Complete one source lifecycle before promising a broad catalog.

Source catalog fields, evidence-envelope storage, index reuse policy and numeric budgets
are implementation design choices to resolve within their stages. Existing semantic answer
verification remains until an evaluated policy change; this plan does not turn it off.
Representative corpus/questions, quality thresholds, concurrency, p50/p95 latency, freshness,
cost targets, retention, production identity and release locale/region/budget remain open.

## What the current code actually does

Read-only review covered processing, retrieval, providers, conversations, intent/source
discovery and model-policy consumers. Current ordinary processing publishes source text,
then still attempts enrichment. Local source-only search/answers already have an F1.1
foundation; RF1 must change execution defaults and product states, not repeat F1.1.
Some metadata filters still depend on extracted entities. Live-source orchestration,
application connectors and external sync are not implemented. Current source answer
policy is `grounded-v6-source-identifiers`; preview/report policy versions differ.

F1.2/F1.3 and later repairs are local work, not all rolled out to protected environments.
Last recorded main inventory is schema 0010; code includes 0011/0012. Latest Lantern paid
probe failed extraction-verdict alignment while all four sources remained searchable.
Existing evidence is retained honestly; complete extraction/graph/chat acceptance is not
retroactively claimed or made a prerequisite for the new source-only core.

No Docker, database, AWS session, account quota or ledger state was inspected during this
document task. Historical values are not fresh observations. Preserve the original
`northstar-sonnet-2026-11-12` cumulative USD 10 guard/unknown reservations; no paid run,
reset/clone/increase/unpause is authorized. Old remaining allowances are not new approval.

## Documentation inventory and disposition

Reviewed all **30 existing project Markdown guidance/runbook/planning/report files**, including
the hidden GitHub PR template and untracked Lantern handoff. They were read as project
instructions or dated implementation evidence and aligned according to role. New content
adds this review and three historical planning snapshots. There is one active roadmap.

Synthetic fixture documents are source data/test inputs, not architecture instructions;
their bytes were not edited. JSON/raw model reports, screenshots/galleries, uploaded PDFs,
private files and dumps remain evidence/assets, not rewritten specifications. This review
does not claim a new private-content, visual, runtime or model-quality acceptance run.

| Existing document | Review action |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | Latest documentation-only authority, accurate local checkpoint, RF priorities/defaults, budget/security boundaries |
| [README.md](../README.md) | Repository/assistant purpose, current-versus-target, RF phases and protected runtime commands |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Active authority, RF core constraints and documentation-only validation path |
| [Original master spec](../COMPANY_BRAIN_CODEX_MASTER_SPEC.md) | Strong supersession notice; original specification body retained |
| [PR template](../.github/pull_request_template.md) | Documentation checks and source-only RF acceptance guidance |
| [Local runbook](../code/README.md) | Current commands clearly separated from target/defaults and authorization; OCR boundary corrected |
| [Diagnostic runbook](../code/apps/api/diagnostics/README.md) | Historical comparison tooling, no active Gemma/paid rerun instructions |
| [PROJECT_SCOPE.md](PROJECT_SCOPE.md) | Rewritten active decisions, core boundaries, proposed defaults and open choices |
| [ARCHITECTURE_M2_M3.md](ARCHITECTURE_M2_M3.md) | Inspected current code plus explicit target ingestion/repository/routing/evidence/sync contracts |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Single RF0–RF6 sequence, acceptance matrix, dependencies, deferred/legacy mapping; completed M0–M3.1 retained |
| [FRONTEND_RULES.md](FRONTEND_RULES.md) | Current design/runtime preserved; target states/flows aligned; rich editor/Spaces/detail access UX deferred |
| [JIRA_KNOWLEDGE_NEXT_STEPS.md](JIRA_KNOWLEDGE_NEXT_STEPS.md) | Source-independent connector lifecycle and durable collection; no mandatory extraction or fixed source order |
| [M3_2_PLAN.md](M3_2_PLAN.md) | Superseded-plan notice with later F1.2/F1.3 status; body retained |
| [M3_2B_PLAN.md](M3_2B_PLAN.md) | Superseded-plan notice; old next tasks not active; body retained |
| [MAIN_DATA_ROLLOUT.md](MAIN_DATA_ROLLOUT.md) | Safety reference retained; RF/current-schema cutover review required, no execution |
| [HANDOFF_LANTERN_FIXES.md](HANDOFF_LANTERN_FIXES.md) | Superseded execution handoff; later results linked; no automatic repair/paid task |
| [ASSISTANT_PERSONA.md](ASSISTANT_PERSONA.md) | Dated evidence notice; implementation/deployment/test body retained |
| [CITATION_FALLBACK_FIX.md](CITATION_FALLBACK_FIX.md) | Dated evidence notice; exact result/budget body retained |
| [COMPANY_TESTING.md](COMPANY_TESTING.md) | Dated evidence notice; T1 acceptance explicitly limited to original fictional test scope |
| [CONVERSATIONAL_TESTING.md](CONVERSATIONAL_TESTING.md) | Dated evidence notice; success/failure and budget chronology retained |
| [F1_1_RESULTS.md](F1_1_RESULTS.md) | Dated evidence notice; original readiness/validation record retained |
| [F1_3_RESULTS.md](F1_3_RESULTS.md) | Dated evidence notice; staged generation/restore/live-probe record retained |
| [GRAPH_EXPLORER_UPDATE.md](GRAPH_EXPLORER_UPDATE.md) | Dated evidence notice; graph/demo/canvas results retained, not core prerequisites |
| [LANTERN_IDENTIFIER_REPAIR_RESULTS.md](LANTERN_IDENTIFIER_REPAIR_RESULTS.md) | Dated evidence notice; failed real verifier remains visible, no required rerun |
| [LANTERN_REPAIR_RESULTS.md](LANTERN_REPAIR_RESULTS.md) | Dated evidence notice; old paid proposal not active authorization |
| [M2_M3_VALIDATION.md](M2_M3_VALIDATION.md) | Dated evidence notice; model/benchmark limitations and old phase wording retained as history |
| [M3_1_UI_REDESIGN.md](M3_1_UI_REDESIGN.md) | Dated evidence notice; original implementation and later user acceptance retained |
| [M3_2A_RESULTS.md](M3_2A_RESULTS.md) | Dated evidence notice; original scores/rates retained, Gemma follow-up explicitly inactive |
| [SOURCE_FOCUS_UPDATE.md](SOURCE_FOCUS_UPDATE.md) | Dated evidence notice; source-picker behavior and checks retained |
| [Original agent rules](reference/AGENTS.original.md) | Historical/non-executable notice; original body retained |

Prior planning snapshots preserve all former detailed requirements/checkpoints, so deferred
capabilities are not silently deleted. Relative links were relocated for the archive:
[prior scope](reference/pre_restructure_2026_11_14/PROJECT_SCOPE.md),
[prior architecture](reference/pre_restructure_2026_11_14/ARCHITECTURE_M2_M3.md),
[prior roadmap](reference/pre_restructure_2026_11_14/IMPLEMENTATION_PLAN.md).

## Documentation verification

Verification is limited to documentation: local relative links and heading targets,
UTF-8/whitespace, authority/current-versus-target consistency, preserved historical
bodies/checklists and unchanged non-document working-tree state. No application tests,
builds, browser checks or paid model acceptance were run, since runtime did not change.

Recorded results on 2026-11-14:

- **34 Markdown documents checked:** 30 existing documents, three planning snapshots and
  this review. **232 local relative links/heading targets passed**, with no missing targets.
- UTF-8 decoding/replacement-character checks and `git diff --check` passed.
- **20 historical body/checklist preservation checks passed**, including all 17 dated
  reports/plans/handoffs, the original specification/instructions and completed roadmap
  record. Only contextual notices were added to retained historical bodies.
- **Three archived planning snapshot comparisons passed** against the pre-edit content,
  allowing only the explicit historical notice and relocated relative Markdown links.
- Non-document working-tree state matched the pre-edit baseline, including the existing
  untracked JSON evidence. Pre-existing edits were retained; no reset/delete/commit occurred.
- Active guidance was reviewed for one-roadmap authority, current-versus-target labels,
  default-off enrichment, the readable-text boundary, durable selected-source collection,
  optional graph, preserved security, deferred enterprise detail and no execution permission.

RF0 documentation alignment is complete. **RF1–RF6 remain planned and unimplemented.**
No application test, live evaluation, runtime-state verification or production acceptance
is claimed by these checks.
