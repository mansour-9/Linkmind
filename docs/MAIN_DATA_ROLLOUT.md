# Main-data rollout review: F1 readiness and staged enrichment

> **Historical cutover proposal; safety reference only — 2026-11-14.**
> No cutover is authorized. The [RF roadmap](IMPLEMENTATION_PLAN.md) replaces the
> old enrichment-first next task. Keep the backup/restore and inference-accounting
> safeguards below, but reinspect actual images/schema/ledger configuration and
> prepare an RF-specific candidate/acceptance/rollback review before execution.
> This proposal targets 0011; later source includes 0012. Do not blindly run its
> commands or require successful full extraction before source-only retrieval value.
> Main and all preview data/services remain untouched by this documentation update.

Prepared 2026-11-13. **Execution against `company-brain` is pending approval.**
F1.3 implementation and rollout preparation are authorized; the user chose to
complete those before F2. No main application mutation, infrastructure provisioning,
model change, or independent USD 10 allowance is included in this procedure.

## Observed target and remaining decision

The read-only audit found the main database already at `0010_test_budget`, with
54 documents, 59 versions, 305 passages and 10 active documents. Historical F1.1
notes saying its database was unmigrated are not the current inventory. The next
schema upgrade is `0011_staged_enrichment`; do not rerun or rebuild F1.1 as new work.
Fingerprints and restored legacy/candidate counts are in [rehearsal evidence](F1_3_REHEARSAL.json).

The running main API has `AI_PROVIDER=bedrock` and the Northstar test run variables,
but its database has **no inference-budget run row**. The running worker has
`AI_PROVIDER=bedrock` without `BEDROCK_BUDGET_RUN`. This is an existing configuration
inconsistency, not a new inference allowance or a configuration changed by F1.3.
Do not start inference-enabled main services with this configuration during rollout:
it would not share the existing Sonnet preview's persistent ledger.

The concrete proposed first cutover uses **mock mode for API and worker**, preserving
all existing data and keeping paid inference disabled. Subsequent main-app Bedrock
enablement requires a reviewed shared accounting arrangement or a separately
approved budget. The existing USD 10 test run remains in `linkmind-company-sonnet`;
do not copy, initialize, reset or increase it in the main database.

The prepared [mock cutover override](../code/compose.main-rollout-mock.yaml) must be
the **last** Compose file, after the three files currently used by the main stack.
It requires explicitly reviewed backend/frontend images, sets both services to mock,
and removes the misleading test-run environment setting without touching any ledger.
Its merged configuration was verified read-only; it has not been applied to main.

## Before the maintenance window

1. Record the actual API, worker, web and database image IDs separately, plus the
   Compose project/files, bound port, and database/artifact volume names. API and
   worker may be using different image builds despite sharing a tag. Preserve the
   immutable image IDs and generate a rollback Compose override naming each image.
   Do not dump credential environment variables into a report or Git.
2. Retain the reviewed current build and F1.3 candidate commit/image. Build images
   before the maintenance window. Confirm no migration after 0011 is accidentally
   included. Backups belong under ignored `.local/` or a user-approved private
   backup destination; never commit database dumps or uploaded originals.
3. Agree on the maintenance window, inference-disabled cutover, and rollback rule.
   If new writes occur after the snapshot, restoring it discards those writes;
   preserve/export them or keep writers disabled until acceptance is complete.

## Consistent backup and actual-data rehearsal

1. Stop web/API mutations and workers in **only** `company-brain`; leave PostgreSQL
   running. Verify no active processing lease or unaccounted writer remains. Capture
   counts, active pointers, passage/citation and claim fingerprints, and source-file
   checksums. A live `pg_dump` alone is not an atomic database-plus-files snapshot.
2. Create the custom-format dump inside the database container, then copy it as a
   binary file with `docker cp`. Avoid PowerShell text redirection of the dump:

   ```powershell
   docker exec company-brain-db-1 pg_dump -U brain -d brain -Fc -f /tmp/pre-f13.dump
   docker cp company-brain-db-1:/tmp/pre-f13.dump <BACKUP_DIRECTORY>/database.dump
   ```

3. Archive the actual originals volume with a read-only source mount. Explicitly
   close the archive before completing the backup; verify archive readability,
   checksum, and a complete file manifest. Preserve both dump and archive together.
4. Restore into a separately named, empty, loopback-only rehearsal database and
   artifact volume. Fail if either target contains unreviewed data. Keep its API and
   worker in mock mode. Apply the candidate's additive migration and compare IDs,
   fingerprints and original files against the frozen snapshot.
5. Verify actual-data access as owner, another organization member and another
   organization; search-ready/failed sources, active graph freshness, evidence,
   downloads, history suppression and one bounded upload/revision/refresh journey.
   Do not send original company files to a paid provider as part of rehearsal.

## Approved cutover and acceptance

1. Confirm the main snapshot still matches the frozen writers. Apply migration 0011
   using the candidate image, then start candidate API/worker in mock mode against
   the unchanged original volumes. Start web only after the API is healthy.
2. Confirm legacy source/citation IDs and artifacts are unchanged. Verify current
   graph facts use the live generation, and staged/rolled-back facts are excluded.
   New source revisions must never revive superseded relationships.
3. Verify the new `Refresh knowledge` journey and distinguish failed candidate work
   from still-available prior enrichment. Check revoked access and saved answers.
   `grounded-v4-staged` suppresses older experimental answers rather than silently
   trusting them under the new generation policy. Their stored records remain.
4. Review observed counts, errors and the agreed acceptance results before reopening
   writes. Record the deployed image IDs and rollback snapshot location.

## Rollback

If acceptance fails while writes remain frozen, stop candidate API/worker/web and
restore the reviewed database and originals together into verified target volumes;
start the individually recorded prior service images with their compatible schema.
Verify the same fingerprints, downloads, permissions and citations before reopening.
Do not combine an old build with the candidate's active-generation schema/data or
reactivate obsolete relationships by changing a pointer.

Migration 0011 allows a metadata downgrade only before any enrichment-generation
records exist and without active/staged-failed jobs. Once a candidate has been
retained or activated, it deliberately requires the snapshot-based recovery path.
Never force a downgrade around that guard.

## Completed synthetic rehearsal

The actual helper [`f13_rollout_rehearsal.py`](../code/scripts/f13_rollout_rehearsal.py)
was run on three new disposable Docker projects. It backed up a schema-0010 fixture
database and original files with writers stopped, restored them into the candidate,
upgraded to 0011, checked citations/history and staged refresh, then restored the
same snapshot with the old build in a third project. Counts, evidence fingerprints,
source pointers and file checksums matched; the main inventory was unchanged.

Reproduce with a **new** run ID and output directory:

```powershell
Set-Location code
python scripts/f13_rollout_rehearsal.py --run-id review2 --output ../.local/f13-rollout-review2
```

The helper refuses existing target projects, volumes or output directories and
mutates only its named disposable projects. Its `company-brain` access is read-only.
This synthetic restore result does not replace the actual-main-data rehearsal or
authorize the maintenance window.
