# Conversational discovery and follow-up testing

Implemented 2026-11-13 following the user's request for natural questions,
approximate source names, clarification, and follow-ups on arbitrary uploads.
This is a focused increment before F1.3; no F1.3 migration or main-data rollout.

## Behavior

- Greetings and application help return local guidance, without model calls.
- Source discovery searches current authorized filenames approximately, including
  transposed acronyms such as PREFQA/PRFAQ, and falls back to passage retrieval
  for topics. Suggestions are possible matches, not proof of every requested fact.
- Similar filenames and unconfirmed same-name identities can prompt clarification.
  Choose a source button, reply with an ordinal, describe the distinguishing name,
  or request both/a comparison. Source selection is resolved server-side against
  the preceding authorized suggestions, never an arbitrary client-supplied ID.
- General Sonnet questions use at most one query-understanding call, with a
  512-output-token limit, before existing bounded retrieval/answer verification.
  It interprets casual wording and Arabic/English follow-ups using up to three
  reauthorized prior turns. The original user question still governs the factual
  answer. Conversation text alone never becomes source evidence.
- Metadata-only suggestions have their own document/version checks, including
  saved history, before planning, and before saving responses. Revoked, deleted,
  superseded, cross-organization, and out-of-scope sources cannot be selected.
- Valid uploaded text remains usable even when enrichment is unavailable.
  Mock mode gives original excerpts; arbitrary files do not receive invented mock
  extraction. Search degradation is disclosed. Catalog responses do not claim
  that Sonnet generated cited evidence.

Source discovery is bounded to 200 prefiltered filename candidates, six displayed
matches, and the existing passage budgets. It is not exhaustive fuzzy matching of
an unlimited catalog. Context understanding remains subject to the model's quality;
new real-model acceptance has not been claimed from mock tests.

## Add your own data

Use **Add documents** on Home, or **Admin Console → Data Sources → Add data source**.
Supported formats: selectable-text PDF, DOCX, UTF-8 TXT and Markdown; 20 MiB limit.
Use **Only me** for owner-only data or **My organization** for shared test data.
Wait for **Search Ready**. Enrichment failure does not require another upload for
text retrieval; unreadable/scanned PDFs still need a text-based replacement.

Three fictional files are available in `code/fixtures/conversation_demo/`:

- `Harbor_Handover_PRFAQ.md`: Leena owns the proposal; rehearsal January 12, 2027.
- `Harbor_Handover_PRFAQ_Updated.md`: separate draft, proposed owner Rami and
  rehearsal January 19, 2027; no automatic authority/supersession claim.
- `Harbor_Travel_Notes.md`: unrelated workshop in Riyadh on February 18, 2027.

Upload the two PRFAQ files separately to test ambiguity, not as revisions of one
document. These are arbitrary documents for mock extraction; excerpts remain usable.

Try a new conversation:

1. `what is this caht do?` — application guidance, no insufficient-evidence warning.
2. `is there a file about the Harbor handover?` or `any PREFQA file?` — source matches.
3. `the updated one` or select its button — context from that source.
4. `who owns it?` then `when is its rehearsal?` — follow-ups retain the chosen source.
5. Start another source lookup, then `compare them` — use both attributed proposals.
6. `find files about travel` — move to the other topic without retaining the PRFAQ scope.
7. Arabic in Sonnet mode: `عندك ملف عن تسليم الدعم؟`, then `الثاني`, then `متى موعده؟`.
   Natural bilingual understanding requires a working model session; mock mode tests
   deterministic routing and original excerpts, not translation or synthesis quality.

## Evidence and operational limits

- Focused API tests: **43 passed** (conversation, grounding, search readiness).
- Broader API run with `PYTHONPATH=/app:/app/apps/api`: **107 passed, 3 failed**
  before the final extra acronym case was added. The three failures also reproduce
  with the previous `company-brain-backend:local` image: company index test depends
  on an empty corpus; runner test expects an earlier stopping behavior; preview-auth
  test expects remote blocking in a non-preview mock configuration. They are not
  reported as fixed or as a fully passing regression suite.
- Six browser workflows passed: new upload/discovery/choice/follow-up/topic-switch
  journey plus existing company-demo and search-readiness workflows. Source choice
  works with Enter; screenshots were checked at 1440/390 px and overflow checks
  passed at 1440/1024/390/1920 px. Frontend typecheck and production build passed.
- Tests run only in `linkmind-conversation-validation`, port **5180**, mock mode.
  No paid evaluation, source retries, or main-app migrations were performed.
- Sonnet preview remains at **5175**. Its ledger was **paused** following
  `LoginRefreshRequired` on an embedding attempt at 2026-11-13 14:42:20 UTC.
  At discovery: limit USD 10, spent USD 2.0724137200, reserved USD 0.0566168200.
  The implementation did not reset, increase, reconcile, or unpause that ledger.
  Refreshing AWS credentials alone did not clear the persisted pause. The later
  user-approved resume is recorded below; the same run is now unpaused.

The isolated mock preview can test uploads, approximate discovery and clarification
without paid calls while Sonnet is paused. Its answers remain clearly labelled excerpts.

API, worker and web were rebuilt/recreated only in `linkmind-company-sonnet`, using
all three existing Compose files and backend image
`linkmind-company-sonnet-backend:conversational`, with no dependency restart/migration.
The API health and frontend proxy returned HTTP 200. A read-only catalog smoke check
of `any PREFQA file?` found the existing search-ready
`Smart_Handover_Assistant_PRFAQ.pdf` without calling Bedrock. The paused ledger was
identical immediately before and after the preview update. The main app, earlier
F1.1 preview, mock company preview, and Sonnet database retained their container IDs.

AWS login was renewed on 2026-11-13 at the user's request. STS identity verification
succeeded in both the local default profile and the running Sonnet API container.
The persisted budget remains paused with the same limit, spent and reserved values;
sign-in did not resume model calls or reconcile the prior unknown reservation.

The user subsequently approved resuming the existing run on 2026-11-13. Only its
persisted `paused` flag was cleared, after verifying there were no in-flight
reservations and spend plus retained reservations remained below the USD 10 cap.
The run ID, USD 10 limit, USD 2.0724137200 recorded spend and USD 0.0566168200
reserved amount were preserved. All three unknown reservations remain charged
against available headroom; none was released or treated as a confirmed zero-cost
call. No paid validation call was made as part of resuming the run.
