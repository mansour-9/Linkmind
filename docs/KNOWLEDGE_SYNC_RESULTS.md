# Company Knowledge Base and Knowledge Sync

## Real-source preview at 5213

The real-source Knowledge Sync preview is available at `http://localhost:5213/admin/knowledge-sync`. The existing `5206` and `5212` environments retain their own data and builds. The `5213` preview uses the existing frontend and mock inference for chat, with live provider reads for collection. The work does not change the chat UI.

One completed sync collected and indexed 181 authorized records in 203 seconds with zero failures and zero model calls. Jira contributed 36 issues each from ATLAS, BEACON, and HARBOR. Confluence contributed all 70 pages in ABL. Notion contributed all three selected handbook pages. Independent readback matched all Confluence and Notion IDs to the authorized scopes. The worker published 198 explicit relationship occurrences. The manual Documents catalog remained empty.

The live Confluence tool advertises `cursor` pagination. The collector resubmits the opaque continuation cursor to the same bound MCP tool and keeps the space restriction on every request. This resolves the Confluence collection issue recorded in the `5212` history below. Knowledge Base search also reuses current short-lived source authorization and refreshes a bounded batch; a search read limit leaves already valid authorizations intact. Opening specific evidence still checks that item's access.

Seven focused API tests passed. The final real-browser check verified the completed dashboard, HARBOR Knowledge Base results, an original provider evidence URL, and the empty manual Documents catalog. The measured filtered search took 5.3 seconds on a cold authorization check.

## Full synchronized record reader at 5213

Fresh read-only MCP comparisons matched the retained ATLAS-23 description and indexed Jira fields, the HARBOR partner pilot page's retained Confluence HTML, and the exact normalized Markdown snapshot for the AsterBridge Labs company and teams page in Notion. PostgreSQL retains Jira's structured fields and Confluence's page body. The Notion body is in the existing artifact volume with its revision and locator in PostgreSQL. The old Knowledge view used graph entities and claim lists, and the evidence view displayed a single chunk, such as the Jira key.

The Knowledge catalog now reads accessible synchronized records directly, including records without claims or graph entities. The reader preserves the source body, timestamps, original links and explicit relationships. Evidence can open the corresponding retained version inline, and normalized downloads are labelled as Markdown exports. The reader uses supported source text and formatting. Provider attachments and embedded media remain available through their source when present.

The 5213 browser check covered all three real records, complete readable bodies, the ATLAS project and Aisha Rahman links, the external Jira tab, the cited passage and retained-version handoff, the Notion mobile layout and a denied non-owner request. A browser check using an intercepted sample response validated formatting and safe links. The web build and isolated API suite passed with 469 tests and two skips. The installed database still has 181 searchable synchronized records and one sync run. No re-sync, schema migration or model call was needed.

## Main publication validation

The publication includes migration `0021`, the unified sync worker, the full reader, and backend corpus boundaries. The clean stack built and migrated successfully. The isolated suite passed 457 API tests with two skips. A separate mock browser check ran sync, opened the retained record and its evidence on mobile, denied a non-owner read, and verified that the record was excluded from manual Documents and chat. The publication uses the existing bounded chat path with the corpus boundary and Notion integration.

## Earlier mock preview at 5212

Implemented in an isolated local preview at `http://localhost:5212`. That preview uses mock inference and a labelled synthetic Confluence connection. The real-source installation at `5206` keeps its existing build and data.

## Content and access

Migration `0021_company_knowledge` adds immutable resource-domain classification and the sync schedule, run, source-task, item and event records. The existing artifact store, revision history, PostgreSQL text indexes, FastAPI service and worker are reused. Older classified uploads retain their visibility. Existing documents lacking reliable provenance are kept outside the two active domains.

Documents accepts admin TXT and text-based PDF uploads. The manual catalog, focus picker, file-revision operations and chat text retrieval use the manual corpus. Knowledge Base Search, Knowledge, People and Graph use the synchronized corpus. Saved chat history keeps its existing access checks. New messages use live MCP and authorized manual documents, including through explicitly scoped source answers. The backend rejects chat attachments and rejects synchronized document IDs as answer sources. Background collection and publication make zero model calls.

## Synchronization

**Admin → Knowledge Sync** provides Sync All Now, a daily configurable IANA-timezone schedule, and run history with source counters and event details. A run snapshots all eligible Live + Sync connections owned by the admin. PostgreSQL leases protect page checkpoints and retries. A source failure allows the other tasks to finish. Jira uses incremental checkpoints with overlap. Confluence and Notion compare retained revisions, and the Notion adapter reads only explicitly selected pages. Source authorization is checked in bounded batches and existing visibility checks gate read surfaces.

Jira project/issue and assignee relationships come from original structured fields. Provider account IDs identify assignees when present. Other pages can contribute explicit role lines with exact evidence; unsupported prose stays searchable as text. No inferred graph relationships are published.

## Verification and connector readiness

- The isolated browser smoke exercised Sync All Now, source completion, schedule settings, searchable synchronized content, an empty manual Documents catalog, manual TXT and PDF uploads with chat citations, and a 390 px mobile layout.
- Real, read-only scope enumeration completed for all 108 Jira issues across ATLAS, BEACON and HARBOR, and all three selected Notion pages. The current Confluence connection can still read an individual page live, but its available bulk collection path requires a configured read credential. Complete real Confluence sync remains unverified. Sync eligibility now checks a real collection batch before enabling.
- A separate isolated worker run retained, indexed and projected 36 actual HARBOR Jira issues and three actual selected Notion pages. A second run skipped all 39 and left exactly 39 resources. The run stored 36 original Jira project links and recorded zero model usage. A focused read-only projection check validated three explicit Notion page-owner relationships from the retained pages.
- The final isolated API suite passed 465 tests with two skips. Existing legacy behavior tests ran in their mock-only compatibility mode, and the new Knowledge Sync tests explicitly exercised the enforced domains. The frontend TypeScript and Vite build passed.
- Publishing to existing environments, employee account management, broader organization grants, and paid chat replay remain separate work.
