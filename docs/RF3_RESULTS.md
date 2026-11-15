# RF3 — Retrieval quality and bounded coordination

## Latest repair checkpoint - 2026-11-15

The user authorized finishing the known grounding repairs. They are implemented in
the new 5195 follow-up with policy v10: complete-statement temporal/authority/freshness
support audits, with ordinary supported present-tense controls preserved. Three new
Sonnet answers passed source review; both captured failure shapes were rejected.
One initial false rejection is retained, with its targeted correction passing.
**315 API / 39 browser / build**, final OAuth 8/8 and mock retrieval 16/16 passed.
See [follow-up results](RF34_RESULTS.md) and [bounded scope](RF34_FOLLOWUP_SCOPE.md).
The original failed outputs/trial below remain unchanged. This establishes bounded
repair acceptance, not independent company-wide quality or production acceptance.

Authorized after RF2 by the user's “do the next one” request. **In progress**.
Arabic/answer enhancements previously deferred to RF3 are now part of this slice.

Focus: bilingual source-only retrieval, direct scoped routes, structure/diversity and
adjacent evidence, bounded expansion and historical-source selection, explicit missing/
ambiguous/verification/provider/budget outcomes, and actual retrieval activity. Keep
exact quotation checks and independent semantic verification. No new extraction,
connector account, sync, production rollout or infrastructure is included.

Use a new isolated local mock preview. Preserve RF1 Sonnet/main/RF2 source stores and
runtime builds. Measure deterministic retrieval baseline separately from real-model
answer quality; prepare a small reviewable Sonnet evaluation rather than assuming
that prior paid allowance authorizes a new autonomous corpus run.

## 2026-11-15 — deterministic acceptance and bounded Bedrock trial

The user explicitly requested starting containers, testing RF3 using real AWS
Bedrock AI, providing the AWS sign-in link, then continuing RF4 planning. AWS CLI
login completed and STS verification succeeded. No AWS infrastructure was deployed.
Concrete files, prompts, operations and stop conditions: [AI test scope](RF3_AI_SCOPE.md).

**Deterministic checks pass. Real-model quality acceptance remains open.** The eight
live prompts completed, but source review rejected two answers containing unsupported
inferences that the semantic verifier had accepted. Do not mark RF3 complete or use
exact citation matching as proof that every generated clause is supported.

## Delivered implementation

- Migration `0015_bilingual_search` adds an Arabic-normalized/simple lexical index
  without changing immutable source text, locators or citation IDs. Bilingual concept
  expansion supplements the existing English/identifier/vector rankings.
- Clear selected-source and explicit-ID routes avoid model planning. Bounded selected
  source context prioritizes role-bearing passages and balances source/version coverage.
  Adjacent evidence retains its own exact passage IDs and authorization checks.
- Explicit previous/current comparison uses retained source revisions; ordinary answers
  continue using current content. Historical dependencies reauthorize and invalidate on
  later revision, access change or deletion. Missing history is explained honestly.
- Per-question limits bound retrievals, planner/model calls, passages/context, request
  bytes and time. Registered fake adapters exercise source selection, bounded fallback,
  tenant/source validation and denial without pretending to be real connectors.
- Arabic/English answer prompts, uncertainty/failure messages, partial-context notices,
  stored-only freshness notices and actual retrieval activity are implemented. The
  trust policy is `grounded-v8-bounded-source-context`; exact citation checks and
  independent semantic verification remain enabled.

The full browser suite exposed an unrelated result for a nonexistent topic because
the simple bilingual index retained English function words such as “no”. Candidate
term generation now excludes `no`, `not` and `such` as standalone expansion hits;
the complete original query and its qualifiers still reach lexical/semantic retrieval
and answering. A real database regression reproduces the failure and checks the fix.

## Validation

| Check | Result |
| --- | --- |
| Final full API suite | **264 passed**, one existing Starlette/AnyIO deprecation warning |
| Final full browser suite | **34 passed**, including two new RF3 journeys |
| Frontend TypeScript/Vite build | Passed |
| Fictional evidence-coverage comparison | Prior baseline **10/16**; intermediate **14/16**; current **16/16** |
| RF3 UI | Long-source Arabic question, actual retrieval activity, exact evidence opening, current-only retrieval and retained-revision comparison |
| Real saved-answer UI inspection | 1440/390px; Arabic previous/current answer and original prior-version citation open; no horizontal overflow, page errors or mutation requests |

The initial full API attempt had six setup failures: two missing `/app` import paths,
two missing Lantern fixture-directory settings, and two processing waits while the
worker was stopped. With `PYTHONPATH=/app:/app/apps/api`, the retained private offline
fixture directory and the mock worker running, the full suite passed. Those fixture
checks use stubs only; the private PDFs were never included in the Bedrock trial.
The final browser suite passed after the bilingual function-word regression fix.

The corpus's `heldout_questions` label is historical test organization. Those authored
questions have been inspected during development and do not establish independent
held-out acceptance, real semantic retrieval precision, production load or quality.

## Actual Sonnet results and remaining quality gaps

