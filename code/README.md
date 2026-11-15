# Linkmind local development

> **RF5 local foundation - 2026-11-15.**
> [Ask across sources at 5196](http://127.0.0.1:5196/ask/sources) combines explicitly
> selected saved context with up to two connected resources. Exact passages and typed
> fields use distinct validated references. Results are transient; no live ingestion.
> **341 API / 43 browser / build**, final 3 browser checks passed. Mock only, zero new
> paid usage, same schema 0018, protected older previews unchanged.
> Branch: `rf5/cross-source-journey`; completed source checkpoint:
> `checkpoint/rf1-rf4-local`. See [RF5 results/commands](../docs/RF5_RESULTS.md).

> **Latest RF3/RF4 local follow-up - 2026-11-15.**
> [Preview at 5195](http://127.0.0.1:5195/admin/connections): known RF3 grounding repairs,
> encrypted server-owned native OAuth lifecycle, accessible scopes and five labelled demos.
> **315 API / 39 browser / build**, final 8 OAuth checks and mock retrieval 16/16 passed.
> Bounded Sonnet repair tests cost USD 0.1153449000 from the original shared ledger;
> this preview remains mock and external connector networking is disabled.
> Requires schema **0018**, trust policy v10; all older previews remain unchanged.
> Real provider registration/consent and source trials remain deferred by the user.
> See [results and isolated commands](../docs/RF34_RESULTS.md) and
> [authentication runbook](../docs/RF4_OAUTH_RUNBOOK.md). Earlier blocks below are dated states.

> **RF4 local delivery — 2026-11-15.** [Sources & MCP Connections](http://127.0.0.1:5194/admin/connections)
> now supports a functional admin configuration/auth-state/test/mode/edit/remove lifecycle
> for Jira, Confluence, OneDrive, SharePoint and Custom MCP. Five labelled demo sources
> are available; real URLs/OAuth are pending and networking is disabled by default.
> **292 API / 37 browser / build passed**, plus final 27 connector checks. See
> [RF4 results and isolated commands](../docs/RF4_RESULTS.md). Requires schema 0017;
> preserve all main/RF1/RF2/RF3 builds and their older schemas. No paid calls or ledger changes.

> **RF3 testing — 2026-11-15.** Mock preview: <http://127.0.0.1:5192>.
> Separate Sonnet/Bedrock preview: <http://127.0.0.1:5193>; both require schema 0015.
> **264 API / 34 browser / frontend build passed**; fictional evidence coverage 16/16.
> Eight live prompts cost USD 0.1341612200 from the original shared USD 10 ledger.
> **Two real answers failed source review; RF3 quality acceptance remains open.**
> See [RF3 results, limits and exact runtime commands](../docs/RF3_RESULTS.md).
> AI background uploads are lexical-only/mock; fixture embeddings were explicitly scoped.
> Main/RF1/RF2 builds and data remain protected. RF4 planning is requested; no connector
> account, synchronization, main rollout or AWS deployment is included.

> **RF2 local delivery — 2026-11-14.** New mock preview:
> <http://127.0.0.1:5191/content/documents>. Metadata/content discovery, source/format/
> project/team/date filters, explicit organization, source catalog and original revision
> inspection are implemented. **231 API / 32 browser / build passed**; final RF2 checks
> passed after UI polish. See [RF2 results and isolated commands](../docs/RF2_RESULTS.md).
> Requires schema 0014. RF1 Sonnet at 5189 retains its previous build/schema 0013;
> main/older previews and paid budget remain unchanged. No paid RF2 evaluation occurred.
> Arabic/answer improvements remain RF3, only when requested.

> **RF1 local implementation — 2026-11-14.**
> The user authorized RF1 and isolated validation. New ordinary uploads/revisions now
> default to source-only indexing; Enrich knowledge is optional and explicit. Text is
> searchable before embeddings finish. RF1 preview: <http://127.0.0.1:5189>.
> See [RF1 results](../docs/RF1_RESULTS.md): 191 API tests, 29 browser workflows and
> frontend TypeScript/Vite build passed. Main/existing-preview rollout is pending.
> Existing main/previews have not received these changes. Do not rebuild/migrate them
> without the reviewed backup/compatibility/rollback process. RF1 requires schema 0013;
> the later RF2 build above requires 0014. RF3's later checkpoint is at the top;
> RF4–RF6/connectors remain planned.
> OCR/conversion is upstream/outside the core.
> RF1 authorizes no paid benchmark, live account access, ledger changes or AWS deployment.
> Preserve the Northstar cumulative USD 10 run, unknown reservations and all existing data.

> **Later confirmed AI follow-up:** RF1 at port 5189 now uses Sonnet and the original
> shared spend/pacing ledger. The final Lantern summary passed; 215 isolated API tests
> passed. See [AI preview results and exact recreation commands](../docs/RF1_AI_PREVIEW.md).
> The no-paid boundary above describes the initial RF1 implementation authorization.

This runbook describes the current implemented runtime, not the target capability set.
The [main roadmap](../docs/IMPLEMENTATION_PLAN.md) owns production-quality phased delivery;
[scope](../docs/PROJECT_SCOPE.md) owns product decisions. F1.1 separates searchable
source publication from knowledge enrichment and is validated in an isolated stack.
F1.3 has not been rolled out to the original running application; review the
[F1.1 rollout boundary](../docs/F1_1_RESULTS.md) before updating valuable local data.
F1.2 and F1.3 are implemented locally. The F1.3 preview is
http://127.0.0.1:5181; see [results](../docs/F1_3_RESULTS.md) and the
[historical rollout safety procedure](../docs/MAIN_DATA_ROLLOUT.md). The recorded
2026-11-13 inspection found main at 0010; no RF1 main inspection/cutover was performed.
A future cutover must review the current migration chain through 0015. Existing local/demo
limits are not product ceilings.


Application code lives under `code/`. Planning and durable agent/design rules live in the repository root and `docs/`.

| Folder | Purpose |
| --- | --- |
| apps/web | React, TypeScript, React Flow and shared neutral/indigo theme |
| apps/api | FastAPI, Alembic, parsers, Bedrock, retrieval and tests |
| apps/worker | Leased database-backed processing worker |
| fixtures/benchmark | 12 synthetic documents, expected records and 30 questions |
| e2e | Playwright browser workflow and responsive checks |
| infra/cdk | Reserved for the Python CDK deployment milestone |

## Local mock mode

Start Docker Desktop, then run these commands from this repository:

```powershell
Set-Location 'C:\Users\manso\OneDrive\سطح المكتب\AWS ABA\ABA Project\code'
docker compose up -d --build --wait
```

Open [Company Brain](http://127.0.0.1:5173). The frontend binds only to loopback.
PostgreSQL and original files persist in named volumes. Alembic migrates the existing database before the API and worker start.
Back up the local database before applying migrations to valuable data; early canonical-schema migrations require backup restoration to reverse.

Ordinary readable files become **Search Ready** with **Ready for search and answers**;
enrichment is **Not requested**, including recognized fixture bytes uploaded normally.
No entities/relationships are fabricated or automatically extracted. Explicit labelled
dataset loaders and an authorized **Enrich knowledge** action can request enrichment.
Mock enrichment recognizes exact fixtures only; arbitrary optional enrichment honestly
fails while the source remains searchable.
Mock chat returns clearly labelled verbatim excerpts, without pretending to perform Bedrock inference.
Local demo tokens deliberately allow identity switching. The API refuses to start unless local demo authentication is explicitly enabled.
Production authentication is a release gate in RF6 (legacy F2/H1/M5) and required before real employee access; detailed enterprise group/Space design is deferred.

## Bedrock mode

The user's current [AI testing preference](../docs/AI_TESTING_POLICY.md) is real Sonnet
for meaningful answer/retrieval-quality trials and mock/stubs for deterministic checks.
Real answering can be tested on RF1 without optional graph enrichment or waiting for RF2.
For the existing CLI-login `default` profile, the user can run `aws login --profile default`,
then verify with `aws sts get-caller-identity --profile default --no-cli-pager`.
The session was valid at the 2026-11-14 read-only check; refresh only if desired/needed.
Sign-in does not enable the RF1 provider or unpause a budget. Do not apply a Sonnet
override to its separate database without the shared-accounting layer: initializing a
second run with the same ID does not share the original cap. RF1 now uses
`compose.rf1-ai.yaml` to connect API/worker to the original ledger directly, while
retaining the RF1 content database. Follow the linked RF1 runbook for this preview;
the generic commands below describe a separate local Bedrock configuration.

For the new Northstar test pack and separate mock/Sonnet previews, follow
[COMPANY_TESTING.md](../docs/COMPANY_TESTING.md). Its approved US$10 budget is tied to
one persistent run, not a reusable allowance. The session was renewed and the same
run resumed with explicit approval on 2026-11-13; use the runtime status for current
availability. Do not reset its budget or copy existing F1.1 uploads into it.

AWS CLI sign-in and local SDK access were verified with the default profile and `us-east-1`.
Sign in through your approved local CLI flow when the short-lived session expires. Do not put credentials in this repository.

```powershell
$env:AWS_CONFIG_HOME = Join-Path $env:USERPROFILE '.aws'
$env:AWS_PROFILE = 'default'
$env:AWS_REGION = 'us-east-1'
$env:BEDROCK_EXTRACTION_MODEL = 'us.anthropic.claude-sonnet-4-6'
$env:BEDROCK_ANSWER_MODEL = 'us.anthropic.claude-sonnet-4-6'
$env:BEDROCK_EMBEDDING_MODEL = 'amazon.titan-embed-text-v2:0'
docker compose -f compose.yaml -f compose.bedrock.yaml up -d --build --wait
```

The geographic inference profile can route within US regions. Confirm data-residency requirements before using company data or selecting another profile.
The selected model must support Converse JSON-schema output. There is no silent fallback to an unvalidated extraction provider.
The SDK uses your local profile, with AWS configuration mounted read-only and only the short-lived login cache writable for token refresh.
This override is for local development. Hosted services will use task roles.

The earlier local account quota reading was **10 Sonnet requests/minute**; RF1 did
not recheck AWS quotas or capacity.
A shared PostgreSQL scheduler defaults to nine requests/minute across API and worker processes.
Set `BEDROCK_REQUESTS_PER_MINUTE` only after checking the actual account, model and regional quota.
Extraction, semantic verification and answers use separate recorded calls. A busy queue and provider failures remain visible.
SDK retries are bounded; extraction and answers can each perform one bounded correction pass, followed by evidence validation again.
No infrastructure or quota changes are made by these commands. Real inference incurs provider usage charges.

To return to mock mode:

```powershell
docker compose up -d --force-recreate api worker
```

## Upload-to-answer workflow

1. As Amal, upload `fixtures/benchmark/alpha-charter.md` and `alpha-review.md` with organization access.
2. Follow **Search Ready** and semantic-index status in **Processing**. The sources are
   already usable for search and answers; no enrichment is required.
3. To demonstrate optional graph knowledge, explicitly choose **Manage source → Enrich
   knowledge** on each fixture and confirm **Start enrichment**. Then open **Knowledge
   Graph**. The documents share the canonical project identifier CB-ALPHA.
4. Open **Content** to inspect separate attributed ownership and launch-date claims.
5. Open **Conflicts** to compare both original sources. Review decisions require a reviewer/admin and a rationale.
6. Ask **Who owns CB-ALPHA in November 2026, and do the sources agree?** in **Home / Assistant**.
7. Open each citation and download the original. The answer must attribute Amal and Omar to their respective documents.
8. Switch to Omar to inspect shared content; Nour belongs to a separate organization.
9. Use source access changes, revisions and deletion to verify immediate server-side invalidation. Saved answers are suppressed if any evidence dependency is no longer current or authorized, or their grounding policy has been superseded.

PDFs must contain selectable text; scanned/image-only pages are reported as unreadable.
DOCX paragraphs and table rows, PDF pages, and text/Markdown lines retain locators.
Limits are 20 MiB per file, 100 PDF pages, 500,000 extracted characters and 1,000 passages.
Text files retain the 5,000-line limit. OCR/image conversion is upstream and outside the core text contract; spreadsheet support is a later separately scoped extension.
Original versions are retained; deleting a source removes it from authorized product views and retrieval rather than purging retained storage.

Revisions activate valid lexical text before semantic indexing, without automatic
enrichment. Parsing/publication failure preserves previous content; failed embeddings
leave new text searchable and report degradation. Optional extraction/conflict failure
also leaves text usable; old-source relationships remain historical. Original passage IDs and prior
versions remain available to authorized users. Query-embedding failure falls back to
authorized text matches with an explicit semantic-search diagnostic. Optional enrichment retries
reuse the published passages; RF1 default-off intent does not remove F1.3 staged refresh.
Names alone produce review candidates. Only strong source-backed identifiers or explicit human review establish shared identity.
Same-attribute conflicts consider effective periods. Complementary or historical statements remain separate.
Free-form predicates outside the configured single-valued set are retained without claiming exhaustive contradiction detection.

## AI usage and pricing

The internal **AI Usage** page is restricted to reviewer/admin roles.
It shows model, operation, region, tokens, latency, failures, SDK retries and available configured cost estimates.
Usage is committed independently of publication, including failed calls. Unknown token usage is null, not zero.

No prices are guessed. To enable estimates, set `BEDROCK_RATES_JSON` to a JSON object keyed by region and exact model/profile ID:
`{ "REGION": { "MODEL_ID": { "input": RATE_PER_MILLION, "output": RATE_PER_MILLION, "currency": "USD", "effective_date": "YYYY-MM-DD" } } }`.
Replace rate placeholders with verified regional rates and restart the Bedrock services.
No configured or valid rate means **Cost estimate unavailable**.
Estimates cover token calls; they are not a complete AWS bill.

## Validate

T1's current mock acceptance is 83 API tests and 25 browser workflows. The checked-in
corpus builder is `fixtures/generate_company_demo.py`. Source hashes and expected
records are deterministic; arbitrary edited files remain unavailable for mock AI
extraction. Selected-document summaries use bounded original passages and disclose
partial coverage. New nonfactual greetings do not call a model.

Run deterministic integration tests in an isolated mock-mode database. The cleanup below removes only this generated validation project:

```powershell
$env:BRAIN_WEB_PORT = '5175'
$env:BRAIN_BACKEND_IMAGE = 'linkmind-validation-backend:local'
docker compose -p linkmind-ui-validation up -d --build --wait
docker compose -p linkmind-ui-validation run --rm --no-deps api pytest -q apps/api/tests
Set-Location e2e
npm ci
$env:BRAIN_URL = 'http://127.0.0.1:5175'
$env:BRAIN_E2E_DISPOSABLE = '1'
npm test
Set-Location ..
docker compose -p linkmind-ui-validation down --volumes
$env:BRAIN_WEB_PORT = ''
$env:BRAIN_BACKEND_IMAGE = ''
```

Playwright uses installed Microsoft Edge in headless mode. Browser checks cover upload/revision, conversations, permissions, revoked evidence,
legacy routes, safe Markdown, keyboard interaction and widths 1440, 1024, 390 and 1920.
The suite requires BRAIN_E2E_DISPOSABLE=1 and defaults to the isolated port 5175;
do not point it at valuable user data.
Screenshots, traces and JSON reports are written under `e2e/results/`.
Tests create and remove synthetic demo uploads. The isolated Compose project keeps them separate from the running demo.
The named validation database and artifact volumes are disposable test data.
These tests verify deterministic behavior, not live AI accuracy.

With Bedrock services running, explicitly run the live benchmark:

```powershell
docker compose run --rm --no-deps api python apps/api/tests/benchmark.py --live |
    Out-File -Encoding utf8 ../docs/BENCHMARK_LIVE.json
```

The benchmark makes paid model calls and respects the configured pacing, so it can take several minutes.
It contains 12 documents and 30 questions with a documented automated rubric.
The gold records are a draft pending independent human review. Automated citation-span checks do not establish perfect semantic accuracy. The validation record distinguishes full-run results from targeted checks after later verifier hardening.
See [validation status](../docs/M2_M3_VALIDATION.md) for measured results and limitations.

## Linkmind UI

Primary routes: /, /chat/:id, /search, /graph, /people, /content and /content/graph.
Graph has its own focused workspace at /graph; /content/graph redirects there with
its query values intact. Content retains Knowledge and Documents tabs. Documents
are accessible under Content and /admin/sources. Operational pages are grouped
under /admin. Existing URLs redirect with their identifiers intact.

The Graph explorer uses bounded, permission-checked API search and one-to-three-hop
neighborhoods with 80-node/120-edge response budgets and paginated immediate neighbors.
It expands only on demand, with compact nodes, discovery, a list view and an evidence
inspector. It is not a promise to render the full workspace. Workspace Search supplements
passage results with a connected entity card for exact names and identifiers such as
CB-ALPHA. Chat remains the primary daily answer workflow; no graph-path answer metadata
is invented or added without verified supporting paths.
The profile menu contains the local demo identity selector; switching clears the
old conversation and query cache. Native document editing is planned in K1; agentic workflows are planned in W1/W2. Neither is implemented yet.
See [redesign validation](../docs/M3_1_UI_REDESIGN.md).

## Theme and extension rules

Edit shared colors, Inter typography, spacing and corners in [theme.css](apps/web/src/theme.css).
Reuse [UI primitives](apps/web/src/ui.tsx), the common evidence presentation and the viewer-scoped query client.
Read [frontend rules](../docs/FRONTEND_RULES.md) before adding navigation or flows.
Every visible feature must use real authorized backend data and working actions, with loading, empty and error states.

The API is versioned under `/api/v1`; FastAPI's schema is reachable through the frontend proxy at [OpenAPI](http://127.0.0.1:5173/api/v1/openapi.json).
Routes cover sources, jobs/retries, document revisions/access/deletion/download, Graph, entities, evidence, Search, Wiki, conflicts/reviews/history, identity review, conversations/answers and usage.

## Stop

```powershell
docker compose stop
```

This preserves documents and the database. Hosted storage, deployment CDK, production authentication and operational hardening remain unimplemented; see RF6 in the active roadmap (legacy H1/H2). Managed queues are an evaluated option, not a mandatory migration.
