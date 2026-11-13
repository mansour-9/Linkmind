# F1.3 — Staged enrichment and rollout preparation

Completed and locally verified 2026-11-13 on `m3.2/baseline-gemma`.
The user authorized F1.3 plus main-data rollout preparation before F2, including
bounded Bedrock checks under the existing persistent USD 10 run.

Open the isolated mock preview at **http://127.0.0.1:5181**. The original app,
existing F1.1 preview, company mock preview and Sonnet preview were not migrated
or replaced by this milestone. F2 and the main cutover remain pending.

## Delivered behavior

- **Refresh knowledge** creates a staged candidate from the current immutable
  source. Original bytes, revision IDs, passages, embeddings and citation IDs remain.
- Search and prior verified same-source facts stay available while extraction,
  exact evidence validation and conflict assessment run. The pending result cannot
  appear in Graph, Search metadata, Wiki, identity review or conflict surfaces.
- Verified activation switches one enrichment pointer in the publication transaction,
  guarded by source revision, tenant/deletion, current job token and lease. Older
  jobs cannot replace a newer revision. Exact source-local entity/evidence anchors
  preserve reviewed identities; similar names across sources do not merge.
- A failed candidate is `rolled_back`; its job is `enrichment_staged_failed`.
  Previous valid live knowledge remains, with a clear retained-knowledge message
  when it actually exists. Retry creates a new candidate, preserving failed history.
- New source revisions still follow F1.1: superseded source relationships remain
  historical, rather than being presented as facts about newly activated text.
- Expired/replaced workers, deletion, unauthorized refresh requests and competing
  revisions fail safely. Retained generations, review records and evidence are not
  deleted. Existing conflict/identity functionality remains available.
- Saved answers record the source/enrichment generations they used. Activation or
  revocation suppresses stale history and context. Validation policy is now
  `grounded-v4-staged`; older experimental answers remain stored but are hidden.

## Schema and publication boundary

Additive migration **0011_staged_enrichment** adds the requested
`processing_jobs.staged_version_id` and `document_versions.activation_state`
(`live`/`staged`/`rolled_back`). Minimal supporting metadata records source lineage,
the active enrichment pointer, verified candidate JSON/time and each entity's
generation. Composite foreign keys prevent a candidate being assigned to another
source or tenant. Shared live-fact views select the active generation before the
existing source-current and permission filters on every derived surface.

Legacy IDs and content need no destructive backfill. The job status constraint is
expanded without deleting jobs. Existing source/evidence foreign keys remain intact.
Downgrade is permitted only before any retained generation or incompatible active
job exists; later recovery uses the reviewed database/originals snapshot and old build.

The source row can represent a historical enrichment generation while still being
the current searchable source. `activation_state` governs enrichment; source search
continues to use `documents.current_version_id`. These boundaries are deliberately
independent.

## Verification

Machine-readable run summary: [F1_3_VALIDATION.json](F1_3_VALIDATION.json).

- **127 API tests passed**, including staged activation, rejection/empty replacement,
  rollback/retry, concurrent database sessions, stale leases/revisions, source/tenant
  constraints, unchanged citations, generation-aware history and access revocation.
- **28 browser workflows passed**, covering the new refresh/failure journey and
  existing uploads, revisions, discovery, chat, source selection, Graph, reviews,
  permissions, errors, history and responsive navigation. The final user-facing stage
  labels were subsequently checked with the two focused refresh browser tests.
- Frontend TypeScript check and production build passed. Screenshots inspected at
  1440 and 390 px; overflow/layout checks also covered 1024 and 1920 px. Refresh uses
  the existing confirmation Sheet, shared buttons, errors and readiness presentation.
- The three previously reproduced baseline failures are resolved: runner failure
  checkpoints now stop correctly and its test counts ordinary/revision questions
  separately; preview auth tests explicitly set and verify their intended mode;
  index repair tests allow other approved corpus fixtures while excluding arbitrary
  uploads. No failing full-suite result is represented as a pass.
- The broader run caught and fixed two integration regressions: preserved enrichment
  remains counted as available after a failed refresh, and an ordinary content topic
  matching its filename still produces source excerpts rather than unwanted discovery.
- Incomplete extraction-verifier output now fails closed after the bounded correction;
  it cannot promote all assertions as verified by default.

## Real Sonnet evidence

[Single-source probe](company_demo/f13_sonnet_probe.json) used the real configured
Sonnet extraction/semantic-verification path on `atlas-charter.md`, a fictional
Northstar fixture. It returned **3 entities, 4 claims and 2 relationships** with
valid original evidence.

Recorded spend moved from **USD 2.0724137200 to USD 2.0997707200**:
**USD 0.027357** for this probe. The existing run ID and USD 10 limit were preserved,
along with USD 0.0566168200 in prior unknown reservations. No new budget, reset,
increase, credential change, infrastructure or Gemma comparison was performed.

[Staging application evidence](company_demo/f13_staging_probe.json) applied the
recorded verified Sonnet result through actual isolated staging/activation without
another paid call. A subsequent deterministic unsupported-quote injection rolled
back and retained that generation. This establishes a bounded real-output integration
check, not a broad production-quality model benchmark or live connector acceptance.
Arbitrary uploads still require a real configured provider for AI extraction; mock
mode provides searchable text and original excerpts without inventing graph facts.

## Rollout preparation and remaining boundary

The [main-data rollout review](MAIN_DATA_ROLLOUT.md) is concrete and supported by
[synthetic backup/restore evidence](F1_3_REHEARSAL.json). It covers schema 0010→0011,
consistent database/originals backup, restored fingerprints/citations, staged refresh,
and recovery of the previous build in another empty stack. An initial archive-close
bug was found by restore verification, corrected, and followed by a complete passing
fresh rehearsal. Local dumps and originals remain ignored under `.local/`.

Read-only inventory found the main schema already at **0010**, not the older
unmigrated assumption. Its current API/worker inference-budget configuration is
inconsistent and does not share the approved Sonnet preview ledger. The proposed
cutover therefore keeps inference disabled until that arrangement is reviewed;
it must not initialize a second USD 10 allowance. The actual main snapshot rehearsal,
maintenance window and cutover require their own approval. Main data fingerprints
remained unchanged throughout this milestone.

F1's broader held-out context/ranking acceptance remains under the F1/R1 roadmap;
production identity/groups/Space permissions remain F2. These are not marked complete
by a staging feature, a mock test suite, or one Sonnet probe.

## Manual checks

1. Open **5181 → Admin Console → Data Sources**, expand **Manage source** for a
   recognized sample, and select **Refresh knowledge**. Confirm the explanation,
   then start the refresh. Search remains available and the knowledge returns ready.
2. Inspect **Processing → F13-atlas-charter.md**, retained from the recorded Sonnet
   probe. Its deliberately failed candidate shows **Refresh rolled back** and that
   previous verified knowledge remains available. Search/citations still resolve.
3. Upload arbitrary TXT/Markdown/PDF/DOCX data in the mock preview. Valid text becomes
   searchable; AI enrichment honestly reports unavailable. A refresh failure leaves
   search ready and offers retry without claiming nonexistent prior graph facts.
4. Verify saved answers are suppressed after successful generation activation or
   revoked access, while an authorized original citation can still be opened.

No new paid calls are needed for these mock checks. Existing Sonnet manual use on
5175 continues to share its unchanged persistent test ledger; F1.3 was not rolled
out into that preview's database as part of this isolated milestone.
