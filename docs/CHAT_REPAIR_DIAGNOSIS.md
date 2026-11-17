# Chat repair: inspected baseline, November 17, 2026

Historical baseline diagnosis. The user's later demo-priority instruction superseded
the verification-preservation recommendations below for ordinary automatic chat.
The delivered simple pipeline, measured quality and important limits are recorded in
[demo readiness results](DEMO_READINESS_RESULTS.md).

The installed 5197 runtime uses Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6`,
us-east-1), Converse structured JSON output, and application-controlled read-only
MCP adapters. Bedrock receives logical documents/search/read/projects actions,
not arbitrary provider tools. Provider allowlists and source scope validation
remain server-enforced. The baseline automatic route permits three planner calls,
one synthesis and one independent statement audit.

## Confirmed failures before retrieval changes

Read-only inspection of saved runtime traces found these cases:

| Question | Server duration | Evidence/failure |
| --- | ---: | --- |
| ATLAS purpose, features, customer | 62.793 s | Engineering/Security pages and ATLAS-5; no project scope page |
| Eight departments | 42.513 s | Department pages plus company page; incomplete selection |
| ATLAS-4 status/owner/criteria | 30.993 s | Repeated `undiscovered_resource`; ATLAS-16 substituted |
| Approved raw analytics retention | 38.066 s | 29.139 s of source calls, 8.664 s model inference |
| ATLAS overview, repeated | 35.467–42.839 s | 27 source calls, five model calls, partial answers |

The exact-read adapter already exposes getJiraIssue; the automatic route's
discovery requirement rejects explicit user keys. Jira search tokenizes keys into
prose terms. Confluence title search only falls back to body search when empty,
and automatic chat reads the first two hits without relevance ranking. Four
originals can be exhausted before a targeted recovery. Live rendering selects
only the first 24 passages/12,000 characters. Direct reads substitute connection
names for native titles. The UI already deduplicates citations per statement;
resource/revision identity needs to remain explicit.

Source authorization rereads originals before each model exposure and delivery.
These checks must remain. Independent operations can run concurrently; metadata
discovery is already cached and cannot explain all repeated resource reads.

Configured pacing is nine model requests/minute (6.667 s between starts). Pacing
waits occur outside recorded model spans. The first-output counter incorrectly
adds request-relative timestamps for every model operation, exceeding total time.
Some model statements are rejected by semantic verification; improving retrieval
does not justify relaxing that check. Root causes of individual rejected policy
or coverage claims require original-source review in connected acceptance.

Baseline source archive, content database dump and private runtime artifacts are
kept under ignored `.local/chat-fix-2026-11-17`; do not commit source bodies or
credentials. No paid calls were used to establish the findings above.
