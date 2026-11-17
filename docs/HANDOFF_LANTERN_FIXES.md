# New-agent handoff: Lantern extraction and chat validation

> **Superseded execution handoff — 2026-11-14. Do not execute this task list.**
> Retained as historical diagnostic/authorization context. Later results are in
> [Lantern repair](LANTERN_REPAIR_RESULTS.md) and [identifier evidence](LANTERN_IDENTIFIER_REPAIR_RESULTS.md).
> The [active RF roadmap](IMPLEMENTATION_PLAN.md) now prioritizes source-only
> ingestion/retrieval; graph/extraction acceptance is not a core prerequisite.
> This documentation request does not resume repairs, paid tests, F2 or rollout.
> Old environment/commit/ledger values below must not be treated as current state.

Prepared 2026-11-13. This is execution context for a focused repair, not a second
roadmap. `docs/IMPLEMENTATION_PLAN.md` remains the active roadmap. The latest user
request below supersedes older paid-test permissions for this repair.

## Task and authorization

Fix both failures **before F2**, using the existing architecture:

1. Split large-document extraction into smaller bounded batches; keep the algorithm
   simple. Record the actual Bedrock stop reason and distinguish truncation, blocking,
   malformed output and other errors. Validate entities, claims and relationships
   before activation. Preserve F1.3 staging, atomic activation and rollback.
2. Identify the exact rejected answer citation, quote or internal ID. Attempt bounded
   correction; if evidence validation still fails, return a clean, helpful
   insufficient-evidence response. Never display unsupported statements as verified.
3. Use the four Project Lantern PDFs for acceptance: extraction, relationships,
   cross-document retrieval, conflicting information, citations, and continued search
   availability when enrichment fails. Run local tests first.

**No additional paid AWS calls without fresh user approval.** An unpaused ledger or
remaining funds is not approval. Do not retry the live jobs, start a paid worker,
run a live benchmark, repeat the historical Gemma comparison, reset/increase/unpause
the budget, provision AWS resources, or modify IAM/quotas. Sonnet is the only permitted
model for later approved model-backed checks. Do not touch `private/`.

**Do not change the main data environment.** Implement and test in a new isolated
mock stack. Report root causes, actual changes and honest test results before asking
for rollout approval. Paid acceptance approval and rollout approval are separate.
Do not start F2, native authoring, Spaces, connectors, infrastructure, a new conflict
engine, an agent platform, or unrelated product work.

The user asked the previous agent to prepare this context for a new agent; that agent
has not implemented these repairs or made paid calls for this investigation.

## Repository and checkpoints

- Workspace: `C:\Users\manso\OneDrive\سطح المكتب\AWS ABA\ABA Project`
- Application/Compose working directory: **`code/`**, not the repository root.
- Shell: PowerShell on Windows; Docker Desktop and Python 3.12 are available.
- Branch: `m3.2/baseline-gemma`. The branch name is historical; do not use Gemma.
- Latest commit: `834ddc2` — use **Linkmind** as the assistant name.
- `0aeb7b0`: conversational persona, natural short help, guarded social replies.
- `36cd16c`: F1.3 staged enrichment, atomic activation/rollback, additive migration 0011.
- `4028a16`: checkpoint of F1.1/F1.2, company testing and conversational discovery.
- `4704d4f`: semantic answer-verdict rejection returns insufficient evidence instead
  of throwing. This did **not** close every exact-citation/internal-ID error path.

No push/merge to main is requested. Commit only this repair and its evidence; preserve
pre-existing edits. At handoff the following tracked files were already dirty:
`AGENTS.md`, `COMPANY_BRAIN_CODEX_MASTER_SPEC.md`, `CONTRIBUTING.md`, `README.md`,
`docs/JIRA_KNOWLEDGE_NEXT_STEPS.md`, `docs/M3_2B_PLAN.md`, `docs/M3_2_PLAN.md`.
Several old `docs/company_demo/` reports are untracked too. Do not reset, delete,
rewrite or sweep those unrelated changes into your commit.

Read first: `AGENTS.md`, `docs/PROJECT_SCOPE.md`, `docs/IMPLEMENTATION_PLAN.md`,
`docs/ARCHITECTURE_M2_M3.md`, `code/README.md`, `docs/F1_3_RESULTS.md`,
`docs/MAIN_DATA_ROLLOUT.md`, and `docs/ASSISTANT_PERSONA.md`. Read frontend rules before
changing error copy/UI. Use the AWS Python SDK and Bedrock skills when applicable.

## Critical environment distinction

