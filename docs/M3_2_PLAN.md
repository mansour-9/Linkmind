# M3.2 — Document-processing reliability

Planning checkpoint: 2026-11-12. Implementation has not started.

## Decision

Keep **one milestone with two sequential checkpoints**, M3.2A and M3.2B. Diagnosis
defines the implementation and acceptance dataset, so separate milestones would
create an artificial completion boundary. M3.3 retrieval/identity, M3.4 verified
GraphRAG, and M4.1 read-only Jira retain their existing order.

## Starting point

The app has immutable uploaded revisions, retained source passages/locators, exact
quote validation, bounded extraction correction, atomic publication, role/source
permissions and persisted processing attempts. Graph, Search and Chat already use
authorized current knowledge. The UI checkpoint includes the loaded synthetic
38-entity/105-relationship Graph demo and canvas-only mode.

The existing `M3_2_BASELINE.json` records an older preparation snapshot. Retain it
as history; create a newly dated baseline tied to the Git checkpoint when M3.2A
starts. Historical live-model results do not substitute for a current benchmark.

## M3.2A — Reproduction and a measurable baseline

Deliverables:

- Audit current parsing, passage creation, quote validation, job retries, embeddings
  and publication. Record which concerns already have working safeguards.
- Reproduce the reported PDF exact-quote failure using an authorized sample or a
  synthetic case. Classify parsing, normalization, locator, schema and provider
  failures separately. Do not assume the root cause before reproduction.
- Establish a format matrix covering selectable PDF, DOCX paragraphs/tables, TXT
  and Markdown. Include Unicode, punctuation/ligatures, line endings, headings,
  long sections, tables, empty/malformed/large files and scanned PDF rejection.
- Freeze current source/fixture/test hashes and independently review expected
  evidence for the representative cases. Keep benchmark expectations unchanged.
- Record baseline success/failure categories, processing-stage time, evidence
  accuracy and available model usage/cost. Compare custom and managed approaches
  using official documentation; do not provision or migrate infrastructure.
- Propose numerical quality/latency/cost targets from the measured baseline and
  record which need user/domain review before evaluating the implementation.

Exit gate: a repeatable failure case, a reproducible baseline, a documented format
matrix, and a concrete implementation design. If the reported failure cannot be
reproduced without the original file, identify that dependency honestly and continue
the independent synthetic/format checks. Do not claim the failure resolved.

## M3.2B — Reliable processing and safe reprocessing

Implement only the changes justified by M3.2A:

- Add normalization with mappings to retained original text and original source
  locations. A displayed citation must resolve to the exact supporting source.
- Add structure/token-aware bounded chunks, measured overlap and parent context
  while preserving paragraphs, headings, tables and page/line/row locators.
- Apply bounded repair to recoverable schema/quote errors. Keep the same exact
  grounding validator; unsupported facts still fail after the repair limit.
- Version processing/index generations and backfill alongside the current data.
  Validate a new generation before switching; preserve immutable document versions,
  old citations, permissions and a tested rollback path.
- Show actual stages and actionable failure categories, distinguishing provider
  credentials/access from invalid evidence and unreadable source content.
- Measure results against the frozen cases and agreed targets. Run permission,
  tenant, revision, retry/concurrency, source-download and saved-answer regressions.

Exit gate: the reproduced PDF failure passes without weakening evidence validation;
the format matrix and existing regressions pass; a failed/revoked/superseded job
cannot publish invalid knowledge; reprocessing and rollback preserve existing data
and citations; measured limits and untested behavior are documented.

## Boundaries

OCR, image/Excel ingestion, Jira credentials/import/sync, new orchestration, hosted
deployment and Arabic are outside M3.2. Original Jira links and future saved graph
views remain in the [Jira discussion](JIRA_KNOWLEDGE_NEXT_STEPS.md).
Default development and CI remain deterministic mock mode. Any live-model evaluation
must have an agreed run scope and usage budget; no new AWS resources are required.
This plan authorizes preparation, not an automatic migration of the main database.

## Delivery record

Each checkpoint updates its issue with changed behavior, commands/results, source
locators/screenshots when relevant, and limitations. Code changes use focused pull
requests. M3.2 closes after both checkpoints and the outstanding quality review are
complete; a green synthetic test suite alone does not establish live model quality.
