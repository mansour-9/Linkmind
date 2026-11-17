# Contributing to Linkmind

## Planning authority

The 2026-11-14 direction is a unified company repository with retrieval-first AI.
Use [the single roadmap](docs/IMPLEMENTATION_PLAN.md), [scope](docs/PROJECT_SCOPE.md)
and [current/target architecture](docs/ARCHITECTURE_M2_M3.md). The restructure was
documentation only; the user subsequently requested RF1 and isolated validation.
Other RF implementation, paid inference and main rollout require their own scope. Old handoffs,
paid-test permissions, main-cutover proposals and original automatic-build instructions
are not active authorization. Preserve pre-existing edits, completed work and evidence.

Target ordinary ingestion does not invoke Sonnet structured extraction/conflict checks;
optional enrichment remains explicit/default off. Source-only retrieval and common
local/live evidence are core. Keep existing security boundaries and immutable sources;
detailed enterprise groups/Spaces design and advanced graph work are deferred.

## Working sequence

1. Read `AGENTS.md`, the active milestone, and relevant architecture/frontend guidance.
2. Branch from `main`, for example `rf1/lightweight-ingestion` or `fix/quote-locator`.
3. Keep a change focused and preserve existing document/evidence API contracts.
4. Validate in a disposable mock Compose project and record what actually passed.
5. Open a pull request with the problem, resulting behavior, validation and limitations.

The latest local RF1–RF4 checkpoint is published on `checkpoint/rf1-rf4-local` while
main remains at its protected earlier checkpoint. The authorized RF5 branch starts
from that source checkpoint; it does not migrate or deploy main. See `docs/GIT_CHECKPOINT.md`.
Use milestone issues to track work;
do not mark an entire milestone complete because its preparation or UI is finished.
Existing data and backend upgrades require compatible migrations, explicit validation,
and a recoverable rollback plan. Human visual/quality acceptance remains separate
from automated tests.

## Checks

For documentation-only work, check authority/status consistency, local links, UTF-8
and preservation of historical evidence; do not start services or paid inference.
For later authorized code work, `code/README.md` contains exact local/Bedrock commands. The GitHub workflow
uses a disposable mock stack to run the frontend TypeScript/Vite build, the API
tests, the deterministic graph-fixture check and Playwright. It does not mount AWS
configuration or run the paid live benchmark. Tests must never target the main
database or valuable uploaded documents.

For UI changes, inspect desktop/tablet/mobile behavior, keyboard operation and
source evidence. For knowledge changes, verify citation grounding, scope, tenant
isolation, revisions, deletion/revocation and saved-answer suppression. Preserve
benchmark expectations rather than loosening them to pass a failing implementation.

## Data handling

Commit source, synthetic fixtures and intentional validation records only.
Keep credentials, `.aws`, `.env` secrets, database exports and real user documents
outside Git. Use existing sign-in tooling; never paste tokens into issues, commits
or logs. Reproduce private failures with authorized or synthetic content.

The current runtime is local; the target is production-quality phased delivery.
Creating AWS infrastructure, changing IAM/access, or deploying hosted resources is
outside normal CI and requires its own reviewed scope.