| Project / address | Current role | Schema / boundary |
| --- | --- | --- |
| `company-brain` / 5173 | Original main app | Observed 0010; protected, no rollout |
| `linkmind-company-sonnet` / 5175 | User's actual Lantern uploads and chat | 0010; persona-only compatible image |
| `linkmind-f11-validation` / 5176 | Earlier F1.1 preview | Preserve its data |
| `linkmind-company-mock` / 5177 | Existing fictional-company mock preview | Preserve |
| `linkmind-conversation-validation` / 5180 | Earlier conversation preview | Preserve |
| `linkmind-f13-validation` / 5181 | Current F1.3 isolated mock implementation | 0011, with staging/live-fact views |

Re-inspect current state before acting. The Sonnet API/worker currently use
`linkmind-company-sonnet-backend:persona`. Their three Compose files are
`compose.yaml`, `compose.bedrock.yaml`, `compose.company-sonnet.yaml`.

**Do not deploy the normal current-source image onto schema 0010 with `--no-deps`**:
it expects the F1.3 columns/views. Do not silently migrate 5175 to solve that mismatch.

`code/scripts/build_persona_preview.py` is another important trap: it reconstructs
`providers.py` and `conversational.py` from **commit 4028a16**, then patches persona
behavior. Merely fixing current HEAD and running this helper would restore old
extraction/citation behavior in the preview. If a later rollout targets 5175, review
and test the compatibility/backport strategy explicitly; do not blindly reuse it.
Existing `.local/persona-preview-build` files are generated, not the authoritative code.

The original main stack also has a known inference configuration mismatch: its API
advertises the Northstar budget but its database has no run row, and its running
worker lacks the run guard. Do not use main for paid validation or initialize another
USD 10 ledger there. This is documented in `docs/MAIN_DATA_ROLLOUT.md`; it is not
permission to alter the original stack during this repair.

## Actual observed failures

All four PDFs are current, **Search Ready**, and have ready embeddings. Their original
text exists in the index. None has accepted enrichment; each job failed on attempt 1.

| File | Version prefix | Passages | Extraction input tokens | Extraction output tokens |
| --- | --- | ---: | ---: | ---: |
| `01_Project_Lantern_Discovery_Charter.pdf` | `3052c3f6` | 8 | 5792 | **6000** |
| `02_Project_Lantern_Decisions_Meetings.pdf` | `2b81a313` | 8 | 5813 | **6000** |
| `03_Project_Lantern_Engineering_Design.pdf` | `51b70242` | 9 | 6015 | **6000** |
| `04_Project_Lantern_Pilot_Readiness.pdf` | `70895df3` | 10 | 6040 | **6000** |

Every extraction usage row is `failed`, `error_code=ValueError`; the job message is
`Model response was incomplete or blocked.` Current extraction output limit is 6000.
The processor batches by a fixed **8 passages**, without bounding the combined text
or the expected structured-output size.

**Strongly supported inference:** output truncation. All four requests ended exactly
at the configured output maximum. **Not confirmed:** the actual Bedrock stop reason,
because it was not persisted. Do not claim moderation/guardrail blocking from this
generic message, or retrospectively manufacture a stored `max_tokens` result.

For `what is Lantern ?`, usage shows a query-understanding call followed by an answer
and bounded correction, each with structured-call status `success`, but no subsequent
answer-verification call. The same pattern appears in two recent attempts. The UI
reports `Answer unavailable (ValueError). No unverified answer was saved.`

**Supported inference:** local validation after response parsing and before semantic
verification rejected the answer/correction: exact citation/quotation checks or the
internal-ID check. **Unknown:** the precise rejected quote/ID. Failed model answer
content and the detailed local validation exception were not saved. Do not invent
the rejected quote or claim that the chat error itself was output truncation.

Enrichment failure must not be used as an explanation for why raw-text chat cannot
work: F1.1 intentionally supports retrieval/answers from searchable, unenriched text.
Fix the chat validation/error path independently.

## Acceptance dataset — ready for offline use

The previous agent downloaded all four immutable originals through the authenticated
local preview and verified their SHA-256 and byte counts against source metadata.
No source records were changed and no model calls were made.

**Local copies:** `.local/lantern-acceptance/` at the repository root.
**Manifest:** `.local/lantern-acceptance/manifest.json` contains filenames, full source,
document/job IDs, checksums, byte counts, passage counts and observed status.
The directory is ignored by Git. Treat these as user/company documents: do not commit
PDFs, extracted private text, full model responses or dumps to the repository, and do
not send their contents to Bedrock before fresh paid-call approval.

Operational IDs, not source facts to show in answers:

| File number | Version ID | Job ID |
| --- | --- | --- |
| 01 | `3052c3f6-5f36-452e-b401-df97c760bb67` | `f6d6fecb-cbf2-4fef-a8e3-9f3591c8a91f` |
| 02 | `2b81a313-73ba-4cad-82da-837cd12b3e07` | `3d4985f5-211d-47bc-8c36-de57c1de4a60` |
| 03 | `51b70242-8666-411c-bd58-4f3d775ca027` | `c9fddd05-0458-429e-bd97-f87a2fe4608d` |
| 04 | `70895df3-7a54-4cfe-b846-6aca7ba63add` | `83971b43-f4ce-4efc-8f0f-de0b1654e1e1` |

If this handoff moves to another machine/workspace, obtain the ignored dataset from
the user or the authorized preview; do not assume those files are tracked in Git.

Offline checks can parse the actual PDFs, inspect batching/coverage, derive reference
expectations from original passages, and test validation/publication with explicit
stubbed provider results. They **cannot establish real Sonnet extraction/answer
quality**. Do not register arbitrary Lantern PDFs as a fake production mock fixture
and report that as real-model acceptance. Fresh real-model checks remain gated on
approval, with their results reported separately from deterministic tests.

## Code map and implementation guidance

### Extraction and provider diagnostics

- `code/apps/api/app/processing.py`: `enrich()` currently uses
  `range(0,len(passages),8)` and prefixes model-local keys before combining batches.
  Retries of search-ready sources reuse original passages/embeddings.
- `code/apps/api/app/providers.py`: `structured()` sets 6000 output tokens for
  extraction, 3000 for ordinary answers, 1024 for verification, with separate 512/256
  limits for query understanding/conversational verification. It accepts only
  `end_turn`/`stop_sequence`, then throws the generic error for every other stop.
- `record()` writes independent `ai_usage` records with operation/model/tokens/error,
  but does not persist stop reason or the exact local answer-validation failure.
- `_extract_verified()` performs exact/schema validation and a semantic check with
  one correction; current HEAD rejects incomplete verifier verdicts rather than
  treating all assertions as supported. Preserve that fail-closed behavior. The
  older preview provider is not identical to HEAD because of the persona backport.

Prefer small ordinary functions: bound both passage count and estimated input size,
keep passage IDs/locators intact, limit assertions/output size, and permit only bounded
split/retry behavior for genuine truncation. Define maximum depth/call count so one
document cannot start an unbounded paid loop. An estimate is not measured token usage.
Do not solve this solely by raising every output limit, accepting partial JSON, or
increasing the USD 10 allowance. Distinguish truncation from content/guardrail blocking,
malformed output, auth, throttling, budget refusal and schema/evidence failures.

### Answer validation and diagnostics

- `providers.answer()` currently catches broad `ValueError`, retries `_answer_once()`
  once with feedback, then lets a second validation exception reach the API's 503 path.
- `_answer_once()` checks internal canonical IDs and calls `validate_citations()`
  before semantic `AnswerVerdict` verification.
- `code/apps/api/app/contracts.py::validate_citations()` currently raises only
  `Evidence is required` or `Evidence quote does not exist in its passage`.
- Semantic verdict rejection already returns `GroundedAnswer(statements=[],
  insufficient_evidence=True)`. Extend graceful final handling to genuine local
  evidence-validation failures without swallowing unrelated provider failures.
- `code/apps/api/app/main.py::ask()` converts uncaught failures to the generic red 503.

Use typed/structured validation diagnostics with statement/citation indexes and the
relevant passage/quote/internal-ID details. Keep diagnostic data protected by tenant,
conversation and source access; never dump full private answers or credentials into
shared logs. Client copy should be useful, not an internal traceback. Distinguish
source evidence failure from expired credentials, paused budget and provider outage.
After bounded correction is exhausted, discard unsupported statements and return an
honest helpful abstention; never relabel an unsupported answer as verified.

### Publication, retrieval and current product behavior

- `enrichment_staging.py`, `processing.publication_guard()` and migration
  `0011_staged_enrichment.py` own candidate verification, live-pointer activation,
  rollback, revision/lease/tenant guards and generation foreign keys.
- `live_entities`, `live_claims`, `live_relationships` select the active generation.
  Raw historical facts/evidence remain retained. Current source selection remains
  independent of enrichment selection. A newer source cannot borrow old relationships.
- `retrieval.py`, `conversational.py`, `main.py` enforce source permissions and
  source/generation dependencies on answers/history. Current policy is
  `grounded-v4-staged` on HEAD; the older Sonnet preview has its legacy policy.
- `assistant_persona.py` is the shared persona. Name is **Linkmind**, not Link9.
  Preserve brief friendly English/Arabic conversation and light emoji use. Familiar
  greetings/help need no model call; nontrivial social replies have a separate check.
