> Historical read-only investigation snapshot. The user subsequently approved all fixes on November 17, 2026. See SOURCE_POLICY_REPAIR.md for implementation and current validation status.

# Linkmind source investigation — November 17, 2026

Read-only investigation of the 5197 preview, its running API code, PostgreSQL/pgvector database, Docker artifact volume, saved chats, retained request logs, and actual MCP traffic. No application fixes, deletions, uploads, ingestion, reindexing, configuration changes, or new saved conversations were performed. Only this investigation directory was created. Model synthesis and embeddings were disabled in the ephemeral diagnostic; no new paid model acceptance run was performed.

## Findings

The concern is confirmed. The 5197 content database contains old Northstar demo documents alongside intentionally uploaded AsterBridge company documents and working live Jira/Confluence connections. General Home chat combines stored and live evidence. Connection “Live Only” controls connector retention; it does **not** impose a live-only boundary on Home chat. The two reported symptoms also expose brittle project-intent routing and a mistaken help classification.

My earlier search was limited to the chat workspace and missed the separate application checkout. The exact atlas-decision.md and delta-status.md originals exist in that checkout. This investigation supersedes the earlier uncertainty about their location.

## Local files and their purpose

Two relevant roots exist:

- Chat workspace: `C:\Users\manso\OneDrive\المستندات\ChatGPT\ABA Project`.
- Application checkout: `C:\Users\manso\OneDrive\سطح المكتب\AWS ABA\ABA Project`.

[Complete filename inventory](<C:/Users/manso/OneDrive/المستندات/ChatGPT/ABA Project/output/source-investigation/MARKDOWN_FILES.md>) lists all 361 Markdown files found in the inspected fixture/test-data/company-knowledge directories, including duplicate copies across the roots and supporting documentation. This is an inventory of those project directories, not a claim to have scanned the entire computer or OneDrive cloud.

| Group | Files per applicable root | Purpose and storage result |
|---|---:|---|
| AsterBridge Confluence Markdown | 25 | Authoring copies of the published ABL pages. They are remote Confluence content when fetched through MCP; their local bytes are not automatically indexed. Two are also the source of intentionally uploaded company copies. |
| AsterBridge Jira Markdown | 108 | Local source copies for seeded Jira issues; not independent uploads to the 5197 index. |
| Editable business-report Markdown | 18 | Companions for generated business DOCX/XLSX files. No matching retained Markdown version in the ten inspected databases. |
| Company profile and supporting documents | 5 | One company profile plus README/generation/expected-answer documentation. |
| Generated company-knowledge copies | 3 | Intentionally uploaded, Search Ready in 5197. |
| Application company_demo | 25 | Northstar synthetic corpus: 24 initial files plus atlas-handover-revision.md. All 24 initial files are active in 5197; the revision file is not a current 5197 upload. |
| Other application fixtures | 21 | 12 benchmark, 3 conversation, 2 graph, 2 processing, cloud-migration.md, and private-review.md. Two standalone fixture documents remain active in 5197. |

There are different beacon-status.md files. The AsterBridge business-report companion has checksum `2e5017ed7e2864bc2c258840b6aa450bbd53ab54e0bfe392efb02329447aee7b` and no matching retained database copy in the inspected databases. The Northstar fixture has checksum `5e1f873a52ec856efe188deed1d9bd6a3eef0d25fb60ac021d7c3d85ccaf0e37` and **is** stored, indexed, and cited in 5197. Matching by filename alone would confuse them.

## What is stored and indexed now

`linkmind-asterbridge-live-api-1` serves the 5197 UI through its web proxy. Its image is `linkmind-chat-polish-backend:local`; its content database is `linkmind-asterbridge-live-db-1`. Runtime hashes for chat_agent.py, structured_chat.py, conversation_routing.py, main.py, and retrieval.py exactly match the reviewed application checkout.

The content database has **47 document records, 30 active documents, 67 retained versions, 445 chunks, zero populated embedding vectors, and 35 saved conversation turns**. Counts include historical and deleted records. Of the active documents, 29 belong to the current organization and one private text fixture belongs to a separate test organization.

The 30 active records consist of:

- 24 Northstar demo Markdown files (23 team-visible, one private).
- Three team-visible AsterBridge uploads: AsterBridge-company-and-teams.md, AsterBridge-employee-onboarding.md, and AsterBridge-people-and-projects.md.
- cloud-migration.md and private-review.md test fixtures.
- unrecognized.txt in the separate test organization.

[Every active file, document ID, version, checksum, and chunk count](<C:/Users/manso/OneDrive/المستندات/ChatGPT/ABA Project/output/source-investigation/CURRENT_STORED_DOCUMENTS.md>) and [full database evidence](<C:/Users/manso/OneDrive/المستندات/ChatGPT/ABA Project/output/source-investigation/database-inventory.json>) provide the exact inventory. 65 of 67 retained version artifacts exist under the live Docker volume mounted at `/artifacts` and match their database checksums. The other two are deleted synthetic test rows (dense-test.md and private-graph.md) with placeholder artifact_key=unused; they have no current searchable version. The three suspicious citation artifacts all exist and match exactly. These are server-side local Docker volume files, separate from the original workspace Markdown files.

