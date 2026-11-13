# Linkmind frontend rules

## Preserved M3.1 direction and current status

The user approved a complete Glean-inspired redesign on 2026-11-11, using
Linkmind branding, English first, and only working features in navigation.
This supersedes the earlier Royal Blue theme and dashboard references.
The supplied product screenshots and recording are the primary visual references;
exclude marketing navigation, tour overlays, sales widgets and protected assets.

The [main roadmap](IMPLEMENTATION_PLAN.md) now targets production-quality phased
delivery. Current routes/limits below are implemented behavior, not a permanent ceiling
on authoring, Spaces, chat interaction or localization. Native editing and streaming/
cancellation controls must ship with actual backend support, not remain indefinitely
excluded. Preserve useful existing journeys and URLs while evolving them.

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

## Target product UX — planned, not implemented

- Deliver a polished Knowledge Hub: rich editor, safe autosave/edit conflict handling,
  preview, publishing audience, library/discovery, revision comparison/restoration,
  archive and deliberate merge. Reuse existing components where they fit; do not
  limit the product to the current generated entity-page UI.
- Published pages have one primary destination. Preselect the current Space or suggest
  one; authorized general knowledge is the fallback. Drafts require no destination.
  Category/tag/related/duplicate suggestions are optional and permission-filtered.
- Show author/editors, maintainer, AI provenance and optional official revision approval
  distinctly; author is not automatically the person responsible for described work.
- Spaces integrate overview, knowledge, connected resources, people, decisions,
  relationships, meaningful updates and contextual chat. Retain Graph and People;
  graph exploration supports the experience rather than requiring graph expertise.
- Delegate Space creation and suggest accessible similar Spaces without blocking names.
  Show default inheritance or explicitly restricted access, audience previews on publish/
  move, and no permission change from links. Never reveal restricted counts or titles.
- Space chat searches its relevant connected scopes by default; broader search is an
  explicit request or simple enabled option, not repeated tool confirmation dialogs.
- Current operational questions use relevant live tools. Show source, observed time,
  partial coverage and dated fallback honestly. Show actual activity and supported
  cancellation without fabricating reasoning, progress or unavailable integrations.
- Connector administration exposes practical modes/scopes, health, last successful sync
  and actionable errors. Do not expose technical internals unless needed to make a choice.
- Introduce Knowledge Hub, Spaces, Updates, Integrations and later work/agent surfaces
  as working end-to-end capabilities. Do not add empty navigation to imply completeness.
- Arabic/RTL and mixed-direction authoring/evidence require deliberate design and
  keyboard/mobile validation; English remains implemented state, not target-only language.
- Existing conflict review/evidence remains useful; advanced resolution/delegated
  verification workflows are later. No mandatory ordinary publishing approval.