- `SourceControls.tsx`, `IntelligencePages.tsx`, `ui.tsx`, `api.ts` show processing,
  errors, refresh/retained facts and retry. Use shared primitives/theme for changes.

If grounding acceptance rules change, review/bump the validation policy so older
experimental answers are not silently trusted. Do not rewrite immutable history.

## Tests, baseline and isolated commands

Relevant tests: `test_grounding.py`, `test_extraction_verdict.py`,
`test_staged_enrichment.py`, `test_staged_concurrency.py`, `test_staged_migration.py`,
`test_search_readiness.py`, `test_readiness_concurrency.py`, `test_conversational.py`,
`test_assistant_persona.py`, and browser `search-readiness.spec.ts`,
`staged-enrichment.spec.ts`, `conversational.spec.ts`, `persona.spec.ts`.

Last broad current-source run: **141 API tests passed**. Persona work also passed
43 schema-0010 compatibility tests and four browser workflows. The subsequent
name-only correction passed eight focused no-network tests and HTTP identity checks.
F1.3 previously passed 127 API/28 browser tests and a synthetic restore rehearsal.
These are baseline evidence, **not proof that the Lantern PDFs currently pass**.

Use a unique project/image/available port. From `code/`, for example:

```powershell
$env:BRAIN_WEB_PORT = '5185' # verify availability first
$env:BRAIN_BACKEND_IMAGE = 'linkmind-lantern-validation:local'
docker compose -p linkmind-lantern-validation -f compose.yaml up -d --build --wait
docker compose -p linkmind-lantern-validation -f compose.yaml run --rm --no-deps -e PYTHONPATH=/app:/app/apps/api api pytest -q -p no:cacheprovider apps/api/tests
```

Use **only base `compose.yaml`** for mock validation; do not add Bedrock overrides.
Inspect/refuse reuse of valuable existing projects/volumes. Never use the shared
default backend image tag for an experimental build. Do not delete another preview's
volumes. Mount the exported acceptance PDFs read-only into this isolated test stack.

From `code/e2e/`, use the matching mock URL and disposable flag:

```powershell
$env:BRAIN_URL = 'http://127.0.0.1:5185'
$env:BRAIN_E2E_DISPOSABLE = '1'
npx playwright test
```

Add meaningful regression cases for truncated output, split coverage/key mapping,
bounded retries, guardrail/no-retry classification, exact diagnostics, final clean
abstention, unsupported-output suppression, staging rollback, cross-document identity/
conflicts, historical citations, revocation, and search availability. Do not weaken
verification just to make expected answers appear.

## Budget and paid-acceptance gate

Read-only snapshot at handoff:

- Run: `northstar-sonnet-2026-11-12`, in `linkmind-company-sonnet` database.
- Limit: **USD 10**, spent **USD 2.7746513600**, reserved **USD 0.0566168200**.
- Unpaused. Re-read before proposing a paid pilot; values may change from user use.
- Three historical unknown reservations were retained. Do not release them or claim
  zero cost without evidence and authorization. Do not copy/create a fresh run in a
  new database or change/reset the run ID to get more headroom.

`inference_budget.py` reserves before dispatch, settles known usage, and pauses while
retaining uncertain reservations. Preserve it, including budgeted one-attempt SDK
configuration, independent usage accounting, pacing and authorization before dispatch.

**Do not run** `f13_live_probe.py`, `company_live_check.py`, `benchmark.py --live`,
paid retry scripts or a Bedrock worker as part of local testing. Earlier permission
for a completed probe is not permission for this repair's additional calls.

After local tests, present a bounded real-Lantern acceptance proposal: exact target
stack, files/questions, maximum calls and correction/split limits, estimated maximum
additional spend within the existing cap, and stop conditions. Obtain explicit paid
approval before execution. Do not present stubbed checks as completion of the user's
real-model acceptance criteria. If necessary, finish the local implementation report
with paid acceptance explicitly pending; do not ask for rollout as if it had passed.

## Required final report

1. Confirmed causes vs inferences, including the newly recorded actual stop reason.
2. Changes made and how they preserve exact evidence, permissions, staging/rollback.
3. Local automated results and offline Lantern coverage, separate from any later
   approved real-model results; include actual failed/blocked gates.
4. Cross-document facts/relationships/conflicts and citation acceptance evidence,
   with private content kept in ignored local reports.
5. Spend/ledger changes (zero during unapproved local work), deployment/schema state,
   and a concrete rollout/rollback proposal. Main and existing preview data remain
   untouched until the relevant rollout is approved.
6. Scoped commit(s), remaining limitations and exactly what needs approval next.
