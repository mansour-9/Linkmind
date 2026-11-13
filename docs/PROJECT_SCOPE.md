# Linkmind — Product Scope and Decisions

Updated 2026-11-12: **Production-Quality Core Platform with Phased Feature Delivery**.
The roadmap revision originally authorized documentation only. The user subsequently
requested F1.1 implementation and isolated local validation on 2026-11-12. The product
direction below is agreed; other slices remain planned. No paid evaluation, model
change or AWS deployment is authorized by that focused implementation request.

The user later authorized T1 fictional-company testing: 24 fictional documents,
example questions, additions/revisions, selected-document overviews and separate
mock/Sonnet previews. An explicit **US$10 maximum** covers the new Sonnet extraction,
embeddings and chat run only. No model comparison or AWS infrastructure deployment.
See [testing guide and actual acceptance](COMPANY_TESTING.md).

On 2026-11-13 the user additionally authorized F1.3 implementation and main-data
rollout preparation, before F2. Bounded Sonnet checks reuse the existing USD 10
run and ledger; there is no new allowance or AWS infrastructure authorization.

## Document authority and actual state

- This file owns product requirements and agreed decisions.
- [Implementation plan](IMPLEMENTATION_PLAN.md) is the single active roadmap and
  contains the Capability Acceptance Matrix, milestones, dependencies and gates.
- [Architecture](ARCHITECTURE_M2_M3.md) separates current behavior from target design.
- M3.2 documents elaborate only the processing work; the Jira note elaborates only
  connector behavior. They do not establish competing delivery orders.
- Validation reports, original specification and original engineering instructions
  remain historical evidence. Explicit latest user instructions take precedence.

Current runtime: local React/FastAPI/PostgreSQL/pgvector/Bedrock application with
uploads, retained revisions, source evidence, hybrid search, grounded chat, graph,
generated entity pages, conflict/identity review and usage. Native authoring,
managed Spaces, organization groups, live connectors and synchronization are not
implemented. M3.1 is completed and user-approved; M3.2A diagnostics are complete;
F1.1/M3.2B search-readiness separation is implemented and validated in an isolated
local stack. F1.2 and conversational discovery are implemented locally; F1.3 staged
enrichment is locally validated. The read-only main inventory is already at schema
0010, while its F1.3/0011 cutover remains pending the prepared rollout review.
See [F1.1 evidence](F1_1_RESULTS.md) and [F1.3 results](F1_3_RESULTS.md). Existing functionality is not
reset by the new scope.

## Product direction

Linkmind is an enterprise knowledge, search, intelligence and AI workspace,
complementing Jira, Confluence and GitLab rather than replacing them. Deliver
complete, polished capabilities incrementally. Simple architecture must not mean
reduced feature depth, an intentionally limited editor, weak GraphRAG, or prototype UX.

Store broadly, structure selectively, verify proportionally, and reason on demand.
Measure useful answers, discovery, evidence, access correctness, latency and cost;
do not optimize for entity counts. Preserve useful existing features and data.

## Knowledge Hub and contribution

- Provide practical rich authoring: headings, lists, tables, links, code blocks,
  media/attachments as appropriate, reliable draft saving, preview and edit-conflict
  protection. Evaluate an established editor before building one. Simultaneous
  real-time collaboration was not required initially; do not silently treat basic
  draft reliability or revision management as optional.
- Support publishing, discovery, categories/tags, related resources, revision
  comparison/restoration, archiving, maintainers and deliberate duplicate merging.
- Drafts need no destination. Every published native page has one primary Space
  or authorized general organization knowledge area. Preselect the current Space;
  otherwise suggest a relevant destination and show its audience before publishing.
- Authorized editors publish ordinary knowledge directly. Categories, tags and
  related-resource/duplicate suggestions are optional and never block publishing.
- Official approval is separate, permission-controlled and tied to a revision.
  Ordinary publication does not imply approval. Editing must not silently carry
  approval to changed content. No new review queue or delegated verification workflow.
- Track creator, revision editors, maintainer and timestamps. An author is not
  automatically the person who performed the work described in the page.
- Human-authored, AI-assisted and AI-generated content retain clear provenance.
  AI-generated additions remain distinguishable; publication requires an authorized
  user's explicit action. Preserve supporting sources and their access restrictions.
- Suggest related or duplicate pages using authorized retrieval; suggestions must
  not disclose restricted titles. Merge deliberately, preserve revisions/citation
  targets and redirects, and never broaden permissions by unioning source audiences.
- Native pages complement imported records; do not duplicate Confluence resources
  as independently maintained native pages without an explicit user decision.

