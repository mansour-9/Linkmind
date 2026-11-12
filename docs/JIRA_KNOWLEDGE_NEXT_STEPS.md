# Jira knowledge and original references — discussion record, 2026-11-12

## Confirmed request

The user confirmed **Jira** as the first external source. They want collected
knowledge to remain available through Graph, Search and Chat, with references to
the original information. They also requested a canvas-only Graph view.
The user intends to share another chat before finalizing the next tasks.

## Current behavior

- Uploaded documents, immutable versions, passages, entities and relationships are
  persisted in the database; the graph is a view of that knowledge.
- Chat, Search and Graph already open authorized stored evidence and original
  uploaded-file downloads. The same source permissions apply across these views.
- Graph URLs retain root, selection and filters. A named saved collection or saved
  canvas layout is not implemented; extra node expansions and dragged positions
  are session state. Saving a view is different from saving the underlying facts.
- A live Jira connector, original Jira links in evidence, and persistent Jira sync
  are **not implemented**. Codex's connected Jira access is not app authentication.

## Proposed follow-up tasks, pending the additional chat

These refine the existing milestone order; they do not mark later milestones
complete or skip document-quality and authorization gates.

1. **M3.2–M3.3: reliable source evidence and cross-source identities.** Keep source
   type, qualified source ID, original URL, source revision/update time, collection
   time and evidence locator together. Continue retaining immutable source excerpts.
   Never merge people or projects solely because their names match.
2. **M4.1: one read-only Jira project.** Use the app's own approved connection and
   map users to verified Jira access. Collect bounded issue data with issue key,
   original issue URL, source timestamps and actual supporting passages. Preserve
   unavailable/denied states. Do not introduce Jira write actions.
3. **M4.1 evidence presentation across Chat, Search, Content and Graph.** A citation
   opens the stored supporting excerpt with its source revision/date and an
   **Open in Jira** action. Opening the current Jira page and viewing the retained
   cited version are distinct actions: later edits must not rewrite old evidence.
   The same evidence model supports uploaded files and future connectors.
4. **M4.2: persistent collection and synchronization.** Save authorized records,
   process revisions idempotently, reconcile deletions and permission changes,
   and show freshness and sync errors. Revoked evidence must stop contributing to
   every dependent answer, result and relationship under the agreed access policy.
5. **Optional saved views/collections.** Name a topic such as “Project Atlas,” save
   its root/filters and optionally selected sources/layout, and reopen it against
   current authorized knowledge. This bookmark must not copy facts or freeze access.
   A historical snapshot/export is a separate feature with explicit revision dates.

## Suggested acceptance example

An authorized user collects an approved Jira issue and uploads a related design
document. Chat, Search and Graph each expose the actual supporting passages and
their source labels. A Jira citation opens its retained excerpt and original issue
URL; a file citation downloads the matching version. Updating the Jira issue makes
its new revision visible without duplicating identities or rewriting the previous
source. Another user without Jira access cannot retrieve its facts or evidence.

No Jira account, credentials, project, live import or sync was configured as part
of the canvas-only UI task. Confirm the exact project/scope and integrate the
additional user chat before starting the connector implementation.
