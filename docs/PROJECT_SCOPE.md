# Linkmind - Product Scope and Decisions

2026-11-17 latest delivery: New ordinary chat uses automatic permitted MCP and Documents retrieval; source-mode selection is removed. Current workspace old content is reset with verified backup and archived chats. AsterBridge Confluence company/customer/department/partner context is expanded. Graph/Knowledge building jobs remain deferred. See [automatic chat results](AUTO_CHAT_RESULTS.md). Earlier dated requirements below are historical where superseded.

2026-11-17 clarified target: organization admins configure persistent upstream connections; employees authenticate only to Linkmind and use explicitly granted company sources. Connection credentials must outlive employee sessions through provider-supported service identities/automatic token acquisition. This replaces the proposed per-employee upstream sign-in interpretation. Current owner-bound demo implementation is not production group authorization. See [organization-managed connections](ORG_MANAGED_CONNECTIONS.md).

2026-11-17 user-approved source behavior: Live Only answers must use authorized live MCP evidence and never silently fall back to local/demo/uploaded knowledge. Stored knowledge and explicit Combined remain legitimate supported modes. Preserve existing files and evidence. The confirmed old fixture ingestion and project-count routing problems are addressed by [the source-policy repair](SOURCE_POLICY_REPAIR.md).

Latest scope, 2026-11-15: the user authorized publishing the completed source checkpoint
and starting new RF work on a separate branch. RF5's explicit cross-source local
question foundation is implemented at 5196, with 349 API / 43 browser / build and final
3 browser checks. This does not accept real provider lifecycles or combined AI quality;
those trials remain deferred. No new paid evaluation or production rollout was started.
See [RF5 results](RF5_RESULTS.md) and [Git workflow](GIT_CHECKPOINT.md).

Latest implementation checkpoint, 2026-11-15: the user authorized RF3 repairs and
local RF4 completion. The new isolated 5195 preview passed **315 API / 39 browser / build**,
final 8 OAuth checks and 16/16 mock retrieval. RF3's known grounding failures now have
bounded real-Sonnet repair evidence; RF4's encrypted server-owned OAuth lifecycle and
scope discovery/selection are implemented and validated offline. Real account/server
trials remain explicitly deferred; independent company acceptance and production
employee authentication/access remain open. See [current results](RF34_RESULTS.md)
and [OAuth runbook](RF4_OAUTH_RUNBOOK.md). Protected previews remain unchanged.

2026-11-15 latest follow-up: the user approved RF4 implementation and specified a
functional **Sources & MCP Connections** admin feature for Jira, Confluence, OneDrive,
SharePoint and Custom MCP. Real source URLs will come later; explicit mock connectors
are authorized now. Local management/persistence and connector interfaces are delivered
at port 5194: **292 API / 37 browser / build**, final 27 connector checks. See
[RF4 results](RF4_RESULTS.md). Real OAuth/consent and source lifecycle acceptance remain
pending; this supersedes the earlier RF4 planning-only state below. No account, paid
model trial, protected environment rollout or AWS hosting was activated.

2026-11-15 follow-up: RF3 testing with AWS Bedrock was explicitly requested and
completed in isolated local stacks (mock 5192, Sonnet 5193). **264 API / 34 browser /
build passed**, but two of eight real-model cases failed source review despite passing
semantic verification; RF3 quality acceptance remains open. See [RF3 results](RF3_RESULTS.md).
The trial spent USD 0.1349612200 against the original cumulative USD 10 ledger;
no new allowance or protected-environment rollout occurred. RF4 **planning** is now
requested for **Jira, Confluence, OneDrive and SharePoint**, with convenient MCP options
to be evaluated. Exact account/resource scopes are unselected and connector execution
is not authorized. See [RF4 plan](RF4_PLAN.md); transport choices and delivery order
are proposals, not agreed commitments.
The dated direction below remains history where superseded by this checkpoint.

Updated **2026-11-14** after the user's architecture discussion and request for a
complete documentation restructure. The user subsequently authorized **RF1 implementation
and isolated local validation**. RF1 is implemented and validated locally: 191 API tests,
29 browser workflows and frontend build passed. RF2 was later approved and completed
in a separate mock stack: 231 API / 32 browser / build passed; see [RF2 results](RF2_RESULTS.md).
Those RF1/RF2 implementation slices excluded paid inference, external connector access,
main/existing-preview rollout and AWS deployment. RF3's later bounded test authorization
and measured checkpoint are recorded above. See [RF1 results](RF1_RESULTS.md).

## Product purpose - agreed