## Spaces and organization

- Spaces are first-class project, team and department workspaces. Start delivery
  with the full project journey; reuse the model for teams/departments rather than
  inventing separate products. Provide overview, objectives, maintained status and
  owner information, knowledge, resources, people, decisions, relationships, updates
  and contextual chat as their data becomes available. Show attribution/freshness.
- Link shared resources; do not copy them. Strong source-qualified identity or
  explicit links allow automatic enrichment inside approved sync scopes. Similar
  names or uncertain associations remain suggestions. Never overwrite approved
  descriptions with inferred content or automatically expand their audience.
- Organization Admins grant Create Space to selected users/groups. Authorized
  creators act without per-Space approval and become initial owners. Creation and
  authority to grant access remain distinct permissions. Owners manage membership,
  content and maintainers within delegated limits; this is not fact-review routing.
- Other employees may suggest a Space. Suggest accessible similar Spaces before
  creation, but do not block similar names or expose inaccessible Spaces.

## Users, groups and resource access

- Isolate organizations. Users may join multiple groups and receive the union of
  their eligible group grants. Keep resource and source restrictions enforceable.
- Native pages inherit their primary Space's audience by default. Authorized owners
  can restrict to a smaller permitted audience; restrictions never broaden access.
  Linking into another Space grants nothing. Preview moves and require explicit
  confirmation when the effective audience changes; never silently reset restrictions.
- The general knowledge area is an explicit publishing audience, not an access bypass.
- External access requires both Linkmind authorization and source-system authorization.
  Privileged sync credentials do not authorize all employees. Unknown or revoked
  source access fails safely, including for cached and historical evidence.
- Enforce access before content reaches the model and on search, titles, counts,
  suggestions, graph paths, summaries, updates, citations, history and caches.
  Derived evidence inherits resource dependencies; no per-chunk/claim/edge ACL UI.
- Use production authentication before real employee access, with a path to enterprise
  identity providers. Cognito remains the proposed hosted option; retain application
  authorization separately. Demo identity switching is local-only.

## Search, chat, research and GraphRAG

- Provide direct search as well as AI answers: exact identifiers, keywords, semantic
  and hybrid ranking, source/type/project/team/date filters, previews and references.
- Evaluate Arabic, English and mixed-language retrieval/answers from early milestones.
  Deliver localized RTL UI as a tracked capability, not an automatic final afterthought.
  Current UI remains English; bilingual readiness is not yet established.
- Use evidence-backed relationships and useful multi-hop retrieval, not indiscriminate
  extraction. Preserve predicate direction, identity, dates and supporting passages.
  Graph remains a valuable exploration surface; employees need not use it to get answers.
- Stable documentation normally uses indexed evidence. Current operational questions
  normally query the relevant live source even if indexed information exists. Historical
  questions require historical evidence, not simply today's response.
- Route by meaning, source capabilities, permission, time and conversation context.
  Clear requests use deterministic tools; complex questions may use bounded planning,
  progressive retrieval, graph paths and multiple sources. No agent per connector.
- Hybrid Smart Scoping: Space chat searches the Space and relevant connected scopes,
  including authorized resources not individually indexed. Broaden when explicitly
  requested or enabled. No approval for every retrieval step or complex scope UI.
- Preserve conversation context without treating conversational memory as source truth.
  Provide citations, evidence inspection, actual progress, cancellation where supported,
  uncertainty, and honest coverage limits. Enforce tool/token/time budgets in code.

## Connected sources and freshness

Deliver Jira first, then Confluence, then GitLab. Each must be robust for real
organizational use; one successful API call is not connector completion. Codex
connections are not application credentials. Use MCP or native APIs according to
verified capability; bulk synchronization need not use MCP.

| Mode | Live retrieval | Persistent index and enrichment |
| --- | --- | --- |
| Live Only | Authorized scoped requests | No automatic organizational indexing or enrichment; temporary citation/history evidence only under retention/access rules |
| Live + Sync | Authorized scoped requests | Selected approved scopes synchronize and enrich Spaces |
| Not Connected | Unavailable through Linkmind | No sync or cached fallback exposure |

Configure at connector-instance/project/repository scope with clear inheritance,
not per record. Disabling a connector stops its scopes. Moving to Live Only removes
previously synchronized resources from active organizational retrieval/enrichment;
retained history follows access and retention policy, not implicit public availability.

