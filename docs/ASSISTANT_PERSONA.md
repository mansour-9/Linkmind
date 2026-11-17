# Linkmind conversational persona

> **Historical evidence / compatibility note — 2026-11-14.**
> The dated implementation, checks, budgets and environment observations below are
> retained; they were not rerun or re-scored by this documentation update.
> The [active roadmap](IMPLEMENTATION_PLAN.md) and [scope](PROJECT_SCOPE.md) now
> prioritize source-only ingestion, a durable selected-source repository and bounded
> retrieval. [RF1](RF1_RESULTS.md) subsequently implements default-off enrichment in
> isolated current code; old next tasks/manual or paid commands are not authorization.
> Historical evidence/security/history remains intact; existing environments are unchanged.

Implemented 2026-11-13 at the user's request for a natural assistant identity,
short friendly interaction, light emoji use, and a substantial system prompt.
The user corrected the chatbot name to **Linkmind**. Both the product and assistant
use Linkmind; the assistant introduces itself briefly as an AI assistant for workplace knowledge.

The editable shared prompt and approved product facts are in
[`assistant_persona.py`](../code/apps/api/app/assistant_persona.py). They define
identity, tone, Arabic/English language matching, interaction examples, capabilities,
source grounding, access and truthful-action boundaries. The prompt is supplied to
both query understanding and factual source answering; model verification keeps its
independent evidence-checking instructions.

## Interaction

- Greetings introduce Linkmind briefly, with a light emoji. Repeated greetings avoid
  repeating the introduction. Identity questions answer identity rather than listing
  features. Thanks receives a short acknowledgment.
- Capability questions explain the benefit in a couple of sentences. Upload steps
  appear when asked, not after every greeting or help question. Casual spelling and
  the user's English/Arabic phrasing are supported without grammar corrections.
- Familiar greetings, identity, capabilities, thanks and upload help use a small
  no-inference path. Unfamiliar help/social requests can receive a tailored model
  reply through query understanding, then a separate nonfactual/product-fact check.
  Unsupported actions/capabilities are rejected; organizational questions are routed
  back to authorized retrieval and factual citation verification.
- The query-understanding output remains limited to 512 tokens; conversational
  verification to 256. Both use the existing provider, usage recording and spend
  guard. Paused budgets and authorization failures still propagate explicitly.
- Persona styling never substitutes conversation memory for evidence, broadens
  source access, confirms an unsupported company fact, or claims tools/actions the
  application has not actually performed. Grounding policy and citation acceptance
  rules are unchanged; existing stored turns are not rewritten.

## Deployment and validation

- Current-source implementation: isolated F1.3 mock preview, port **5181**.
- User's actual exchange was found in the Sonnet preview at **5175**. It received
  a narrowly backported persona image, `linkmind-company-sonnet-backend:persona`,
  preserving schema **0010**, original data, source processing and its test ledger.
  No F1.3 migration or main-data cutover was performed.
- [`build_persona_preview.py`](../code/scripts/build_persona_preview.py) constructs
  the compatible image from the current immutable preview image plus the reviewed
  pre-F1.3 source boundary at commit 4028a16. Only the persona/routing/provider files
  are patched; it refuses a preview already migrated beyond schema 0010. The narrow
  filename/topic routing correction is included to preserve the current chat contract.
- API and worker were recreated only in `linkmind-company-sonnet`, with the existing
  three Compose files and `--no-deps --no-build --wait`. Main app, frontend, database,
  other previews and AWS infrastructure were left untouched.
- **141 API tests passed** on the current code. **43 persona/grounding/conversation
  compatibility tests passed** against the schema-0010 image. **Four browser
  workflows passed**, including the new English/Arabic persona journey, source
  discovery, uploads, follow-ups and company examples. Desktop/mobile screenshots
  were checked for the new short replies.
- A live HTTP smoke check of `hi`, `who are you?`, the user's exact capability typo,
  and `thanks` returned nonfactual system replies with no evidence or paid model
  calls. Ledger before/after was identical: USD 10 limit, USD 2.1017705200 spent,
  USD 0.0566168200 reserved, unpaused. No new paid evaluation was run.

## Try it

Start a **new conversation** at <http://127.0.0.1:5175>. Try `hi`, `who are you?`,
`can you help me?`, `what can you do for me?`, `مين انت؟`, and `thanks`.
Ask upload instructions separately to see the relevant short instructions. Older
messages retain the text they had when originally saved.

Broader real-model personality quality remains subject to manual review; mock and
stubbed-model tests verify routing, prompt attachment and safety behavior, not an
exhaustive natural-language quality benchmark.
