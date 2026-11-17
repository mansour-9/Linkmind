# Linkmind — Real AI and Mock Testing Policy

2026-11-17 demo delivery: the user explicitly approved simplifying ordinary automatic
chat to one answer pass, simple links and basic grounding. Independent statement
verification remains on older advanced explicit-source paths, not the demo auto path.
Small real Bedrock/MCP acceptance and final focused retests completed; no further paid
replay is scheduled. Approved original cap USD 17; cumulative spent USD 11.4130081600,
unknown held USD 0.2873231200/six calls, paused=false. Task settled USD 3.9025998000
under USD 7 additional approval, including all failed/retired experiments. AWS renewal/
resume was explicitly approved with holds retained. Pytest remains isolated/mock only.
Subsequent installed interactive use reached USD 11.4615907600 at handoff, with all
unknown holds unchanged; it is separate from completed acceptance cost. See
[measured demo quality and limits](DEMO_READINESS_RESULTS.md). Prior caps below are history.

2026-11-16 main-chat acceptance: [four new Home-chat cases](MAIN_CHAT_RESULTS.md) used
12 settled planning/answer/support operations, USD 0.3018378000 actual and USD 1.3827066000
conservative reservations within the scoped USD 2 bound. No paid replay/embeddings/
extraction/enrichment. Original ledger spent USD 4.7731804600, historical unknown
USD 0.0566168200/three calls unchanged, paused=false, cap USD 10. Sixteen points remained
visible; one Arabic candidate failed support. Arabic terminology guidance was revised
without another paid repetition; broader language/held-out acceptance remains open.
The full deterministic suite targeted the separately verified mock API with no budget,
AWS credentials or MCP token. Earlier spend/outcome checkpoints below remain history.

2026-11-16 measured real MCP follow-up: [the clean platform trial](REAL_MCP_TRIAL_RESULTS.md)
completed four representative questions, all citation_failed, with no independent
verification calls. Four intentional answer calls cost USD 0.1013925000. Preserve
and disclose the earlier test-isolation error: four additional settled calls cost
USD 0.0304194000. Total additional USD 0.1318119000, eight calls, conservative reservations
USD 0.8522580000 under the same scoped USD 2 bound. Original cumulative spent is now
USD 4.4106589600; unknown reservations USD 0.0566168200/three calls unchanged,
paused=false, cap USD 10. Zero embeddings/extraction/enrichment. The deterministic
355-pass retry targeted a verified separate mock API. Do not automatically repeat
paid questions or infer answer quality from successful live retrieval/mock tests.
Earlier spend checkpoints below are historical.

2026-11-15 RF3 repair acceptance: [the concrete follow-up scope](RF34_FOLLOWUP_SCOPE.md)
completed using the original shared ledger, 15 Sonnet calls, no embeddings and
USD 0.1153449000 total. Known unsupported additions were rejected and three new answers
passed source review; one initial false rejection and its targeted correction are
preserved. [Current results](RF34_RESULTS.md) separate bounded repair acceptance from
independent company quality. Total spend is USD 4.2788470600; unknown reservations stay
USD 0.0566168200. The new 5195 preview remains mock; the one-shot paid harness does not
authorize automatic repetition or a new interactive AI preview.

Agreed **2026-11-14**. The user prefers meaningful hands-on testing with real AI so
the assistant's actual usefulness and retrieval/answer quality can be evaluated.
Use mock/stub checks where real inference would not improve the test. This policy
does not require AI for every test or authorize repeating a historical paid run.

## Choose the method by what the test needs to prove

| Test purpose | Preferred method |
| --- | --- |
| Actual answer usefulness, explanation, summarization and source comparison | Bounded real Sonnet testing against representative uploaded evidence |
| Arabic/English understanding, natural follow-ups, factual support and abstention quality | Real Sonnet questions with inspected original evidence and citations |
| Semantic retrieval relevance | Real embeddings/query retrieval where needed; assess retrieved evidence separately from generated answers |
| Parsing, file validation, source-only default, state transitions, migrations, leases and revisions | Deterministic local tests; no paid inference |
| Permission/revocation, dependency invalidation, budget guards, citation/schema rejection and injected failures | Mock/stub regression checks; real acceptance only where it proves an additional provider-dependent property |
| Layout, navigation, buttons, responsive views and routine smoke checks | Mock UI/API tests unless the requested behavior specifically depends on live model output |

