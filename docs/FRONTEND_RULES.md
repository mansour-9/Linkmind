# Linkmind frontend rules

Latest UI checkpoint, 2026-11-15: the new 5195 Sources & MCP Connections preview
includes secure provider sign-in initiation, honest registration-pending states,
metadata-only accessible-scope selection and retest-before-enable. Token/client-secret
fields never appear in the browser. Preserve the native OAuth versus explicit MCP
server-auth distinction. **39 browser workflows/build** passed; scope picker and OAuth
setup were visually reviewed on mobile. See [current results](RF34_RESULTS.md).

2026-11-15 RF4: **Sources & MCP Connections** is now a working Admin Settings section
and Admin Console destination at `/admin/connections` in the isolated 5194 preview.
Maintain the add/edit/authenticate/test/enable/disable/remove lifecycle, explicit source
scopes, Demo/Real labels and live/collection health. No browser token/password exposure
or fake real-provider sign-in. Real auth remains clearly unconfigured until supplied;
mock fixtures are labelled and never imply real source access. See [RF4 results](RF4_RESULTS.md).

## Preserved M3.1 direction and current status

The user approved a complete Glean-inspired redesign on 2026-11-11, using
Linkmind branding, English first, and only working features in navigation.
This supersedes the earlier Royal Blue theme and dashboard references.
The supplied product screenshots and recording are the primary visual references;
exclude marketing navigation, tour overlays, sales widgets and protected assets.

## Active product direction — 2026-11-14

The [single roadmap](IMPLEMENTATION_PLAN.md) now prioritizes a unified company
repository, lightweight ingestion, useful search and evidence-based AI. RF1 was later
authorized and is locally implemented: ordinary source-only success, optional Enrich
knowledge/Refresh knowledge, honest semantic status and revised guidance. See
[RF1 results](RF1_RESULTS.md). Remaining target behavior is planned; preserve current
working navigation. No main/existing-preview rollout is included.

RF2 is now implemented locally at port 5191: **Documents is a paginated resource
library**, with content/title/project/team discovery, source/format/group/date filters,
explicit metadata editing and original revision inspection. Sources/Processing keep
their operational role; Manage source deep-links with document scope. See
[RF2 results](RF2_RESULTS.md). RF1 Sonnet/main remain untouched. Arabic/answer-style
enhancements remain RF3; no prompt/Arabic behavior changed in RF2.

Ordinary content must be useful without extracted entities/relationships. Preserve
existing working graph, source evidence and review journeys, URLs and permissions.
Native rich authoring, managed Spaces, detailed enterprise access UX and advanced
graph/conflict workflows are deferred. Their former UX requirements remain preserved
in the [prior scope](reference/pre_restructure_2026_11_14/PROJECT_SCOPE.md).

## Design system

