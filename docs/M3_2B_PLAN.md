# M3.2B — Independent search readiness and evidence-safe processing

> **Superseded delivery plan — 2026-11-14; retained for history.**
> Use [the active RF roadmap](IMPLEMENTATION_PLAN.md), [scope](PROJECT_SCOPE.md)
> and [current/target architecture](ARCHITECTURE_M2_M3.md). Old unchecked work and
> next-task wording below are not an active queue. F1.2 and F1.3 were subsequently
> implemented locally; main rollout remains pending. RF1 targets default-off
> enrichment, not another mandatory extraction-repair cycle. No implementation,
> model call or rollout is authorized by the current documentation request.

Updated 2026-11-12. **F1.1 implemented and validated in an isolated local stack;
F1.2/F1.3 remain planned.** The user requested starting F1.1; the main running
database/application has not been migrated. See [results](F1_1_RESULTS.md). This
elaborates F1 in the [main roadmap](IMPLEMENTATION_PLAN.md); other slices, new
infrastructure and paid evaluation are not authorized. Use Sonnet only for ongoing
model-backed work and retain its existing configuration. Gemma is unavailable per the
user's 2026-11-12 decision; repairing, re-evaluating or adopting it is not an active task.
The completed comparison and its frozen results remain historical evidence.

## Findings retained from M3.2A

Exact quotation validation currently raises before semantic correction; a synthetic
line-wrap case reproduced the failure class. A reversed task-assignment edge passed
the common model verifier. Gemma returned fenced JSON rejected by the strict integration;
that is not a factual-quality verdict. Fixed 2,400-character passages can lose context,
and published versions cannot safely be reprocessed in place. Original private-PDF
response bodies are unavailable; do not promise those files fixed before checking them.

## Design change from the earlier proposal

Previously, one complete validated projection gated all publication. Now **searchable
content and structured enrichment have separate readiness/activation boundaries**.
An enrichment or cross-document conflict failure cannot hide valid authorized text.
Preserve the previous search revision if parsing/index preparation fails. Once a new
content revision is search-ready, do not keep the older revision's relationships active
as though they describe the new current content. Preserve those records as history.

This is not permission to skip source/ACL checks, publish unsupported relationships,
or delete useful conflict review. It removes a blocking dependency, not evidence safety.

## F1.1 — Search-ready content independently of enrichment

- [x] Add a regression for valid parsed text with extraction/conflict assessment failure.
  Search and answers may use its authorized source passages, while graph results omit
  unsupported enrichment. Test new uploads and revisions separately.
- [x] Design the smallest additive readiness representation using existing document
  versions/chunks/jobs; keep content and enrichment status distinguishable internally.
- [x] Publish the search-ready revision after bounded parsing/indexing and source/access
  checks. If embeddings fail but lexical indexing succeeds, expose degraded semantic
  readiness honestly. An authorization failure never becomes degraded public access.
- [x] Update retrieval, current graph/wiki projections and saved dependencies consistently.
  Old evidence remains addressable to authorized viewers; no stale current relationships.
- [x] Separate enrichment execution/failure from content publication using existing
  worker patterns. Preserve conflict/review records and useful existing review behavior.
- [x] Expose real Processing/Search Ready/Enrichment states without rewriting old job
  history or falsely marking full knowledge enrichment complete.

Exit: extraction/conflict failure does not prevent supported search; concurrent revision,
deletion, revoked access and replaced leases cannot publish unauthorized or stale state.

### Focused F1.1 implementation sequence

Prepared and implemented 2026-11-12 from inspection of processing.py, retrieval.py,
main.py, existing migrations/tests and the Processing UI. The first slice passed
isolated validation; F1.2/F1.3 remain later slices. Use Sonnet for model-backed extraction,
verification and answers; retain the separately configured embedding model.

1. **Freeze the failure and acceptance cases.** Add disposable-database regressions
   for a new upload and a replacement revision whose valid parsed text survives
   extraction failure, plus a conflict-assessment failure. Verify source passage
   retrieval/citation independently of enriched entities and relationships. Keep
   arbitrary-document fixture extraction unavailable honestly; do not fabricate AI.
2. **Define compatible readiness and activation.** Record search readiness separately
   from enrichment completion using the smallest additive version metadata. Prefer
   retaining current_version_id as the active content revision and explicitly gating
   current enrichment to that revision's successful publication; confirm all consumers
   before finalizing the schema. Preserve processed_at's existing meaning or migrate
   its consumers explicitly. Backfill only demonstrably published legacy content;
   previously failed revisions must not become active merely because chunks exist.
3. **Separate the worker publication boundaries.** Prepare bounded parsed/indexed
   content and activate it before extraction/conflict assessment. Each activation
   rechecks lease ownership/expiry, deletion and revision ordering under appropriate
   locks. Preserve previous active content on parsing/index-preparation failure.
   Enrichment uses its own atomic validated publication and cannot revert the content
   pointer. Its failure leaves searchable text available with an honest error.
4. **Align retrieval and evidence consumers.** Audit Search, Chat dependencies, graph,
   generated knowledge, conflicts, People/entity views and document/source pickers.
   Text matching must work without an entity join. Query-embedding failure must not
   discard valid lexical results; preserve authorization and report degradation.
   A newly active revision invalidates old saved-answer dependencies and excludes old
   relationships from current views while retaining authorized historical citations.
