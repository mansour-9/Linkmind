# RF4 — Sources & MCP Connections

## Latest local completion - 2026-11-15

The new [5195 preview](http://127.0.0.1:5195/admin/connections) adds server-owned
encrypted delegated OAuth/refresh state and native scope discovery/selection, with
**315 API / 39 browser / build**, final 8 OAuth checks and persisted demo state after
restart. Real provider setup/consent and real-server MCP testing remain deferred.
Custom MCP retains its separate server-managed contract. See [current results](RF34_RESULTS.md),
[validation](RF34_VALIDATION.json) and [authentication runbook](RF4_OAUTH_RUNBOOK.md).
The 5194 delivery and counts below are the preserved earlier checkpoint.

2026-11-15 follow-up: the user deferred real-server MCP/connector testing until later.
Keep this as an outstanding acceptance gate; do not treat deferral as a passed test
or request account sign-in/URLs during the remaining-work review. Local development
and planning can continue without claiming real-source acceptance.

Implemented locally on 2026-11-15 after the user approved RF4, then explicitly refined
the scope to a functional admin-managed configuration lifecycle. The user will supply
real source URLs later; labelled mock connectors are authorized for this delivery.

**Local management and connector foundation are delivered. Real-provider OAuth sign-in
and real-source lifecycle acceptance remain pending.** No account was connected, real
company corpus imported, paid inference run or AWS infrastructure deployed.

## Review the feature

Open <http://127.0.0.1:5194/admin/connections> as local Amal, or go to **Admin Settings →
Sources & MCP Connections → Manage sources and connections**. The RF4 stack is
`linkmind-rf4-validation`, with separate content/artifact volumes and backend image
`linkmind-rf4-backend:local`. Protected main/RF1/RF2/RF3 services retain their builds.

Add Source supports Jira, Confluence, OneDrive, SharePoint and Custom MCP Server.
Choose **Demo** for the complete local flow without external credentials, or **Real
source** to save provider URLs and explicit scope details for later activation.

1. Save a source name, type, environment and scope. Demo scope choices come from the
   backend options API. Real configuration uses explicit project/space/folder/library
   identifiers; custom MCP additionally stores its endpoint and read-tool contract.
2. Authenticate the configured source. Demo authentication is explicitly synthetic.
   Real authentication uses only a server-owned credential binding; absent provider
   setup returns an actionable unconfigured state. No tokens/passwords are returned
   to or requested through this UI. A real OAuth browser-consent integration is not
   delivered or simulated in this slice.
3. Test connection before enabling. The backend ties a successful test to the exact
   configuration generation and expires its enablement approval after 15 minutes.
   A connection test retains no source content and creates no embeddings/graph.
4. Choose **Live Only**, **Live + Sync** or **Not Connected**. Live Only performs an
   explicit bounded resource read and optional grounded answer without shared indexing.
   Sync collects only the chosen scope using the ordinary worker and source-only jobs.
5. Edit, disable or remove the source. Editing invalidates authentication/testing,
   turns access off and clears outstanding work/access leases. Optimistic generation
   checks reject stale edits. Removing hides the connection and its evidence while
   retaining originals/history. Changing source identity after retention requires a
   new connection, preventing old native IDs from becoming facts of another system.

The fixed demo fixture says it is synthetic and contains no company/source-URL data.
Its live resource ID is **demo-1**. Demo and real source badges are distinct, and
unconfigured sources never appear authenticated or operational. A mock answer remains
labelled verbatim excerpts. Configuration, authentication, test and mode state persist
in PostgreSQL, rather than browser-only state.

## Reused architecture and implemented transports

- Reuse React, existing theme/Sheet/Button/Feedback and Admin navigation; FastAPI;
  PostgreSQL source instances/documents/immutable versions/passages; existing artifact
  storage, citations, audit events, query limits and ordinary worker. No event platform,
  new service, mandatory graph/enrichment pass or extra reasoning provider.
- `connector_transport.py`: bounded HTTPS reads, no credential-bearing redirects,
  redacted failure classifications, call/time/byte bounds, exact host checks and a
  Streamable HTTP MCP client with initialization, tool discovery, explicit read-tool
  allowlists and schema checks. No model-invented tools or write dispatch.
- `connector_providers.py`: Jira project-scoped issue reads and enhanced JQL pagination;
  Confluence space-scoped page reads; shared OneDrive/SharePoint Graph folder traversal
  and original file downloads. Traversal stays inside the configured folder/drive,
  checkpoints page/folder progress and does not crawl the whole drive to filter later.
  Compatible unchanged Graph eTags skip repeated file downloads during collection.
- Optional official Atlassian MCP live reads use server-owned native/MCP credential
  bindings. Native collection remains separate. Microsoft Work IQ was researched in
  the plan but is **not implemented or enabled**; Microsoft document adapters use Graph.
- `custom_mcp.py`: an explicit resource-read contract, required read-only annotations,
  fixed administrator-selected tools, source-scope validation, public-host checks and
  audience-bound server credentials. Arbitrary MCP servers are not assumed compatible.
- `connector_demo.py`: the fixed labelled fixture for all five demo types. It exercises
  the same configuration/mode/retention paths and never calls external services.

## Persistence, revisions and access

Migration **0016_readonly_connectors** adds source connections, connected resources and
retained source record observations. **0017_connection_management** adds authentication,
test-generation and removal state. Existing source text/citation IDs are preserved.
Downgrade of 0016 refuses to discard populated connector history.

Each collection page and its checkpoint commit together under a generation/lease guard.
Interrupted pages resume; duplicate/unchanged content avoids new indexing; older updates
cannot replace newer state; conflicting payloads for an identical source revision fail
closed. Mode/config changes invalidate outstanding workers. A stale worker failure cannot
cancel a replacement lease. Missing list/search results never imply deletion: retained
resources are checked individually for access/existence at a completed scan.

Original document bytes are retained. Jira's typed fields and Confluence's source record
payloads are retained in `connected_revisions`; normalized searchable text is labelled
as a snapshot where applicable. Evidence exposes original URLs, source-update/observation
times and actual fields. Pre-authorized Graph download URLs are not retained or sent
OAuth headers. Unsupported text formats/OCR are outside the core contract.

The initial local access model is **owner-bound and private**, including for connections
created by the demo administrator. Another employee or organization cannot inherit the
administrator's source credential permissions. Production delegated employee/group access
and authentication remain separate release work. There is no team-sharing escape hatch
for connected snapshots.

Common access predicates require an enabled sync connection, matching configuration
generation and a valid resource access lease. Relevant native resources are reauthorized
before retrieval, model dependency use, evidence/download delivery and supported metadata
surfaces. Leases expire after two minutes; authorization uncertainty hides retained data.
Metadata refresh is bounded to 30 relevant resources/40 source calls per request, so this
small local slice does not establish enterprise-scale ACL freshness or completeness.
The trust policy is **grounded-v9-connected-source-access**; exact/semantic checks remain
enabled. This source-access change does **not** repair RF3's two known model-grounding gaps.

## Deliberate limits and activation gates

- Local collection limit: 25 resources per connection; 100 traversed folder IDs; bounded
  page/call/time/response sizes. Broader scopes fail with an actionable limit rather than
  becoming silent complete imports. Default rescan/backoff is five minutes.
- Graph uses folder-scoped traversal/reconciliation, not a delivered delta-feed adapter.
  Original permissions and native pagination/history behavior still need real acceptance.
- Source credentials stay server-side. Configuration persists only nonsecret references;
  no password/token entry, secret-return API or plaintext secret columns were added.
  Optional real-trial deployment bindings are in `compose.rf4-readonly.yaml` and
  `connectors.env.example`; default RF4 has networking disabled and no credentials/AWS mount.
- Real OAuth/consent callbacks, tenant registration and live scope discovery depend on
  the later source URLs/provider setup. The interface explicitly reports this limitation;
  mock authentication is not evidence of real authentication success.
- Custom real MCP compatibility requires read-only annotated `fetch_resource` (or the
  configured read tool) accepting `resource_id`/`scope_id`. It returns original `text`,
  `resource_id`, `scope_id`, `revision`, `updated_at` and same-host HTTPS `url`. Sync also
  requires `list_resources(scope_id,cursor)` returning at most 25 `records`, boolean
  `complete` and `next_cursor` when incomplete. Custom credentials require a matching
  `audience_host`; writes, private-address endpoints and arbitrary tools are excluded.
- Real accounts, tenant-wide access, paid MCP/Work IQ calls, new Bedrock evaluation,
  main rollout and AWS deployment are not activated. The original USD 10 ledger is
  preserved; real model/source acceptance needs its concrete bounded follow-up scope.

## Validation

The full isolated API suite passed **292 tests**, including 28 connector checks.
Final focused checks passed **27/27** after subsequent small fixes. All **37 browser
workflows** and the frontend TypeScript/Vite build passed.
The connector browser workflows exercise all five demo types, real-unconfigured state,
settings navigation, test-before-enable, live non-persistence, selected-scope collection,
edit/removal suppression, owner isolation and responsive layouts. Final observed totals
and protected-environment metadata are recorded in `RF4_VALIDATION.json`.

All **104 pre-existing container IDs** remained unchanged. RF4 has zero Bedrock usage
and zero budget-run copies. The original ledger still records USD 4.1635021600 spent,
USD 0.0566168200 historical unknown reservations and the unchanged USD 10 cap. Five
labelled demo configurations are available in Live Only mode, with no automatic
repository import. Their saved authentication/test state survived an API restart.
RF1/RF2 source fingerprints also match their recorded prior checkpoint. A final
API regression confirms that validation failures do not echo accidentally submitted
secrets or credential-bearing URL input.

Initial browser checks found a missing exact selector label, a live-read button lacking
submit behavior and a stale display name on reconnect. These were corrected. Connector
tests also stopped assuming the disposable database contained no earlier UI-created
configurations; their test scope IDs are isolated and assertions target their own IDs.
Passing mocks establish deterministic lifecycle behavior, not external authentication,
provider compatibility or actual answer quality.

## Run only the isolated RF4 stack

From `code/` in PowerShell:

```powershell
$env:BRAIN_WEB_PORT = '5194'
$env:BRAIN_BACKEND_IMAGE = 'linkmind-rf4-backend:local'
docker compose -p linkmind-rf4-validation -f compose.yaml up -d --build --wait
```

Do not apply this schema/build to protected older previews. Keep configuration and
offline UI testing practical now; supply real URLs and app-owned authorization later
for a separately bounded source trial.
