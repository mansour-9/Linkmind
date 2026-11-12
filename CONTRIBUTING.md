# Contributing to Linkmind

## Working sequence

1. Read `AGENTS.md`, the active milestone, and relevant architecture/frontend guidance.
2. Branch from `main`, for example `m3.2/processing-baseline` or `fix/quote-locator`.
3. Keep a change focused and preserve existing document/evidence API contracts.
4. Validate in a disposable mock Compose project and record what actually passed.
5. Open a pull request with the problem, resulting behavior, validation and limitations.

`main` holds the current validated checkpoint. Use milestone issues to track work;
do not mark an entire milestone complete because its preparation or UI is finished.
Existing data and backend upgrades require compatible migrations, explicit validation,
and a recoverable rollback plan. Human visual/quality acceptance remains separate
from automated tests.

## Checks

`code/README.md` contains the exact local and Bedrock commands. The GitHub workflow
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

This is a local MVP. Creating AWS infrastructure, changing IAM/access, or deploying
hosted resources is outside normal CI and requires its own reviewed scope.