Linkmind is a company's unified knowledge repository with intelligent search and an
AI assistant. It collects and retains selected organizational information from uploads
and connected systems, organizes it lightly, and helps employees find, understand and
connect evidence. It is more than a live search proxy: selected synchronized knowledge
must remain durably stored, versioned and discoverable under its access/retention rules.

The primary journey is: ask a question, identify relevant sources, retrieve supporting
information, reason over that evidence, and deliver a useful cited answer. Evaluate
success by answer usefulness, retrieval coverage, freshness, citation support, latency,
reliability and cost. Entity/relationship counts are not product success metrics.

Linkmind is the central reference point for discovering company knowledge. Original
systems retain their field semantics and provenance: Jira task status is a Jira record,
a policy is supported by its document, and a Slack discussion is attributed discussion.
Retention does not make a source authoritative, current, approved or accessible forever.
Conflicting sources remain distinguishable; no silent global winner is invented.

## Document authority and authorization

- This file owns agreed requirements, proposed defaults and open decisions.
- [Implementation plan](IMPLEMENTATION_PLAN.md) is the single active roadmap and
  capability/status matrix; its RF milestones are planned unless explicitly complete.
- [Architecture](ARCHITECTURE_M2_M3.md) distinguishes inspected current code from target
  behavior. Filenames are retained for existing references.
- [Restructure decision and document review](RESTRUCTURE_REVIEW_2026_11_14.md) records
  rationale, superseded assumptions, review coverage and unresolved choices, not a
  second implementation backlog.
- The [previous planning snapshots](reference/pre_restructure_2026_11_14/IMPLEMENTATION_PLAN.md),
  original master specification and dated validation reports are historical evidence.
  Their imperative language does not authorize work or override this scope.
- User-facing discussion may be Arabic. Product copy and repository documentation
  remain English until explicitly changed. Arabic/English evidence quality is core.

Current completed implementation authorization covers RF1 and the later approved RF2
local slice. Existing Sonnet test accounting remains
`northstar-sonnet-2026-11-12`, with a cumulative USD 10 ceiling. Do not reset, clone,
increase, unpause or dispatch against it under this RF1 request. Historical probe
permissions and remaining headroom do not authorize a new run. No Gemma work is active.

Subsequent agreed testing preference (2026-11-14): prefer bounded real Sonnet trials
when assessing actual assistant usefulness, retrieval and answer quality. Keep simple
deterministic/safety/UI checks on mock/stubs when inference adds no evidence. AI answer
testing can follow RF1 immediately; it is not blocked on RF2 or optional graph enrichment.
The user requested self-service AWS login and this durable policy. No new allowance,
ledger reset/clone/unpause, paid dispatch or protected-environment change is implied.
See [AI testing policy and login](AI_TESTING_POLICY.md).

After the user renewed login and confirmed proceeding, the RF1 preview at port 5189
was switched to Sonnet with direct shared accounting against the original USD 10 run.
The bounded follow-up and final supported Lantern summary are recorded in
[RF1 AI preview](RF1_AI_PREVIEW.md). This subsequent authorization supersedes the
RF1-only no-paid-dispatch boundary above for that preview; no new allowance, main
rollout, connector deployment or RF2 work is implied. Ordinary ingestion remains source-only.

The user then explicitly approved **RF2**, deferring Arabic/answer-style enhancements
to RF3. RF2 is implemented/validated in a new mock preview at port 5191, using no paid
inference and preserving RF1 Sonnet at 5189. Delivered: stable uploaded-source identity,
explicit project/team organization, metadata/content catalog and search filters, retained
revision inspection and typed common evidence. Live field evidence is tested offline;
actual connector auth/live/sync remains RF4. See [RF2 results](RF2_RESULTS.md).

## Current state - retained, not target acceptance

The repository implements a local React/FastAPI/PostgreSQL/pgvector application with
uploads, immutable revisions, passage locators, text/vector search, cited chat,
conversational source discovery, selected-source overviews, generated entity pages,
a bounded graph explorer, conflict/identity review, usage and test-spend controls.

F1.1 separates search publication from enrichment. F1.2 repairs and F1.3 staged
refresh exist locally; later Lantern work adds bounded extraction/citation diagnostics.
RF1 current code/new isolated preview defaults ordinary uploads and revisions to source-only
indexing. Explicit optional enrichment and labelled dataset loaders retain the existing
verified path. Lexical content publishes before embeddings, unchanged compatible text in
the same document can reuse vectors, and source-only answers avoid unused graph dependencies.
Query understanding exists but does not route across live connectors. Existing main and
preview builds/schemas remain untouched. Last recorded main inventory was schema 0010;
current-source migrations include 0011–0015. RF1 Sonnet retains 0013; RF2 uses 0014;
the separate RF3 stacks use 0015.
Reinspect before later rollout.

