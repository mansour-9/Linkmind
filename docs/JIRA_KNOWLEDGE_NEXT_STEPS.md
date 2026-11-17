# Connected Sources and Jira — Supporting Architecture Contract

2026-11-15 update: the user requested Jira, Confluence, OneDrive and SharePoint in
the RF4 planning scope, with convenient MCP options investigated. See the
[RF4 plan and provider documentation](RF4_PLAN.md) for the verified Atlassian Rovo /
Microsoft Work IQ options and proposed native-API sync paths. Delivery is staged and
each source keeps separate scope/permission/lifecycle acceptance. The prior first-source
choice below is historical; exact resources and app authorization remain open.

Updated **2026-11-14**. Supports RF2–RF5 in the [single roadmap](IMPLEMENTATION_PLAN.md).
This is planning only: no application connector, external connection, sync or import
was configured. Old Jira → Confluence → GitLab ordering is superseded as a mandatory
sequence; the first connector/scope is open, with Jira as the previous candidate.

## Purpose

Linkmind retains selected uploaded/synchronized company knowledge and combines it with
relevant live evidence. Jira, OneDrive, SharePoint, Slack, GitLab, Confluence and other
approved systems fit this model. Each source needs actual supported operations and its
own lifecycle acceptance; listing it here is not a claim of delivered integration.

## Current implementation

Uploads, immutable revisions/passages, original downloads, source-only search/chat,
optional graph/entity/review views and source evidence exist locally. RF1 current code
now defaults ordinary uploads/revisions to source-only indexing, with explicit optional
enrichment. Existing preview/main installations remain unchanged. No application Jira/MCP
connector, external persistent sync or adaptive live source router exists. Codex's own
connected accounts are not application credentials. Named saved graph views remain later.

## Shared connector behavior

- Verify app-owned authorization/credentials, source instance identity, approved scopes
  and actual MCP/native API capabilities before implementation. Bulk collection may use
  a different transport from live tools; MCP does not guarantee sync/history support.
- Store tasks/messages/documents as appropriate original records plus searchable text/
  fields, provenance and immutable source revisions/observations. No routine Sonnet
  entity/claim/relationship extraction, graph generation or conflict scan on sync.
- Live Only: authorized scoped reads; no automatic shared index/graph updates.
- Live + Sync: authorized live reads plus durable selected-scope collection/indexing.
- Not Connected: no source calls or cached fallback that bypasses the mode/access policy.
- Configure at a practical folder/project/channel/repository scope. A connection does
  not imply importing everything. Expose health and last successful collection.
- Enforce existing source/tenant boundaries before model use and on evidence/history/
  cache delivery. Full enterprise groups/Space delegation design is deferred, not source
  safety. Privileged sync credentials do not authorize every employee to read all records.

## Routing and common evidence

Use the configured source catalog and question meaning/time/scope. Policies and reports
normally use stored evidence; current issue status/assignee/blockers use the relevant
live source. Historical requests require actual dated history; absent history is a limit,
not permission to infer the past from today's response. Combine sources when needed.

An evidence item preserves organization/source-instance/resource-type/native-ID, original
URL, source revision/update marker when available, observed time, support and coverage.
Support may be a retained excerpt/locator or actual structured field/value. Do not invent
verbatim text for JSON fields. Preserve existing uploaded citation IDs and reauthorize
all answer dependencies. An issue reference is not proof of completion; assignee is not
project owner; similarity alone does not establish a shared identity.

Use bounded direct tools for clear requests and bounded planning for compound questions.
Do not search all connectors by default. No agent per connector, new graph database or
event platform is required. Managed Spaces/native authoring are not prerequisites.

## Persistent collection and refresh

Use the existing worker pattern with idempotent resource/version identity, pagination,
cursors/checkpoints, resume, bounded retries/backoff and source rate limits. Reconcile
changes/deletions/access even without employee queries. A missing search hit does not
prove deletion. Avoid unchanged embeddings and whole-corpus processing.

A live response can answer immediately and request a deduplicated refresh only within
approved sync scopes. Partial/user-filtered payloads cannot replace complete records,
erase omitted fields or overwrite newer state. Refetch when completeness/version/access
cannot be established. Separate source-updated, observed and explicit effective times.

Mode/scope removal stops collection and excludes disallowed material from active use;
historical retention does not grant current access. During outage, dated last-known
fallback is allowed only while access remains reliably valid; authorization uncertainty
forbids it. Live Only citations/history never become shared knowledge automatically.

## First connector and acceptance

Proposed default: prove one useful source end to end, then a complementary document or
project source. Jira remains a prior candidate; OneDrive/SharePoint is a core document-source
class, not blocked behind Confluence/GitLab. Select exact source/scopes/access before work.

For Jira, demonstrate a current issue whose stored status is older: retrieve actual live
fields, cite the issue and observed time, then refresh once if Live + Sync. Separately
prove selected-scope persistence/restart/update history without mandatory extraction.
For a document source, prove selected folder collection, changed versions, original links,
searchable text, unchanged-content reuse and permission/deletion reconciliation.

Live and sync gates are separate. Test two distinct access profiles, expiry/denial,
rate limits/outage, partial pagination, schema errors, injected instructions, duplicated/
reordered updates, missed cycles, revocation/deletion and mode changes. Unavailable source
features must be documented, not simulated. A single API response is not full acceptance.

Actual source access, paid model acceptance and rollout each require their own concrete
authorization. This documentation task configures no credentials, imports or services.
