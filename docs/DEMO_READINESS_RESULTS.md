# November 19 demo readiness — delivered November 17, 2026

Installed at **http://127.0.0.1:5197**, schema `0020_auto_chat`, answer policy
`grounded-v19-simple-linked-chat`. Start a new conversation for the demo. The user
explicitly prioritized useful, fast answers over independent statement verification.
This delivery supersedes the earlier verification-heavy ordinary-chat requirements.

## Result

Ordinary automatic chat now retrieves relevant authorized sources, then makes one
Bedrock answer request. It does not make a model planning request, independent
semantic-verification request, or citation-repair request. One targeted additional
retrieval/answer is allowed when the first answer explicitly identifies a missing
query; two answer calls are the hard ceiling. None of the final real cases needed
that fallback. Native Jira status-only questions use the actual fields with no model.

Project/issue identifiers carry the conversational topic, allowing ownership,
blocker, resolution and next-action follow-ups without repeating ATLAS. Previous
answer prose is not evidence for the next answer. Exact issue keys go directly to
their authorized Jira scope. Release questions read the plan and up to three linked
issues; this is a bounded view, not an exhaustive issue audit.

Sources have their native titles/issue keys and original links. Unknown source IDs
are discarded. Basic native-status checks remain, including the distinction between
Jira's workflow status and a narrative business blocker. Initial MCP reads authorize
content; current local access/configuration is checked before model exposure, with
one fresh remote permission/revision check at delivery. Source previews and history
retain their access checks. Explicit stored/live/combined and advanced selected-source
contracts retain their existing boundaries and stricter path.

No new indexing, graph work, background enrichment, infrastructure, authentication
architecture, source-mode change or provider write was introduced.

## Real answer quality and latency

Ten real Bedrock + read-only MCP questions were run in a content-isolated candidate,
followed by three focused checks after the final concise-answer/status/authority
corrections. Review used the actual source originals. Gold review notes never enter
the runtime prompt. The table uses the latest relevant result for each question.

| Question | End-to-end server time | Result |
| --- | ---: | --- |
| What is ATLAS? | 11.185 s | Purpose, features, customer and beta scope, with useful links |
| Who owns it? | 8.687 s | Product, delivery, identity and frontend responsibilities distinguished |
| What issues are blocking it? | 12.027 s | Relevant issue dependencies; native statuses remain In Progress |
| Has the issue been fixed? | 1.599 s | Both antecedent blocker issues freshly read; neither claimed fixed |
| What should we do next? | 12.631 s | Dependency order, accountable owner, review and launch sign-offs |
| ATLAS-4 status, owner and acceptance criteria | 4.972 s | Direct exact issue read; unassigned Jira field distinguished from accountable owner |
| Approved raw analytics retention | 6.576 s | Approved 30-day policy distinguished from old draft and separate audit retention |
| Company departments | 6.575 s | All eight departments; Executive Office distinguished |
| Arabic introduction | 15.739 s | Natural project introduction with sources |
| Arabic ownership follow-up | 10.705 s | ATLAS topic retained and role ownership explained |

Every explanatory answer used one answer-generation call. The native resolution
follow-up used zero. The inspected old saved pipeline took about 31–63 seconds and
four to five model calls on comparable problem cases; this is a small practical
sample, not a controlled latency benchmark or a percentile/SLA.

An initial simple run confused narrative Blocked with native status and attributed
launch authorization to delivery ownership. Basic field normalization and clearer
role guidance corrected these in the final real blocker/next-action checks. Earlier
failures, retired verification experiments and their costs remain in private evidence.
Arabic outputs were checked with valid Unicode; earlier corrupted prompt experiments
are excluded from Arabic quality claims, but their costs remain counted.

## Validation and preservation

- **444 API tests passed, 2 skipped**, in the dedicated mock-only database/network.
  No live credentials, shared budget or provider networking were enabled for pytest.
- Frontend build passed; five focused isolated browser workflows passed. The full
  historical browser suite was not rerun.
- Installed 5197 desktop/mobile smoke passed: fresh ATLAS-4 status, native title/link,
  source preview, current status, focus return and no horizontal overflow. It used no
  model; page navigation plus answer took 3.703 seconds. Only its own new chat was archived.
- All nine document rows (including deleted), four source connections and 32 prior
  conversation rows matched a restored pre-task backup before the installed smoke.
  Schema remained 0020. All **149 other container IDs** were unchanged.
- Existing images/network bindings, source IDs, modes, credentials, originals and
  historical data were preserved. Only this preview's API/worker/web were updated.
  No commit, push, merge, main rollout, workspace reset or AWS provisioning occurred.

## Spending

The user approved up to USD 7 additional inference, increasing the original ledger
from USD 10 to **USD 17** through an audited amendment. Task settled spend was
**USD 3.9025998000**, including failed/retired experiments. Original cumulative spent at final acceptance:
**USD 11.4130081600**. Held unknown reservations: **USD 0.2873231200 / six calls**.
The AWS-expired request added USD 0.1036926000 to those holds. After explicit user
approval, AWS login/STS succeeded and the same ledger resumed with every hold intact.
It remains unpaused. There was no new ledger, spend reset or unknown release.

After installation, concurrent interactive use increased cumulative spend to
USD 11.4615907600 at the handoff readback; all held reservations remained unchanged.
That subsequent use is separate from the completed acceptance cost above.

Conservative reservations summed across completed experiments are not outstanding
usage or settled cost. The durable task guard counts settled spend plus outstanding
new holds against the approved USD 7. No more automatic paid retesting is scheduled.

## Important demo limits and handoff

This is a useful local demo, not independently certified grounding or production
employee authentication. Simple links establish relevant source context; they do not
prove every generated clause. Basic status checks reduce a specific failure class
and do not guarantee all paraphrases or Arabic statements are correct.

Provider search/generation latency still varies: Arabic and cold answers reached
about 16 seconds. Current retrieval is optimized for supported source capabilities
and bounded project questions; broader ambiguous/cross-project questions may be partial.

AWS and Atlassian access is time-limited. Renew through the existing login flows and
check all four source scopes before the November 19 demo; do not wait until the live
presentation. A source outage, revision or access change can still hide an answer.
Connections remain owner-bound and employee identities remain the local prototype.
Use the connected administrator identity for this authorized demo.

Private evidence is in ignored `.local/chat-fix-2026-11-17`: `demo-live.json`,
`demo-final-live.json`, `observed-sources.json`, `api-final.xml`, `browser-final.json`,
`installed-smoke.json`, desktop/mobile screenshots, `installed-preservation.json`,
budget amendment/resume receipts, and pre-install image/network metadata. Do not
publish this directory: it contains private source bodies and credentials.

For rollback, use the saved original image IDs and original compose chain while
retaining current database/volumes/networks. The ledger remains at its approved USD 17
cap; rolling back app images is not authority to reset, clear holds or lower the
configured cap to the old USD 10 value. No schema rollback is needed.