The stored content can be found through PostgreSQL full-text indexes, simple bilingual indexes, and graph-related retrieval; **zero vectors does not mean zero retrieval**. The demo documents also have extracted graph entities. The connection-retention tables contain **zero connected_resources and zero connected_revisions**, so the suspicious Markdown citations are uploads/demo loads, not retained Jira/Confluence sync copies.

Ten Linkmind databases were inspected. Other older previews also retain test data and some have actual vectors. The 5197 content engine points to its own database; no cross-database content search was found. The shared Sonnet budget database accounts for model use and is not an extra content retrieval source for this chat.

## Exact origin of the suspicious citations

The screenshot matches saved turn `f3efffa8-2786-4b34-8519-1831bbaeba48`, conversation `5982c575-c906-47ae-825c-f0bf468f0f55`, question “قصدي المشاريع”, saved at **2026-11-16 23:23:54 Asia/Riyadh**.

| Citation | Document ID | Stored passage ID | Origin |
|---|---|---|---|
| atlas-decision.md | `9d40a0c2-c3bc-48cf-b666-f7e7b3a50f47` | `01412964-7c26-5dcc-abf9-467c543df807` | Northstar fixture, original line 3: Atlas / NS-ATLAS owned by Lina Faris |
| beacon-status.md | `ec3001d8-42c2-4f9b-8af4-b9ad7f06e7f5` | `0638326a-d99a-51c6-9c4d-cd2c48ff428f` | Northstar fixture, original line 3: Beacon / NS-BEACON owned by Lina Faris |
| delta-status.md | `08a400d4-088f-4ec7-953e-5b740bef5712` | `11801967-b874-5cdf-abd7-efd713fca495` | Northstar fixture, original line 3: Delta / NS-DELTA owned by Samir Haddad |

The originals are in `C:\Users\manso\OneDrive\سطح المكتب\AWS ABA\ABA Project\code\fixtures\company_demo`. Database version hashes match the originals, and retained artifact bytes match the version hashes. This establishes the chain from local fixture to stored version to retrieved chunk to saved citation.

That answer retrieved four stored passages and three live resources. Its project/owner list cited the Northstar chunks; its BEACON date statement cited the live ATLAS-16 description. Thus it demonstrably **combined different test-company datasets in one answer**. Exact citation validation passed for those clauses because the quoted text existed; it did not enforce the user's intended live-only corpus boundary.

The same 24 demo records were created at **2026-11-16 22:30:59 Asia/Riyadh**. API access logs at 22:30:59–22:31:00 record three `/demo/company/load` requests: 403, 202, 202. This exactly matches the unauthorized-user/idempotent-load sequence in test_company_demo.py. Subsequent upload/revision/access/delete requests also look like integration tests and originated from the live API container's own network address. The confirmed cause of insertion is the demo-load endpoint; attribution to that specific test invocation is a strong inference from the matching sequence, not a recovered shell command or human identity.

The loader inserts ordinary upload-origin, team-visible records using add_version. It has no environment-isolation gate preventing it from being invoked against the live preview. The test helper hardcodes `http://api:8000/api/v1`. This makes running it in or against the wrong Compose environment dangerous. See [main.py:251](<C:/Users/manso/OneDrive/سطح المكتب/AWS ABA/ABA Project/code/apps/api/app/main.py:251>) and the application test file `code/apps/api/tests/test_company_demo.py:29`.

## Why the newest conversation failed

Saved conversation `204ced98-456b-4d47-9e94-12698a2f4478` contains the exact messages you supplied.

1. **“how many porject are they”**, turn `97d42ff2-96d6-407b-bfa3-dd61e36010e8`, saved **2026-11-17 00:13:25 Asia/Riyadh**. The structured project shortcut did not match. Because “they” is recognized as a follow-up, planning was skipped and the prior greeting polluted the retrieval query: `hi how many porject they`. The generic route searched stored knowledge and searched issue/page text for that phrase. It did not enumerate projects. It selected Confluence plus only ATLAS and BEACON for the broad bounded search, omitting HARBOR. All live searches returned no matches. Two stored company/onboarding passages remained; the synthesized answer claimed there was no list/count and cited the company overview. That paragraph cannot establish the absence of Jira projects.

2. **“no u shoude be use jira and see how may project ?”**, turn `b1f9da36-a2c7-4bcc-81a9-30e6eabbe256`, saved **2026-11-17 00:13:56 Asia/Riyadh**. The structured shortcut requires the plural `projects` and specific list wording, so this also missed. Model routing treated the correction as help/social, and the nonfactual verifier permitted its explanatory response. The saved trace has two model calls, no source calls, no retrieval activity, and no citations. It answered how the integration works rather than performing the authorized Jira lookup.

