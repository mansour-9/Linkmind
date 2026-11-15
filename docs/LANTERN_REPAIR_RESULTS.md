# Project Lantern extraction and chat repair

> **Historical evidence / compatibility note — 2026-11-14.**
> The dated implementation, checks, budgets and environment observations below are
> retained; they were not rerun or re-scored by this documentation update.
> The [active roadmap](IMPLEMENTATION_PLAN.md) and [scope](PROJECT_SCOPE.md) now
> prioritize source-only ingestion, a durable selected-source repository and bounded
> retrieval. [RF1](RF1_RESULTS.md) subsequently implements default-off enrichment in
> isolated current code; old next tasks/manual or paid commands are not authorization.
> Historical evidence/security/history remains intact; existing environments are unchanged.

Implemented and locally tested on 2026-11-13, on `m3.2/baseline-gemma`.
This is a focused offline repair, not a rollout or real-model acceptance claim.

Subsequent identifier investigation and authorized bounded Sonnet results are in
[LANTERN_IDENTIFIER_REPAIR_RESULTS.md](LANTERN_IDENTIFIER_REPAIR_RESULTS.md).
Real end-to-end acceptance remains incomplete; the later report supersedes this
document's pending-paid-acceptance status, not its historical offline evidence.

## Root causes and evidence

- **Extraction:** the processor grouped eight passages regardless of source size. All
  non-success Bedrock stop reasons became `Model response was incomplete or blocked.`,
  so the stored historical errors did not identify truncation versus blocking. The four
  historical rows all reached the 6,000-output-token ceiling, strongly supporting output
  truncation, but their actual `stopReason` was not recorded and cannot be reconstructed.
- **Chat:** `_answer_once()` performed local exact-citation/internal-ID checks before
  semantic verification. `answer()` caught every `ValueError`, attempted one correction,
  and allowed a second local validation error to become the generic HTTP 503 response.
  The original rejected quote/ID was not retained and remains unknown. These failures
  did not imply chat output truncation, and unenriched text was still searchable.

## Repair

- Batches contain at most **three passages and 9,000 source-text characters**. The
  character limit is a bound, not measured token usage. Original passage IDs, locators,
  and verbatim text are retained.
- Only a `max_tokens` stop permits a split, at one level per initial batch. Extraction
  calls are capped at three per initial batch (failed parent plus two children). Each
  batch retains the existing single semantic correction. Content/guardrail blocking,
  malformed output, other stops, and transport/budget/auth failures do not split.
- Batch-local entity keys are namespaced before combination; relationships remain
  source-local. All combined entities, claims, relationships, identifiers, references,
  and exact quotations are revalidated before F1.3 staging/activation.
- Migration `0012_inference_diagnostics` additively stores the actual Bedrock
  `stopReason` and bounded JSON diagnostics in tenant-scoped `ai_usage`. Existing
  reviewer/admin usage authorization remains in force. Full failed model answers and
  raw response bodies are not logged.
- Exact local answer failures now identify statement/citation indexes, passage ID,
  rejected quote (capped at 500 characters), or internal canonical ID. Only these typed
  local failures get one correction; unrelated errors propagate. If correction also
  fails, no statements are returned and the normal helpful insufficient-evidence UI is
  used. The bounded diagnostics are persisted separately.
- Answer validation policy is `grounded-v5-bounded-evidence`, so superseded experimental
  answers are not silently reused as current verified context.

F1.3 candidate verification, atomic activation, rollback, immutable evidence,
revision/lease/tenant guards, source ACLs, and search-readiness separation are unchanged.

## Offline Lantern evidence

The four original PDFs were read from ignored `.local/lantern-acceptance/`, mounted
read-only into a new mock stack, and verified against manifest SHA-256 and byte counts.
They contain 8, 8, 9, and 10 parsed passages respectively. No PDF or private extracted
text is committed.

| PDF | Initial batch sizes | Largest source-text batch | Calls with one injected truncation |
| --- | --- | ---: | ---: |
| 01 Discovery Charter | 3, 3, 2 | 5,230 chars | 5 |
| 02 Decisions and Meetings | 3, 3, 2 | 5,439 chars | 5 |
| 03 Engineering Design | 3, 3, 3 | 6,090 chars | 5 |
| 04 Pilot Readiness | 3, 3, 3, 1 | 5,870 chars | 6 |

