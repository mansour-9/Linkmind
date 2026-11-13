# F1.1 — Independent search readiness

Verified 2026-11-12. **Implemented and validated in an isolated local stack.
Main-data rollout pending.** F1 and M3.2B remain partial: quotation/direction
correction (F1.2) and controlled reprocessing/context generations (F1.3) are planned.

## Delivered behavior

- Valid parsed/indexed source text becomes searchable before extraction and conflict
  assessment. Their failure leaves text available without unsupported graph facts.
- Migration `0009_search_readiness` adds one nullable `search_ready_at` timestamp.
  `documents.current_version_id` selects current source content; `processed_at` retains
  successful enrichment meaning. No new stage service, queue or knowledge store.
- New content activation immediately excludes the previous revision's relationships,
  generated entity views and conflicts from current queries. Historical source passages,
  original downloads, claims, relationships and review records remain stored.
- Existing current-version/permission checks suppress superseded or revoked saved
  answers. Grounded-v3 validation and exact-source/semantic answer checks are unchanged;
  this slice changes publication readiness, not the grounding policy.
- Text/exact matching works without extracted entities. Missing/failed passage
  embeddings and failed query embeddings do not prevent authorized lexical retrieval.
  Per-source index status and query semantic diagnostics disclose degradation; the
  `X-Linkmind-Semantic-Status` response header covers empty results too.
- Content and enrichment publication recheck organization, current/latest revision,
  deletion, lease token and expiry under document/job locks. Enrichment never changes
  the active content pointer. Lease recovery uses job-before-attempt locking.
- Enrichment retries reuse published passage IDs/text/locators and do not reparse or
  re-embed. Already enriched and superseded versions cannot be manually retried.
  Original attempt records remain intact; the existing retry-cycle counter still resets.
- Sources and Processing distinguish **Search Ready**, **Knowledge Enriched**, and
  unavailable/failed enrichment, with a working **Retry enrichment** action. Source
  revision copy explains the content/relationship transition. Shared UI/theme reused.

Sonnet model settings and the separate embedding configuration are unchanged. No
Gemma repair/comparison, paid inference, model change, AWS provisioning or main-data
migration was performed. Arbitrary mock documents get searchable source passages,
honest unavailable enrichment and explicitly labelled verbatim chat excerpts.

## Validation

| Check | Observed result |
| --- | --- |
| Focused pre-change regression | Failed because unavailable extraction left the current content pointer unset |
| Complete API suite on a fresh disposable database | **65 passed**, including 17 new readiness/migration/concurrency cases |
| Complete headless Edge browser suite | **23 passed**, including 3 new readiness journeys |
| Frontend TypeScript/Vite production build | Passed in the web Docker build |
| Responsive/keyboard checks | Browser suite at 1440, 1024, 390 and 1920 px; focused desktop/mobile Processing screenshots visually inspected |
| Additive migration/backfill/reversal | Passed: completed legacy records only; failed retained chunks stay inactive; safe metadata reversal and unsafe downgrade refusal |
| Two independent PostgreSQL sessions | Passed: uncommitted content invisible, document lock blocks concurrent revision insertion, late superseded enrichment rejected |
| Disposable PostgreSQL dump/restore | Passed into `f11_restore_validation`; document/version/passage/claim/relationship/answer/review fingerprints matched |
| Original-file archive restoration | **16 referenced original artifacts** restored to a temporary directory and SHA-256 checked against the restored database |

New regressions cover upload and replacement revision, unavailable/failing extraction,
conflict assessment failure, parser failure, document/query embedding failure, source
revocation/deletion during enrichment, supersession, expired/replaced leases at both
publication boundaries, preserved citations, immutable completion and retry recovery.
One mixed Arabic/English exact-text case validates the fallback path; this is not a
claim of full bilingual relevance quality.

The full suite exposed a pre-existing graph test that assumed all same-name projects
shared an identity. Its name-based assertion now checks the returned entity/graph agree;
its explicit CB-ALPHA lookup still requires the correct specific root. No graph ranking
or identity behavior was changed. New privacy tests are scoped to their own documents
so unrelated fixture content cannot create false failures or false passes.

Generated browser evidence is under `code/e2e/results/` (ignored local artifacts):
`f11-full-report.json`, `screens/f11-1440-processing.png`, and
`screens/f11-390-processing.png`. Visual inspection is agent evidence, not user approval.
The three focused browser journeys also passed again after strengthening the retry
assertion to verify both original attempt records appear in the details dialog.

## Reproduce in isolation

From `code/` in PowerShell:

```powershell
$env:BRAIN_WEB_PORT = '5176'
$env:BRAIN_BACKEND_IMAGE = 'linkmind-f11-backend:local'
docker compose -p linkmind-f11-validation up -d --build --wait
docker compose -p linkmind-f11-validation run --rm --no-deps api pytest -q apps/api/tests
Set-Location e2e
$env:BRAIN_URL = 'http://127.0.0.1:5176'
$env:BRAIN_E2E_DISPOSABLE = '1'
npm ci
npm test
```

The validation stack is left available at http://127.0.0.1:5176 with synthetic data.
Its database, originals, network and backend image tag are distinct from the running
main project. The original application remains at http://127.0.0.1:5173.

## Main-data rollout preview and rollback boundary

The main database was not inspected/migrated during implementation. Before a separately
scoped rollout, stop its ingestion/API mutations and workers, retain the old application
build, take a PostgreSQL custom-format dump and an originals-volume archive, and restore
both to a separate rehearsal database/volume. Use actual main-data counts rather than
the synthetic counts in this report. Preview the readiness backfill:

```sql
SELECT
  count(*) FILTER (WHERE v.processed_at IS NOT NULL) AS enriched_versions,
  count(*) FILTER (WHERE v.processed_at IS NULL AND EXISTS (
    SELECT 1 FROM processing_jobs j WHERE j.version_id=v.id AND j.status='ready'
  )) AS legacy_ready_versions,
  count(*) FILTER (WHERE v.processed_at IS NULL AND NOT EXISTS (
    SELECT 1 FROM processing_jobs j WHERE j.version_id=v.id AND j.status='ready'
  )) AS versions_left_unready
FROM document_versions v;
```

Migration 0009 backfills the first two groups only. It does not move current pointers,
promote failed historical attempts, delete evidence or retry documents automatically.
Preview active pointers and preserve fingerprints of original files, citation IDs,
source locators and reviews. Rehearse upgrade plus authorized search/graph/history and
download checks before applying to the original data. Start API/workers only after the
compatible schema is ready; observe a bounded upload/revision/retry journey.

Metadata downgrade is permitted only with no processing job and no active source-only
revision. Otherwise the migration refuses to drop readiness metadata. After new
source-only activation, rollback requires the reviewed complete database/originals
snapshot and old application, with an explicit decision about post-snapshot writes;
do not silently reactivate older relationships. The disposable dump/archive restoration
above validates the procedure on synthetic data, not recovery of the user's main data.

## Remaining work

- F1.1 main-data rollout and user visual acceptance remain pending.
- F1.2 quotation/format correction and deterministic relationship-direction guards.
- F1.3 controlled index/context reprocessing, activation/rollback and ranking evaluation.
- Independently reviewed representative company questions and an approved Sonnet live
  evaluation budget. Mock checks do not establish factual model quality.
- Original failed private-PDF response bodies remain unavailable; this slice does not
  claim those quotations repaired. Production sign-in, Spaces, connectors and hosted
  release retain their separate roadmap gates.