Relevant code: [structured_chat.py:62](<C:/Users/manso/OneDrive/سطح المكتب/AWS ABA/ABA Project/code/apps/api/app/structured_chat.py:62>), [conversation_routing.py:30](<C:/Users/manso/OneDrive/سطح المكتب/AWS ABA/ABA Project/code/apps/api/app/conversation_routing.py:30>), [conversation_routing.py:66](<C:/Users/manso/OneDrive/سطح المكتب/AWS ABA/ABA Project/code/apps/api/app/conversation_routing.py:66>), [chat_agent.py:87](<C:/Users/manso/OneDrive/سطح المكتب/AWS ABA/ABA Project/code/apps/api/app/chat_agent.py:87>), and [chat_agent.py:105](<C:/Users/manso/OneDrive/سطح المكتب/AWS ABA/ABA Project/code/apps/api/app/chat_agent.py:105>).

## Live MCP verification and reproduction

The diagnostic used the running image's code and existing owner-authorized connection configuration. It did not use Codex's separate Atlassian connector as a substitute for Linkmind's MCP flow.

- **Actual structured question:** “What projects are available?” ran three real `searchJiraIssuesUsingJql` calls through `mcp.atlassian.com`, one per configured project, with `project = "ATLAS" ORDER BY updated DESC` (and BEACON/HARBOR equivalents). It returned the three project names from native Jira `project` fields, with live connection IDs/revisions/original URLs and no stored dependencies. This verifies **three configured, visible project scopes**, not every project in the Atlassian account. The implementation cannot discover empty/out-of-scope projects with this issue-based snapshot.
- **Screenshot retrieval replay:** the saved planner output `projects` again returned the same four stored passages plus real Jira and Confluence resources. Captured context contained four stored sources and eight live context entries after bounded context selection. Actual calls included `searchJiraIssuesUsingJql`, `getJiraIssue`, `searchConfluence`, and `getConfluenceContent`.
- **Newest failure retrieval replay:** the saved query `hi how many porject they` again yielded two stored passages and zero live hits. Captured Jira JQL included `project = "ATLAS" AND text ~ "hi how many porject they" ORDER BY updated DESC`; CQL likewise searched title/text for the same phrase.

The two retrieval replays reused recorded planner outputs and disabled synthesis. They are not claims that a new independent paid planner/synthesis replay passed or failed identically. The original saved turns provide the actual model-output evidence.

The normal connectors.live function updates health after a successful read. The first strict read-only probe rejected that bookkeeping; it is preserved in runtime-probe.json and must not be interpreted as an MCP outage. The completed replay suppressed only that lock/health bookkeeping inside an ephemeral diagnostic process. Actual source transport, parsing, scoped retrieval, source selection, and citation construction ran normally. No running service was patched. Before/after fingerprints confirm unchanged document/version/chunk/turn/audit counts and connection mode/generation/health values. See [completed runtime trace](<C:/Users/manso/OneDrive/المستندات/ChatGPT/ABA Project/output/source-investigation/runtime-probe-without-health-writes.json>) and [artifact verification](<C:/Users/manso/OneDrive/المستندات/ChatGPT/ABA Project/output/source-investigation/artifact-storage-check.json>).

## Live Only, stale data, and caches

- Connection mode `live` prevents connector sync retention. Home chat still unconditionally performs stored retrieval in its general route, then merges sources. The conversation model only stores document_ids; it has no live-only chat policy. The UI says “All sources.” This is the main source-boundary defect for your intended behavior.
- Stored Northstar documents are active current versions, not merely a stale UI cache. They remain eligible for retrieval on every new general question. Dataset provenance is lost: stored_sources sets synthetic only from connected-resource metadata, so these upload-origin fixture chunks reach synthesis with `synthetic=false`. Retrieved line-3 passages omit the original fictional-data heading.
- Previous replies and cited excerpts are saved in PostgreSQL. Current validation policy/access checks do not make mixed-corpus history incompatible with a new live-only intention. Source-policy compatibility needs an explicit rule.
- The MCP cache stores protocol negotiation/tool metadata for 120 seconds. It does not cache issue/page answer bodies. Current source access/revision checks fetch originals. Clearing it will not remove indexed Northstar content.
- Frontend code uses React Query for conversation display and sessionStorage for demo identity/recent entity IDs; no document-content localStorage/IndexedDB retrieval path was found. Browser storage itself was not directly inspected. The observed citations are independently explained by database rows and real runtime retrieval.
- The two newest queries show an additional evidence-validation problem: absence of a fact in a company paragraph was allowed to support a claim about absence of a project list. Discovery coverage must be tracked and negative/exhaustive claims constrained accordingly.

## Recommended next action

Review [the proposed implementation and acceptance plan](<C:/Users/manso/OneDrive/المستندات/ChatGPT/ABA Project/output/source-investigation/FIX_PLAN.md>). No deletion is needed to fix live-only answers: enforce source policies on the server, fix routing, label/isolate known demo data, and prevent test-loader contamination. Preserve legitimate uploads, stored knowledge, old evidence, and current MCP credentials/configuration. Changes remain pending your approval.
