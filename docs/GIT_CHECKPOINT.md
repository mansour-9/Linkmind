# Git checkpoint and RF branch workflow

## November 17 demo publication

The user explicitly approved cleaning up the completed work, pushing it, and merging
it into `main`. This supersedes the older no-main-merge instruction below for this
delivery. Publish through `rf5/chat-performance-source-links`, preserving all existing
history and branches; no force push, reset or branch deletion.

The cleanup versions application source/tests, additive migrations 0019/0020, demo
delivery notes and the authored fixture catalog/builders. Generated datasets, full
provider responses, screenshots, publication maps, credentials, database backups and
local trial outputs remain ignored and preserved locally. The CI compose override
explicitly uses an isolated mock runtime with networking and shared budget disabled.
Publishing Git source does not migrate or redeploy any running environment.

Demo validation: 444 isolated API passed/2 skipped, build and five focused browser
workflows passed; installed desktop/mobile/status/source-preview checks passed.
See [demo results](DEMO_READINESS_RESULTS.md). Publication checks below record any
additional clean-checkout/CI validation without repeating paid inference.

Publication cleanup: **119 files** in the new delivery commit, rather than approximately
800 pending files including generated output. Merging the existing branch lineage also
includes 15 earlier commits, for **341 changed files relative to the old main tip**.
A clean index export built successfully and passed 444 API tests/2 skips. Updating
six browser test files removed obsolete UI assumptions and retained coverage of
selected sources, organization-default uploads, streaming retry, history and citations.
The broad browser run passed 44/45; its historical-preview failure exposed a missing
retained-dependency argument. Passing the server-returned dependency through the
existing access endpoint repaired it, and all seven affected source/history workflows
then passed. GitHub Actions runs the full offline suite before main publication.

Secret scan found no new credentials. Its one historical finding was the SHA-256
source fingerprint at `RF2_VALIDATION.json:43`, confirmed as metadata. Full evidence
and publication logs remain in ignored `.local/git-publish-2026-11-17`. No connected
runtime was redeployed during this Git cleanup; the historical-preview follow-up is
in source pending a separate runtime installation.

The user requested publishing the latest completed work and placing the next RF work
on a new branch. This authorizes normal commits/pushes for this checkpoint and RF5;
it does not authorize rewriting history, deleting remote branches, merging main,
deploying infrastructure, connecting real source accounts or repeating paid trials.

`checkpoint/rf1-rf4-local` preserves the existing implementation lineage and the
validated RF1–RF4 local source, migrations through 0018, and trust policy v10.
The checkpoint has 315 API / 39 browser / build validation; the final eight OAuth
checks and bounded Sonnet repair evidence are recorded in RF34_RESULTS.md.

`rf5/cross-source-journey` starts from that checkpoint. New RF5 changes belong there,
with isolated local mock validation. Real MCP/provider trials remain deferred. Main
and every existing runtime/database remain protected. Neither branch is production
acceptance or a main-data migration instruction.

Keep source, synthetic fixtures and reviewed validation summaries versioned. Full
provider responses, local preflight/checkpoint outputs, credentials, databases and
private source files remain ignored and preserved locally. Do not use destructive
cleanup, force pushes or a new spend ledger to obtain a clean working tree.

Clean-checkout CI includes the application root on the Python import path so the
offline company-runner tests can import `scripts`. The two private-original Lantern
checks explicitly require `LANTERN_ACCEPTANCE_DIR`; public CI skips those two checks
with a reason rather than publishing the originals. They remain part of the recorded
315-test local acceptance when the private fixture directory is supplied. All ordinary
source, connector, grounding and permission checks remain enabled in CI.
