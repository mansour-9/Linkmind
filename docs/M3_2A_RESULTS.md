# M3.2A — Baseline and Gemma pilot results

> **Historical evidence / compatibility note — 2026-11-14.**
> The dated implementation, checks, budgets and environment observations below are
> retained; they were not rerun or re-scored by this documentation update.
> The [active roadmap](IMPLEMENTATION_PLAN.md) and [scope](PROJECT_SCOPE.md) now
> prioritize source-only ingestion, a durable selected-source repository and bounded
> retrieval. [RF1](RF1_RESULTS.md) subsequently implements default-off enrichment in
> isolated current code; old next tasks/manual or paid commands are not authorization.
> Historical evidence/security/history remains intact; existing environments are unchanged.
> The old Gemma follow-up suggestion is inactive: ongoing model work is Sonnet-only
> and the historical comparison must not be repeated under this restructure.

Verified on 2026-11-12. **M3.2A diagnostics are complete; M3.2B is proposed, not implemented.**

## Recommendation

Keep the production model unchanged. **Gemma 4 31B is not a drop-in replacement
under the strict-output integration tested here.** All six responses were fenced
Markdown JSON and therefore rejected without repair. That establishes a formatting/
integration problem, not a reliable comparison of intrinsic factual accuracy.
Sonnet also needs processing safeguards: one quotation failed exact validation,
and the common verifier accepted a reversed assignment relationship.

## Frozen experiment and spending

Fixtures, expected records, allowed scoring aliases, source/passage hashes, prompt
and schema hashes were frozen before inference. Commit `7277652` contains that
pre-response checkpoint, based on `m3.1-ui-checkpoint` (`b25f528`). The historical
M3.2 baseline and old live benchmarks were not overwritten. The `manifest_sha256`
inside `frozen.json` hashes canonical JSON; `baseline.json` also records raw file hashes.

The six cases cover simple PDF, PDF typography/wrapping, DOCX tables, Markdown
sections/long text, UTF-8/CRLF, and temporal facts with an untrusted instruction.
Only synthetic content was transmitted. The private PDFs were inspected locally.

| Check | Result |
| --- | --- |
| Inference attempts | **17 / 24 maximum** |
| Estimated token cost | **US$0.12665844 / US$5 projected limit** |
| Gemma extraction | 6 attempts; US$0.00270054 |
| Sonnet extraction | 6 attempts; US$0.10925310 |
| Common Sonnet verification | 5 attempts; US$0.01470480 |
| Unused allowance | 7 verification slots; not reassigned to repairs or extra runs |
| Usage / retries / repair | All 17 attempts accounted for; zero retries and zero repair calls |

Rates came from the official AWS regional catalogs: Gemma Standard US$0.14/0.40
and regional Sonnet US$3.30/16.50 per million input/output tokens. Catalog publication,
SKU, unit conversion and effective dates are retained in `live.json`. The cheaper
global Sonnet rate does not apply to the configured `us.` geographic profile.
Costs are usage-based list-price estimates, not an AWS invoice or billing guarantee.

## Side-by-side results

| Measure | Gemma 4 31B | Sonnet 4.6 |
| --- | --- | --- |
| Strict JSON/schema | 0 / 6 | 6 / 6 |
| Exact quotation gate | Not reached | 5 / 6 |
| Passed existing first-pass model gates | 0 / 6 | 5 / 6 |
| Shared verifier calls | 0, correctly skipped | 5, all returned supported |
| Gold direction errors in admitted output | Not assessable | **1**, despite verifier approval |
| Median extraction latency | 5,288.5 ms | 2,856.5 ms |
| Extraction input/output tokens | 9,301 / 3,496 | 19,687 / 2,684 |
| Cost per matched gold claim/relationship record, including verifier | Undefined: no admitted outputs | US$0.00885414 |

Gemma has no schema-admitted output, so content precision is **not assessed**.
Zero accepted-output recall describes pipeline yield; it does not mean every raw
fact was wrong. Sonnet metrics below are for outputs admitted by its existing gates,
with rejected cases counted as missing expected records:

