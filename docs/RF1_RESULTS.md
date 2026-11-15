# RF1 — Default Lightweight Ingestion

> Historical initial mock acceptance below. The later confirmed Sonnet activation,
> 215-test follow-up and bounded real-model evidence are in
> [RF1 AI preview](RF1_AI_PREVIEW.md). Port 5189 now uses that AI build.

Implemented 2026-11-14 at the user's explicit request. **Current source and a new
isolated local preview only; implementation and isolated acceptance complete.** Main and all
existing previews remain unchanged. RF2–RF6 remain planned. No paid inference,
external connection, ledger operation, infrastructure, commit or push occurred.

Preview: <http://127.0.0.1:5189> — `linkmind-rf1-validation`, mock provider, schema
`0013_optional_enrichment`, separate database/originals volumes and backend image
`linkmind-rf1-backend:local`. Do not replace older-schema environments with this image.

## Delivered behavior

- Ordinary uploads, revisions and internal source creation default to **no structured
  enrichment**. No entity/claim/relationship extraction, extraction verification, identity
  resolution or cross-document conflict assessment. This includes recognized fixture
  bytes uploaded through the ordinary path.
- Valid text and stable citation passages become Search Ready **before** embeddings.
  Semantic status stays pending until ready/unavailable/failed. Embedding failure does
  not turn valid source-only content into an enrichment error.
- New jobs finish `ready`, with `enrichment_requested=false`, derived API state
  `enrichment_status=not_requested`, null `processed_at` and no invented graph records.
  `processed_at` retains its successful optional-enrichment meaning.
- Sources display **Ready for search and answers** without an enrichment retry prompt.
  **Manage source → Enrich knowledge → Start enrichment** is explicit/optional, with
  cost/source-use explanation. Existing enriched sources retain **Refresh knowledge**.
- Revisions default off again, even if their predecessor was enriched. Superseded facts
  stay historical; citations, original bytes, attempts and review records remain.
- Labelled graph/Northstar dataset loaders explicitly request enrichment. Exact fixture
  validation and provider/synthetic labels remain; this does not enable ordinary uploads.
  Mock enrichment never fabricates arbitrary facts.
- Indexing reuses compatible exact-text embeddings only within the same tenant/document,
  including completed passage vectors after interruption. Different sources/models/
  dimensions do not reuse them. New revisions keep distinct passage identities.
  Existing metadata/access mutations invalidate directly without extra indexing.
- Pending indexing resumes from published passages without reparsing. Publication, vector
  writes and completion preserve lease/source/tenant/deletion/revision guards.
- New source-only answers avoid null/unused enrichment dependencies. Selected-source
  overviews use text alone, including already enriched sources; empty optional projections
  introduce no generation dependency. These answers survive optional activation but are
  still suppressed after source revision/revocation/deletion.
- Answers supplied entity metadata retain generation checks. Existing saved turns and
  dependency lists are not rewritten. Exact citations, identity/support checks, semantic
  answer verification and `grounded-v6-source-identifiers` remain; no trust relaxation.

## Migration and legacy work

Migration 0013 adds one non-null job-intent boolean. Existing jobs receive `true`,
preserving their prior processing/retry semantics/history; the new-row default is then
set to `false`. A staged candidate requires enrichment intent. No source, revision,
passage, citation, fact, review, attempt or budget record is deleted or reprocessed.

Existing queued jobs are not silently cancelled/reclassified. Review them and actual
provider/accounting configuration before later rollout. The known main inference-guard
mismatch must not become unguarded paid processing.

Downgrade refuses to discard intent after source-only jobs exist: older builds would
misinterpret them. Restore the reviewed consistent DB/originals snapshot and prior build
if required, deciding about post-snapshot writes. Do not bypass the guard or blindly
execute the older 0011-only cutover procedure. No main rehearsal/cutover is included.

## Validation

