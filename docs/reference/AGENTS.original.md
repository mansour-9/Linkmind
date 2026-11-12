# Company Brain — Codex Agent Operating Instructions

Read `COMPANY_BRAIN_CODEX_MASTER_SPEC.md` in full. It defines the product, features, data model, security rules, graph UX, AWS target, acceptance tests, and implementation order.

## Mission
Implement a working, secure, polished, local-first MVP of Company Brain. Do not only write a plan or produce visual mockups. Build the end-to-end flow: ingest → normalize → extract → resolve entities → detect conflicts → persist → graph/wiki/search/AI.

## Required behaviors
- Inspect the repository and preserve useful existing code.
- Write an implementation checklist to `docs/IMPLEMENTATION_PLAN.md`; execute it in increments and update progress.
- Make real backend routes, migrations, fixtures, tests, and connected frontend features.
- Keep local mock mode deterministic and honestly labeled. Use real Bedrock only when configured.
- Enforce org/record ACLs server-side before revealing any graph, wiki, search, citations, or AI context.
- Preserve source evidence; never invent facts or silently resolve conflicts.
- Make React Flow Knowledge Graph exceptional, navigable, and connected to persisted entities.
- Provide Docker Compose startup commands and seed script.
- Do not use or commit credentials. Do not provision AWS resources without explicit approval.
- Run tests, fix failures, and document limitations after each major phase.
- Work autonomously on agreed requirements. Ask only when a missing detail truly blocks safe execution.

## Preferred technology
React/TypeScript/Vite, Tailwind/shadcn, `@xyflow/react`, FastAPI/Pydantic, SQLAlchemy/Alembic, PostgreSQL/pgvector, Docker Compose, Bedrock provider adapter, ECS/RDS/S3/SQS/Terraform later.

## Definition of done
The system runs locally, displays genuine seeded content, provides working graph exploration, generated wiki, source-backed conflict review, authorized search/AI, and passes core security and data-integrity tests. Clearly distinguish completed functionality from planned AWS integrations.
