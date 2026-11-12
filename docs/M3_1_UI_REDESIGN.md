# M3.1 — Linkmind UI redesign

Approved: 2026-11-11. Full interface redesign, Linkmind identity, English first,
working features only. Backend schemas and /api/v1 contracts are preserved.

## Reference review

Reviewed all five supplied Glean screenshots and frames spanning the 76-second
recording: research/read layout, evidence and the document split pane. The latter
remains deferred because the application has no document editor. The public
Glean tour is form-gated; no registration or authentication bypass was attempted.
Geometry and palette are visual estimates, not official Glean tokens.

## Implemented

- 280px warm-gray sidebar, neutral active state, personal recent conversations,
  new conversation, searchable history, profile/workspace and local identity menu.
- Centered Ask Linkmind home and multiline rounded composer; full-height reading
  column and bottom composer for conversations. Personal persistence, scope,
  source suppression and original downloads use the existing APIs.
- Safe Markdown with GFM tables/code, raw HTML disabled, source chips and a shared
  source preview. Show work distinguishes cited passages from additional context,
  without inventing retrieval traces or model reasoning.
- Search rows and filters; real-data People directory; Content library, detail
  pages, source/version history, connected knowledge and React Flow exploration.
- Compact source rows with upload, access and revision management; processing
  stages/attempts/errors; conflict and identity review; aggregated usage table.
- Canonical /chat, /people, /content and /admin routes plus legacy redirects.
- Responsive desktop/tablet/mobile navigation and accessible Radix sheets.

## Engineering

Retained React, TypeScript, Tailwind, Radix, React Query, Lucide and React Flow.
Added react-markdown and remark-gfm for safe Markdown rendering. No backend or
schema changes. Existing local demo authentication remains local-only.
Design tokens remain in theme.css; layout rules are in linkmind.css. Shared
conversation/evidence types are in contracts.ts and the shared evidence body
is used by Graph and the evidence drawer.

## Validation status

- Existing backend regression suite: **25 passed**, isolated mock database.
- Frontend type check and production build: passed during implementation.
- Expanded Playwright suite: **15 passed**, final clean run (approximately 1.1 minutes).
- Responsive screenshots: 1440, 1024, 390 and 1920px, plus expanded evidence and
  source-preview views; no viewport overflow or browser page errors in these checks.
- Verified actual mock-mode API flows: new/follow-up conversations, reload, source
  scope, failed submission/retry, duplicate-submit prevention, personal history,
  identity switching, source revocation, original evidence/download access, Search,
  People/Content/Graph navigation, upload/revision, processing details and conflict review.
- Transport-failure and malicious-Markdown renderer checks use test-only response
  interception; the application itself never substitutes mock responses for APIs.
- Five before screens and 42 final responsive/evidence screens are saved in
  [the visual comparison gallery](ui/m3.1/comparison.html). The gallery also preserves
  the supplied references. [Machine-readable results](ui/m3.1/browser-results.json).
- No standalone lint script exists in the frontend package; the production build
  includes TypeScript checking. These checks are not a formal accessibility audit.
- Existing real Bedrock configuration was retained. No new live-model quality
  benchmark was run; mock regression results do not establish live answer accuracy.
- User visual acceptance remains pending; it is separate from automated results.

No Agents, streaming, cancellation, document editing, new connectors, Arabic,
cloud deployment or fabricated activity has been introduced.

## Fixes discovered during validation

The selected local demo identity now survives refresh within the same tab, and
switching still replaces the query client and resets the current conversation.
Search filter controls have explicit accessible names. Tablet rail expansion works
independently of desktop collapse state; profile and Admin remain bottom-aligned.
Removed conflicting old shell/home CSS rather than accumulating layout patches.

## Independent follow-up completed

[M3.2 baseline manifest](M3_2_BASELINE.json) records backend/test/fixture hashes,
the existing draft 12-document/30-question benchmark, and measured mock regressions.
Historical live results are explicitly labelled and were not rerun. No processing,
retrieval, schema or cloud change was made. The real PDF failure reproduction and
representative-data quality acceptance remain future work.

## Local handoff

The redesigned app runs at http://127.0.0.1:5173. Only the frontend container was
replaced; the existing live backend, worker, database and documents were preserved.
The final test suite used the separate linkmind-ui-validation Compose project with
its own mock backend, database and artifact volume. Its fixtures are disposable.
The repeatable commands are in code/README.md.

User instruction allows completing independent automated work without waiting for
manual screen tests. M3.1 implementation and automated validation are complete;
visual preference acceptance is not falsely recorded on the user's behalf.

## Checkpoint approved — 2026-11-12

The user approved the current UI, Graph demo and canvas-only follow-up, then
requested M3.2 planning and a GitHub checkpoint before backend implementation.
The latest follow-up build and 20 browser workflows passed; Graph-demo validation
previously passed 33 API tests. This records acceptance to proceed with planning,
not completion of later live-model quality or hosted-release gates.
