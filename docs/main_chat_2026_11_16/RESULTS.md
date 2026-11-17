# Main chat with connected company knowledge — 2026-11-16

The main Home chat at http://127.0.0.1:5197/ now automatically combines searchable company knowledge with scoped Jira/Confluence discovery and fresh original reads. Users can ask “What is HARBOR?”, then “Who owns it?” and “What is blocking its launch?” in the same conversation without selecting tickets, pages or the advanced Ask across sources screen. Its shortcut was removed from Home; the advanced route remains available.

The new `rf5/main-chat-agent` branch preserves previous uncommitted connector work. Only the isolated clean preview and the separate mock regression preview were updated; no main rollout, commit/push/merge, AWS infrastructure or schema change. Schema remains 0018; answer policy is `grounded-v11-main-chat-partial-support`.

## Delivered behavior

- Main-chat planning resolves follow-up references from recent reauthorized conversation context. It searches the stored index and selects relevant owner-enabled connector scopes. Discovery is bounded to three selected scopes/four original live resources, with real source-specific allowlisted read/search tools. Native source IDs and server-built project/space filters prevent scope escape. Search snippets are discovery metadata, never answer evidence.
- Confluence stores its numeric space ID for original-page authorization and its space key for scoped CQL. The ABL key was configured and the actual source retested. Title matches precede body fallback, so HARBOR questions retrieve HARBOR pages rather than unrelated pages merely mentioning the project.
- The model selects actual field names and source pointers. The server resolves original typed values, removing the fragile requirement to reproduce long JSON values. Description prose also has exact passage support. Unknown/malformed references remove that independent statement; a failed semantic review removes that statement, preserving other approved points. A mismatched/reordered verifier cannot certify an answer. No fabricated citation, unsupported field or revoked source is accepted.
- Focused document chats stay within their selected stored scope. Explicit retained-version comparisons keep their existing history-aware route. Past-only questions do not use current live state as proof of a past state. Ambiguous identities retain clarification.
- Helpful source excerpts remain labelled as excerpts if synthesis cannot be approved. Provider wording no longer claims verification on rejected output. Live citations recheck authorization/revision and fetch original evidence when opened; duplicate live page references are grouped.
- Conversation history stores derived replies and cited excerpts/field values with dependency metadata. It redacts full live evidence context text and does not ingest native source documents/raw provider objects. Saved answers are hidden when authorization, connection generation or revision cannot be confirmed. Local demo authentication remains; real employee production delegation is not inferred.

## Company information

Three source-only, team-visible Markdown documents were uploaded and became Search Ready: company/teams overview, employee onboarding, and the people/project directory. They contain the existing fictional AsterBridge delivery cohort and dated project facts, not invented real-company HR rules. Eighteen named people are a test cohort, not the entire company headcount. No salaries, leave entitlements, credentials, real accounts or signed approvals were fabricated. No automatic enrichment or embeddings ran; three documents, zero graph entities, four real source connections.

## Validation

Final deterministic API suite: **365 passed, 2 skipped**, two dependency deprecation warnings, 56.97 seconds. Frontend TypeScript/Vite build passed. The regression API was explicitly verified as mock with no shared-budget binding or MCP credential; no AWS mounts or paid inference were supplied to the runner. Fixture setup failures were corrected without weakening the checked contracts, as recorded in validation.json. The old 43-test browser suite is historical and was not rerun for this change.

Four new real Sonnet questions were submitted from the ordinary Home chat, not the advanced screen:

| Case | Result |
| --- | --- |
| What is HARBOR? | Five candidate points anchored and independently accepted; overview, scope, conditional date, business gates and roles displayed. |
| Who owns it? | Three points accepted in the same conversation, with no repeated project name or manual source choice. Ownership wording was cautious/document-oriented; future prompt guidance prefers direct responsibility roles. |
| What is blocking its launch? | Four points accepted in the same conversation, separating accepted webhook delivery from authentication, agreement and Product authorization gates. |
| Arabic employee introduction/onboarding | Five candidates anchored; one failed semantic support, four paragraphs remained visible with team/contact/onboarding evidence. This demonstrates partial delivery rather than erasing the entire answer. |

The Arabic output had literal “pilot” and “sandbox” translations that were unsuitable for software. Contextual Arabic terminology and onboarding brevity guidance were added afterward and deterministically checked, without repeating a paid question. These prompt refinements have not had another real-model acceptance case; Arabic linguistic quality remains a bounded observed limitation. No claim of complete bilingual or independent company acceptance follows.

During final API restarts, one UI authorization refresh temporarily hid live replies; a fresh complete authorization check restored all three without model repetition. This conservative behavior remains for provider availability/access uncertainty. Permission checks were not bypassed to keep content visible.

## Usage and remaining work

Exactly **12 settled model operations** (four planning, four synthesis, four independent support checks), **USD 0.3018378000 actual**, **USD 1.3827066000 aggregate conservative reservations**, within the four-question/twelve-call/USD 2 scope. Original cumulative ledger: baseline USD 4.4713426600 / 603 settled, final **USD 4.7731804600 / 615 settled**. Original cap USD 10, paused=false, three historical unknown calls/USD 0.0566168200 unchanged. No reset, clone, increase, unpause, unknown release, paid repetition, embeddings, extraction or enrichment.

Remaining gates: broader Arabic/held-out answer quality, provider availability/latency, scoped Microsoft/custom search, actual sync/refresh/revocation lifecycle, production employee authentication/delegation and RF6 release/operations acceptance. The previous failed manual-source trials remain preserved as history; they are not silently reclassified as successful.

Evidence: validation.json, case-01.json through case-04.json, company-uploads.json, company-knowledge/, AI_SCOPE.md and UI screenshots.
