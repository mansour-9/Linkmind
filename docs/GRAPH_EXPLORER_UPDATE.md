# Focused Graph explorer and connected Search — 2026-11-11

## Product direction

Chat remains Linkmind's primary daily answer workflow. Workspace Search remains
an ordinary evidence search, supplemented by a connected-entity card for a relevant
exact/near entity name or identifier match. Graph is an optional exploration,
explanation, investigation and demonstration surface, not a required answer step.

The user approved a light Linkmind canvas with compact Obsidian-style colored nodes,
indigo selection, progressive exploration, and a separate evidence inspector.

## Implemented

- Promoted Graph to the primary navigation at `/graph`. Content now has Knowledge
  and Documents tabs. `/content/graph` preserves legacy query values and redirects.
- Full-height three-part workspace: Discover, bounded React Flow canvas, Inspector.
- Compact colored nodes, selected-neighborhood emphasis, quiet edges, radial stable
  positions, fit/reset, optional minimap and a keyboard-usable visible-entity list.
- Entity/identifier discovery across all authorized current entities, not just the
  legacy 150-node graph response. Search result pagination and center-on-entity.
- Per-node expansion, bounded batched root expansion, one-to-three-hop depth,
  entity-type and relationship filters, and visible/authorized connection counts.
- Separate Overview and Connections inspector tabs, source citations, conflict
  indicators, relationship evidence and original downloads via the shared source UI.
- Responsive desktop/tablet/mobile layouts; the inspector becomes a lower panel
  rather than permanently hiding the canvas on small screens.
- Workspace Search shows Project Alpha context for `Project Alpha` and `CB-ALPHA`,
  while broad questions retain ordinary passage search. Claims remain attributed;
  duplicate conflicting claims are not silently resolved by this presentation.

## API contracts

Added under `/api/v1`, leaving the existing `/graph` and `/graph/neighborhood`
contracts and consumers intact:

- `GET /graph/search?q=&kind=&offset=&limit=` — permission-filtered entity/alias/
  identifier search, totals, pagination, incoming/outgoing/connection counts.
- `GET /graph/explore?root=&depth=1..3&kind=&relationship=&offset=&limit=` —
  stable immediate-neighbor pages and bounded breadth-first traversal.
- `GET /graph/overview?q=` — an optional exact/near entity match with its one-hop
  context; returns `null` for broad questions or no suitable entity.
- `GET /graph/relationships` — authorized current relationship predicate choices.

Exploration caps each response at 80 nodes and 120 edges, and each immediate
neighbor page at 40 (24 in the UI). `truncated` is explicit. Variable UUID lists
use SQLAlchemy expanding bind parameters. No schema migration was needed.
Canonical/occurrence/redirect handling, current-version and tenant/source ACL
filters apply to every node, edge, count and conflict indicator. Conflicts use
the existing query requiring both authorized claims.

## Validation

- Frontend TypeScript and Vite production build: passed in the web Docker image.
- Isolated mock backend suite: **30 passed**, including the previous suite and
  focused entity search, dense paging, type filters, overview, UUID binding and
  isolated source-revocation regressions.
- Playwright: **17 passed** on the final clean run. Covers real fixture upload,
  Search connected overview, Graph entry, entity inspection, relationship evidence,
  expansion, recentering, depth filters, list view, legacy links and existing Chat,
  upload, source, conflict and permission workflows.
- Responsive screenshots checked at 1440, 1024, 390 and 1920px, with no viewport
  overflow. Screenshots and JSON report are under `code/e2e/results/`.
- Dense synthetic current-data test: 30 real relationships, stable two-neighbor
  pages, accurate root/leaf counts and a truthful empty type-filter view.
- Main local app was rebuilt with the existing Bedrock Compose configuration and
  local `.aws` mount. Existing database, documents and worker configuration remain.
  Main app: http://127.0.0.1:5173. Tests used a separate disposable Compose project.
- No live model benchmark was run; these results establish deterministic behavior,
  not improved live extraction or answer quality. No AWS infrastructure was created
  or modified. User visual acceptance remains separate from automated validation.

## Deliberate boundary

Chat answer schemas were not changed to claim a connection path. A future Chat
connection preview must use verified source-backed paths with their dependency
checks; it must not infer paths from document text or expose internal canonical IDs.
Per-node collapse and persistent saved graph views are not added in this iteration.
Very large workspaces remain discoverable through bounded exploration, not a single
all-data visualization.

## Larger graph demo completed — 2026-11-12

The main local app at http://127.0.0.1:5173/graph successfully loaded the demo
through **Load graph demo**. Loading it again reused the same two team-visible
documents. No existing user document was deleted or revised.

### Dataset and implementation

- Replaced the broken generator with deterministic entity/relationship declarations.
  `python code/fixtures/generate_graph_demo.py --check` verifies the generated bytes.
- Two explicitly synthetic Markdown documents contain **38 canonical entities**:
  4 projects, 12 people, 6 teams, 8 tasks, 4 decisions and 4 technologies.
  Each appears in both documents: **76 cited entity occurrences**. There are
  **105 distinct source-backed relationships** across the documents.
- Every entity identifier and relationship is present in its exact cited passage.
  Documents retain independent source line numbering. Project keys, task keys,
  synthetic emails and stable synthetic URLs prevent accidental name-only merges.
  Task keys use `GD-…`; `DEMO-ATLAS` finds Project Atlas directly.
