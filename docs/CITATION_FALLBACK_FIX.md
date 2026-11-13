# Answer citation verification fallback

Verified locally on 2026-11-13, branch `m3.2/baseline-gemma`.

When the answer verifier rejects a statement or returns the wrong number of
verdicts, the provider now returns no statements and `insufficient_evidence=true`.
This avoids the generic HTTP 503 previously caused by this verification result.
Accepted answers retain their citations. Exact-quote validation still has its
existing bounded correction path; other provider errors retain their error handling.
The criteria for trusting factual answers are unchanged.

## Validation

- `test_grounding.py`: **7 passed** in a network-disabled container, both with
  the working source mounted and from the rebuilt image. Tests cover accepted
  answers, rejected/missing/extra verifier verdicts, exact-quote correction,
  repeated fabricated quotes, and original-text-only verification payloads.
- Built API and worker with `compose.yaml`, `compose.bedrock.yaml`, and
  `compose.company-sonnet.yaml`. Recreated only those services in the
  `linkmind-company-sonnet` project using `--no-deps --no-build --wait`.
- Used image `linkmind-company-sonnet-backend:citation-fallback` to avoid replacing
  the image tag shared by the other previews. The image includes the existing
  uncommitted F1.2 changes; those changes are separate from this fix's commit.
- API `/health` returned `status=ok`, `mode=local-demo`, `provider=bedrock`.
- Main app, mock preview, F1.1 preview, and Sonnet web/database container IDs
  remained unchanged. No migration, document retry, or paid inference was run.
- Budget ledger before and after restart was identical:
  `northstar-sonnet-2026-11-12`, limit USD 10, spent USD 2.0724137200,
  reserved USD 0.0564514400, paused false. No budget settings were changed.
- F1.3 and F1.1 main-data rollout remain pending. No AWS infrastructure or
  `private/` files were changed.

## Manual checks

Open the Sonnet preview at <http://127.0.0.1:5175> and start a fresh conversation
for each check. Manual model calls use the existing persistent test allowance.

1. Repeat the question that previously produced the citation-verification 503.
   If the verifier rejects the generated answer again, expect a normal
   insufficient-evidence response with no unsupported statements. A supported
   answer is also valid if the model produces one on this attempt.
2. Ask a known supported company question, such as who owns NS-ATLAS. Confirm
   the answer has citations and each citation opens the original passage.
3. Ask for an unsupported company acquisition date. Expect insufficient evidence
   rather than an invented date.
4. Select `atlas-handover.md` and ask what it is about. Confirm either a supported
   cited overview or an honest insufficient-evidence response.

Existing failed enrichment jobs are not automatically reprocessed by this rebuild.
The exact verifier-rejection branch is covered deterministically by the tests;
an unsupported question alone does not guarantee that branch is exercised live.