| Check | Observed result |
| --- | --- |
| Full final API suite | **191 passed**, one existing Starlette/AnyIO deprecation warning |
| New RF1 API coverage | Ordinary/known-byte uploads, PDF/DOCX, lexical-first publication, failure/resume, compatible reuse/isolation, optional intent/access, revision/history, empty-projection dependencies |
| Existing regression coverage | Optional extraction/staging, graph/demo, conflicts/identity, leases/concurrency, permissions/revocation, evidence/history, accounting and conversations/persona retained |
| Migration/rollback guard | Passed: legacy intent, new false default and staged-intent constraint |
| Offline original-PDF checks | Four existing Lantern originals mounted read-only; model/extraction responses explicitly stubbed, not Sonnet acceptance |
| Frontend TypeScript/Vite build | Passed in the isolated Docker web build |
| Final browser suite | **29 passed**, zero failures/skips/flaky tests |
| Responsive/keyboard/visual checks | Browser workflows at 1440/1024/390/1920 px; source-only desktop/mobile, optional action and Processing screenshots inspected |
| Protection/no paid calls | All **40** previously running container IDs unchanged; running RF1 source hashes match the workspace; zero paid model calls/ledger changes |

The first broad API run lacked two private-fixture mount settings and reused an already
enriched idempotent fixture. Final validation supplied the read-only dataset and a
distinct test owner. Legacy graph-focused tests deliberately request enrichment rather
than assume it happens on upload. Lease tests inject at actual lexical publication.

The first browser run passed 28/29. Its remaining assertion expected identical search
candidate lists across first enrichment; graph-assisted ranking can legitimately add
candidates. The corrected test verifies retained original candidates, complete overview
passage IDs, byte-identical download and unsuppressed source-only history. No source
content or safety criterion was weakened to make a model output pass.

## Reproduce safely

Use a **new isolated project/image/port** for independent validation. These commands refer
to the already created RF1 test stack, never main. From `code/` in PowerShell:

```powershell
$env:BRAIN_WEB_PORT = '5189'
$env:BRAIN_BACKEND_IMAGE = 'linkmind-rf1-backend:local'
docker compose -p linkmind-rf1-validation -f compose.yaml up -d --build --wait
docker compose -p linkmind-rf1-validation -f compose.yaml run --rm --no-deps -e PYTHONPATH=/app:/app/apps/api api pytest -q -p no:cacheprovider apps/api/tests --ignore=apps/api/tests/test_lantern_offline.py
Set-Location e2e
$env:BRAIN_URL = 'http://127.0.0.1:5189'
$env:BRAIN_E2E_DISPOSABLE = '1'
$env:PLAYWRIGHT_JSON_OUTPUT_NAME = 'results/rf1-full-report.json'
npx playwright test --reporter=list,json
```

The recorded full API run additionally mounted the ignored `.local/lantern-acceptance`
directory **read-only** at `/lantern-acceptance`, with
`LANTERN_ACCEPTANCE_DIR=/lantern-acceptance`. Without that private dataset, the command
above explicitly excludes its two tests rather than implying they ran. Do not commit
private PDFs, extracted text or dumps. Mock/stub checks are not real-model quality or
production cost/latency acceptance.

The 191 API cases include **11 new RF1 cases**. The initial browser assumption was corrected;
the final full run passed all 29. No implementation change was needed for that assertion.

Local evidence: `code/.local/rf1-validation/api-junit.xml`, protected-container preflight,
and `code/e2e/results/rf1-full-report.json`/screenshots. Final summary is recorded in
[RF1_VALIDATION.json](RF1_VALIDATION.json). No historical budget was reset or resumed.

## Remaining boundaries

RF1 changes the default path. Embeddings still incur processing/cost when deliberately
configured; query/answer verification follows existing rules. There was no paid live
assessment or guaranteed savings/zero-failure claim. Metadata/catalog, adaptive routing,
real connectors/sync and hosted readiness remain RF2–RF6. User visual acceptance remains
separate. Main/existing-preview rollout needs its own reviewed scope/backup/compatibility/
rollback step. RF2 does not start automatically after RF1 acceptance.