| Case | Source review |
| --- | --- |
| Arabic responsibilities from long English notes | Accepted: all three supported roles, original English quotes, partial-context notice |
| Ambiguous “he” follow-up | Accepted: asks for clarification instead of choosing a person |
| English question over Arabic policy | **Rejected**: adds “prior to the requested day”; the source establishes only submission before Thursday |
| Approved decision versus unapproved draft | Accepted: 22 versus 18 December, prior 15 December date, approval/reason and source distinction |
| Arabic previous/current revision comparison | Accepted: Amina/10 December versus Daniel/17 December, with retained citations |
| Three-sentence source summary | **Rejected conservatively**: “project is led by Maya” promotes Product Manager/scope responsibilities into overall project leadership |
| Unsupported annual budget question | Accepted: no factual statements, actionable evidence-gap explanation |
| Current operational question over stored decision | Accepted with wording concern: explicit stored-only notice; answer should say “latest recorded” instead of unqualified “latest” |

All factual output citations matched exact original passage substrings. Each factual
answer also passed the existing model semantic verifier, including the two answers
rejected above. This is a measured verifier sensitivity gap, not a citation-anchor
failure. Original results are preserved; no failed question was repeated, no test was
rescored as a pass and no verification rule was weakened.

Source review accepted **6/8 authored cases**, not a statistical accuracy claim. The
next RF3 quality task is a bounded repair/regression for unsupported temporal modifiers,
role-to-leadership inference and freshness wording. Preserve the failed examples and
valid controls; any trust-rule change needs its policy bump and measured regression.
Independent representative/user acceptance remains outstanding.

## Runtime, cost and protected environments

- Mock regression preview: <http://127.0.0.1:5192> (`linkmind-rf3-validation`).
- Real Sonnet preview: <http://127.0.0.1:5193> (`linkmind-rf3-ai`), separate content DB.
- Inspect the [reviewed Arabic history answer](http://127.0.0.1:5193/chat/2ab11756-087a-436c-95a8-ed973ad655ab)
  or [roles and ambiguity conversation](http://127.0.0.1:5193/chat/7fa85c8d-0c4d-4beb-b793-5da3cbabb6b3).
- Real trial: **62 passage embeddings**, four query embeddings, **14 Sonnet calls**,
  **USD 0.1341612200** actual recorded cost, **99.608 seconds** total. All 80 calls
  settled. Conservative reservation sum was USD 1.19534408, below the USD 1.50 bound.
- Original ledger after trial: cap **USD 10**, cumulative spend **USD 4.1635021600**,
  historical unknown reservations **USD 0.0566168200**, unpaused. No reset, clone,
  increase, unpause or release of unknown reservations occurred.
- The AI content DB contains zero budget runs, zero entities and zero extraction
  usage. The original rates were rechecked against their published AWS price-list
  dimensions and matched. Original Sonnet/Titan model IDs remain configured.
- API uses the original ledger/pacing DB directly through `compose.rf3-ai.yaml`.
  Background worker remains mock/lexical-only; new uploads do not trigger paid indexing
  or enrichment. Only the reviewed fixture scope received paid embeddings.
- **94 protected container IDs remained unchanged**. RF1/RF2 document/version/chunk/
  entity/claim/relationship fingerprints match this turn's preflight. Main and protected
  application builds were not restarted/rebuilt/migrated. Only necessary protected DB
  containers were started for read-only fingerprints and the original shared ledger.

Further user interactive answers consume the same original cumulative cap; AWS sign-in
does not create an allowance. The preview remains experimental with the quality gaps
above. RF4 planning may continue; connector access, sync, main rollout and AWS hosting
remain separately scoped.

Machine-readable metadata: [RF3_VALIDATION.json](RF3_VALIDATION.json). Raw model results,
XML, screenshots, fingerprints and browser reports remain ignored under
`code/.local/rf3-validation/2026-11-15/` and the RF3 AI artifact volume.

## Recreate RF3 only

Mock checks use the existing isolated RF3 project and schema 0015. Do not run these
commands against main, RF1 or RF2. From `code/` in PowerShell:

```powershell
$env:BRAIN_WEB_PORT = '5192'
$env:BRAIN_BACKEND_IMAGE = 'linkmind-rf3-backend:local'
docker compose -p linkmind-rf3-validation -f compose.yaml up -d --build --wait
```

To recreate the existing RF3 AI API against its own content DB and original ledger:

```powershell
$env:BRAIN_WEB_PORT = '5193'
$env:BRAIN_BACKEND_IMAGE = 'linkmind-rf3-backend:ai-v8'
$env:AWS_CONFIG_HOME = Join-Path $env:USERPROFILE '.aws'
$env:AWS_PROFILE = 'default'
$env:AWS_REGION = 'us-east-1'
$env:BRAIN_BUDGET_NETWORK = 'linkmind-company-sonnet_default'
$env:BEDROCK_BUDGET_DATABASE_URL = 'postgresql+psycopg://brain:brain-local@linkmind-company-sonnet-db-1:5432/brain'
docker compose -p linkmind-rf3-ai -f compose.yaml -f compose.bedrock.yaml -f compose.rf3-ai.yaml up -d --no-deps --no-build --wait api
```

The worker is started with the base mock configuration only, without AWS mounts.
Do not rerun `scripts/rf3_ai_check.py`: its completed paid report intentionally refuses
repetition. New real-model acceptance requires a concrete bounded follow-up scope;
remaining headroom alone is not authorization for an automatic rerun.
