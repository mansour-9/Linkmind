# RF5 — Local cross-source question journey

Implemented on `rf5/cross-source-journey`, based on the published
`checkpoint/rf1-rf4-local` source checkpoint. The isolated preview is
[Ask across sources](http://127.0.0.1:5196/ask/sources), Compose project
`linkmind-rf5-validation`. Schema remains `0018_connection_oauth`; no new tables or
services were added. Main and all older previews remain unchanged.

## Delivered local behavior

The Assistant links to a functional cross-source question page. Users explicitly
select stored documents and up to two connected resources. The system retrieves
bounded saved context and reads only those chosen live resources, then uses one
answer operation with an independent support audit when Bedrock is configured.
The current preview is mock and returns clearly labelled excerpts/source fields.

Stored context supports current and explicitly requested retained previous revisions.
Live current observations are not substituted for a past-state request. Selected
source outages produce explicit partial coverage while available authorized evidence
remains usable. No automatic same-name identity join or source-wide search is introduced.

The new answer contract distinguishes exact passage quotations from actual typed
field/value references. It rejects unknown sources, invented quotes, fabricated field
values, and JSON type substitutions such as true versus 1. Source support verification
still checks the complete statement's temporal, authority and freshness claims.
All real dispatch would use existing per-question bounds and persistent budget guards;
no new SDK client, provider fallback or spend store exists.

The model transport uses a flat, non-recursive output schema. A field value is encoded
as a JSON string for transport, then decoded into the strict application contract and
matched against the original field including its JSON type. Local length/cardinality
validation is retained. This avoids unsupported recursive/arbitrary-object model
schemas documented in the [Bedrock structured-output guide](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html).
Eight offline transport/schema/type cases were added; no paid compatibility probe was run.

Results show source origin, revision, update/observation time, exact passage or fields,
partial context, synthetic labels and source-specific failures. Results are transient:
no live content or answer is added to the repository, graph or conversation history.
Reload clears the result. Access, selected connection generation and observed source
revision are rechecked before model exposure, delivery and evidence opening; a periodic
check also hides an open result when authorization can no longer be confirmed.

Endpoints:

- `GET /api/v1/retrieval/connections`: owner-bound enabled source choices, without
  credential/configuration disclosure; not the admin configuration API.
- `POST /api/v1/source-answers`: explicit documents/resources, bounded transient answer.
- `POST /api/v1/source-answers/access`: no-model permission/revision recheck.

Existing native/MCP adapters are reused. Additional adapter regressions fix original
Atlassian links to point to the source site rather than the OAuth API gateway, validate
returned native identity, and keep Confluence cursor paths inside the verified gateway.
Live reference IDs now distinguish identical content from different source resources.

## Validation

Full API validation: **349 passed**, including the two private-original offline Lantern
checks with their local fixture directory supplied. The suite includes **34 new RF5
cases** for mixed evidence, exact/typed references, semantic acceptance/rejection stubs,
no retention, tenant/owner denial before reads, source outage, generation/revision
revocation, revocation during generation, retained history, past-state protection,
bounded unique selection, context and native OAuth provenance/pagination.

Full browser validation: **43 passed**; final focused browser checks after copy/navigation polish: **3 passed**. The new workflows cover: combined stored/live evidence,
reauthorization and hiding after disable, historical abstention/mobile rendering,
transience after reload, explicit scope and member isolation. The frontend build passed. Desktop/mobile visual checks found no overflow or browser errors; see [validation](RF5_VALIDATION.json).

The local AI-dependent tests use explicit structured stubs and honest mock extraction.
No new Sonnet/embedding call or real connector account was used. They establish local
contracts and workflow behavior, not actual synthesis quality or real-provider acceptance.

The first full browser run preserved two failures: repeated fixture content caused
upload deduplication to reuse an older filename, and initial graph discovery could
replace a newly typed query. The fixture now has unique content and explicit search;
the graph URL update preserves the search and has a new loading/query regression.
The corrected full run passed all 43 workflows without relaxing assertions.

A later GitHub run also exposed a delayed source-selection navigation effect clearing
a newly typed question before submission. Own scope transitions now preserve the
current draft, while external navigation keeps its reset behavior. The existing
workflow additionally checks that the created request contains exactly the two selected
document IDs. The final local full run again passed all 43 workflows; the failed
GitHub log/trace is retained in ignored local evidence.
The next GitHub run exposed a remaining graph-query timing case. Graph URL changes
now read synchronously maintained latest parameters, with committed URL synchronization,
so delayed default discovery cannot overwrite a newer query. Seven graph workflows
passed three consecutive local rounds (21/21) after this final correction.

All **114 pre-existing container IDs** were preserved. The original USD 10 ledger
remains **USD 4.2788470600 spent / USD 0.0566168200 historical unknown reservations**;
zero additional paid usage and zero new preview budget runs. Five labelled demo
connections and two fictional review notes are available in the new mock preview.
Source management remains admin-only and runtime reads remain private/owner-bound;
production employee delegation is not inferred from this local journey.

## Git and GitHub

Completed RF1–RF4 work is published at
[checkpoint/rf1-rf4-local](https://github.com/mansour-9/Linkmind/tree/checkpoint/rf1-rf4-local).
The snapshot commit is `e020372`; clean-checkout CI correction is `925e880`.
The correction adds the application root to the container Python path and makes the
two private-original tests explicitly opt-in. Their assertions are unchanged and still
run locally. Full raw provider/preflight outputs stay ignored and preserved locally;
reviewed summaries, synthetic fixtures and source stay versioned.

[Checkpoint CI passed](https://github.com/mansour-9/Linkmind/actions/runs/43684279870).
RF5 started from that checkpoint on its own remote branch. No force push, branch
deletion, history rewrite, main merge or deployment occurred.

## Remaining acceptance

Real MCP/provider registration, consent, exact approved scopes and source lifecycle
testing remain deferred by the user. Actual cross-source Sonnet quality, independent
question/coverage review, latency and cost acceptance still require a separately bounded
trial over accepted sources. RF5 is a validated local foundation, not full real-source
acceptance. RF6 production authentication/delegation, load/cost, recovery and reviewed
rollout remain separate. Do not activate a real account or rerun paid corpora from this report.

## Isolated local runtime

From `code/`:

```powershell
$env:BRAIN_WEB_PORT='5196'
$env:BRAIN_BACKEND_IMAGE='linkmind-rf5-backend:local'
docker compose -p linkmind-rf5-validation -f compose.yaml up -d --build --wait
```

Do not apply this build to protected older preview schemas. Existing base mock CI is
enabled on checkpoint/RF5 branches and contains no AWS credentials or real-source setup.