Native authoring, managed Spaces, production sign-in, application connectors, persistent
external sync and adaptive live routing are not delivered. Historical Northstar results
do not establish new-architecture acceptance. Latest recorded Lantern extraction
acceptance failed semantic-verdict alignment; source text remained searchable. Use
[the latest evidence](LANTERN_IDENTIFIER_REPAIR_RESULTS.md), not older next-task text.

## Input boundary - agreed

- Core inputs are readable text: selectable-text PDFs, TXT/Markdown, existing DOCX
  support, and source text/structured records provided through MCP or native APIs.
- The user guarantees extractable text for this core journey. OCR, scanned/image-only
  document interpretation and upstream text-conversion services are outside this
  restructure's core scope. Do not build Linkmind OCR services or a microservice
  platform to anticipate them. Future upstream adapters can supply text if requested.
- Basic format, size, integrity and readable-content checks remain. Unsupported input
  receives an honest result, not fabricated text or a promise that OCR is available.
- Source content, names and metadata are untrusted data, never executable instructions.

## Core repository and ingestion - agreed

1. Save the original upload or source record, stable source identity, content version,
   provenance and existing access boundary. Preserve source URLs/locators when available.
2. Extract readable text or map structured source fields using ordinary parser/adapter
   code. This step does not require Sonnet to interpret the complete document.
3. Keep useful metadata: title, type, source instance/native ID, source-updated time,
   observed/synchronized time and reliable project/team references. Unknown stays unknown.
4. Create searchable passages and lexical/semantic indexes. Embeddings are a separate
   model operation with measurable cost; they are not Sonnet claim/relationship extraction.
5. Publish authorized valid text independently of optional enrichment. Lexical search
   remains usable during embedding degradation, with semantic readiness shown honestly.

**Default-off structured enrichment is a hard target requirement.** Ordinary uploads,
revisions and sync do not automatically run Sonnet entity/claim/relationship extraction,
identity resolution or cross-document conflict assessment. A new skipped/not-requested
state must not masquerade as a failure. No automatic per-document summaries are required.
Useful metadata and explicit source links do not depend on model extraction.

Only changed content requires new indexing work. Avoid re-embedding unchanged passages
where safely reusable within the tenant/source/version and model/dimension contract.
Metadata/access-only updates still reconcile visibility without unnecessary paid work.
Do not silently reuse stale embeddings or erase source history to save processing.

## Core search and answer experience - agreed

- Provide direct document/record search, not only chat: exact IDs, lexical and semantic
  retrieval, source/type/project/date filters where supported, previews and source links.
- Search source text/fields even with zero extracted entities, claims or relationships.
  Broad discovery must not depend on knowing filenames or internal canonical IDs.
- Interpret question, time, user-selected scope and conversation references. Route using
  source capabilities and lightweight metadata; do not search every connector by default.
- Use direct deterministic routes for clear requests. Use bounded model planning for
  ambiguous/compound requests only where it adds value, then retrieve progressively.
- Stable knowledge normally uses the index; current operational fields use the relevant
  live source when available; historical questions require dated/historical evidence.
- Analyze relevant evidence on demand. Cross-source reasoning does not require a
  precomputed graph edge and does not automatically create a shared persistent fact.
- Return supported answers with inspectable citations, unresolved material disagreements,
  freshness and honest coverage limits. Ask focused clarification when ambiguity matters.
- Bound passages, context size, source calls, planning rounds, model calls, output and
  wall time in code. Expand only within authorized scope; disclose partial coverage.
- Whole-document or many-document summaries are a distinct bounded workload. Do not
  claim complete coverage from passage samples or promise every question is cheap.
- Preserve existing answer grounding and fail-safe behavior. Essential reference/access
  checks stay mandatory. Evaluate proportionate additional semantic checks before changing
  runtime acceptance or validation policy; this planning does not disable verification.

## Connected sources and persistent collection - agreed direction

Uploaded documents and connected document sources are first-class inputs. Jira, Slack,
OneDrive, SharePoint, GitLab, Confluence and other approved sources fit the same conceptual
repository; each still needs a real capability and lifecycle implementation.

| Mode | Live use | Shared repository behavior |
| --- | --- | --- |
| Live Only | Authorized scoped retrieval | No automatic shared indexing; retained answer evidence remains subject to access/retention |
| Live + Sync | Authorized scoped retrieval | Persist selected scopes, maintain revisions and incremental indexes |
| Not Connected | No live retrieval | Exclude connector-dependent material from active use under the mode/access policy; retained history is not a bypass |

Connection does not mean import everything. Select practical scopes such as project,
repository, folder or channel. Store structured tasks/records as appropriate rather than
turning every response into a fake PDF or running a universal extraction schema.

