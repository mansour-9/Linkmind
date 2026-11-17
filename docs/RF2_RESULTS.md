# RF2 — Repository, source metadata and evidence

Authorized 2026-11-14 after the user approved the proposed RF2 scope. **Implemented
and validated locally**. Main/previous-preview rollout remains excluded.
Arabic/retrieval/answer-style improvements remain RF3. No paid evaluation, connector
access, main-data rollout or AWS deployment is included.

Implementation scope: reuse documents/versions/passages; add a stable source instance
and native identity, explicit project/team associations, a permission-filtered resource
catalog and search filters, source provenance and a typed local/live evidence contract.
Only uploaded sources are active. Live evidence is validated through offline fixtures;
real connector execution and sync remain RF4. Do not expose nonworking connector tiles.

Use a new isolated mock stack for acceptance. Keep RF1 Sonnet at port 5189 and all
previous source stores/services untouched. No existing corpus reprocessing is required.

## Delivered journey

Open <http://127.0.0.1:5191/content/documents>. Documents is now a paginated resource
library, independent of the capped processing-job list. Search content, display title,
filename or explicit project/team names. Filter by source system, file format, project,
team and received dates. Matching requires no extracted entities, claims or relationships.
Search's passage results support the same metadata filters; its existing entity-type
filter remains an additional optional tool for previously enriched knowledge.

Open **Details**, then **Edit details** to set a display title and deliberately choose
or create a project/team. Equal names do not merge groups. One project and one team
association per document is supported in this slice; these are organizational labels,
not extracted facts or ownership claims. The original filename/content remains intact.
Changes require owner/admin access, retain actor/action audit records and use an
optimistic revision check to reject stale edits. They enqueue no indexing or AI work.

Details shows source, format, access, received time, semantic readiness, original files
and paginated immutable revisions. The source-updated time stays unknown for uploads;
received time is never relabelled as the author's modification time. **Manage source**
opens the existing upload/revision/access controls scoped to that document, including
documents outside the general 200-job list. **Ask about this document** starts a scoped
assistant draft; this new preview honestly remains mock.

## Small storage and evidence contracts

- Migration `0014_repository_metadata` adds source instances, explicit project/team
  groups and document metadata. Existing documents retain all IDs, revisions, evidence,
  graph data and originals. Each organization has a stable uploaded-source instance;
  each document has its own native resource ID. Uniqueness includes tenant and source
  instance; the current persisted resource type is a document. New organizations and
  all existing upload/fixture entry points receive the same identity through one trigger.
- The shared `ResourceIdentity` contract also explicitly includes resource type for
  future adapter evidence. Source identity contains no replaceable connection credentials.
  Native-ID collisions across source instances remain separate. Offline reconnection
  checks preserve identity; **real connector authentication/reconnection is RF4**.
- The permission-filtered source catalog reports only actual retained uploads and their
  indexed/history capabilities, local health, visible resource counts and received/indexed
  times. Live is false, sync time is unknown, and no unavailable connector appears active.
- `/evidence/{existing-passage-id}` keeps its existing response fields and adds typed
  provenance: source-qualified identity, retained revision, exact excerpt/locator,
  observed time, access dependencies and explicit passage-only coverage. Original PDF/
  text/DOCX downloads continue through the retained version reference.
- `SourceEvidence` defines live excerpts **or** actual typed structured fields, original
  URL when supplied, source/observation times and coverage. Offline fixtures validate
  that JSON assignee fields never become fabricated verbatim prose. This adds no live
  endpoint, observation persistence, connector credentials or synchronization engine.
- Group titles/counts are visible only to their creator or through accessible attached
  documents. Current organization/item checks apply to resource lists, metadata,
  history, evidence and downloads. Queries and UI recheck revocation; metadata does not
  expand source access or silently rewrite stored answer dependencies.

No mandatory extraction, new agent framework, universal fact store, graph database,
event platform, managed Spaces or native authoring was introduced. Answer prompts,
Arabic behavior, semantic verification and `grounded-v7-whitespace-anchors` are unchanged.

## Validation

| Check | Observed result |
| --- | --- |
| Full isolated API suite | **231 passed**, one existing Starlette/AnyIO deprecation warning |
| Full browser suite | **32 passed**: prior 29 workflows plus three RF2 journeys |
| Frontend build | TypeScript and Vite build passed inside Docker |
| Final follow-up | All **16 RF2 API checks** passed after strengthening the pagination case to 203 resources; all **3 RF2 browser journeys** passed again after input-framing polish |
| RF2 browser coverage | Metadata editing, deliberate grouping, source-only search filters, original downloads, retained revisions, management navigation, revocation, empty/error/retry and keyboard focus |
| Responsive coverage | 1440, 1024, 390 and 1920px; library, details and edit screenshots; no viewport overflow |
| Live evidence | Offline typed fixtures only; no claim of real connector acceptance |

All **48** pre-existing running container IDs remained unchanged. RF1 source-table
fingerprints and the original cumulative budget matched the captured preflight exactly.
RF2 has no configured Bedrock provider, zero Bedrock usage rows and zero copies of the
original budget run. Running API source hashes match the workspace.

The first full API attempt exposed a test assumption that only the new fixture could
be private. It was corrected to compare permission-filtered counts against each
identity's baseline. The subsequent complete suite passed. Initial UI review also
led to clearer input framing; final targeted checks cover that presentation follow-up.
The preview also includes an explicitly organized **Project Alpha (CB-ALPHA)** example
using the existing fictional benchmark charter/review files. This is a deliberate
validation association, not AI-inferred project membership. Those older fixture files
may already have enrichment; new arbitrary ordinary files still require none.

Metadata-only validation: [RF2_VALIDATION.json](RF2_VALIDATION.json). Raw XML, browser
reports, screenshots and protected-environment fingerprints remain under ignored
`code/.local/rf2-validation/` and `code/e2e/results/`.

## Run the isolated preview

From `code/` in PowerShell, use this project only:

```powershell
$env:BRAIN_WEB_PORT = '5191'
$env:BRAIN_BACKEND_IMAGE = 'linkmind-rf2-backend:local'
docker compose -p linkmind-rf2-validation -f compose.yaml up -d --build --wait
```

No AWS profile/mount/override is present. To run deterministic checks against this
disposable project:

```powershell
docker compose -p linkmind-rf2-validation -f compose.yaml run --rm --no-deps -e PYTHONPATH=/app:/app/apps/api api pytest -q --tb=short apps/api/tests/test_repository.py apps/api/tests/test_repository_migration.py
$env:BRAIN_URL = 'http://127.0.0.1:5191'
$env:BRAIN_E2E_DISPOSABLE = '1'
Set-Location e2e
npx playwright test
```

Main and the 5189 Sonnet preview are older builds/schemas and were not migrated.
Do not apply this migration/build to valuable existing data without the separately
reviewed backup/compatibility/rehearsal/rollback process. Downgrade refuses to discard
non-default identities, groups or edited metadata; it is not a data-loss escape hatch.
RF3 remains planned, including the explicitly deferred Arabic and answer-quality work.