- Use white surfaces, a warm-gray sidebar (#F8F7F7), neutral selected navigation
  (#ECEAEA), near-black text and restrained indigo (#4545F5). Colors are visual
  estimates, not official Glean tokens. Define literal colors in theme.css.
- Retain Inter, a 4px spacing grid, 14–16px interface text and a 16px reading size.
  Desktop sidebar: 280px. Assistant reading/composer width: up to 840px.
- Use neutral rows and quiet controls, minimal borders and shadows. Reserve
  large rounded framing for the composer and source chips rather than every page.
- Keep React/TypeScript, Tailwind, Radix, Lucide, React Query and React Flow.
  Reuse Button, Sheet, Feedback and the shared Evidence source presentation.
- Use semantic controls, visible keyboard focus, accessible labels, Escape and
  focus restoration for overlays. Respect reduced motion and safe areas.

## Current implemented navigation and behavior (M3.1 baseline)

- Primary: Home, Search, Graph, People, Content. Graph is a focused explorer;
  Content contains Knowledge and Documents. Recent conversations are personal
  and live in the shared sidebar. Admin Console
  groups Sources, Processing, Conflicts, AI Usage and Settings. Preserve existing
  owner and role capabilities; grouping pages does not grant or remove access.
- Home is an assistant composer on a white canvas. Conversations have one reading
  column, one scroll area, source citations and a bottom composer. No nested chat
  history sidebar or decorative dashboard cards.
- Use All sources by default. Focus sources opens a centered, searchable picker.
  Search document contents by topic/project and show actual matching excerpts;
  filenames are supplementary. Search is submitted explicitly to avoid embedding
  calls on every keystroke. Support multiple selected sources as removable chips.
  Browse current documents through the paginated /documents catalog rather than
  the processing-job list. Keep source access checks and the API limit of 30 selected
  documents. Empty selection means all accessible indexed sources.
- Keep evidence scope visible. Existing conversation scope is immutable; choosing
  another scope starts a new draft. Preserve backend suppression of saved answers.
- Show work displays actual supplied evidence, separating cited passages from
  additional context. Never simulate searches, progress percentages or reasoning.
- Conversational source suggestions show actual permission-checked filenames and
  distinguish approximate/related matches. Similar matches ask for clarification;
  only the latest turn's source choices are actionable. Choosing a source continues
  the conversation with server-validated context. Help/catalog messages have no
  Sonnet citation label; abstentions are not labelled cited source evidence.
- Render Markdown without raw HTML. Preserve citations per statement. Add no
  streaming, agent controls, document editing or cancellation until supported.
- Keep canonical routes under /chat, /search, /graph, /people, /content and /admin.
  Preserve /content/graph and administrative URLs through redirects and query values.
- Graph is an optional exploration/explanation surface, not the daily answer workflow.
  Chat remains the primary answer experience; Search supplements document passages
  with source-backed entity context for exact project/person/identifier searches.
  Never require users to navigate a graph to get an answer or source evidence.
- Use compact Obsidian-style graph nodes, progressive neighborhood expansion, a
  discovery list and a separate evidence inspector. Do not render the full workspace
  as an unbounded graph. Show loaded versus authorized connection counts honestly.
- Desktop uses a permanent collapsible sidebar, tablet an expandable rail, mobile
  a navigation drawer. Keep knowledge pages, tables and graph usable at 390px.

## Evidence, identity and permissions

- Enforce access on the server. Reset the entire query client on identity changes
  and remove the prior conversation route. Recheck evidence and original downloads.
- Only render successful authorized queries; retained query data after errors must
  not keep restricted content visible. Never invent people, claims or relationships.
- Preserve original filenames, passage locators, version history and provider/demo
  attribution. Clearly distinguish owner-only from organization access.
- Reflect real processing stages and errors. Separate expired AWS credentials from
  source-evidence validation failures. Unknown usage/cost values stay unknown.
- Refresh knowledge is a separate, explained same-source action. Search remains
  available; pending/failed replacement work must not imply that prior verified
  enrichment disappeared. Show retained knowledge only when it actually exists
  on the still-current source. Candidate failure is recoverable through retry;
  do not imply that arbitrary mock uploads received real AI extraction.
- The T1 testing journey labels mock excerpts and Sonnet answers before submission.
  Greetings return nonfactual guidance without fabricated evidence. A selected-file
  overview uses authorized bounded source context even when the question has no
  matching keywords; show partial coverage explicitly. The fictional-company pack
  lives in Sources' sample area with working loading, questions and downloads;
  its private fixture metadata/expected answer are limited to the demo administrator.

## Validation and delivery

- Build/typecheck with npm run build. Run the existing isolated API regressions and
  Playwright workflows covering identity, revocation, upload/revision, citations,
  scope, failures, search, graph and conflict review.
- Compare screenshots at 1440, 1024, 390 and wide desktop sizes; verify no viewport
  overflow, keyboard focus, loading/empty/error states and composer visibility.
- Record implementation evidence separately from the user's visual acceptance.
  User instruction permits independent automated validation and follow-up work
  without waiting for a manual test of every screen.

## Target core UX — planned, not implemented

- Make Assistant, direct Search and the stored resource library useful with zero graph
  facts. Discover by topic and source metadata; do not require exact filenames.
- Uploads/synchronized text finish as usable knowledge after parsing/indexing. Separate
  availability from semantic-index readiness. Optional not-requested enrichment must not
  look failed, incomplete or required. Existing enriched source controls remain supported.
- Inputs already provide readable text/extractable PDFs. Explain unsupported files
  honestly; do not imply Linkmind OCR/conversion capability or add an OCR setup journey.
- Show original source/link, content version where available, source-updated time,
  observed/last-successful-sync time, semantic degradation and meaningful coverage limits.
- Distinguish stored knowledge from live observations. Current operational questions
  use the relevant live source where available; historical questions need dated evidence.
  A dated fallback is not newly confirmed live status.
- Show actual queried sources and inspectable citations. Do not fabricate tool calls,
  progress percentages or private reasoning. Add cancellation/streaming only when supported.
- Source selection/routing should avoid unnecessary configuration for employees. Clarify
  consequential ambiguity; do not ask approval for each authorized read step. Expansion
  remains within the user's selected/enabled scope and server-enforced budgets.
- Broad summaries disclose coverage; ordinary top-passage answers never imply complete
  company/document review. Failed optional enrichment cannot make text unusable.
- Connector administration exposes practical Live Only / Live + Sync / Not Connected
  modes, selected folder/project/channel/repository scopes, health and recovery errors.
  Live Only does not automatically add shared records. Do not add inactive connector tiles
  or claim the app can use Codex's accounts.
- Light project/team/resource grouping may use reliable metadata/explicit links without
  managed Spaces or a rich editor. Similar names and AI guesses are not confirmed links.
- Graph remains optional navigation over reliable links. Do not require a populated
  canvas for upload success, search or answers. Preserve existing graph/People/review
  routes and attribution; changes require a compatible, working journey.
- Keep existing org/owner/source boundaries on titles/counts/previews/history/caches.
  Detailed group/Space access administration is later; do not remove current controls.
- Native authoring, managed Spaces and advanced review/research/actions remain later
  complete journeys. Introduce their navigation only when implemented, not as placeholders.
- Evaluate Arabic/English questions and evidence early. Full Arabic/RTL UI remains an
  explicit later release choice; preserve mixed-direction source identifiers and keyboard/
  mobile accessibility. English is the current interface language.

## Target cost and processing copy

Use plain distinctions: saved/indexed content, semantic search availability, synchronization
and explicitly optional enrichment. Do not expose extraction machinery or internal generation
IDs in the main employee journey. Diagnostic detail belongs in authorized operational views.
Embeddings still have processing/cost; avoid claiming uploads perform no AI work at all.
