# Linkmind

Linkmind is being shaped as a **unified company knowledge repository with intelligent
search and an AI assistant**. It retains selected uploaded/synchronized knowledge,
organizes it lightly and answers employee questions using relevant stored and live
source evidence, with citations and freshness context.

## Direction update — 2026-11-14

The agreed target is lightweight ingestion: **retain → parse/map → index → available**.
Readable text and structured source records do not require complete Sonnet extraction
or a knowledge graph. Entity/claim/relationship enrichment becomes optional/default off;
lightweight links and the graph support discovery. Selected connector scopes persist in
the repository; current operational questions can use live MCP/native tools.

Inputs already provide readable text/extractable PDFs; OCR/conversion is upstream and
outside the core. Detailed enterprise access design, native authoring, managed Spaces
and advanced graph/conflict workflows are deferred; current security boundaries remain.

**RF1 is implemented and validated locally: 191 API tests, 29 browser workflows and
frontend build passed.** Ordinary uploads and
revisions now finish without automatic extraction. Source text is available before semantic
indexing completes; optional enrichment remains explicit. Existing main/previews are
unchanged; live connectors/sync/routing are not implemented. Initial RF1 acceptance used mock.
The subsequently confirmed **Sonnet preview** now runs at port 5189 using the original
shared USD 10 budget. Its Lantern summary passed with citations and semantic verification;
the follow-up API suite passed 215 tests. See [AI preview details](docs/RF1_AI_PREVIEW.md).
The new RF1 preview is at <http://127.0.0.1:5189>; see [results](docs/RF1_RESULTS.md). See [scope](docs/PROJECT_SCOPE.md),
[architecture](docs/ARCHITECTURE_M2_M3.md) and the [single roadmap](docs/IMPLEMENTATION_PLAN.md).

**RF2 is also complete locally:** the new [Documents preview](http://127.0.0.1:5191/content/documents)
supports graph-independent content/metadata discovery, explicit project/team organization,
source catalog, original evidence and revisions. **231 API tests, 32 browser workflows
and frontend build passed**; final RF2 checks passed after presentation polish.
It is mock, incurs no paid usage, and leaves RF1 Sonnet/main untouched. See
[RF2 delivery and limits](docs/RF2_RESULTS.md). Arabic/answer-quality enhancements remain RF3.

## Current local checkpoint

Existing code provides uploads, immutable versions and passage evidence, hybrid search,
cited chat/follow-ups, selected-source overviews, a bounded React Flow graph explorer,
generated entity pages, basic conflict/identity review and model usage/test-spend controls.
The interface is English and runs locally with Docker Compose and demo identities.

M3.1 UI/Graph/canvas is user-approved. F1.1 search-readiness separation and F1.2/F1.3
repairs/staged enrichment are implemented locally; main-data cutover is pending.
Current-source code and existing previews differ in schema/build. Latest recorded Lantern
real-model extraction acceptance failed verifier alignment while source text stayed
searchable; this is not acceptance of the new architecture or a zero-failure promise.

Dated evidence: [F1.1](docs/F1_1_RESULTS.md), [F1.3](docs/F1_3_RESULTS.md),
[Northstar testing](docs/COMPANY_TESTING.md), [persona](docs/ASSISTANT_PERSONA.md),
[Graph](docs/GRAPH_EXPLORER_UPDATE.md), [latest Lantern result](docs/LANTERN_IDENTIFIER_REPAIR_RESULTS.md).
Old test counts/budget figures are historical, not fresh observations.

## Plan, not automatic implementation

| Stage | Intended result |
| --- | --- |
| RF1 — complete locally | Source-only ingestion default; explicit optional enrichment |
| RF2 — complete locally | Repository metadata, source catalog and common evidence; live contract tested offline |
| RF3 | Better retrieval and bounded intelligent source routing |
| RF4 | One accepted read-only connector with live access and selected-scope sync |
| RF5 | A complementary source and complete cross-source company journey |
| RF6 | Measured quality/cost/load, production security and reviewed rollout |

RF1/RF2 local acceptance is complete; RF3 is the next candidate only when requested. First connector and
scope are still to be selected; prior Jira context does not exclude OneDrive/SharePoint.
Keep current data/working capabilities; no graph completion or rich editor prerequisite.
Detailed prior ambitions remain preserved, not silently deleted.

## Run the existing code locally

These commands run the current implementation, not the RF target. Do not rebuild/migrate
valuable main or preview data without the reviewed backup/compatibility/rollback process.
For a fresh local checkout with Docker Desktop's Linux engine:

```sh
docker compose -f code/compose.yaml up -d --build --wait
```

Open [Linkmind](http://127.0.0.1:5173). Database and original files persist in named
volumes. Mock mode recognizes exact checked-in fixtures; arbitrary readable documents
can be searched as text while AI enrichment is unavailable. Mock answers are labelled
original excerpts. Demo identities must not be used for real employee hosted access.

[Local runbook](code/README.md) contains exact isolated validation and opt-in Bedrock
commands. Bedrock incurs charges and needs separately authorized scope; this documentation
update authorizes no calls. Preserve the existing `northstar-sonnet-2026-11-12` USD 10
cumulative ledger without cloning/reset/increase/unpause. No Gemma work is active.

## Repository map

| Path | Contents |
| --- | --- |
| `code/apps/web` | React/TypeScript and shared UI/theme/React Flow |
| `code/apps/api` | FastAPI, PostgreSQL/pgvector, parsing, evidence and retrieval |
| `code/apps/worker` | Existing leased processing jobs |
| `code/fixtures` | Labelled synthetic source content and benchmark fixtures |
| `code/e2e` | Isolated browser workflows |
| `docs` | Active scope/architecture/roadmap, dated evidence and reference snapshots |
| `.github` | CI and contribution templates |

Read [CONTRIBUTING](CONTRIBUTING.md), [agent guidance](AGENTS.md) and
[frontend rules](docs/FRONTEND_RULES.md). Preserve server-side permissions, originals,
revision/citation history and truthful unavailable states. Never commit credentials,
company uploads, private raw model responses or database dumps.

The [original specification](COMPANY_BRAIN_CODEX_MASTER_SPEC.md) and
[original instructions](docs/reference/AGENTS.original.md) are historical. For the
changes and review coverage see [restructure review](docs/RESTRUCTURE_REVIEW_2026_11_14.md).
