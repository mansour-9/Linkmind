# Linkmind clean real-source trial — 2026-11-16

The new clean instance of the existing Linkmind is available at http://127.0.0.1:5197/admin/connections. Four real scoped MCP sources work: Jira ATLAS, BEACON, HARBOR and Confluence ABL. The four representative Sonnet questions all failed citation validation, so RF5 real-model acceptance remains open. Passing connector reads or deterministic tests does not accept the AI answer journey.

The user clarified that this is a fresh runtime of the same application with isolated content, not a new company workspace feature or a replacement application. The old previews and data remain outside this new runtime. The test company's AsterBridge content is fictional, retrieved from actual Atlassian services through Linkmind's own adapter; no local export or Codex connector response was substituted for live evidence.

## Verified behavior

- New `linkmind-asterbridge-live`, loopback port 5197, schema `0018_connection_oauth`. Final database has zero documents, graph entities, conversations, retained connected resources and revisions; four real source connections and four answer usage records. Live Only reads stay transient.
- Corrected one-shot Atlassian MCP read-only PKCE consent completed by the user. Access credential stays in a restricted local temporary directory outside Git/OneDrive. Provider-required offline scope was requested; no refresh token is retained or used. Production sign-in remains open; the local UI still uses standard demo identities.
- Connector fixes support actual wrapped `data` responses, full Jira records, current Confluence content tools/HTML and source metadata. MCP reauthorization stays on MCP, with no native-credential forwarding. Protocol negotiation is reused within one request while source access/content are fetched again. Generic execution/write/destructive tools remain disallowed.
- UI Test connection now asks for one authorized issue key/page ID for real Atlassian MCP. Verified ATLAS-16 from the browser and opened actual source evidence, URL, native status, revision and observation time.
- Full API regression against the verified separate mock API: **355 passed, 2 skipped**, two dependency warnings, 46.80 seconds. Frontend TypeScript/Vite image build succeeded. Prior 43 RF5 browser tests are historical, not a new full browser result.
- **13 actual platform access checks passed**: cross-project resource rejected, non-admin management denied, another identity receives no inherited connections and cannot use the owner connection, real MCP dependency rechecked, BEACON disconnect denies live/stale access, resource retested, Live Only restored, old generation remains invalid. These are local connection/access tests, not provider grant revocation acceptance.

## Real-model outcomes

| Case | Actual transport and source | Result |
| --- | --- | --- |
| live-A01 | Browser UI; ATLAS-16 | citation_failed; zero accepted statements |
| live-AR02 | Linkmind API; HARBOR-5; Arabic ownership question | citation_failed; zero accepted statements |
| live-B05 | Linkmind API; ATLAS-4 + Confluence ADR007 (327699) | citation_failed; zero accepted statements |
| live-B07 | Linkmind API; HARBOR-15 + Confluence release gates (229602) | citation_failed; zero accepted statements |

All selected reads were actual non-synthetic observations. The three API reports explicitly return `retained:false` and `saved:false`; the UI states its result is transient and final database counts corroborate no retained content/history. The answer candidates were rejected before independent verification; **no semantic verification calls occurred for these four questions**. The current exception handling groups several wire/citation validation failures under `citation_failed`; raw candidate outputs were not retained, so the exact root cause is not established. Do not label these as accepted model answers.

One UI wording defect was also observed: it says “Sonnet · verified source answer” even when the result is citation_failed. The failure message and absence of accepted statements remain visible. Provider wording must reflect actual validation state.

## Preserved failures and accounting

The initial full regression run hit an AI-enabled HTTP API despite its runner having AI_PROVIDER=mock. It ended **1 failed, 354 passed, 2 skipped** and caused four settled calls costing **USD 0.0304194000**. This was disclosed, the API was stopped, and the original trial was retained separately at port 5199 with mock AI, no shared-budget connection, no MCP credential and no AWS mount. Only then was the full deterministic suite rerun successfully. Those accidental calls are not real MCP acceptance and were not hidden or removed from the ledger.

The four intentional real-source questions cost **USD 0.1013925000**. Total additional cost including the isolation error is **USD 0.1318119000**, eight settled calls, with **USD 0.8522580000** aggregate conservative reservations within the scoped USD 2 bound. The original cumulative USD 10 ledger now records **USD 4.4106589600** spent, **USD 0.0566168200** historical unknown reservations, three unchanged unknown calls, and paused=false. No reset, clone, increase, unpause or unknown release occurred. No extraction, enrichment or embeddings ran. No paid question was repeated.

The first OAuth consent invalid_request and the original wrapped-record/tool incompatibility were preserved before correction. The Arabic harness socket denial happened before any HTTP/model dispatch; the ledger was checked before network-permitted execution. A terminal Unicode printing issue occurred after saving that preflight report and did not justify resubmitting a paid result.

## RF plan disposition and next work

1. RF4: bounded real Jira/Confluence MCP discovery/read/access acceptance has concrete evidence. Native provider OAuth, durable sync/revision/deletion recovery, refresh/reconnect and actual provider grant revocation remain separate open gates. OneDrive/SharePoint are not connected. Current document adapters support PDF/DOCX/Markdown/text, not XLSX.
2. RF3/RF5: real answer acceptance is blocked by four citation-contract rejections. Next repair should classify wire/field/quote failures without storing credentials, reproduce the failure offline, preserve exact typed values and independent semantic checks, and consider representing description prose with exact passage citations while retaining native fields. This is a proposed repair, not an established diagnosis or a successful live retest. Fix misleading provider wording. Do not automatically repeat these paid cases.
3. RF6: production authentication, employee delegation, held-out quality, measured operations/recovery and release acceptance remain open. This local trial authorizes no main deployment or AWS infrastructure.

Evidence: `validation.json`, four `live-*.json` question reports, live readbacks, `connections.json`, `access-checks.json`, and `platform-ai-citation-failure.jpg`. Source changes remain uncommitted on `fix/asterbridge-real-mcp`; no push/merge occurred.
