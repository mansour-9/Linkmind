# Organization-managed source connections

User requirement clarified November 17, 2026. This is the agreed target design and implementation plan, not a claim that shared-employee authorization or durable service authentication is already shipped. The working 5197 source-boundary repair remains installed.

## Intended user experience

An organization admin adds Jira, Confluence, OneDrive/SharePoint or a supported custom MCP source. The connection belongs to the organization and remains configured across user sessions and server restarts. Employees authenticate to Linkmind, ask questions and use only the sources granted to them. Employees do not configure upstream connectors or supply the admin's credentials. Logging out of Linkmind does not disconnect an organization source.

Connection lifetime and access-token lifetime are separate. Linkmind should obtain replacement access tokens automatically using a provider-supported service identity or retained grant. Credentials can still be revoked or require rotation under provider policy; no integration can promise permanent access against revocation or provider requirements. Reconnection/rotation is an admin workflow and does not prompt every employee.

## Authentication choices

| Provider | Preferred organization connection | Current limitation |
|---|---|---|
| Atlassian MCP | Service-account OAuth 2.0 client credentials, scoped to selected sites and read/search agent-interface tools. Obtain 60-minute access tokens automatically before expiry. | Existing trial uses temporary interactive PKCE and discards refresh tokens. Service-account credential creation/configuration and automatic token acquisition are not implemented in Linkmind's MCP path. |
| Microsoft business OneDrive/SharePoint | An Entra application/service identity with admin-consented application permissions; obtain Graph tokens without employee interaction. Prefer provider-supported certificate/federated identity where suitable. Scope selected sites/drives/folders and Linkmind grants explicitly. | Existing native delegated OAuth code is not equivalent to organization application authentication. Consumer OneDrive or unsupported endpoints need separate capability evaluation. |
| Custom MCP | Use the server's documented service credential, client-credentials flow or persistent renewable admin grant. Preserve exact host, read-tool allowlist and scope boundaries. | MCP does not guarantee one universal authentication or expiry mechanism. Unsupported unattended auth must be reported clearly. |

Atlassian announced service-account client credentials for MCP on November 12, 2026. It does not require enabling organization-wide API-token authentication. Service accounts require appropriate app/site roles and read/search agent-interface scopes plus read:me and read:account. API tokens remain an alternative with provider-defined expiration and admin enablement; they are not required for this design.

Primary sources:

- [Atlassian MCP service-account support](https://developer.atlassian.com/cloud/rovo-mcp/changelog/)
- [Create Atlassian service-account OAuth credentials](https://support.atlassian.com/user-management/docs/create-oauth-2-0-credential-for-service-accounts/)
- [Microsoft Graph application access without a user](https://learn.microsoft.com/en-us/graph/auth-v2-service)

## Access model

Upstream authorization uses the connector's service identity. It does not automatically apply the asking employee's individual Jira/Confluence permissions. Linkmind must enforce explicit organization, employee/group, source and item boundaries on its own shared knowledge surface.

The admin chooses permitted projects, spaces, drives/folders and read-only capabilities, then grants those sources to all employees or selected groups/users deliberately. Default sharing is not inferred from the admin's personal upstream access. Group-sensitive or restricted original items require source ACL mapping or narrower separately granted connector scopes; absent a mapping, fail closed for the restricted content.

The same grant resolver must gate discovery, live reads, retained/synced records, graph/evidence views, source suggestions, synthesis, original links and saved conversations. A change to membership, scope or credential generation invalidates the relevant authorization/cache dependencies. Shared credentials never reach employee browsers, prompts, citations or logs.

The current prototype has owner-bound connection checks in connectors.owned, chat_agent.connections and retained-source access predicates. Removing owner_id filters alone would expose excess data. Employee sign-in is still the local demo identity mechanism; production employee authentication and group membership integration are separate required work.

## Implementation sequence

1. Add explicit organization-managed connection ownership and employee/group source grants. Preserve existing owner-managed connections and their source identifiers by default; do not share them automatically during migration.
2. Centralize connection-use authorization separately from admin-only credential/configuration management. Apply it to every retrieval, retained-source, history and citation path.
3. Add secure server-side service credential storage and provider-specific token acquisition. Coordinate renewal with per-credential locking, expiry buffers, bounded retries and secret redaction. Persist credential bindings independently of process memory and employee sessions.
4. Add the organization-admin source setup/share/health/rotation UI and audit events. Employee UI shows only available granted sources and never asks for service credentials.
5. Integrate real employee authentication/group membership before treating the prototype as a production multi-user permission boundary.
6. Validate in an isolated stack: two employees with different grants, a second organization, shared allowed scope, denied scope, native item restrictions, revocation across saved answers/caches, admin sign-out, process restart, token expiry/replacement, credential revocation and no stored fallback in Live Only.
7. Perform bounded real service-account tests only after the org admin creates credentials with the intended scopes. Confirm service-account support in the actual tenant before replacing the working trial connection; do not create accounts, widen grants or change tenant policy during this design task.

## Manual tests available now

Open a new chat at http://127.0.0.1:5197/ and keep Live Only selected. Try `how many porject are they`, then `no u shoude be use jira and see how may project ?`. Both were verified after renewal and should return the three configured Jira scopes with Live citations. Open a Live citation to inspect the original Jira resource. Live Only must show no stored Markdown citations.

For uploaded knowledge, choose Stored knowledge and select a file using Focus sources. Deliberately selecting a known fixture such as atlas-decision.md should show a Demo citation. Live + stored permits authorized normal stored knowledge alongside live sources; known demo files remain excluded from automatic retrieval.

Employee/group sharing and unattended service-account renewal cannot be tested as delivered features yet. They are the next implementation phase described above. Current source selection and authorization/identity limitations must remain visible in acceptance reports.