| Frozen literal/alias metric | Precision | Recall |
| --- | --- | --- |
| Entity occurrences | 100% | 86.67% (13/15) |
| Identifiers | 100% | 86.67% (13/15) |
| Claims | 88.89% | 72.73% (8/11) |
| Relationships | 75% | 66.67% (6/9) |

These are representation-sensitive metrics, not semantic truth scores. For example,
Sonnet's source-supported `target_database` edge is a literal mismatch for frozen
`uses`; that alias was not added after seeing responses. A management fact appeared
as an edge but not a duplicate claim. An additional task-owner claim was outside
the frozen list; that alone does not establish hallucination. The claim/relationship
cost denominator can count two representations of one fact, not deduplicated facts.

Manual source review found the reversed `Omar -> assigned_to -> Validate rollback`
edge conflicts with `GD-M32-101 is assigned to Omar.` The gold direction check caught
it even though all common-verifier booleans were true. The typography output also
normalizes a source quotation over line breaks, making it inexact. Neither defect
was repaired or published by this diagnostic run.

Raw Gemma blocks contain identifiable source-backed entities and relationships;
the typography block also visibly joins line breaks in quotations. Markdown blocks
were not stripped or admitted for automated content scoring. Dates and the injected
Mallory instruction were inspected, but no broad Gemma quality-equivalence claim is made.

## PDF diagnosis

Both existing handover PDFs remain failed with the original exact-quote error.
Checksums match their stored artifacts. Each has three retained passages/pages;
fresh parsing reproduces those passages and locators exactly, with no 2,400-character
boundary split. This does not prove the PDF extractor captured every visual detail.

The invalid model response bodies were not retained. Their precise bad quotations
cannot be recovered. The synthetic regression reproduces the recorded exception
by changing `Project Birch is owned by\nNora.` into a single-line quote. The current
provider raises during local validation before reaching semantic correction. The
live typography case independently demonstrates this failure class on synthetic data.

## Validation and preservation

- **23/23** offline format/limit scenarios passed, including malformed/empty files,
  scanned/encrypted PDFs, page/text/passage/upload limits and exact long-text slices.
- **48/48 API tests** passed in a fresh disposable mock database, including 15 new
  diagnostic tests for strict output, budget reservation, unknown usage, attempted
  budget expansion, no retries, reasoning exclusion, frozen gold and offline default.
- **20/20 existing browser workflows** passed against the isolated mock application.
- Frontend TypeScript/Vite build passed. Both deterministic fixture generators passed.
- All fingerprinted original rows remain identical, including **47 documents and
  635 main-app AI-usage records**. Live pilot usage is in its dedicated ledger, not
  the main database. API/worker/web/database container IDs and configurations match.
- No production app/provider/schema/worker/frontend source was changed or deployed.
  No AWS resources, keys, IAM policies, quotas or model selection were changed.
  The approved `aws login` refreshed the existing expired session.

The comparison is a six-case, single-pass pilot using temperature 0 and Gemma low
reasoning. Both models receive the same prompt/schema text; Sonnet additionally has
native constrained output. Token counts include that interface difference. The
results are not a held-out representative-company benchmark, a Chat-quality test,
or a statistical non-inferiority claim. Do not switch models based solely on price.

## Handoff

Approve [M3.2B](M3_2B_PLAN.md) before implementing evidence mapping, the bounded
correction envelope, relationship-direction safeguards and versioned reprocessing.
Keep Gemma experiments separate until native strict-output compatibility and quality
are validated under a newly approved live-test budget. Existing app behavior remains
available while that work is reviewed.

Artifacts: [baseline](m32/baseline.json), [format matrix/reproduction](m32/offline.json),
[frozen inputs](m32/frozen.json), [raw final outputs and rates](m32/live.json),
[request ledger](m32/ledger.json), [comparison metrics](m32/summary.json),
[PDF inspection](m32/pdf-inspection.json), [main preservation](m32/main-preservation.json),
and [browser report](m32/playwright-report.json).
