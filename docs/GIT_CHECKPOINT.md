# Git checkpoint and RF branch workflow

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
