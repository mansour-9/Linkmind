# M2/M3 validation record

> **Historical evidence / compatibility note — 2026-11-14.**
> The dated implementation, checks, budgets and environment observations below are
> retained; they were not rerun or re-scored by this documentation update.
> The [active roadmap](IMPLEMENTATION_PLAN.md) and [scope](PROJECT_SCOPE.md) now
> prioritize source-only ingestion, a durable selected-source repository and bounded
> retrieval. [RF1](RF1_RESULTS.md) subsequently implements default-off enrichment in
> isolated current code; old next tasks/manual or paid commands are not authorization.
> Historical evidence/security/history remains intact; existing environments are unchanged.

Core local workflows and the two-document live Bedrock acceptance scenario are implemented and verified. This is a local MVP; independent review of the benchmark and hosted readiness remain outstanding.

## Implemented and exercised

- Immutable source versions, current projections, canonical identities, aliases, uncertain-match review and preserved entity URLs.
- Selectable-text PDF, DOCX, TXT and Markdown parsing with page, line, paragraph and table-row locators.
- Real boto3 Bedrock JSON-schema extraction, exact source-span validation and separate semantic verification.
- One bounded correction for extraction or answers, followed by the same validation again. Failed answers are not saved as trusted responses.
- Conservative identity resolution, explicit human merges and effective-period-aware conflicts.
- Leased jobs, attempts, stages, bounded retries, errors, migration-safe passage reuse and atomic publication.
- Revisions, deletion and access changes invalidate derived views and saved evidence dependencies.
- Hybrid exact/full-text/vector/graph retrieval with access filtering before each ranking channel.
- Leading semantic evidence is retained to prevent rare qualifiers being buried by broad identifier matches.
- Graph neighborhoods, Search filters/pagination, generated structured Wiki, conflict/identity reviews and persistent scoped Chat.
- Canonical metadata can guide entity scoping but cannot serve as factual source evidence or appear as internal IDs in answer text.
- Grounding-policy changes suppress superseded experimental answers while preserving history.
- Independent model accounting and explicit configured regional cost estimates.
- Royal Blue shared design system and responsive original evidence/download flows.

## Automated checks

On 2026-11-11:

- **25 parser/PostgreSQL/API tests passed** against an isolated local database.
- All eight schema migrations were applied, including upgrade of existing local M1 records.
- **Four Playwright tests passed**, covering upload → Processing → Graph → Wiki → question → citation, original download, persisted conversations and identity switching.
- The browser suite also checks 1440, 1024 and 390 pixels; no horizontal page overflow was found.
- TypeScript and Vite production bundling passed.
- Valid PDF text/page locators, DOCX paragraphs/table rows, original text offsets, rollback/retry, legacy passage IDs, identity merges/links, citation rejection, vector permissions, access revocation and saved-answer suppression have regression coverage.

Fixture tests verify deterministic behavior; they are not evidence of live model accuracy.

## Live Bedrock checks

The default AWS CLI login profile authenticated from the backend SDK in us-east-1.
Claude Sonnet 4.6 geographic inference and Titan Text Embeddings V2 both succeeded.
No infrastructure, IAM policy or quota was provisioned or modified.

Two original documents sharing CB-ALPHA produced connected knowledge and genuine ownership/launch-date conflicts.
A real answer attributed Amal and Omar to their respective documents without choosing a winner.
Original evidence and downloads were verified through the browser.

The account's geographic Sonnet quota was read as ten requests/minute. Shared pacing defaults to nine across API and worker processes.
Estimates remain unavailable unless verified model/region prices are configured; no AWS bill total is inferred.

## Full live benchmark

[BENCHMARK_LIVE.json](BENCHMARK_LIVE.json) records twelve real-processed synthetic documents and thirty question observations:

| Check | Result |
| --- | --- |
| Expected entity occurrences found | 17 / 18 |
| Expected claims found under the documented rubric | 13 / 13 |
| Response/citation-span checks | 30 / 30 |
| Automated answer rubric | 28 / 28 graded questions |
| Project identity groups | One canonical identity each for CB-ALPHA, CB-CEDAR and CB-BIRCH |

The missed entity is the separate Amal person occurrence in alpha-revision.md. Its ownership claim and evidence were retained.
Claim scoring accepts documented deadline/launch_date aliases and separate decision/approval representations.
The two ungraded questions are stateful revision/deletion controls, covered by integration tests rather than keyword scoring.
Some questions intentionally have insufficient or restricted evidence, so 30/30 citation checks does not mean thirty factual answers were generated.

The contradiction rubric was corrected to accept the equivalent wording “do not agree.” The scoring note preserves that distinction; no response was changed.
Implementation-agent review found an earlier permissive identity rubric that accepted a wrong same-name project match. Both retrieval/grounding and the rubric were corrected.
Earlier runs are retained as diagnostic baselines, including throttling and validation failures; they are not passing quality results.

[BENCHMARK_TARGETED_FIXES.json](BENCHMARK_TARGETED_FIXES.json) records targeted live checks for dates, decisions, person identity and uncertain projects.
After the full run, source-only semantic verification was tightened further and assigned grounding policy grounded-v3.
The four targeted checks and the browser journey validate that final policy. The full thirty-question snapshot is from the preceding policy; it must not be described as a complete grounded-v3 rerun.

The source/gold records were inspected during implementation. Independent human review, broader real-company documents and measured pilot targets are still required.
These small automated scores do not establish perfect entity extraction, citation entailment or production answer quality.

## Remaining boundaries

- Demo authentication is local only. Cognito and hosted security hardening remain M5.
- Original files/history are retained after product deletion. Hosted purge and backup-retention policy remain open.
- Wiki pages are structured attributed views rather than unchecked generated prose.
- Search uses bounded candidate pools and exact pgvector comparisons. Larger-scale ANN tuning is future work.
- Automatic conflict comparisons cover the configured single-valued attributes; other attributed claims remain available for review.
- Ready publications are immutable; changing processing configuration does not silently replace already-published facts.
- More representative PDF/DOCX documents, throughput/load tests, independent benchmark review and semantic-quality improvements remain.
- Live Jira/Slack connectors are M4. CDK deployment approval and hosted operation are later milestones.
- OCR/images and Excel are later releases. Arabic remains M7.