Live answers do not wait for sync. Changed observations within approved sync scopes
may request a deduplicated refresh. A partial or user-filtered response must not
replace a complete shared record. Re-fetch when version, completeness or ACLs are
insufficient; older observations cannot overwrite newer state. Preserve previous
evidence and distinguish source-updated, observed and explicit effective times.

Use incremental sync, checkpoints, pagination, bounded retries, source limits and
permission/deletion reconciliation. Begin with appropriate polling; add webhooks
where justified. A missing search result does not prove deletion. Query-triggered
refresh does not replace reconciliation of rarely queried resources or permissions.

On temporary outage/rate limit, provide clearly dated last-known information only
when access remains reliably established. Never call cached status currently confirmed.
Permission uncertainty does not permit fallback. Updates begin with meaningful recorded
changes and freshness indicators, not a separate event engine or LLM per modification.

## Authority, verification and conflict safety

Prioritize evidence by relevance, semantic meaning, direct support, appropriate source
authority, freshness and explicit effective dates. Optional scoped authority settings
are available to admins/authorized owners, not mandatory per fact. Jira assignee is
not project owner; newer text is not automatically authoritative. Model confidence
alone is not a reason to resolve a contradiction.

Always validate structure, source references, permissions and supporting evidence.
Recover safe formatting errors without inventing facts. Use deeper semantic checks
for ambiguous, contradictory or consequential information; evaluate any relaxation
against the current safeguards before rollout. **Model decision, 2026-11-12: use
Sonnet only for ongoing model-backed work.** Gemma is unavailable per the user;
repairing, re-evaluating or adopting it is not an active task. Retain the existing
Sonnet configuration and essential verification. The completed six-case Gemma/Sonnet
pilot remains historical evidence, not an outstanding comparison or proof of
equivalence. This documentation decision does not change runtime configuration or
authorize new paid evaluation.

Keep original sources, document versions, relevant dates and relationship evidence.
New ingestion must not silently destroy conflicting evidence. Explain material
unresolved disagreements in retrieved evidence with citations; no claim of exhaustive
organization-wide conflict discovery. Keep useful existing conflict/identity review
features and records, but their failures must not block document searchability.

Advanced Conflict Resolution and Delegated Verification are later-phase features:
automatic resolution, review queues, escalation and ownership routing are not new
core requirements. Do not add tables/events/services solely to anticipate them.

## Architecture, delivery and retained requirements

Retain React/TypeScript/React Flow, FastAPI/Python, PostgreSQL/pgvector, Bedrock via
boto3, and existing worker patterns. Use ordinary modules and compatible migrations.
Use AWS CDK v2 in Python for any approved infrastructure, superseding original Terraform.
Require a concrete security/cost/deployment review before billable provisioning.
Do not adopt a new graph database, event platform or agent framework without benefit.

Earlier AWS candidates remain proposals: ECS Fargate/ECR, RDS PostgreSQL, private S3,
Cognito, Secrets Manager and CloudWatch. SQS/DLQ and EventBridge Scheduler are options
when justified, not mandatory replacements for the existing queue/scheduler approach.
Frontend delivery, HTTPS, backups/restore, availability, region and cost need review.
No service has been provisioned by this planning update.

Earlier scope items are retained: selected public Slack channels/readable replies,
named saved graph views, OneDrive/SharePoint, OCR/images/spreadsheets, private Slack/DMs
and customer onboarding. They remain tracked extensions with their prior authorization
constraints, not silently deleted or treated as replacements for Confluence/GitLab.

## Open sizing and release decisions

The previous 20-user / 50–200-document pilot assumption is not a new capacity limit.
The user discussed 100–200 employees; actual concurrency, corpus size and source scope
remain to be measured. Earlier internal-team/Jira Cloud assumptions are starting
context, not permission to connect arbitrary live data.

Before capacity/release acceptance, agree representative documents and source access;
held-out quality criteria; p50/p95 latency, concurrent load and cost targets; freshness
and ACL verification windows; retention/purge/backup behavior; deployment budget/region;
and localization release coverage. Keep unknowns explicit, not invented commitments.

## Changes from the prior scope

- Replaced a minimal-MVP ceiling with production-quality phased delivery.
- Promoted native Knowledge Hub, intelligent Spaces, Confluence and GitLab to committed
  product scope; did not reset implemented upload/wiki/search/graph/chat capabilities.
- Moved bilingual evaluation and security work earlier; English-only current state is
  preserved as fact, not a permanent product constraint.
- Replaced mandatory extraction-before-search and extensive new conflict workflows
  with independent search readiness and essential conflict safety.
- Preserved advanced conflict functionality as a later phase and existing useful
  reviews as implemented work. No destructive removal is authorized.