Run relevant deterministic checks first, then use a small representative real-model
journey for AI-dependent acceptance. Avoid rerunning a paid corpus or spending on an
unchanged deterministic test. Mock excerpts and stubbed verdicts do not establish model
quality; real-model success is not a substitute for deterministic safety regressions.

## RF1 and later stages

Real AI answer testing can happen **now on RF1**; it does not need to wait for RF2.
Sonnet answering and optional structured enrichment are separate capabilities.

- Ordinary uploads/revisions remain source-only: save, parse and index. Do not enable
  automatic entity/claim/relationship extraction or conflict assessment for an AI trial.
- At question time, retrieve relevant passages and use Sonnet to produce supported cited
  answers. Preserve the current grounding checks, source access and uncertainty handling.
- Do not require **Enrich knowledge** to use real AI answers. That action is a separate
  optional workload, not an AI-mode switch.
- Retain the existing source revisions/passages/embeddings. Do not reupload/reprocess
  the whole corpus merely to switch the answer provider. Any needed semantic-index work
  must be explicitly scoped/accounted for, without redoing unchanged compatible vectors.
- Label actual provider/mode honestly. Do not present verbatim mock excerpts as real
  reasoning, or imply AI is enabled merely because AWS sign-in succeeds.

## Spend and authorization

Preserve the existing `northstar-sonnet-2026-11-12` cumulative **USD 10** ceiling,
recorded spend and unknown reservations. This preference does not create a new allowance,
reset/clone the ledger, authorize a comparison rerun or silently clear a paused budget.
An available AWS session or remaining headroom alone is not paid-run authorization.

Before agent-run real-model testing, establish concrete files/questions, operations,
call/time/spend bounds and stop conditions under the applicable explicit scope. Verify
that every dispatch uses the persistent approved guard, including embeddings and answer
verification. Keep useful authorized user testing practical; do not ask again for an
action already covered by its explicit scope.

RF1 uses a **separate content database**. Merely applying the old Sonnet Compose
override would not share the existing ledger: the budget code can initialize a new run
in that database. Do not enable paid calls there until the accounting arrangement is
concretely reviewed and correctly connected to the existing guard. No new ledger copy,
unguarded provider toggle or automatic unpause is allowed.

This request records testing preference and supplies self-service login instructions;
it does not deploy an AI preview, dispatch paid tests, alter protected environments or
authorize AWS infrastructure. Sonnet remains the sole reasoning model; no Gemma work.

**Confirmed follow-up after login:** RF1 at port 5189 now uses Sonnet. API and worker
connect directly to the original spend/pacing store through `BEDROCK_BUDGET_DATABASE_URL`
and `compose.rf1-ai.yaml`; no budget copy is created. The final Lantern summary passed
real answer and semantic verification after two safely rejected citation probes.
Total additional recorded spend was USD 0.1808961. See [AI preview evidence and bounds](RF1_AI_PREVIEW.md).
The paragraph above records the earlier preference-only request; this follow-up is the
subsequent confirmed activation. The original cumulative USD 10 cap and unknown
reservations remain binding for interactive testing. No new corpus run is authorized.

## AWS login performed by the user

The inspected local `default` profile uses **AWS CLI login**, not IAM Identity Center
SSO. AWS CLI 2.38.5 was installed and read-only STS verification succeeded on 2026-11-14.
Those are dated observations, not a future credential-validity guarantee.

In PowerShell, renew that profile with:

```powershell
aws login --profile default
```

Complete the browser sign-in, then verify locally:

```powershell
aws sts get-caller-identity --profile default --no-cli-pager
```

Do not paste credentials or sign-in tokens into chat or repository files. Login refreshes
credentials; it does not switch the RF1 provider or change the application's budget state.
The user requested to run login personally; the assistant did not launch it on this turn.

## Reporting

RF2 follow-up uses deterministic tests: metadata, identity, permissions, pagination,
original evidence and responsive UI do not require new model reasoning. Its separate
mock preview at 5191 has no configured Bedrock provider/AWS mount. Full 231 API / 32
browser checks and final focused checks passed, with zero paid usage and unchanged
original budget. RF1 Sonnet at 5189 remains available for authorized interactive AI
testing. See [RF2 evidence](RF2_RESULTS.md); this does not establish RF3 answer quality.

Record what each check proves, provider/mode, source coverage, inspected citations,
actual usage/cost when available, failures and remaining limitations. Keep private source
text/raw model outputs in protected ignored evidence. Never re-score a mock run as live
acceptance or claim lower latency/cost without measurement.
