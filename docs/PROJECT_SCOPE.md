# Company Brain — Current Scope and Decisions

M2/M3 core workflows are implemented locally, including Bedrock processing,
Processing, Search, Wiki, Graph, Chat, conflict/identity review and Usage. See
[M2/M3 validation](M2_M3_VALIDATION.md) for verified checks and limits, and the
[frontend rules](FRONTEND_RULES.md) for shared UI guidance.

## UI direction approved 2026-11-11

- Product identity: Linkmind. Complete Glean-inspired frontend redesign using the supplied references.
- English first; working features only in navigation. Preserve the backend and API contracts.
- See [UI redesign](M3_1_UI_REDESIGN.md) for implementation and validation evidence.

## Confirmed direction
- Build a substantial, usable MVP, eventually hosted on AWS.
- Use this project to organize the knowledge and instructions needed for the build.
- Make direct file uploads a core input path alongside service connectors.
- Use Python with FastAPI for the API and Python for the ingestion worker.
- Use boto3 for application calls to AWS services and AWS CDK v2 in Python for
  infrastructure. This supersedes the Terraform choice in the original specification.
- Preserve the original priorities: premium UI, real React Flow graph, working
  extraction and conflict detection, source-backed wiki, Bedrock answers, secure
  permissions, database persistence, local development, and tests.
- Prepare infrastructure and deployment documentation before requesting permission
  to provision billable AWS resources.

## Confirmed upgrade order — 2026-11-11

- The current UI does not meet the user's expectations. M3.1 starts with a full
  UI discussion, then agreed fixes and a user acceptance walkthrough. Backend
  upgrades follow this milestone; existing visual references are not final acceptance.
- The next release is for local testing and prioritizes knowledge quality.
- M3.2 establishes the baseline, fixes PDF/evidence-processing reliability and
  introduces safe versioned chunk/index improvements. M3.3 improves retrieval and
  identity resolution; M3.4 adds verified graph paths with three hops by default.
- Jira is the first external source. M4.1 establishes a read-only authorized
  integration; M4.2 adds persistent sync, freshness, deletion and revocation handling.
- M4.3 evaluates bounded orchestration after retrieval quality is demonstrated.
  Keep deterministic tools as the baseline; extra agents/frameworks require a
  measured benefit. Keep organizational facts separate from conversational memory.
- Retain FastAPI/PostgreSQL/pgvector and evolve compatible APIs. Use migrations
  and parallel index generations to preserve document versions, data and citations.
- MCP is a supported live-tool transport, not a requirement for every internal
  tool or bulk sync. Native source APIs/webhooks may be needed for reliable sync.
- Preserve source ACLs and qualified IDs; never share a sync account's privileged
  results with an organization by default. Keep uncertain inferred links separate
  from explicit facts and verified conclusions.
- Compare custom retrieval with current managed alternatives before major new
  orchestration work. Gateway, Identity, Memory, dedicated graph databases and
  managed KB adoption remain decisions to evaluate, not deployed dependencies.
- Slack remains in the later hosted-pilot scope. Confluence and GitLab are later
  candidates; they do not expand the next local release automatically.
- English remains the current release language. Hosted readiness, approved AWS
  deployment and M7 Arabic/bilingual validation remain later milestones.

The detailed checklist and acceptance gates are in [the implementation plan](IMPLEMENTATION_PLAN.md).

## Confirmed pilot scope
- One invite-only internal team. Design and test tenant isolation from the beginning.
- Direct uploads, one approved Jira Cloud project, and selected public Slack channels.
  Ingest readable thread replies and restrict Slack access to verified channel members.
- English UI, documentation, and validated document intelligence through the hosted
  pilot. M7 adds Arabic UI and right-to-left layouts and validates Arabic and
  mixed-language processing, search, answers, and citations.
- Upload formats are selectable-text PDF, DOCX, TXT, and Markdown.
- Review the AWS region and data-location policy before deployment.

## Pilot assumptions and later releases
- Size for up to 20 invited users and 50–200 representative documents.
- Use employee, reviewer, and administrator roles together with explicit source and
  document permissions.
- Schedule SharePoint/OneDrive, spreadsheets, OCR, private Slack channels, DMs, and
  self-service customer onboarding for later releases.

