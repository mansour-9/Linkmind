# Topic-based source focus — 2026-11-11

> **Historical evidence / compatibility note — 2026-11-14.**
> The dated implementation, checks, budgets and environment observations below are
> retained; they were not rerun or re-scored by this documentation update.
> The [active roadmap](IMPLEMENTATION_PLAN.md) and [scope](PROJECT_SCOPE.md) now
> prioritize source-only ingestion, a durable selected-source repository and bounded
> retrieval. [RF1](RF1_RESULTS.md) subsequently implements default-off enrichment in
> isolated current code; old next tasks/manual or paid commands are not authorization.
> Historical evidence/security/history remains intact; existing environments are unchanged.

Implemented the requested optional source picker. All sources is the default.
Users can enter a project/topic without knowing the filename, inspect actual matching
passages, select multiple documents and apply them. Compact chips support individual
removal and Use all sources. Cancel/Escape does not apply draft selection.

The popup uses existing permission-filtered hybrid passage search, grouped by document,
and supplements it with filename matches. The first relevant passage is shown as an
excerpt. Search is explicitly submitted, avoiding inference calls on every keystroke.
Semantic matches depend on configured embeddings; this change does not introduce a
new retrieval model or promise exhaustive topic recall. Search displays ranked
candidate documents; recent-document browsing is paginated separately.

An additive GET /api/v1/documents endpoint provides current authorized revisions,
filename filtering, pagination and selected-ID metadata lookup. It is independent
of the bounded processing-job list. Access, deletion and current-version conditions
are enforced server-side. No database migration was required.

The existing conversation document_ids array now accepts the multi-select UI (up to
30 sources, the existing API limit). Repeated scope URL parameters retain selection
across refresh. Existing single-scope links remain compatible. Changing an existing
conversation's scope starts a new draft and preserves the unsent question; applying
an unchanged selection keeps the original conversation.

## Validation

- TypeScript and production build passed.
- 27 backend tests passed, including current revisions, source revocation,
  cross-user/organization isolation and pagination over 100 current documents.
- 16 browser tests passed, including topic matches whose filenames do not contain
  the query, multiple-file answer scope, reload, cancel, clear and mobile layout.
- Checked 1440, 1024, 390 and 1920px layouts. Existing chat, source evidence,
  upload/revision, graph and conflict workflows passed regressions.
- Main local app verified after deployment. Existing Bedrock model settings and
  credential mounts were preserved. Validation used a separate mock-mode database.

[Desktop picker](ui/source-focus/desktop.png) · [Mobile picker](ui/source-focus/mobile.png)
· [Browser results](ui/source-focus/browser-results.json)
