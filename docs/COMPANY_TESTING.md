# T1 — Fictional company testing

Updated 2026-11-12. The user authorized the complete test experience and **US$10
maximum** for the new Sonnet extraction/embedding/chat run. Mock workflows are
implemented and validated. The Sonnet run is **complete**; real-model acceptance is
confirmed. See [validation_summary.json](company_demo/validation_summary.json).

Operational update 2026-11-13: the preview now includes conversational source
discovery/clarification and user-data test files; see
[current testing guide](CONVERSATIONAL_TESTING.md). The persistent Sonnet ledger
was paused after `LoginRefreshRequired`. AWS login was renewed and the user then
approved resuming the same run on 2026-11-13. It is now unpaused; the USD 10 cap,
recorded spend and unknown reservations were preserved. The historical completed-run
figures below are not a new evaluation of the conversational changes.

F1.3 update: the [isolated staged-enrichment milestone](F1_3_RESULTS.md) is now
verified at port 5181. One authorized real-Sonnet fictional-source probe added
USD 0.027357 to the existing ledger (recorded spend now USD 2.0997707200), with
prior unknown reservations retained. The Sonnet preview's database was not upgraded
to F1.3; its original test experience remains at 5175.

## Open the right preview

| Address | Purpose | Data and cost |
| --- | --- | --- |
| http://127.0.0.1:5177 | Northstar mock preview | 24 loaded fictional documents; deterministic fixture graph and verbatim evidence excerpts; no paid inference |
| http://127.0.0.1:5175 | Northstar Sonnet preview | Separate fictional dataset; real Sonnet/Titan calls share one persistent US$10 allowance; run complete ($1.59 spent) |
| http://127.0.0.1:5176 | Earlier F1.1 preview | Existing user uploads remain here; not copied into the paid test |
| http://127.0.0.1:5173 | Original application | Running application/database unchanged |

These are local demo identities, not production employee authentication. The two new
previews use separate Docker projects/databases/artifact volumes from the original app.

## Try the company

1. Open the mock preview as Amal. Go to **Admin Console → Data Sources** and expand
   **Try sample documents**. Find **Northstar Labs test company**.
2. The **Load fictional company** action reuses already loaded sources. Current source
   revisions are preserved; loading again does not silently undo your edits.
3. Expand **Example questions and expected results**. Each question opens a new chat
   with its supporting sources selected. Expected outcomes are fictional test gold,
   authored for this dataset; they have not received independent company-data review.
4. Select `atlas-handover.md` and ask **What is that?**, **What is this about?** or
   **Summarize this document**. Mock mode returns labelled excerpts. Sonnet mode can
   produce a supported summary. Source context is supplied even when the question has
   no matching keywords. Open **Show work**, citations and original downloads.
5. Say **hi**. The assistant gives guidance without a paid model call or a misleading
   zero-evidence failure. A vague request with no selected/prior source asks for a source
   or topic. Named topic questions continue to use ordinary retrieval.

## Add information and test revisions

- Use **Add data source** for your own files. In mock mode arbitrary valid text becomes
  searchable, but no extracted entities/relationships are invented. Only exact checked-in
  fixture bytes get deterministic extraction. Editing any fixture removes that match.
- The sample panel provides **Download an addition to upload**. It says NS-ATLAS has
  a support drill on December 15, 2026. Upload and search `support drill`; inspect the
  original evidence. Sonnet mode can enrich newly uploaded content within its allowance.
- Download **Atlas handover revision**, then use **Manage source → New revision** on
  `atlas-handover.md`. The task deadline changes from December 3 to December 8, 2026.
  The charter's launch plan remains a separate statement. Current results move to the
  new revision, old relationships become historical and old citations remain accessible
  to authorized users. Saved answers depending on superseded evidence are suppressed.
- Changing a conversation's selected sources starts a new conversation. Uploading a
  file with **My organization** shares its indexed content within that organization;
  **Only me** restricts it to its owner. External connector/source ACLs are not simulated
  as completed live integration.

## Permissions and evidence checks

The pack contains Atlas, Beacon, Cedar, Delta and Ember projects; five people and
teams; handovers/tasks; database decisions; status notes; onboarding; an English/Arabic
leave policy; and one owner-only Ember budget. Use explicit project/email/URL identifiers
to link entities; authors and people described in sources are distinct concepts.

