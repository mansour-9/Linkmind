# Linkmind local development

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

The default provider recognizes the two original samples and the exact benchmark files. Arbitrary files are retained but report **Extraction unavailable**.
Mock chat returns clearly labelled verbatim excerpts, without pretending to perform Bedrock inference.
Local demo tokens deliberately allow identity switching. The API refuses to start unless local demo authentication is explicitly enabled.
Hosted Cognito authentication remains M5.

## Bedrock mode

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

The current account's Sonnet request quota was read as **10 requests/minute**.
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
2. Follow parsing, extraction, embedding and publication in **Processing**.
3. Open **Knowledge Graph**. The documents share the canonical project identifier CB-ALPHA.
4. Open **Content** to inspect separate attributed ownership and launch-date claims.
5. Open **Conflicts** to compare both original sources. Review decisions require a reviewer/admin and a rationale.
6. Ask **Who owns CB-ALPHA in November 2026, and do the sources agree?** in **Home / Assistant**.
7. Open each citation and download the original. The answer must attribute Amal and Omar to their respective documents.
8. Switch to Omar to inspect shared content; Nour belongs to a separate organization.
9. Use source access changes, revisions and deletion to verify immediate server-side invalidation. Saved answers are suppressed if any evidence dependency is no longer current or authorized, or their grounding policy has been superseded.

PDFs must contain selectable text; scanned/image-only pages are reported as unreadable.
DOCX paragraphs and table rows, PDF pages, and text/Markdown lines retain locators.
Limits are 20 MiB per file, 100 PDF pages, 500,000 extracted characters and 1,000 passages.
Text files retain the 5,000-line limit. OCR, images and Excel are later releases.
Original versions are retained; deleting a source removes it from authorized product views and retrieval rather than purging retained storage.

Revisions publish a new current projection atomically only after validation. Older source versions remain available to authorized users.
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

Run deterministic integration tests in an isolated mock-mode database. The cleanup below removes only this generated validation project:

```powershell
$env:BRAIN_WEB_PORT = '5175'
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
old conversation and query cache. Agents and document editing remain deferred.
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

This preserves documents and the database. Hosted storage, managed queues, deployment CDK, authentication and operational hardening remain later milestones.
