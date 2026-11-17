# M3.2 — Document-processing reliability

> **Superseded delivery plan — 2026-11-14; retained for history.**
> Use [the active RF roadmap](IMPLEMENTATION_PLAN.md), [scope](PROJECT_SCOPE.md)
> and [current/target architecture](ARCHITECTURE_M2_M3.md). Old unchecked work and
> next-task wording below are not an active queue. F1.2 and F1.3 were subsequently
> implemented locally; main rollout remains pending. RF1 targets default-off
> enrichment, not another mandatory extraction-repair cycle. No implementation,
> model call or rollout is authorized by the current documentation request.

Updated 2026-11-12 for the main roadmap's F1 foundation. **A completed; B partial:
F1.1 implemented and validated in an isolated stack, main-data rollout pending;
F1.2/F1.3 planned.** See [F1.1 results](F1_1_RESULTS.md).
This is a focused supporting plan, not a second roadmap.
The [main roadmap](IMPLEMENTATION_PLAN.md) owns phase order and acceptance status.

Model decision (2026-11-12): ongoing work uses Sonnet only. Gemma is unavailable per
the user; no Gemma repair, comparison rerun or adoption task is active. The completed
pilot and frozen results below remain historical evidence. No runtime configuration
change or new paid evaluation is authorized by this documentation update.

## Preserved checkpoint A

M3.2 remains one milestone with A diagnostics and B implementation checkpoints.
The frozen format matrix, reproduction and six-case Gemma/Sonnet pilot are complete.
Recorded results: 23/23 offline cases, 48/48 API tests, 20/20 browser workflows, frontend
build, 17 inference attempts and US$0.12665844 estimated token cost. No production
model/schema/data changes occurred. This is historical validation, not a fresh run.

Read [M3.2A results](M3_2A_RESULTS.md) and its frozen artifacts. Do not rewrite the gold
after observing outputs or rerun the pilot using its old approval. The exact original
private-PDF bad quotations remain unavailable; synthetic reproduction establishes the
failure class, not that those original files are fixed. Gemma's fenced JSON rejection
does not establish factual inaccuracy, nor does Sonnet verification prove every edge.

The historical M3_2_BASELINE.json and docs/m32 records remain immutable references.
Independent representative-company quality review and numeric targets are still open.

## Revised checkpoint B — F1 in the main roadmap

The previous all-or-nothing publication design is superseded: content search readiness
must be independent of knowledge enrichment and cross-document conflict assessment.
This change is required for uploads, native pages and connected resource sync alike.

1. **F1.1:** make valid authorized indexed content searchable even if enrichment fails;
   keep source versions and current/historical relationship behavior consistent.
2. **F1.2:** safe mapped quotation repair, bounded correction and deterministic direction
   checks justified by A's findings; unsupported items still fail.
3. **F1.3:** safe versioned reprocessing and improved context/index generation, only adding
   metadata needed for reproducibility/activation and stable citations.

Detailed implementation proposal and tests are in [M3.2B](M3_2B_PLAN.md). No main database
migration is included in the isolated F1.1 delivery. Other slices remain planned.

## Reuse and boundaries

Reuse immutable uploaded versions, retained chunks/locators, evidence validators,
lease/retry/accounting and existing UI/API contracts. Keep useful conflict and identity
review functionality and historical records; do not expand conflict workflows here.
Show actual content/enrichment states and distinguish source-access, parsing, provider,
formatting and semantic failures. Keep deterministic fixture processing honest.

F2 identity/group planning and early Jira authorization feasibility may proceed as
design work alongside this milestone; the old rigid M3.3 → M3.4 → all connector work
ordering is replaced by dependencies in the main plan. Bilingual evidence evaluation
is included where relevant. Full localization, rich editor, Spaces, connectors, hosted
deployment and OCR/Excel remain elsewhere in the main roadmap. Model replacement is
not an active task under the Sonnet-only decision. No new infrastructure is needed
to implement F1 locally.

## Exit gate

- Searchable text survives extraction/conflict failure without unsupported graph facts.
- New content revisions never inherit old relationships as current.
- The diagnosed formatting/direction regressions pass without relaxing source truth.
- Existing evidence/downloads, review history, permissions and saved-answer invalidation
  remain correct through retry, reprocessing, revision races and rollback.
- Relevant disposable API/build/browser tests pass; held-out/live results, untested
  original files, cost estimates and independent review remain accurately distinguished.

Record progress per slice without marking B or M3.2 complete prematurely. The next
development slice, when requested, is F1.2. Do not repeat the completed F1.1
implementation, UI handoff or pilot. Main-data rollout remains separately tracked.