The injected `max_tokens` paths preserved all passage IDs and exact evidence. In a
separate explicitly stubbed graph/publication fixture, source-backed identifiers linked
four project occurrences, producing four relationships and six cross-document conflicts.
These are **synthetic assertions used to test identity/conflict mechanics**, not facts
extracted by Sonnet and not a semantic quality score. Exact citation resolution,
cross-document retrieval, retained facts after failed refresh rollback, and revoked
search/evidence access all passed.


## Validation and boundaries

- **160 API tests passed** in the isolated mock stack, including the two offline Lantern
  tests, no-network Converse stop-reason tests, exact diagnostics/correction tests,
  migration downgrade, search readiness, staged activation/rollback, concurrency,
  history, and permissions. One existing Starlette deprecation warning remains.
- Initial full-suite failures were old generic quote-error assertions in the historical
  M3.2 offline diagnostic; these now assert/serialize the typed diagnostic instead.
  An earlier stalled run used HTTP polling while the mock worker was stopped; the final
  suite ran with the isolated mock worker active.
- Targeted browser regression: **7/7 workflows passed** (28.6 seconds), covering
  search readiness, staged replacement/failure, citations, conversations and persona.
- Isolated validation: `linkmind-lantern-repair-clean`, port **5186**, schema
  **0012_inference_diagnostics**, using only `compose.yaml` and a unique backend image.
  No Bedrock/AWS provider, credentials, budget run, or paid worker was configured.
- No real Bedrock `stopReason` was obtained during this repair: no paid call was made.
  Tests used fake Converse responses. Real Sonnet extraction/relationship quality,
  actual production stop reasons, and real answer acceptance remain pending approval.
- Original main data and every existing preview stack remain untouched. No infrastructure,
  private files, Gemma work, F2 work, budget changes, or paid AWS calls were made.
- Local database/artifact volumes and ignored diagnostic files belong only to the new
  repair stacks. The earlier `linkmind-lantern-repair` development stack is separate.

## Paid acceptance proposal (approval required)

Use a **new isolated Bedrock acceptance stack**, not main or an existing preview, with
schema 0012 and the reviewed commit. Mount the same four PDFs read-only and upload them
as new test sources. Reuse the existing `northstar-sonnet-2026-11-12` ledger after a
read-only preflight; do not reset, unpause, copy, or increase its USD 10 cap.

- Hard ceiling: **144 model calls**, with **1.50 USD** maximum additional spend and
  the existing ledger's lower remaining headroom taking precedence. No batch may exceed
  three extraction calls (parent plus two children), one semantic correction per
  extraction, one conflict-assessment call per document, or one answer correction.
- Sonnet extraction: **13 initial / 39 maximum** calls. Initial semantic verification:
  **13 initial / 38 maximum** calls (two per split child). Verifier corrections:
  **13 initial / 51 maximum** calls. Each individual extraction path still permits only
  one semantic correction. This is a strict outer bound, not an expected call count.
- Conflict assessment: at most **4** calls, one per document, subject to the existing
  50-pair guard. Any overrun stops acceptance.
- Chat: four questions covering overview, a cross-document relationship, a documented
  conflict with both citations, and `what is Lantern ?` (regression). Maximum three
  model calls per question, including one correction and semantic verification.
- New embeddings are excluded. Use existing source evidence and lexical retrieval for
  this focused gate; embeddings can be assessed separately with their own cost approval.
- Before dispatch, calculate the actual reservation maximum using configured Sonnet
  rates and observed request sizes. Proceed only if every reservation fits within
  remaining ledger headroom. As a planning ceiling, no more than **USD 1.50**
  additional spend is proposed; this does not assert current ledger availability.
- Stop immediately on credential/auth failure, paused/uncertain budget state, throttling,
  content/guardrail blocking, malformed output after permitted correction, split
  exhaustion, evidence failure after one correction, permission mismatch, or any attempt
  to touch main/existing preview data. Keep actual stop reasons and bounded diagnostics.
- Acceptance requires all four documents to have exact valid enriched records or an
  honest classified failure, searchable original text throughout, valid relationship/
  conflict evidence, cited or clean abstaining chat, and no unsupported answer saved.

Rollout remains a **separate approval** after real-model acceptance. A rollout must use
a reviewed backup, maintenance window, schema 0011/0012 upgrade, health/search/evidence/
permission checks, and a restore/application rollback plan. It must not use the old
persona preview builder, which reconstructs older provider behavior.
