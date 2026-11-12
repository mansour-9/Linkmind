# M3.2B — Evidence-safe processing and versioned reprocessing

**Proposal for approval; not implemented by M3.2A.** Keep Sonnet as the production
extractor and verifier. The Gemma pilot did not satisfy the strict-output gate.
No further paid evaluation is authorized by this document.

## Why these changes

M3.2A found: (1) line-wrap/hyphenation changes can invalidate otherwise plausible
PDF quotations; exact validation currently raises before correction is reached;
(2) the common semantic verifier accepted a reversed task-assignment edge;
(3) fixed 2,400-character source passages can split long sections without parent
context; and (4) published versions currently cannot be safely reprocessed in place.
The original two private PDF response bodies are unavailable, so their precise
bad quotations remain unconfirmed. Do not promise those files fixed until tested.

## 1. Preserve source truth and bound correction

- Retain original bytes, parsed source passages, IDs and locators unchanged.
  Introduce a separate normalized view with a reversible character-range map to
  each original passage. Normalize NFC, line endings, Unicode whitespace and
  typographic quotation marks. Join whitespace after a hyphen only when followed
  by a line break and a lowercase continuation; retain the hyphen itself.
- Validate the model output strictly first. If a quotation is not exact, allow a
  deterministic mapping only when its normalized text has one unambiguous match
  inside the referenced original passage. Replace the quotation with that exact
  original slice, record the mapping/repair category, and rerun the unchanged exact
  citation validator. Never alter names, numbers, dates, word order, or passage IDs.
- Reject ambiguous matches and cross-passage automatic replacements. Route
  recoverable JSON/schema/reference/quote and semantic failures through one shared
  correction envelope: at most two extraction attempts total, at most one semantic
  verification per locally valid attempt. The correction receives the validation
  feedback and the same authorized original passages. Never retry indefinitely.
- Reject failed or unsupported results after the correction limit. Keep the old
  current projection during a failed revision/reprocessing attempt.

## 2. Validate relationship direction and periods

- Give the verifier structured subject/predicate/object records, entity kinds and
  literal identifiers, exact citations, and corresponding original passages.
  Require it to check direction, attribution and effective periods explicitly.
- Add deterministic type constraints for the known predicates: `assigned_to`
  task → person/team; `belongs_to` task → project; `owned_by` project/task →
  person/team; `owns` is the declared inverse; `uses` project/system →
  technology/system; `approved_by` decision → person/team; `leads` person → team.
  Reject violations and request correction; do not guess by swapping endpoints.
- Preserve the custom-predicate path with full semantic verification. Do not infer
  unknown predicate meanings from names or silently equate management with ownership.
  Require ordered relationship date ranges, just as claims already require them.
- Add a held-out reversed-assignment regression which fails even if a mocked model
  verifier says every assertion is supported. Add inverse, period, ambiguous-name,
  source-revocation and untrusted-instruction controls.

## 3. Add a separate, bounded context/index generation

- Keep the existing `chunks` records as immutable citation passages. Do not rewrite
  their text, IDs or evidence spans to implement a new chunk size.
- Add a versioned context builder: respect headings, DOCX paragraphs/table rows and
  PDF page boundaries. Use conservative UTF-8 byte counts as the initial token
  upper-bound estimator, explicitly labeled as an estimator. Target 1,024 units,
  maximum 1,536; overlap at most 128 units only inside a long section. Add a parent
  heading/paragraph window capped at 4,096 units. Keep source-ID delimiters and
  mappings on every fragment; never combine different documents or permissions.
- Store new retrieval/context units separately with source-passage span mappings,
  policy hash, embedding model/dimensions and generation ID. Search/answer payloads
  still cite original passage IDs. Parent passages supplied to an answer become
  permission-checked saved dependencies using the existing contract.
- Keep this policy opt-in/shadow until the frozen and held-out cases show no
  citation/mandatory-fact regression. Record context duplication, unit counts,
  measured provider tokens, latency and available cost; do not infer savings from
  the estimator. No new embedding provider or vector database is introduced.

## 4. Compatible generation schema and management

- Add `processing_generations` with organization/version IDs, immutable policy
  configuration/hash, state, timestamps and validation summary. Add a nullable
  generation reference to jobs and generation references to derived entity,
  claim and relationship projections. Backfill a `legacy-v1` generation for each
  existing publication before making those references required.
- Add an active-generation pointer on each document version. Existing versions and
  citation passages remain immutable. Every current Graph/Wiki/Search/conflict
  projection must filter by both the current source version and active generation.
  Historical source evidence/downloads retain their existing authorization behavior.
- A new generation builds alongside the active one. Activate in one transaction
  only after complete validation, rechecking source access, deletion, latest
  revision, expected active generation and job lease. Preserve old records/reviews.
  A concurrent revision or activation returns a conflict rather than overwriting it.
- Add management endpoints under `/api/v1`: `POST /documents/{id}/reprocess`
  (policy allowlist `legacy-v1` / `m32-v2`, returns a queued job/generation),
  `POST /processing-generations/{id}/activate`, and
  `POST /processing-generations/{id}/rollback`. Activation/rollback bodies contain
  `expected_active_generation_id`; return HTTP 409 on mismatch. Require existing
  source access plus the existing owner/operator management rule for all actions.
  Use an organization/version/policy lock and uniqueness constraint for idempotency.
- Keep generation states distinct from existing job-status values. Existing
  `/api/v1` fields remain compatible; add generation/policy/error-category metadata
  without changing conversation scope or answer/citation schemas. Expose the
  supported management actions in Processing; show actual stages and errors.

## 5. Verification and rollout gates

1. Add the migration and generation filters in a disposable database first. Verify
   the backfill preserves legacy query results and every original citation URL.
2. Implement normalization/correction and direction guards with deterministic
   regressions. Keep existing benchmark expectations and validation strictness.
3. Build `m32-v2` in shadow mode. Verify no duplicate current facts, stale generation
   leaks, lost review history, cross-tenant access, or changed source downloads.
4. Test activation/rollback, concurrent revisions, expired leases, failed jobs,
   deletion/revocation and saved answers. Reindexing unchanged original evidence
   must not invalidate its IDs; changed/revoked source versions still suppress it.
5. Run the full API/build/browser suites and report known limitations. Request a
   separately bounded live regression run before claiming live-quality improvement.
6. Prepare a main-database backup and concrete generation preview. Main migration,
   backfill activation and deployment occur only after the approved rollout step.
   Compare original row fingerprints and test rollback before switching.

Success requires: exact source-backed citations for every admitted item; rejection
of the known reversed assignment even if the model judge approves it; no weakening
of tenant/source permissions; unchanged old source evidence; failed builds leaving
the active generation intact; and a verified reversible switch. OCR, Jira, hosting,
Arabic, GraphRAG orchestration and a production Gemma switch remain outside this plan.
