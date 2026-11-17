# RF4 planning draft — Jira, Confluence, OneDrive and SharePoint

Latest follow-up, 2026-11-15: the user authorized continuing local RF3/RF4 work.
The server-owned OAuth lifecycle and metadata scope picker are now implemented and
validated offline at 5195. Actual provider registration/consent and source trials remain
explicitly deferred. See [current results](RF34_RESULTS.md). The planning/delivery
snapshots below remain history; current architecture is documented in the runbook.

**Subsequent implementation authorization/delivery — 2026-11-15:** the user approved
implementation and refined it into Sources & MCP Connections, adding Custom MCP and
requesting functional admin management with explicit mocks until real URLs arrive.
The local feature is delivered at 5194; see [RF4 results](RF4_RESULTS.md). Configuration,
test/auth state, modes, edit/removal, live evidence and selected collection are real
local workflows. Real OAuth/account acceptance is pending. The planning-only paragraph
below describes the earlier stage and is superseded for this local implementation.

Requested 2026-11-15 after RF3 testing. **Planning only**; no account access, import,
sync, AWS infrastructure or connector implementation is authorized by this draft.
The existing [roadmap](IMPLEMENTATION_PLAN.md#8-rf4--read-only-connectors-live-and-persistent)
remains authoritative. RF3 deterministic checks pass, but its two measured grounding
gaps remain open; see [RF3 results](RF3_RESULTS.md). Do not present RF4 planning as
RF3 quality acceptance.

## Agreed coverage and remaining choices

On 2026-11-15 the user requested **all four systems in the RF4 plan: Jira,
Confluence, OneDrive and SharePoint**, and asked whether MCP can simplify delivery.
This supersedes choosing only one system for the planning scope. Implementation
and acceptance should still be staged, with bounded source scopes for each adapter.

The proposed starting scopes are one Jira project, one Confluence space or page tree,
one OneDrive folder, and one SharePoint site/library folder. These are proposals;
no actual site, tenant, project, account type or folder has been selected or accessed.
Microsoft 365 work/school access is the proposed enterprise path; personal OneDrive
compatibility must be checked separately if needed. Codex's connected accounts are
not Linkmind application credentials.

The concrete implementation review should name the source instance, resource scope,
identity/permission model, actual MCP/native capabilities, historical availability,
retention expectations and a synthetic/offline test pack. Do not assume source names
prove identity, list/search results are complete, or a connector supports synchronization
merely because a search/fetch tool exists.

## Verified MCP options — 2026-11-15

| System | Official live-access option | Proposed persistent-collection path |
| --- | --- | --- |
| Jira Cloud | Atlassian Rovo MCP, shared provider with Confluence | Bounded native Jira API reads where MCP cannot prove complete pagination, changes or access reconciliation |
| Confluence Cloud | Same Atlassian Rovo MCP provider; separate resource scope and adapter | Native Confluence API reads where required for complete selected-space/page collection and revisions |
| OneDrive | Microsoft Work IQ MCP is a candidate for supported read-only file paths | Shared Microsoft Graph file adapter, with an explicit drive/folder scope |
| SharePoint Online | Work IQ SharePoint Tools, currently public preview | Same Microsoft Graph file adapter, with explicit site/library/folder scope and separate identity |

Atlassian documents one OAuth 2.1 MCP server for Jira and Confluence at
`https://mcp.atlassian.com/v2/mcp`. It respects the signing-in user's permissions;
some enriched tools consume Rovo credits. This makes it the **proposed simplest first
live-access proof**, subject to the actual site's client/admin policy. It does not
by itself prove the persistent sync lifecycle. See [Atlassian setup](https://developer.atlassian.com/cloud/rovo-mcp/guides/getting-started/)
and [supported tools](https://developer.atlassian.com/cloud/rovo-mcp/guides/supported-tools/).

Microsoft's current Work IQ MCP exposes reads and file-byte fetching alongside
mutation and Copilot tools. Discover supported schemas/paths, then expose only
approved read operations to Linkmind. Use original source records/content for evidence;
do not substitute Copilot's `ask` answers for originals or introduce another reasoning
model. Sonnet remains the application reasoning model. See [Work IQ MCP](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/mcp/overview)
and [tool reference](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/mcp/tool-reference).

The SharePoint Tools require tenant enablement and `WorkIQ.Read` for read-only paths;
`WorkIQAgent.Ask` alone does not expose them. They cover SharePoint content and personal
file context in OneDrive. Availability depends on user permissions and tenant policy;
some v2 CLI setup details are still pending. See [SharePoint Tools](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/sharepoint-iq).
Work IQ API calls have usage-based billing; assess this separately from the Bedrock
ledger before any trial. See [Work IQ access and pricing](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq).
Microsoft advises new projects to use Work IQ rather than its legacy workload-specific
MCP servers: [server options](https://learn.microsoft.com/en-us/microsoft-agent-365/tooling-servers-overview).

**Recommendation, not a selected dependency:** use Microsoft Graph for the RF4 durable
document lifecycle, and evaluate Work IQ MCP for convenient live reads if the tenant
already supports it. Graph offers a common file model for OneDrive/SharePoint and a
delta feed with pagination/checkpoints and deletion markers; those are useful building
blocks, not complete permission reconciliation. See [Graph file model](https://learn.microsoft.com/en-us/graph/api/resources/onedrive?view=graph-rest-1.0)
and [drive delta](https://learn.microsoft.com/en-us/graph/api/driveitem-delta?view=graph-rest-1.0).
Microsoft documents Selected permissions for sites, lists, folders and files with
explicit assignments. Verify that each required listing/delta/permission operation
works under the chosen least-privileged scope; do not silently request tenant-wide
access or assume an incomplete feed is a complete corpus. See [Selected permissions](https://learn.microsoft.com/en-us/graph/permissions-selected-overview).

## Current chat tooling versus application integration

Atlassian Jira/Confluence tools are available in this assistant session; their presence
does not verify any particular site's access or authorize source queries. Plugin catalog
inspection found an available, uninstalled SharePoint connector; a OneDrive-specific
search returned that same entry, not a separate OneDrive plugin. Its exact OneDrive
coverage remains unverified. No account was connected, source content read, integration
installed or permission changed for this planning update. These plugins cannot be
silently reused as Linkmind's backend credentials.

## Proposed delivery slices

1. **Common foundation:** one bounded MCP client/adapter interface, application-owned
   auth/session handling, source-qualified identity, explicit scope enforcement and
   read-operation allowlists. Reuse repository/evidence/access contracts and the worker.
2. **Atlassian:** Jira and Confluence adapters sharing provider/auth plumbing, with
   separate project/space scopes and source identity. Prove live reads, then each source's
   selected-scope collection, history and revocation/recovery contract.
3. **Microsoft documents:** OneDrive and SharePoint adapters sharing Graph file/indexing
   code and Entra plumbing, retaining distinct drive/site/library identities. Prove
   bytes/text, immutable revisions, original URLs and safe incremental collection.
4. **Optional Work IQ live path:** only after actual supported reads, tenant prerequisites,
   original evidence fidelity, pagination/size bounds and additional billing are reviewed.
   No Copilot reasoning dependency or automatic switch away from Sonnet.
5. **Per-source acceptance:** apply all gates below to all four systems. Shared transport
   does not let one source inherit another's permission/history/sync acceptance. RF5 then
   validates the richer combined company journey over accepted adapters.

## Proposed implementation sequence

1. Inspect the selected source's current read-only APIs, account requirements and
   permission/deletion semantics. Prepare the exact app-auth flow without connecting
   until its source/scope/access is authorized.
2. Deliver bounded source search/fetch/current-field evidence with original URLs,
   real field names/types, source-updated and observation times, query scopes and
   denial/outage/rate-limit/empty-result distinctions. Register only supported operations.
3. Prove **Live Only** first: retrieve authorized evidence without adding it to the
   shared index/graph. Use a stored fallback only when its access remains valid, and
   label dated evidence honestly. This is a live gate, not full RF4 acceptance.
4. Add **Live + Sync** for the explicitly selected scope: immutable revisions,
   checkpoints/cursors, pagination, idempotency, restart recovery and changed-content
   indexing. Keep model enrichment off; account separately for necessary embeddings.
5. Reconcile access removal, deletion, scope/mode removal, expiry, partial responses,
   stale/out-of-order updates and missed cycles. **Not Connected** must not bypass
   current access through old answers, history or caches.
6. Validate the full lifecycle offline, then perform a separately bounded real-source
   acceptance with concrete records/questions, calls, runtime and spend limits. Present
   actual evidence and unresolved limitations before considering RF5 or rollout.

## Acceptance gates and outputs

| Gate | Required evidence |
| --- | --- |
| Access and identity | Tenant/source-qualified native IDs; privileged app access does not grant every employee source access; no same-name merging |
| Live | Correct bounded search/fetch, field semantics, original link, observation/freshness, honest denial/outage/empty results, no shared Live Only indexing |
| Persistent sync | Selected data survives restart; cursors/pagination resume; duplicate and older updates cannot overwrite newer complete content |
| Revocation and deletion | Source/access/scope changes revoke every derived/history/cache surface; missing search hit alone never implies deletion |
| Answers | Original exact citations plus independent semantic checks; each requested part covered or explicitly missing; RF3 known qualifier/role errors included in regression |
| Operations | Hard tool/context/time/cost limits; redacted diagnostics; separate sync/index/query measurement; actionable health and last-successful-sync |

The reviewable delivery should include a per-source capability matrix, minimal
compatible persistence changes for that delivered lifecycle, implementation/test plan,
source-mode UI states and a bounded real acceptance plan. Reuse FastAPI, the ordinary
worker, PostgreSQL/pgvector, repository identity and common evidence contracts. No
agent-per-source fleet, speculative permission platform or mandatory graph extraction.

## Open inputs

- Exact Jira site/project, Confluence space/page tree, OneDrive account/folder and
  SharePoint tenant/site/library/folder; start order is proposed, not fixed.
- Which application identity and employee access checks can that source support?
- Which source records, changes, revocations and employee questions will prove value?
- What sync/freshness cadence and retained-history behavior are actually required?

Resolve each source's concrete scope and credential model before implementation or
account sign-in. The provider documentation above is capability research, not a login
instruction or an active connection.
Production sign-in, release security and main/AWS rollout remain RF6/separate reviews.
