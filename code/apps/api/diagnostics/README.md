# M3.2A diagnostic runner

> **Historical diagnostic tooling — 2026-11-14.**
> This runner and the Gemma comparison are not active RF work. The
> [single roadmap](../../../../docs/IMPLEMENTATION_PLAN.md) prioritizes lightweight
> source ingestion/retrieval; no model comparison, paid run or service command is
> authorized by this documentation update. Keep frozen artifacts and Sonnet-only
> ongoing model policy. Original runner mechanics/budget limits below are historical
> implementation details, not permission to repeat the experiment.

This package is explicitly invoked and is not imported by the API or worker.
Production providers, schemas, jobs, documents and model settings are unchanged.
See `docs/M3_2A_RESULTS.md` for the frozen pilot and limitations.

## Offline / CI

Run inside a disposable mock Compose project after its migrations:

```sh
docker compose -p linkmind-m32-validation -f code/compose.yaml run --rm --no-deps api python fixtures/generate_m32_cases.py --check
docker compose -p linkmind-m32-validation -f code/compose.yaml run --rm --no-deps -v "$PWD/results:/results" api python -m diagnostics.m32 --out /results
docker compose -p linkmind-m32-validation -f code/compose.yaml run --rm --no-deps api pytest -q apps/api/tests
```

The default runner performs the format matrix and synthetic reproduction without
creating an AWS client or making an AWS request. The real private PDFs and their
contents are not fixtures. `code/fixtures/m32/unicode.txt` deliberately preserves CRLF.

## Preflight and a separately approved live run

The paid pilot requires `--live` and existing local AWS authentication. It uses a
one-off container with the local `.aws` directory mounted, never CI secrets or the
main database. Keep the API and worker in mock mode; mount AWS only into that one-off
runner. `--preflight` checks sign-in, models, existing default project and prices
without inference. No key, project, profile, IAM policy or resource is created.

Before a future live run, obtain a new explicit run scope/budget. The completed
M3.2A authorization is not a standing budget for repeated runs. Maximums remain
24 inference attempts / US$5 projected spend. Each call reserves a conservative
input/output allowance on disk first; failed or missing usage stops further calls.
SDK/HTTP retries and correction runs are disabled. A preexisting ledger cannot be
reset by the runner. Do not delete it to evade the approved request allowance.

The runner writes `frozen.json`, `live.json` and `ledger.json`. It retains final
synthetic outputs and token usage, not credentials, headers or separate reasoning
traces. Failed schema/quote checks skip the corresponding verifier call; unused
slots are not reassigned. `manifest_sha256` in `frozen.json` is canonical-JSON SHA-256.

Summarize a completed report without further inference:

```sh
python -m diagnostics.m32_report /results/live.json --out /results/summary.json
```

Scoring uses pre-response gold and aliases. Schema-failed output is never fence-
stripped or treated as accepted. Literal gold mismatches and independent source
review must be reported separately from the common model-verifier result.