## Shared ingestion behavior
Uploads and connectors create immutable source versions with metadata and access
rules. Processing normalizes content, creates addressable evidence, extracts claims
and entities, resolves identities conservatively, builds relationships, and flags
potential contradictions. Graph, wiki, search, and answers read this persisted layer.

Uploads need format and size validation, safe filenames/storage keys, bounded parser
execution, progress/errors/retries, owner/readers, original-file access, replacement,
and deletion. A hosted pilot needs quarantine/scanning appropriate to its upload
threat model. Downloads and evidence access require authorization.

Changes in content, access, or deletion invalidate dependent views and retrieval.
Records retained for audit must not remain visible to users who lost access. Exact
retention, purge timing, and backup deletion policy remain open decisions.

## AI behavior
- No AWS credentials are required for the local fixture demonstration.
- The deterministic mock supports recognized fixtures only. Other uploads may be
  stored and text-indexed as permitted, but must show AI extraction unavailable.
- Bedrock enables general-document extraction, embeddings, and grounded
  answers when configured. PostgreSQL combines exact ID and keyword matching with
  pgvector search. The approved M2/M3 implementation uses reciprocal-rank fusion.
  A reranker is not currently enabled. M3.3 compares reranking against the
  baseline and adopts it only when measured quality and latency/cost justify it.
- Structured output validation is separate from evidence/semantic validation.
- Do not infer that contradictory statements can always be reconciled automatically.
- Preserve uncertain matches and conflict candidates for human review.

## Proposed AWS target
Retain the original specification's target, subject to regional availability,
budget, and implementation review:

| Component | Proposed service |
| --- | --- |
| API and processing worker | ECS Fargate; container images in ECR |
| Knowledge database | RDS PostgreSQL with pgvector |
| Uploaded artifacts and source versions | Private S3 storage |
| Processing queue and failed jobs | SQS and a dead-letter queue |
| Scheduled connector synchronization | EventBridge Scheduler |
| AI extraction and answering | Amazon Bedrock |
| Hosted sign-in | Cognito; application still enforces org/item authorization |
| Source credentials | Secrets Manager |
| Operational logs and metrics | CloudWatch |
| Reproducible infrastructure | AWS CDK v2 in Python, deployed through CloudFormation |

The API and worker use boto3 for Bedrock, S3, SQS, and Secrets Manager as needed.
Hosted services use their ECS task roles for AWS credentials. Docker Compose and
fixture processing remain usable without AWS credentials. CDK deployment code
and dependencies are separate from the API and worker runtime.

Frontend delivery, HTTPS ingress, networking/egress, database sizing, backup policy,
and availability level will be selected in the deployment design. Do not present
this service list as a complete deployment or a verified lowest-cost architecture.

AWS Fargate supports running ECS containers without managing EC2 servers:
[AWS documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html).
Bedrock structured-output support must be checked for the selected model and API:
[AWS documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html).
References checked 2026-11-10; revalidate before implementation/deployment.

## MCP and connector boundaries
MCP integrations can help investigate source systems and support development.
Connections in the Codex chat do not automatically authorize the hosted application.
The application's connectors need their own authentication, permission mapping,
incremental synchronization, retry behavior, and deletion handling.
No additional MCP connection is required to begin local implementation with fixtures.

## Decisions to collect
| Decision | Why it matters | Required before |
| --- | --- | --- |
| Which representative documents and Jira project/application connection can we use? | Next local quality evaluation and live Jira authorization | M3.2 / M4.1 validation |
| Which approved Slack channels can we use later? | Verified membership and hosted-pilot scope | M4.4 live validation |
| UI visual walkthrough | Linkmind/Glean direction approved; verify final visual preferences | M3.1 acceptance |
| What quality, latency, cost and freshness targets apply? | Evaluate gains and set enforceable budgets/policies | M3.2 baseline / M4.2 sync |
| Actual pilot users, document volume, file sizes, and sync frequency? | Limits, performance testing, cost assumptions | Capacity and deployment sizing |
| AWS monthly budget, region, and data-location restrictions? | Deployment options and model availability | AWS design approval |
| Who reviews conflicts and which sources have authority? | Review permissions and predicate-specific policies | Conflict workflow acceptance |
| Data retention and deletion expectations? | Storage lifecycle, audit, backups | Hosted pilot |

Unknown answers should be recorded honestly, not converted into approved requirements.