- Exact checked-in fixture bytes use `graph-demo-fixture` extraction, including
  when Bedrock is configured. Normal schema and passage validation still run.
  Demo ingestion skips model extraction, embeddings and conflict inference;
  embedding status is explicitly unavailable. Modified bytes use normal processing.
- `GET /api/v1/demo/graph-dataset` reports expected canonical/occurrence counts.
  `POST /api/v1/demo/graph-dataset/load` serializes loading per organization and
  reuses authorized, team-visible matching uploads. `GET …/status` checks actual
  published counts before reporting success. Existing graph/evidence contracts
  and database schemas remain unchanged.
- The loader shows real stages, failures, timeouts and a Processing link. Its
  status popup is anchored below its button and no longer blocks repeat loading.
- The main walkthrough exposed an existing traversal bug: later hops rejected
  every newly discovered neighbor. A narrow backend correction now pages the
  first hop and traverses later hops under the existing 80-node/120-edge budgets.
  The completed Graph components and benchmark fixtures/expectations are unchanged.

### Verified results

| Check | Result |
| --- | --- |
| TypeScript and Vite production build | Passed |
| Fresh isolated mock API suite | **33 passed** |
| Final Playwright suite | **19 passed**, none skipped or flaky |
| Responsive workflows | 1440, 1024, 390 and 1920px; no viewport overflow |
| Main persisted demo | 38 canonical entities / 76 occurrences / 105 relationships |
| Atlas discovery | `DEMO-ATLAS` finds Project Atlas |
| Main Atlas exploration | 12 nodes at one hop; 38 nodes / 78 traversed edges at three hops |
| Shared demo identity | One `amal@demo.linkmind.local` person connected to Atlas and Delta |
| Evidence | `graph-demo-connections.md`, line 51: “Amal contributes to Project Delta.” |
| Original download | Exact byte match with the checked-in synthetic source |
| Main data preservation | Existing documents, versions, entities, relationships, claims and chunks retain identical row fingerprints |
| Main additions / model usage | 45 → 47 documents; **634 → 634** AI-usage records |

Backend tests cover exact evidence, entity kinds, deterministic generation, strict
fixture recognition, no paid calls even in Bedrock mode, cross-document identity,
repeat loading, same-organization reuse, other-tenant denial, graph bounds and
source permissions. Browser tests cover successful/repeated loading, actual
multi-hop growth, source inspection, failure feedback and existing application
workflows. Stronger assertions were added after the traversal bug was observed.

API, worker and frontend were rebuilt in the main app. Deployment inspection found
the API lacked the worker's Bedrock override; both now use the existing worker's
models, region, pacing, pricing configuration and local `.aws` mounts. No AWS
resources or credentials were changed. No live model calls were made by this work.
Main graph verification deliberately used SQL-backed Graph discovery, avoiding
model-powered workspace Search in Bedrock mode. Workspace Search was exercised
only in the isolated mock browser suite.

Artifacts are under [ui/graph-demo](ui/graph-demo/): main verification JSON,
Playwright JSON report, responsive Graph screenshots, before/after traversal
screenshots, and the final Amal/Delta evidence screenshot. Only the disposable
`linkmind-demo-validation` Compose project and its volumes were removed afterward.

This completes the demo loader and its implementation validation. The synthetic
fixture demonstrates navigation and grounding mechanics; it does not measure live
model quality or complete M3.4 GraphRAG. User visual acceptance of the broader UI
and the next milestone's quality baseline remain separate.


## Canvas-only Graph view — 2026-11-12

Added **Canvas only** inside the Graph canvas. It uses browser fullscreen to show
only nodes/relationships and the small canvas controls. **Exit canvas view** or
Escape restores the surrounding navigation, filters and inspector. Existing nodes,
positions, root, selection and URL remain intact; Fit is available to center the
expanded canvas. Opening relationship evidence exits fullscreen to its inspector.
Fullscreen failure is reported explicitly rather than pretending it opened.

The browser regressions also exposed two small existing frontend state bugs:
centering the current root could clear its cached graph, and a fast failed first
answer could have its draft/error cleared by the new-chat navigation effect.
Current-root selection now preserves the graph, and the internally created chat
route preserves the pending send state and retry feedback. No API/schema changes.

Validation: TypeScript/Vite build passed; the final **20/20 Playwright workflows**
passed, including desktop/mobile fullscreen dimensions, Escape, focus restoration,
unchanged node positions and URL, retry behavior, graph demo loading and the four
responsive widths. Backend tests were not rerun for this frontend-only change.
Only the main frontend container was replaced; API, worker and database container
IDs stayed unchanged, preserving Bedrock configuration and user documents. The main
UI walkthrough verified fullscreen entry, Fit, and exit back to the same Amal/Delta
source evidence. No model calls or Jira connections were made.

Screenshots and the browser report are in [ui/graph-canvas](ui/graph-canvas/).
Fullscreen was verified in Chromium/Edge and the in-app browser; other browser
engines remain untested. Only the disposable `linkmind-canvas-validation` Compose
project and its volumes were removed after validation.

The user confirmed **Jira** as the first external source. Current persistence,
original-file evidence, and proposed connector/sync/saved-view tasks are recorded
in [Jira knowledge next steps](JIRA_KNOWLEDGE_NEXT_STEPS.md). The additional user
chat and exact Jira project scope are pending; connector milestones remain open.
