# AsterBridge Labs enterprise connector test organization

This is an entirely fictional, connected company dataset for Linkmind retrieval and source acceptance. The scenario date is **November 16, 2026**, in Asia/Riyadh. The 18 employees are a cross functional delivery cohort within a mid sized fictional company, not its entire employee census.

The dataset is separate from Linkmind application code. It does not require graph extraction, new infrastructure, a model call, or a change to an existing preview.

Repository cleanup, November 17: the authored scenario catalog, generators and their
instructions are versioned. Generated input payloads, expected answers, text/Office
files, publication maps, provider responses/readbacks, account metadata and validation
artifacts remain ignored and preserved locally. Regenerate offline inputs using the
scripts below; the generators do not publish or contact external services.
Publication/readback validation requires those separately retained local artifacts; a
fresh checkout does not contain or certify remote source readbacks. Existing publication
maps record historical IDs and do not authorize another publication run.

## Published and local content

| Source | Result | Location |
| --- | --- | --- |
| Jira | 3 new test projects and 108 issues, 36 per project | [ATLAS](https://mansor1233123909.atlassian.net/browse/ATLAS), [BEACON](https://mansor1233123909.atlassian.net/browse/BEACON), [HARBOR](https://mansor1233123909.atlassian.net/browse/HARBOR) |
| Jira history | 108 comments containing dated fictional history, plus 21 native issue relationships | `jira/comment-responses/`, `jira/link-results.json`, `jira/snapshots/` |
| Confluence | 25 authored pages published in one dedicated ABL test space | [AsterBridge Labs Test Organization](https://mansor1233123909.atlassian.net/wiki/spaces/ABL/overview) |
| Business files | 12 DOCX and 6 XLSX files generated locally | `onedrive/AsterBridge Labs/` |
| Evaluation | 62 prepared cases across Jira only, Jira plus Confluence, and all three sources | `test-cases/` |

The Confluence pages use Company, Engineering, ATLAS, BEACON, and HARBOR page groups within **one dedicated test space**, rather than creating five spaces. Jira project IDs are ATLAS `10002`, BEACON `10003`, and HARBOR `10004`. The confirmed Confluence space ID is `262712`, key `ABL`. Cloud ID is `ccf2f991-7acb-4c59-8be2-baf48d7b7eaf`. These identifiers are not credentials.

Actual issue identifiers and URLs come from Jira responses, never from anticipated issue numbers. The source manifests record actual publication and local file state. The OneDrive files have **not been uploaded** by this task. A workspace folder synchronized by the user's own OneDrive client is not connector confirmation of an upload or an accessible drive item.

## Company narrative and important evidence

- ATLAS moved its beta target from November 20 to November 27 because claims v2 and consent filtered event publishing remain incomplete.
- BEACON ingestion, cohorts, and adoption reports depend on ATLAS events. Its pilot moved from November 30 to December 4, with reconciliation still required.
- HARBOR webhook delivery passed technical readiness on November 13, while authentication, the partner agreement, and Product launch authorization remain open.
- Partner authentication implementation moved from Omar Haddad to Leo Martinez effective November 12. Omar remains shared identity owner, Maya engineering delivery accountable, and Aisha partner product owner.
- The approved identity policy requires tenant and product audience validation. The ATLAS refresh replay fix is complete, but BEACON partition work and HARBOR consumer work remain open.
- Raw analytics retention is 30 days, aggregate retention 13 months, and security audit retention 90 days. Retained drafts document earlier proposals.
- An Operations meeting claim of a 1.0 percent reconciliation threshold conflicts with current Jira and Data runbook requirements of 0.5 percent. No Data or Security approval supports the meeting claim; case C16 tests how the discrepancy is reported.

`organization/facts.json` records the operational facts and supporting source seeds. The business documents add distinct impact and management action evidence. Stage C requires those report details as well as Jira status and a Confluence technical rule. The validator checks that the distinct business evidence is absent from Jira and Confluence, so the case cannot be answered completely from a single issue.

## Source semantics

Fictional employees are not real Atlassian users. The test account lookup found no Maya Chen account; no fictional accounts were created, invited, or assigned. Native assignees remain unassigned. Descriptions and labels identify fictional owners explicitly. Native reporters and comment authors are the actual authenticated dataset operator.

Native workflow statuses are To Do, In Progress, and Done. Blocked business work uses **In Progress plus `abl-blocked`**, with explicit dependency and reason. The full readback contains 54 In Progress, 35 Done, and 19 To Do issues. Planning sprint and release names are recorded in descriptions, not represented as confirmed native sprints or fix versions. No Jira sprint/version creation operation is exposed by the connected plugin.

Every issue has the dataset label `asterbridge-labs-v1`, a unique `abl-seed-...` label, and an `abl-owner-...` label. Narrative event dates are fictional. Remote `created`, `updated`, and comment timestamps are the actual seeding times. A newer import timestamp alone does not supersede an older effective policy or establish historical implementation order.

## Test through Linkmind

1. Start with **Stage A** from `test-cases/jira-tests.json`. In the chosen isolated Linkmind environment, authorize the actual Jira site and selected ATLAS, BEACON, and HARBOR scopes. The current native adapter scopes one project per connection, so use separate selected project connections. Begin with Live Only, verify original IDs, typed fields, source URLs and current access, then validate selected sync separately.
2. For **Stage B**, authorize Confluence space `262712` and only the relevant page tree. Use `test-cases/cross-source-tests.json` with stage `B`. Compare draft effective dates, approved decisions, implementation status, and exact evidence. A successful Jira import does not establish Confluence acceptance.
3. For **Stage C**, upload the business DOCX files to an explicitly authorized Microsoft folder and record returned drive, item IDs, URLs, revisions, and access. Until then, manual DOCX import can test retrieval, but label the source as a manual upload. It does not prove the OneDrive connector. Files and editable Markdown copies are under `onedrive/`.
4. The recorded RF5 preview at `http://127.0.0.1:5196/ask/sources` supports explicitly selected stored documents plus up to **two connected resources**. Choose a stored report, one relevant Jira issue, and one Confluence page. Broader portfolio questions may need selected synchronized evidence or multiple bounded requests; do not silently expand the resource limit. The preview has not been configured or changed by this seeding task.
5. Compare the answer and citations with `expected-answers.md` and the case's required source contributions. Record actual answer, original citations, observed time, latency, coverage, and errors in `run-results.json`. Every case starts `not_run`; dataset consistency is not application or model acceptance.
6. Configure real ACLs and distinct test principals before permission tests. Intended `security-reviewers` metadata in this fixture is not an enforced ACL. Run revocation, deletion, partial response, older revision, and injection cases only on disposable dataset records in an isolated environment. Check every derived answer, citation, cache, history, and metadata surface.

Useful first records are ATLAS-4 (claims), ATLAS-6 (events), ATLAS-16 (release), BEACON-4 (ingestion), BEACON-15 (release), HARBOR-4 (authentication), HARBOR-5 (handover), HARBOR-14 (delivery acceptance), and HARBOR-15 (business approval). Exact references are also in each case.

## Limits and outstanding checks

- The current inspected Linkmind Microsoft file adapter accepts PDF, DOCX, Markdown, and text; it rejects XLSX as `unsupported_format`. The six Excel files are usable business artifacts, not evidence that Linkmind can ingest spreadsheets. Editable Markdown companions permit labelled text retrieval tests; add XLSX extraction only through a separately authorized implementation.
- The DOCX files passed structural and hyperlink checks. The required `render_docx.py` attempt failed because `soffice.exe` is unavailable. Their final Word page layouts have **not** been visually verified. Do not mark the Word render gate passed.
- All seven workbook sheet previews were reviewed. Formula controls, error scans, and input change/restoration checks passed in the bundled artifact engine. Native Microsoft Excel interactive recalculation was not exercised. The artifact process returned exit code 1 after exporting all files and writing its checks; independent saved-file checks are included in validation rather than treating that exit as success.
- Confluence space creation also generated its standard homepage and two template pages. Those three platform-generated pages are excluded from the 25 authored test pages. They are preserved, not deleted.
- No source ACL configuration, Microsoft upload, Linkmind account connection, application trial, paid model call, production change, deployment, commit, or push was performed by the dataset builders.

## Local reconstruction and safe reruns

Read `scripts/README.md` before regenerating. `catalog.py` and `build_dataset.py` are the editable source for organization records, Jira payloads, pages, and business sources. `build_documents.py` produces Word files and `build_workbooks.mjs` produces Excel files with the bundled artifact library. `build_evaluations.py` derives expected answers and source requirements. `validate_dataset.py` checks saved artifacts and remote snapshots.

Use `scripts/publish-with-connected-tools.md` to reconstruct in another authorized test environment or safely resume. Native IDs are environment specific. Preserve the current maps as a snapshot and build a separate map for a new environment. Reconcile by unique seed labels and exact page titles before creating anything. Never copy source credentials, manufacture IDs, or rerun creation blindly.

The full dataset is intentionally uncommitted until reviewed. `source-manifest.json` is the main inventory, `jira/jira-manifest.json` is the Jira publication record, `validation/consistency.json` is the measured consistency result, and `test-cases/rf-coverage.json` maps prepared evaluations to RF1 through RF6 without changing their acceptance status.
