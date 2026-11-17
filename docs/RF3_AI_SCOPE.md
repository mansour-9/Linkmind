# RF3 bounded Bedrock acceptance — 2026-11-15

The user requested starting containers, testing RF3 with real AWS Bedrock AI,
providing the AWS sign-in link, and planning RF4 after reviewing RF3 results.
This is authorization for the following local test slice, not AWS hosting.

## Concrete scope

- Keep the RF3 mock regression stack at 5192; use separate RF3 AI content at 5193.
- Use only the fictional `code/fixtures/retrieval/corpus.json` sources: roles,
  Arabic policy, English policy, approved decision, unapproved draft, long notes,
  and retained release history. Exclude the private finance fixture from model input.
- Index at most 72 previously unembedded passages using Titan V2, 256 dimensions.
  Reuse compatible vectors; retain exact passage text and IDs. No enrichment.
- Run eight prompts: Arabic team responsibilities from long English notes;
  ambiguous follow-up; English question over Arabic policy; approved/draft date
  comparison; Arabic previous/current revision comparison; English source summary;
  unsupported budget question; stored-only operational status question.
- At most 24 Sonnet calls and 80 total embedding calls (indexing plus queries),
  sequential dispatch, 15 minutes total, existing per-question runtime bounds.
- At most USD 1.50 in cumulative conservative dispatch reservations for this test,
  inside the original `northstar-sonnet-2026-11-12` cumulative USD 10 ledger.
  The slice is not a new allowance. No ledger clone/reset/increase/unpause or release
  of historical unknown reservations. Unknown usage pauses further test dispatch.
- Mandatory original citation validation and independent semantic verification stay
  enabled. No repeated paid question or automatic retry of a started test report.
- Stop on provider/authentication/usage uncertainty, an unavailable/paused guard,
  exhausted bounds, or completion. Preserve partial results without rerunning them.

## Evidence and limits

Run deterministic regressions and retrieval comparison before real-model dispatch.
Record source-only counts, exact citation matches, actual model/operation usage,
cost, latency, outcomes and failures. Inspect actual answers against originals.
These authored synthetic questions establish bounded acceptance only; questions
already used during development are not independent held-out quality evidence.

Main, RF1 5189, RF2 5191 and their data/builds remain protected. Starting their
database containers solely to inspect fingerprints or use the original ledger does
not authorize migrations or application/worker startup. Only normal shared ledger
and pacing writes from this authorized trial may change the original budget store.

The AI preview's background worker remains mock/lexical-only. Paid semantic indexing
is limited to the explicit harness; UI answers use Sonnet and the original shared
guard. Interactive questions, if used by the user, consume the same cumulative cap.
The English product UI and Arabic answer text remain distinct from full RTL release
acceptance. RF4 planning follows; no connector account access or sync is authorized.
