# Company Brain knowledge layer

## Processing and publication

Original bytes are stored by organization and SHA-256 checksum. Every document revision has an immutable version ID and filename.
The database queue leases one job at a time with SKIP LOCKED. Attempts, stages, errors and abandoned leases are persisted.
Parsing creates stable passage IDs using the version ID and passage position. Locators retain source pages, lines, paragraphs or table rows.

The configured Bedrock provider requests JSON-schema output using boto3 Converse. Extraction is not a regex pipeline.
Pydantic validates the schema and references. Every quoted span must occur verbatim in the referenced original passage.
A separate model check evaluates entities, identifiers, claims, relationships and effective periods.
One bounded correction is allowed; a second failure prevents publication.
The deterministic provider only recognizes exact checked-in fixture bytes.

Strong identifiers resolve entity identities under an organization advisory lock. Same-name matches become review candidates.
Human merges require a reviewer role, access to all affected sources, a rationale and audit history. Redirects preserve old canonical links.
Claims retain attribution, typed JSON values, effective periods and multiple evidence spans. Relationships retain multiple spans and effective dates.
Entity evidence is also retained.

Single-valued attribute conflicts compare the same canonical entity and attribute across overlapping effective periods.
Bedrock assesses source-backed candidate pairs before publication, distinguishing incompatible statements from equivalent/complementary/historical statements.
Publication rechecks the job lease, document deletion and latest revision. A concurrent new claim that was absent from semantic assessment remains a review candidate.
The current-version pointer and all derived records publish in one transaction.
A failed revision leaves the previous current projection intact.

## Retrieval and derived views

Graph, Wiki, Search and Chat use the same current records.
Permissions require matching organization and either source ownership or organization visibility; deletion always removes derived access.
Entity labels are selected only from authorized occurrences. Relationships require their own source access.
A conflict is visible only when both underlying claims remain authorized and current.
Original evidence/history can be opened by authorized viewers even when a version is historical.

Hybrid retrieval ranks bounded candidate lists from exact identifiers/entities, PostgreSQL full text, matching pgvector embeddings and related graph claims.
Permissions and source/type/date filters are applied inside each candidate query before ranking.
Reciprocal-rank fusion combines channels. Leading semantic evidence is retained so rare entity qualifiers are not buried by broad identifier matches. Current-version, embedding model and dimension checks exclude incompatible or outdated vectors.
Graph neighborhoods are bounded and server-backed. The focused /graph explorer
adds permission-filtered entity/identifier search, stable immediate-neighbor pages,
one-to-three-hop traversal, type/predicate filters, and 80-node/120-edge budgets.
React Flow preserves existing node positions during exploration. Truncation and
loaded connection counts are explicit; it never claims to show the complete workspace.
Workspace Search adds an optional connected-entity overview only for a relevant
exact/near name or identifier match, while retaining ordinary document results.

Wiki pages are generated structured views with attributed claims, conflicts, uncertain matches, source citations and version history.
They do not add unchecked factual prose.

## Grounded conversations

Conversations belong to one user and organization, with workspace or selected-file scope.
Only current authorized passages are sent for answering. Follow-ups can reuse permission-checked prior evidence and context.
Source entity metadata preserves canonical distinctions internally. Answers must not assume same-name entities match, expose internal IDs, or cite internal metadata as original source facts.
Each factual statement must carry exact evidence quotes and passage IDs. A separate semantic check must approve every statement using the corresponding full source passages to resolve references. One bounded correction is permitted and must pass the same validation.
Missing evidence produces an explicit response. Conflicting evidence must retain both source positions.
No failed or unverified answer is saved.

Stored turns record every supplied evidence dependency, not merely the displayed citations.
History rechecks all dependencies and the answer-validation policy version. Any revoked, deleted or superseded evidence, or a superseded grounding policy, suppresses the answer while preserving the original record.
Identity changes replace the entire frontend query client; deep links and original downloads reauthorize on the server.

## Operations

Model usage is committed independently of knowledge publication and includes failed calls.
Records retain provider, model, region, operation, processing attempt, token usage, latency, retries and configured cost information.
Unknown token counts and unavailable cost estimates remain null.
Pricing is explicitly supplied per exact model and region with currency and effective date.

PostgreSQL coordinates model request pacing across API and worker processes. SDK adaptive retries remain bounded.
The verified local account quota is ten Sonnet requests per minute; the default scheduler uses nine.
No AWS resource, IAM policy, infrastructure stack or service quota is created or changed.

## Release boundary

The current runtime is a local MVP with deliberately enabled demo identities, local artifact volumes and a database-backed queue.
M4 adds live connectors. M5 adds Cognito, production hardening and reviewed Python CDK infrastructure. M6 requires explicit deployment approval.
English first; Arabic is M7. OCR/images and Excel are later releases.