- Amal can inspect the owner-only budget. Omar, another user in the same organization,
  cannot retrieve that source, its budget claim, filename or private gold answer through
  the demo API. Nour belongs to a separate organization and sees none of the loaded data.
- Beacon's charter names Omar Nasser as owner; its status note names Lina Faris. Both
  are fictional source assertions. A supported answer should preserve the unresolved
  disagreement with citations rather than invent an approved winner.
- An acquisition-date question has no supporting evidence. A safe answer abstains.
- Long/multiple selected sources use a bounded overview, with partial coverage shown.
  Passage selection is not a claim of exhaustive document or organization review.

## Sonnet run, spend and outcome

The approved run is `northstar-sonnet-2026-11-12`, capped at USD 10 across extraction,
verification, document/query embeddings and answers. Do not reset this ID, delete its
ledger, raise its limit or treat old M3.2A budgets as reusable approval. The cap persists
across API/worker restarts. Future manual use of this preview consumes the same allowance.

Read-only preflight verified the existing default AWS session, active Sonnet 4.6 US
profile and Titan V2 model. Rates were read from the official AWS regional catalogs:
[Sonnet catalog](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrockFoundationModels/current/us-east-1/index.json)
and [Bedrock/Titan catalog](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrock/current/us-east-1/index.json).
Applicable rates and price dimensions are frozen in [rates](company_demo/rates.json);
[scope](company_demo/run_scope.json) freezes the fictional corpus hash and USD 10 limit.
No Gemma call, infrastructure deployment, IAM change or quota modification is included.

**Run completed 2026-11-12.** Spent: USD 1.587 of USD 10 cap (remaining: ~USD 8.36).
Full checkpoint at [live_checkpoint.json](company_demo/live_checkpoint.json);
evidence summary at [validation_summary.json](company_demo/validation_summary.json).

- 14 of 15 questions answered (Q14 is revision-mode, handled in revision stage)
- 9 questions: full pass; 2: content-pass (conflict detection, selected-document overview)
- 5 original failures (Q4/Q5/Q9/Q10/Q11): temporary empty-retrieval (vocabulary mismatch
  before semantic index ready); all 5 pass on retest with 8–13s Bedrock latency
- Revision stage passed: old answer suppressed; December 8 deadline correctly returned
- User addition: enrichment failed, raw text search-ready (expected F1.1 behavior)

Initial expiry: `ExpiredTokenException` during first ingestion wave (USD ~0.16 spent).
Run resumed after `aws sso login`; prior questions not repeated (budget guard prevents it).
The USD 0.16 / USD 1.587 figures cover different run phases, not a discrepancy.

Enrichment failures observed across 17 of 24 documents (all text remains search-ready):

- 5 decision documents: `project_key` namespace rejected for non-project entities — fixed
  in F1.2 (contracts.py now allows `project_key` for `decision` entities)
- 12 documents: unsupported assertions after bounded correction — fixed in F1.2 (providers.py
  now prunes unsupported assertions instead of rejecting the full extraction)

Existing original private-PDF failures are not claimed fixed.

## Implementation and verification

- Generated corpus: `code/fixtures/company_demo/`, deterministic builder
  `code/fixtures/generate_company_demo.py`; 24 initial files, one revision and one
  arbitrary-addition file. `manifest.json` holds exact hashes, records and 15 questions.
- API: permission-checked company loading/status/files, selected-source context,
  nonfactual greeting/guidance, current evidence and persistent test-budget ledger.
- UI: sample panel, scoped question links, working downloads/additions/revisions,
  provider/budget labels, real processing states and partial overview coverage.
- Complete mock API/browser validation and production frontend build passed; final
  counts and the live interruption are recorded in `docs/company_demo/validation.json`.
- The budget tests cover concurrent reservations, fixed limits, unknown/excess usage,
  SDK dispatch refusal, one-attempt budgeted SDK configuration and unaffected
  unbudgeted operation. Source tests cover exact-fixture recognition, edited-file
  rejection, privacy, idempotency, bounded overviews and revocation/history suppression.
- Browser screenshots of the selected-document journey were inspected at 1440 and
  390 px; the full suite also checks 1024 and 1920 px. Agent inspection is not user
  visual acceptance or a real-model quality benchmark.

F1.2/F1.3, independent real-company question review, production sign-in, native
authoring, managed Spaces, connectors and hosted release retain their own roadmap gates.
