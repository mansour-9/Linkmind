# Automatic chat and Documents — delivery and measured limits

Installed local app: http://127.0.0.1:5197

## Delivered

- New ordinary chats use server-enforced automatic access to permitted Documents and enabled owner-authorized sources. The source selector is removed; explicit legacy policies keep their boundaries.
- Model-directed interpretation of typos/Arabic/English, up to three read/search rounds, five model operations and the existing 90-second question guard. Only declared connections and discovered resource IDs can execute. Exact citation and independent semantic checks remain.
- Shared multi-file upload and drag/drop in Documents and chat; persisted attachment references; private default, explicit organization sharing in Documents, readiness/errors, originals/revisions, access and deletion controls. Text PDF/DOCX/TXT/Markdown, 20 MiB per file. No OCR or XLSX claim.
- Confluence ABL: 12 new fictional department/customer/partner pages and 4 expanded company/project overviews; all 16 were read back. Existing dates, ownership handovers and Jira content were preserved. See confluence/readback.json.
- The old current-workspace corpus was reset after a verified database restore and cleanup rehearsal. Removed 46 document records/66 versions/443 passages/216 entities and dependent knowledge; archived 21 old chats; removed 299 byte-verified original files from that organization only. Other organization data, connection configuration fingerprints, audit history and spend were preserved. Backup and original source snapshots remain outside application retrieval.
- Knowledge/graph extraction and periodic knowledge-building jobs remain deferred. Indexing ordinary files still works without a graph. No embeddings, hosted deployment or employee-shared service identity was added. Microsoft folder search has scoped offline coverage; an actual OneDrive connection is still not verified.

## Validation

Final TypeScript/Vite build passed. API regression suite: 414 passed, 2 skipped; see api-release.txt. Browser acceptance passed attachment reading, Documents drop, multiple files, unsupported format, and responsive layouts. Installed preview checks confirmed zero active Documents, zero graph nodes/edges and no source selector. These mock/browser checks do not establish real answer quality.

## Real answer quality — partial acceptance

Six new cases were prepared. Two passed source review (ownership follow-up; BEACON/customer/partner), one person question produced only a partial answer, one failed delivery at source reauthorization, and two could not dispatch within the remaining reservation ceiling. See quality-review.json and real-acceptance-corrected.json. Typical completed-case latency was 43–47 seconds. This is not broad production acceptance.

The partial case's remaining sentence omitted the direct subject/project after another statement was rejected. Answer guidance now requires standalone subject/project statements. The source-read path now bounds originals to four and reuses sequential MCP sessions for fresh checks; a read limit is distinguished from access/revision changes. These follow-up changes passed isolated tests; they were not paid-retested.

## Initial failure and accounting

The first planner request was rejected with ValidationException and returned no usage. Its USD 0.0646239000 reservation remains unknown. The guard paused. The new planner wire schema was corrected against the documented Bedrock subset while keeping local length/array validation; all object properties are closed/required. Reference: https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html

The user explicitly approved resuming while preserving all five unknown calls/USD 0.1836305200 held, with a remaining USD 1.9353/23-operation ceiling. The corrected run used 20 settled operations, USD 1.8806601 conservative reservations and USD 0.4043292000 measured spend. Combined initial+corrected reservations were USD 1.9452840000, within the original USD 2 bound. No paid replay followed the post-acceptance repairs.

Original project ledger after acceptance: USD 6.1672753600 spent; USD 0.1836305200 held unknown; cap USD 10; paused=false. Unknown reservations were not released. Acceptance attachments were removed from active Documents and acceptance chats are archived after evidence preservation. No automatic repeat or fresh test allowance is implied.

## Review and recovery

Database backup, artifacts archive, restore verification, cleanup rehearsal/result, Confluence publication/readback, browser evidence, original source snapshots, code-change hashes and actual model evidence are retained beside this report. Application checkout: C:/Users/manso/OneDrive/سطح المكتب/AWS ABA/ABA Project. Code remains local; no push/merge occurred.

Restore instructions are in the application docs/AUTO_CHAT_ROLLOUT.md. Application rollback must never rewind or reset the original independent spend ledger.

Final installed runtime verification: schema 0020; zero active Documents, graph entities and active chats; preserved connection fingerprint; original ledger paused=false; running source hashes match the reviewed candidate. See final-runtime.json and installed-browser.json.
