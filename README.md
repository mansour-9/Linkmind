# Linkmind

Linkmind turns uploaded documents into permission-aware knowledge, a browsable
graph, source-backed pages, and cited AI answers. The current release runs locally
with Docker Compose. English is the current interface language.

## Current checkpoint

The M3.1 interface is implemented: Home/Assistant, topic-based source selection,
Search, People, Content, Graph, and administration. Graph includes progressive
exploration, relationship evidence, and a **Canvas only** fullscreen view.
The optional synthetic graph demo has 38 canonical entities, 76 cited occurrences,
and 105 relationships across two explicitly labeled source documents.

Latest recorded validation: **33 API tests**, **20 browser workflows**, and the
TypeScript/Vite production build passed. These checks establish deterministic
behavior and permissions; live-model quality is tracked separately. See
[Graph validation](docs/GRAPH_EXPLORER_UPDATE.md) and the
[historical knowledge-layer results](docs/M2_M3_VALIDATION.md).

## Run locally

Install Docker Desktop with its Linux engine. From the repository root:

```sh
docker compose -f code/compose.yaml up -d --build --wait
```

Open [Linkmind](http://127.0.0.1:5173). Database and uploaded files persist in
local named volumes. Default mode recognizes the checked-in synthetic fixtures;
arbitrary documents report unavailable extraction until a real provider is configured.
Demo identities are for local testing. Hosted authentication is a later milestone.

For real Bedrock processing, use the opt-in configuration in the
[local runbook](code/README.md#bedrock-mode). It uses your local AWS profile;
real model calls incur provider usage. Default CI uses mock mode and no AWS credentials.

## Repository map

| Path | Contents |
| --- | --- |
| `code/apps/web` | React, TypeScript, Tailwind/Radix and React Flow interface |
| `code/apps/api` | FastAPI, PostgreSQL/pgvector, evidence, retrieval and migrations |
| `code/apps/worker` | Leased document-processing jobs |
| `code/fixtures` | Recognized synthetic samples, benchmark and graph demo |
| `code/e2e` | Playwright workflows and responsive validation |
| `docs` | Architecture, scope, milestones and verified results |
| `.github` | CI and issue/pull-request templates |

## Next milestones

| Milestone | Outcome |
| --- | --- |
| **M3.2** | Reliable document processing, original-source mappings and safe reprocessing |
| M3.3 | Better retrieval and conservative entity resolution |
| M3.4 | Verified multi-hop answers with evidence for every connection |
| M4.1 | One approved read-only Jira integration with original references |
| M4.2 | Persistent sync, freshness, deletion and permission reconciliation |

M3.2 remains **one milestone with two checkpoints**: diagnosis/baseline, then
implementation/validation. Read the [M3.2 plan](docs/M3_2_PLAN.md) and the
[complete roadmap](docs/IMPLEMENTATION_PLAN.md). Jira, named saved graph collections,
additional sources, hosted deployment and Arabic remain future work.

## Development and verification

Read [CONTRIBUTING](CONTRIBUTING.md), [agent guidance](AGENTS.md), and
[frontend rules](docs/FRONTEND_RULES.md) before editing. Run destructive test
workflows only against the named disposable mock environment described in the
[runbook](code/README.md#validate). CI builds the frontend and runs API/browser
regressions in its own isolated Compose project.

Preserve server-side permissions, immutable source revisions, exact evidence and
honest unavailable states. Never commit credentials, local AWS configuration,
uploaded company documents, database exports, or generated dependency folders.

The [original specification](COMPANY_BRAIN_CODEX_MASTER_SPEC.md) and
[original engineering instructions](docs/reference/AGENTS.original.md) are retained
for history; current scope and explicit user decisions take precedence.
