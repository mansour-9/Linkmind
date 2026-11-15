# Lantern identifier/evidence repair

> **Historical evidence / compatibility note — 2026-11-14.**
> The dated implementation, checks, budgets and environment observations below are
> retained; they were not rerun or re-scored by this documentation update.
> The [active roadmap](IMPLEMENTATION_PLAN.md) and [scope](PROJECT_SCOPE.md) now
> prioritize source-only ingestion, a durable selected-source repository and bounded
> retrieval. [RF1](RF1_RESULTS.md) subsequently implements default-off enrichment in
> isolated current code; old next tasks/manual or paid commands are not authorization.
> Historical evidence/security/history remains intact; existing environments are unchanged.
> Its failed extraction gate remains an honest historical result. It is not a
> prerequisite to source-only RF1/RF3 acceptance or a task to rerun automatically.

Work started 2026-11-13; final local checks completed 2026-11-14, on
`m3.2/baseline-gemma`. **Real end-to-end acceptance did not pass. No rollout.**

## Diagnosis

The previous acceptance report did not retain the response or rejected identifier.
Its database confirms two extraction calls, `max_tokens` then `end_turn`, followed
by `Identifier lacks source evidence`. That historical item cannot be recovered.

The new isolated probe retained responses under ignored local storage and reproduced
the failure. Sonnet assigned a document reference to a project as `project_key`,
while the project's own quotation omitted that reference. It also assigned document
references as `issue_key` identifiers to document entities. Original text explicitly
labels the first code as a document ID. The evidence validator was correctly rejecting
unsupported identity assertions; batch merging had not lost or rewritten citations.
Exact entity, identifier, source passage, and quotations are retained privately in
`.local/lantern-identifier-live/acceptance.json` and `raw/002-response.json`.

Two implementation gaps prevented useful recovery: local identifier errors were
generic and bypassed extraction's correction path; validation stopped at the first
item, so one correction could fix that item and leave other known failures untouched.
Replay of the captured response found 27 evidence issues, including flattened PDF
line wraps, across 19 entities, 17 claims and 12 relationships.

## Changes

- `contracts.py` retains strict source-local exact quotation checks, collecting
  entity/claim/relationship citation and identifier errors before rejection. Diagnostics
  include item/entity/identifier indexes, entity name/key, namespace/value, passage IDs
  and bounded quotation samples. At most 12 issues are retained, with the total count.
- Identifier comparison now uses the same trim/case normalization as persistence.
  It does not remove punctuation, derive aliases, rewrite URLs, borrow another
  passage's evidence, or change an original quotation.
- `providers.py` allows one complete correction for typed local evidence failures,
  then repeats exact validation and semantic verification. It explains namespace
  restrictions, retaining document references as ordinary grounded source facts,
  and preserving literal PDF whitespace. Invalid identifiers are not automatically
  published or silently pruned. Persistent failure rejects the candidate.
- Split children and correction calls share the original batch's three-extraction-call
  ceiling. Unrelated provider, authorization and budget failures still propagate.
- Diagnostic recording converts exception objects to their error type before SQL
  insertion, also repairing the existing exhausted-chat diagnostic path.
- Extraction verification requests now include assertion indexes and an explicit
  expected count. Count mismatches retain precise expected/received diagnostics and
  still fail closed. This final prompt change has **local validation only**.
- Answer policy is `grounded-v6-source-identifiers`, suppressing older experimental
  answers without rewriting retained history.
- `code/scripts/lantern_identifier_acceptance.py` provides explicit, isolated acceptance
  with direct accounting against the existing shared ledger, conservative per-call
  reservations, raw local response capture, and cumulative accounting on explicit
  resume. It refuses an existing application database except the same stopped run.

No schema migration, permission relaxation, automatic identity merge, deterministic
fact fabrication or new service was introduced. Publication/staging/activation code
is unchanged.

## Local verification

- **180 API tests passed** on the final code, with one existing Starlette deprecation
  warning. Cases cover exact/missing/mismatched/wrong-passage identifiers, normalization,
  aliases, batch references, combined validation, diagnostic persistence, shared call
  bounds, valid staged activation/provenance, invalid-candidate rollback, immutable
  source versions, permissions, history, search and citations.
- **7 browser workflows passed** in 25.8 seconds, covering conversations/persona,
  source readiness, staged activation/failure and citations.
- Synthetic test assertions remain explicitly synthetic. Captured real-response replay
  reproduces rejection; it does not establish semantic support or authorize activation.

## Real Sonnet result

One fresh application/database was created: `linkmind-lantern-identifier-live`.
The four existing originals were checksum-verified and indexed once. Resumption reused
those exact sources/passages. No new embeddings were requested. All paid reservations
and settlements went directly to `northstar-sonnet-2026-11-12`; no ledger was copied,
seeded, reset, increased or unpaused.

| Check | Observed outcome |
| --- | --- |
| First probe | Parent truncated; completed child rejected unsupported/mistyped identifiers; one correction still left namespace errors |
| Resumed probe after complete feedback/prompt repair | Smaller 3,000-character source bound still needed one truncation split; local correction passed identifier and exact-quote validation |
| Latest candidate | 24 entities, 17 claims, 14 relationships; no accepted strong identifiers |
| Semantic verification | `end_turn`, 123 output tokens; **58 booleans for 55 assertions**, rejected as incomplete/misaligned |
| Activation | Zero entities, claims, relationships or conflicts activated; both staged candidates rolled back |
| Search | All four immutable sources remain Search Ready |
| Chat | Not run: extraction/verification gate failed; zero saved chat turns |

The final assertion-index/count prompt and diagnostics were added after inspecting
the mismatch; no further paid retry was performed. Neither first-batch verification
nor four-document graph/chat acceptance is claimed. Smaller source batches alone did
not eliminate output truncation.

No-model postflight retrieval exercised all eight requested questions and resolved
every returned original citation. Seven searches returned passages from four sources;
the shipment-rule conflict question returned only one source, so conflict-comparison
coverage is insufficient. Other-tenant searches returned no results. These checks
prove access/search/citation safety, not answer accuracy or semantic coverage.

| Budget | USD |
| --- | ---: |
| Before this task's paid calls | 3.09859286 spent |
| Additional paid calls | **0.62187180** across **7 calls** |
| Total recorded spend | **3.72046466** |
| Preserved historical reservations | **0.05661682**, three unknown calls |
| Overall limit | **10.00**, unchanged, unpaused |
| Unspent task authorization | 0.87812820; no further calls dispatched |

Private evidence: `.local/lantern-identifier-live/acceptance.json`, `raw/`,
and `postflight.json`. Originals, extracted text, raw model responses and database
dumps are excluded from this commit.

## Readiness

**Not ready for Main or production rollout.** Local identifier recovery and strict
publication safety are verified, but the real extraction verifier still failed
acceptance, graph activation/chat were not reached, and conflict retrieval coverage
is incomplete. A later focused acceptance must prove complete verifier alignment,
bounded output, activation and all eight grounded answers; remaining budget is not
evidence of success or permission to repeat unchanged failures. Main and all existing
preview data remain untouched; only normal authorized test-ledger accounting changed.
No AWS infrastructure, F2, private-directory, push or deployment work occurred.
