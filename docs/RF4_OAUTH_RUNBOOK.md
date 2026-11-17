# Sources & MCP Connections — local authentication foundation

2026-11-16 one-shot Atlassian MCP trial: the user completed a separate read-only
PKCE consent for the actual Atlassian MCP service. Four scoped real reads passed in
the clean 5197 runtime. This is a server-managed MCP trial credential, not acceptance
of native-provider OAuth/scope discovery, production delegated employee login or
refresh/revocation lifecycle. Provider-required offline scope was requested, but no
refresh token was retained or used. Credentials stay outside repository/OneDrive.
See [actual results and limitations](REAL_MCP_TRIAL_RESULTS.md).

Implemented in the isolated 5195 follow-up, schema `0018_connection_oauth`.
Real-server testing is deferred by the user. Default external networking is disabled;
no provider registration, account consent or live-source acceptance is claimed.

## Admin journey

1. Open Admin Settings → Sources & MCP Connections → Add Source.
2. Choose a labelled Demo, or a Real source. For native Jira, Confluence, OneDrive
   and SharePoint, the default real authentication method is secure provider sign-in.
3. Save the source. Atlassian needs its site origin; SharePoint needs the site URL.
   A real OAuth source may stay scope-pending until consent and discovery complete.
4. Sign in securely, then choose one accessible project, space, library folder or
   OneDrive folder. Scope discovery reads metadata only. Nothing is imported.
5. Test the selected scope, then explicitly choose Live Only or Live + Sync. Scope
   changes disable access and collection, revoke access leases, and require another test.

The provider can consent to broader API permissions than Linkmind's selected scope.
The UI discloses this; retrieval and collection still enforce the explicit selected
scope and original-source authorization. This local slice is private and owner-bound;
delegated employee access and production application sign-in remain RF6 gates.

## Server preparation for the later approved trial

Use the ignored private environment file with `compose.rf4-readonly.yaml`, applied
only to a separately selected isolated project. The example file contains no secrets.
Do not apply it to protected previews or enable networking during the deferred trial.

- `LINKMIND_PUBLIC_ORIGIN`: exact public HTTPS origin. HTTP loopback is accepted only
  in the explicitly enabled local demo. Never derive the callback from request headers.
- Register the web callback `{origin}/api/v1/connections/oauth/callback` in the
  app-owned Atlassian/Entra application. End users are not asked to create integrations
  or paste API tokens into Linkmind.
- `LINKMIND_OAUTH_PROVIDERS_JSON`: server-only object keyed by `jira`, `confluence`,
  `onedrive`, `sharepoint`; each value has `client_id`, `client_secret`, and Microsoft
  also has the exact `tenant_id` UUID. An absent entry produces honest setup-pending UI.
- `LINKMIND_CONNECTION_KEY_FILE`: mount a private Fernet key outside the database,
  accessible to API and worker. Back it up separately with restricted access. In local
  demo mode only, an atomic private key is created in `/artifacts/connection-secrets/key`
  and reused across restarts. No key or token belongs in tracked files or browser state.
- Networking stays `LINKMIND_CONNECTOR_NETWORK=0` until a scoped real-source trial is
  separately ready. The existing worker remains the only collection mechanism.

Microsoft uses a confidential authorization-code client with S256 PKCE, pinned to
the configured organizational tenant. OneDrive requests delegated Files.Read;
SharePoint requests delegated Files.Read.All and Sites.Read.All; both request offline_access.
Atlassian uses app-owned confidential 3LO with state and offline_access, Jira read:jira-work
or Confluence read:confluence-content.all/read:confluence-space.summary. Its site cloud
ID is verified against accessible-resources and reads use the appropriate Atlassian
API gateway. Real permission/endpoint compatibility must be verified in the deferred trial.

Custom MCP and official Atlassian MCP retain their separate server-owned credential
bindings and bounded read contracts. Arbitrary MCP OAuth discovery/registration is
not implemented; a native provider's consent is not silently reused as an MCP token.

## Persistence, revocation and bounds

OAuth state is random, hashed at rest, bound to an HttpOnly SameSite cookie, owner,
organization, configuration generation and ten-minute expiry. Consumption is atomic
and single use; PKCE verifiers and access/refresh tokens are encrypted. Callback codes
and state are removed from Uvicorn's response-time access log; callbacks return only
a fixed local success/failure redirect with no-store/no-referrer headers. Configure
the same query redaction at any future reverse proxy.

Runtime credentials are resolved by a reserved server-only connection binding that
the configuration API rejects as user input. Audience checks prevent forwarding
OAuth tokens to custom hosts. Expiring tokens refresh under a per-grant row lock;
refresh rotation persists atomically. Invalid consent, unknown keys and denied refresh
fail closed. Reconfiguration/removal delete the grant and pending state. Mode and
verified scope changes retain the same authentication while invalidating access/test
approval and advancing its generation safely. No tokens appear in API listing/errors.

Scope discovery returns at most 25 entries, with explicit truncation and exact-ID
verification fallback. SharePoint library discovery is tied to its configured site;
folder browsing uses read-only Graph metadata. It downloads no documents and never
turns on indexing, embeddings or graph enrichment automatically.

## Verification basis

Controlled offline HTTP transports exercise all four native consent flows, state/
cookie/replay/expiry, PKCE, encryption, refresh rotation, source discovery/selection,
audience mismatch, binding forgery, denied refresh and missing setup. These prove
local protocol/configuration behavior, not real accounts or enterprise ACL acceptance.
See [follow-up results](RF34_RESULTS.md).

Protocol references inspected on 2026-11-15:
[Atlassian 3LO](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/),
[Microsoft authorization code](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow),
[Graph drives](https://learn.microsoft.com/en-us/graph/api/drive-list?view=graph-rest-1.0),
[Graph folder contents](https://learn.microsoft.com/en-us/graph/api/driveitem-list-children?view=graph-rest-1.0),
[Fernet](https://cryptography.io/en/latest/fernet/).
