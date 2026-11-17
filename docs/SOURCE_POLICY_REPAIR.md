# Latest verification — November 17, 2026

The renewed session was activated in the existing 5197 API. Both exact reported questions now return three configured Jira projects: ATLAS, BEACON and HARBOR. Each response is structured, source_policy=live, with three live citations and zero stored retrieval activity. Each uses three searchJiraIssuesUsingJql calls plus three fresh getJiraIssue authorization checks. No model call was needed.

Verified chat: http://127.0.0.1:5197/chat/8f037585-839b-4dcb-bf95-b3568b70ae58

Confluence ADR 007 (page 327699) was independently read through Linkmind's actual getConfluenceContent MCP call. Its response was live, revision 1, retained=false, 16 parsed passages; tenant_id and audience requirements were present. No document import, vector indexing or model call occurred.

Full release API suite: 396 passed, 2 skipped. Desktop/mobile checks and frontend build passed. Existing document/version/chunk/connection-configuration and pre-existing answer hashes remain unchanged. The earlier expired-auth verification is preserved as failure history.

The temporary MCP credential remains an interactive test credential; automatic service-account authentication and organization-shared employee access are the next implementation phase. They were not introduced by the source-boundary repair.


---

# Chat source boundary repair — November 17, 2026

The user approved investigating and fixing local-demo contamination and the project-count/Jira-correction routing failures. Changes are installed only in the existing local preview at http://127.0.0.1:5197. No Git publication, AWS infrastructure, source-scope expansion, content deletion or corpus reprocessing occurred.

## Behavior

- New chats default to **Live Only** when the current user has enabled real connectors. Source policy is stored with the conversation and enforced on the server. Stored knowledge and Live + stored remain explicit choices. Selecting documents starts a stored-source conversation.
- Live Only never runs stored retrieval, offers stored suggestions, or falls back to uploads when live authentication/search fails. Final answer, history, previous-context and citation checks retain the policy boundary.
- Project-count/list intents recognize the reported typos, singular/plural wording and Arabic corrections before application-help classification. They verify project metadata from configured Jira scopes, count distinct verified projects, and report partial/empty/unavailable scope limitations. They do not count arbitrary retrieved paragraphs or claim to enumerate every account project. Source counts need no model synthesis.
- Known synthetic fixture versions are labelled by exact SHA-256 rather than filename. They are excluded from automatic knowledge retrieval but remain available through deliberate document selection; their citations and source picker show demo provenance. Ordinary uploads remain first-class retained knowledge.
- Old conversations remain intact with source_policy=legacy. Their earlier mixed-source answers are not promoted to current trusted responses, and continuing them requires a new source-scoped conversation. No old response or citation text was rewritten.
- Demo loaders now require an explicitly isolated mock runtime with networking disabled and no real source connections/shared inference ledger. API and browser integration tests perform a target handshake before mutation. Safe diagnostics expose MCP tool-name counters without credentials or raw tool arguments.

## Schema and preservation

Additive migration 0019_chat_source_policy adds conversations.source_policy and document_versions.dataset_id. It classifies known fixture hashes without changing original bytes, passages, immutable revision identifiers, graph records or source permissions. Grounding policy is grounded-v12-chat-source-policy. Exact citation, semantic support, source revision and owner/item checks remain enabled.

Before rollout, the 5197 database was backed up in a custom-format PostgreSQL archive and the archive listing verified. Pre-change images and source files were captured. Rollout verification confirmed unchanged document, version, chunk, connection-config/mode/generation/auth-state and old-answer hashes. At rollout there were 47 document records, 67 versions and 445 chunks. Additional saved conversations from deliberate UI verification are separate from pre-existing records.

## Validation

- Final release API regression: **396 passed, 2 skipped**. The focused source-boundary selection also passed **55 tests**. These checks include default Live Only for real scopes, expired-auth no-fallback, explicit stored/demo access, combined knowledge, typo/correction routing, source compatibility and loader refusal.
- Frontend TypeScript/Vite build passed. Headless desktop and 390px mobile checks passed with no page errors or horizontal overflow. Explicitly selected atlas-decision.md showed a Demo citation label. The cramped mobile selector found during visual inspection was corrected.
- Earlier read-only runtime investigation verified actual Jira and Confluence MCP responses and traced the exact stored-plus-live contamination. The completed updated-UI smoke attempt reached live MCP authentication and returned authentication_expired for all three configured Jira scopes. It returned no stored evidence, demonstrating refusal to fall back.
- The existing Atlassian credential expired at **2026-11-17 02:09 Asia/Riyadh**, before the final verification. Same-scope PKCE renewal was prepared; user sign-in and a successful post-renewal Jira/Confluence verification remain pending at the time of this checkpoint. Do not describe the expired-auth UI run as a successful live project count. No new model inference, embeddings, extraction or enrichment was used by these repair tests.

The working read-only MCP transport/configuration is preserved. This checkpoint does not imply that OAuth refresh-token retention, production sign-in, account-wide project discovery, or broader model quality has been implemented.

## Isolated regression commands

From the repository root:

```powershell
docker compose -p linkmind-source-policy-tests -f code/compose.yaml -f code/compose.source-policy-tests.yaml build api web
docker compose -p linkmind-source-policy-tests -f code/compose.yaml -f code/compose.source-policy-tests.yaml up -d --wait
docker exec -e LINKMIND_CHAT_AGENT=0 -e LINKMIND_CHAT_POLISH=0 linkmind-source-policy-tests-api-1 pytest apps/api/tests -q --disable-warnings
```

This project owns separate database/artifact volumes and a dedicated 10.253.19.0/24 Docker network. It has no AWS credentials, MCP credential file, original shared-budget network or real source access. Its explicit test-only flags must never be applied to 5197. Do not run mutating integration tests by docker-exec into a live API.

The live overlay code/compose.source-policy-live.yaml is added only to the existing 5197 base, clean-MCP and chat-polish overlays; it preserves the loopback port and disables test dataset loading. Do not apply it to unrelated older previews. Rollback can reuse the recorded old image IDs; additive columns are compatible with the earlier application. Preserve the backup and do not restore over new user work without review.

Detailed investigation: [source data investigation](SOURCE_DATA_INVESTIGATION.md). Evidence, hashes, snapshots, test outputs and the private local backup are in the chat workspace under output/source-investigation; do not commit the database archive or source data dump.
