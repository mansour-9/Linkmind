# RF3 repair and RF4 local completion — 2026-11-15

The user authorized finishing RF3 and continuing RF4 locally, while explicitly
deferring MCP/connector trials against real servers. The new isolated preview is
[Sources & MCP Connections](http://127.0.0.1:5195/admin/connections), project
`linkmind-rf34-followup`, schema `0018_connection_oauth`, trust policy
`grounded-v10-qualified-statement-support`. All older previews remain unchanged.

**The RF3 grounding repairs and RF4 local authentication/scope foundation are
implemented and validated. Real-provider consent and source acceptance remain deferred.**
The preview uses mock AI and five clearly labelled demo connectors; real Sonnet was
used only in the separately bounded grounding harness below.

## RF3: measured repair

Answer verification now audits the exact complete statement, unsupported fragments,
temporal qualifiers, role/authority scope and operational freshness. A missing,
shortened, reordered or negative review cannot certify an answer. Generation preserves
literal deadline meaning and precise roles. Saved operational answers must qualify the
claim in the answer itself, rather than relying on a separate UI freshness notice.
Exact quotation anchoring, unique whitespace repair, independent semantic verification,
source permissions, per-question limits and the shared spend guard remain mandatory.

The two previously captured failures were reproduced as verifier controls and rejected:
the invented relation between a weekday deadline and the requested event, and promotion
of Product Manager/workstream ownership into overall project leadership. Original
failed outputs and the original eight-prompt report were preserved.

Three new fictional generation cases passed original-source review: English equipment
deadline from Arabic policy; Arabic role summary from English project notes; and latest
recorded launch date with an explicit saved-source qualification. All displayed quotes
were exact source substrings, and the facts/roles/dates matched the originals.

The first new run passed five of six verifier controls. It over-rejected an explicitly
stated overall project leader because of ordinary present tense. That failed control is
preserved. The freshness condition was clarified to apply to operational/latest/current
requests, with bilingual deterministic classification checks. A separately scoped
three-control correction then passed: explicit leadership accepted, invented temporal
relation rejected, and unqualified saved-latest claim rejected. Final expected outcomes
are covered for all six distinct controls; this is bounded synthetic acceptance, not
independent company-wide model certification.

Total: **15 Sonnet calls, zero embeddings, USD 0.1153449000 actual cost**, all settled.
First run: USD 0.0964260000, 75.326 seconds, conservative reservations USD 1.0521588
within its USD 1.25 bound. Correction: USD 0.0189189000, 15.505 seconds, conservative
reservations USD 0.2434146 within USD 0.35. No prior corpus or extraction run was repeated.
The deterministic retrieval comparison separately remained **16/16**; it is mock
evidence-coverage validation and does not establish model quality.

See [concrete scope and correction bounds](RF34_FOLLOWUP_SCOPE.md). Raw synthetic
outputs remain in ignored `code/.local/rf34-followup/ai-results.json` and
`ai-freshness-correction.json`. These provider-level grounding checks complement the
prior end-to-end retrieval trial; they do not replace representative acceptance.

## RF4: functional local authentication and scope selection

- Native Jira/Confluence app-owned confidential 3LO and Microsoft delegated confidential
  code flow with S256 PKCE. Provider URLs/client secrets come from server configuration;
  the browser receives only the authorization URL and a fixed callback result.
- Short-lived hashed single-use state, HttpOnly cookie binding, tenant/owner/generation
  checks, encrypted PKCE verifier and access/refresh tokens, audience-bound runtime
  bindings, atomic refresh rotation, and removal/reconfiguration local grant revocation.
- Admin scope discovery and explicit selection: Jira projects, Confluence spaces,
  OneDrive folders and SharePoint site libraries/folders. Discovery reads metadata only,
  is bounded, and exposes truncation with verified exact-ID fallback.
- Scope selection preserves authentication but disables access/collection, invalidates
  tests/leases and requires another successful test. Mode changes preserve the correct
  authentication generation; stale callbacks cannot restore an edited connection.
- Real-source setup can be saved before a scope is selected. Missing provider registration
  is shown honestly. Custom MCP retains an explicit server-managed read/auth contract;
  arbitrary remote MCP OAuth is not advertised as working.

All new provider HTTP behavior was exercised through controlled offline transports.
No real Atlassian/Microsoft/MCP account was contacted, no Confluence document created,
and no real-source data was imported. Default connector networking remains disabled.
See the [authentication runbook](RF4_OAUTH_RUNBOOK.md) for later server preparation.

## Verification and preservation

**315 API tests, 39 browser workflows, frontend build passed.** Final focused OAuth
checks passed **8/8**, including actual PKCE challenge/verifier agreement and grant
preservation across enable/disable. Two dependency deprecation warnings remain
(Authlib's httpx compatibility and Starlette/AnyIO); no test failure occurred.

The five demo configurations, authentication/test states and modes survived an API
restart. Screenshots at 1440/390 showed no horizontal overflow or browser errors;
scope picker and real OAuth setup were visually inspected at 390. Broader browser
workflows also passed at 1024/1920. The five saved demo sources use Live Only; adding
them did not automatically synchronize documents or create graph knowledge.

All **109 pre-existing container IDs** remain. Protected builds/schemas were not
replaced or migrated. There is **no budget run in the new preview database**. The
original USD 10 ledger moved only by the approved USD 0.1153449000 test cost, from
USD 4.1635021600 to **USD 4.2788470600** spent. Historical unknown reservations stayed
**USD 0.0566168200**, and no reset, clone, unpause, increase or unknown release occurred.

Machine-readable evidence: [RF34 validation](RF34_VALIDATION.json). Ignored local
artifacts include API XML, browser JSON/screenshots, retrieval results, persistence,
container preservation and spend snapshots.

## Remaining gates

Real app registration/consent, exact approved URLs/scopes and server testing remain
for the user's later trial. That trial must prove source permissions, expiry/revocation,
rate limits/outages, live reads and selected sync/recovery against actual providers.
Production delegated employee access is still separate from this private local slice.

RF5 remains the combined company-source journey after source lifecycle acceptance;
RF6 covers representative independent quality, production sign-in/access, load/cost,
backup/restore and staged rollout. No deployment, main cutover, push or merge occurred.

## Reproduce local checks

Do not layer this build onto older protected databases. From `code/`, use the existing
new project and its isolated volumes:

```powershell
$env:BRAIN_WEB_PORT='5195'
$env:BRAIN_BACKEND_IMAGE='linkmind-rf34-followup:local'
docker compose -p linkmind-rf34-followup -f compose.yaml up -d --build --wait
docker exec -e PYTHONPATH=/app:/app/apps/api linkmind-rf34-followup-api-1 pytest -q apps/api/tests
```

The recorded full run also mounted the existing private offline Lantern acceptance
fixtures via `LANTERN_ACCEPTANCE_DIR`; those files were not model input. From `code/e2e/`:

```powershell
$env:BRAIN_URL='http://127.0.0.1:5195'
$env:BRAIN_E2E_DISPOSABLE='1'
npx playwright test
```

Do not automatically rerun either paid harness report. The optional
`compose.rf34-ai.yaml` is for the reviewed one-shot harness with the original shared
ledger; it was not applied to the running mock preview.