Use MCP or native APIs based on verified source capabilities. MCP is transport/tool access,
not a database or synchronization guarantee. A live-only response is not a complete sync
record. Sync requires cursors/pagination, resumability, deduplication and permission/deletion
reconciliation. Partial or user-filtered results cannot overwrite complete shared records;
older updates cannot replace newer content. A missing search hit does not prove deletion.

Live answers need not wait for background sync. Refresh configured scopes separately when
safe. Prefer dated fallback only if retained access remains reliably valid; authorization
uncertainty forbids fallback. Show source-updated, observed and last-successful-sync times
separately. Querying rarely used resources is not a substitute for reconciliation.

Earlier Jira-first discussions remain context. **Proposed default:** prove one read-only
connector end to end, with Jira as the existing candidate, then a document-source connector
(OneDrive or SharePoint) and the next useful source. Exact first source, scopes and order
remain choices before implementation; the former Jira -> Confluence -> GitLab order is no
longer a mandatory prerequisite for document-source value. Do not promise all connectors
or connect accounts under this documentation request.

## Lightweight organization and graph - agreed

Projects, teams and resources may be grouped using known source metadata, explicit IDs,
original links or deliberate human association. Similar names alone do not prove identity.
Keep source-qualified identifiers; do not create a universal ontology before storing text.

The graph is an optional projection/navigation aid over reliable links. It is not the
repository, its completeness is not a gate, and its absence must not degrade source
availability. Retain useful existing graph/People/entity views and evidence; do not delete
legacy facts, reviews or URLs. Source changes must still prevent old relationships from
appearing current. Selective model-backed enrichment requires a concrete use case and
bounded scope; advanced multi-hop GraphRAG is deferred until measured retrieval benefit.

## Security boundary and deferred enterprise design

Preserve organization isolation, owner/organization visibility, source restrictions,
server-side access checks before model exposure and delivery, and history/cache revocation.
Links do not expand access; privileged sync credentials do not grant all employees rights.
Do not infer that deferring enterprise design authorizes weakening current boundaries.

Detailed groups, delegated Space management, narrowing-page controls and enterprise access
UX are deferred. Implement only the source-access contract necessary for each accepted
connector. Production authentication and adequate release security are still required
before real employee access; local demo impersonation must not become hosted behavior.

## Keep, simplify and defer

| Keep and reuse | Simplify for the core | Defer as separate capabilities |
| --- | --- | --- |
| Source originals, immutable revisions, passages, citations, evidence access | Ingestion: retain -> parse/map -> index -> available | Native rich authoring and managed Spaces |
| PostgreSQL/pgvector, React/TypeScript/React Flow, FastAPI and workers | Optional default-off structured enrichment | Advanced graph reasoning and exhaustive conflict discovery |
| Useful graph/review/history behavior and usage controls | Source catalog and bounded retrieval coordinator | Detailed enterprise access-control design |
| Existing basic safety and unresolved-source attribution | Only changed-content indexing and practical sync scopes | Delegated review/resolution, writes and autonomous workflows |

Native Hub and Spaces remain later product ambitions with their previous detailed
requirements preserved in the [prior scope](reference/pre_restructure_2026_11_14/PROJECT_SCOPE.md).
They do not block the current retrieval core. OCR is upstream/outside the core. Full archival
export, legal retention and model training are examples of possible future uses, not newly
requested deliverables. Durable originals, versions and provenance support later decisions.

## Engineering and release constraints

Retain the current local Docker stack and ordinary Python modules/workers. Bedrock runtime
calls use boto3; future approved AWS infrastructure uses Python CDK v2. No new graph database,
vector store, event bus, agent-per-source architecture or microservice fleet is justified
by this restructure. Model-backed reasoning stays Sonnet-only; keep separately configured
embeddings. Do not replace providers, remove migrations or discard useful existing work.

Use isolated deterministic checks first, then separately authorized representative live
acceptance. No paid evaluation, source credentials, data cutover or infrastructure changes
are included. Main/preview inventory, inference accounting, compatible migration, backup,
actual-data rehearsal and rollback need explicit review before any later rollout.

## Open decisions - not assumed commitments

- First connector and approved source scopes; identity/permission feasibility.
- Representative corpus, employee questions, source size and actual concurrency.
- Held-out retrieval/answer quality, freshness, p50/p95 latency and cost targets.
- Source history coverage, retention/deletion/export requirements and embedding reuse rules.
- Routing budgets, fallback policy and any change to extra semantic verification.
- Hosted region/budget, production identity and Arabic/RTL release coverage.

No time, cost-saving percentage, zero-failure promise or enterprise-scale acceptance is
inferred. See the active roadmap for the phased plan and measurable acceptance gates.