5. **Make retries and UI states truthful.** Review retry/immutability guards so a
   search-ready revision with failed enrichment can safely retry that unfinished work
   without duplicating enrichment or changing passage IDs. Distinguish search readiness,
   enrichment failure and semantic-index availability in API contracts and shared UI.
   Preserve existing attempt history, downloads and working fixture journeys.
6. **Validate and report before rollout.** Cover parser failure, unavailable/failed
   embeddings, extraction/conflict failure, duplicate retries, superseding revisions,
   expired/replaced leases, deletion, access changes and historical citations. Run
   relevant API regressions, frontend build and affected browser workflows on disposable
   services. Inspect desktop/mobile and keyboard states. Record actual results and
   remaining independent-quality limitations; do not mark all F1 or M3.2 complete.

Deliverables: focused regression coverage, compatible readiness migration if needed,
worker/retrieval/API/UI changes, and updated architecture/runbook/status evidence.
Prepare a backup, concrete backfill preview and tested rollback before touching the
main database. F1.1 migrated only disposable databases and made no paid model call. M2/M3's
representative document/question review can be prepared alongside F1.1; the full
dataset is not a prerequisite for these deterministic reliability regressions.

## F1.2 — Safe correction and relationship safeguards

- [ ] Retain original bytes, passages, IDs and locators. Build a normalized comparison
  view only where necessary, with a reversible map to original character ranges.
- [ ] Strictly validate first. Recover a quote only when one unambiguous normalized
  match maps to an exact original slice; rerun original-source validation and record
  the repair. Never alter names, numbers, dates, ordering or passage identity.
- [ ] Evaluate NFC/line-ending/whitespace/typographic-quote normalization against frozen
  cases. The earlier hyphen/line-break heuristic is a candidate, not a license to change
  word meaning. Reject ambiguous or cross-passage automatic replacements.
- [ ] Allow bounded transport formatting repair (such as a sole fenced JSON object)
  without accepting malformed schemas or unsupported content. Do not reinterpret the
  frozen Gemma pilot scores after repair or switch the production provider implicitly.
  This is a general Sonnet processing safeguard, not a Gemma compatibility task.
- [ ] Route recoverable format/schema/reference/quote failures through one bounded
  correction envelope: at most two extraction attempts, no unbounded retries.
- [ ] Enforce known predicate endpoint types and direction: task assigned_to person/team;
  project/task owned_by person/team; uses appropriate project/system and system/technology
  endpoints; decision approved_by person/team. Retain declared inverses deliberately.
  Do not guess by swapping endpoints or equate assignee, manager and owner.
- [ ] Validate periods and unknown/custom predicates carefully; uncertain semantics
  receive deeper verification or remain unpromoted. Give semantic checks ordered
  subject/predicate/object and original evidence/context when invoked.
- [ ] Keep essential deterministic checks always. Evaluate selective semantic verification
  by uncertainty/consequence against the existing baseline before reducing blanket calls.
  A verifier boolean or exact quote alone is not proof of factual support.

Exit: reversed-edge regression fails even with an approving mock verifier; valid repaired
quotes cite exact originals; unsupported results remain excluded without hiding valid text.

## F1.3 — Reprocessing, context and compatible activation

- [ ] Keep chunks as stable citation passages. Store only the derived context/index
  mappings and generation metadata required for repeatable reprocessing and rollback.
  Preserve source version, policy/model/dimension identifiers and active generation.
- [ ] Evaluate structure-aware context respecting headings, paragraphs, table rows and
  page boundaries. Bound overlap and parent context; never combine permissions/sources.
- [ ] Earlier proposed 1,024 target / 1,536 maximum / 128 overlap / 4,096 parent units
  based on UTF-8 bytes are candidate experiment settings, not tokens or accepted optimum.
  Measure provider tokens, retrieval benefit, duplication, latency and cost before adoption.
- [ ] Backfill a legacy generation compatibly if a new generation table is necessary.
  Build beside active data, validate each projection and switch under expected version/
  generation/lease checks. Preserve review history and citation URLs. No new queue per stage.
- [ ] Reprocessing/activation/rollback controls must be authorized and race-safe; exact
  API routes/schema are implementation design, not mandatory complexity. The former
  /documents/{id}/reprocess and /processing-generations/{id}/activate|rollback routes
  remain possible compatible designs, not an instruction to build three services.
- [ ] Keep search activation independent from enrichment success. Reject a failed derived
  generation without corrupting current evidence. Historical rollback must be deliberate
  and must not bypass source deletion/access or make superseded facts current accidentally.

## Validation and rollout

Use a disposable database first. Test old-citation preservation, original downloads,
legacy queries, parser/format limits, generation/revision races, duplicate retries,
lease expiry, partial enrichment, graph version filters, permissions and saved answers.
Run relevant API/build/browser suites. Preserve old gold, reports and fingerprints.

Before a main-data migration, prepare backup, concrete backfill/activation preview and
tested rollback. F1.1 main-data rollout is still pending. Live-model regression
requires its own approved scope/budget; mock success is not proof of live answer quality.
Record original-PDF uncertainty and independent-quality-review limits explicitly.

No new conflict engine/review queue/ownership routing belongs here. Existing conflict
functionality is preserved where useful, decoupled from searchability. Rich authoring,
Space management, connectors and hosted deployment remain in the main roadmap, not
out of product scope. Arabic/English evidence tests inform this work; full RTL UI is L1.
