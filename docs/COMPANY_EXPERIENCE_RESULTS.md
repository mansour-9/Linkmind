# Company experience — November 17, 2026

The latest user scope creates a realistic AsterBridge company demonstration, expands Confluence content, removes in-world testing disclaimers, and moves all file uploads from Chat to Documents. New uploads default to organization visibility. Existing private documents and backend attachment contracts are preserved. The current prototype's organization boundary remains in force; production department grants and employee-managed connections remain deferred.

## Application changes

- Chat has no attachment button, file input or file-drop uploader.
- Documents has one Add document button, opening a centered accessible upload dialog (bottom sheet on mobile) with file selection, drag/drop and progress. Uploads use organization visibility without a selector. The upload API now also defaults to team visibility; explicit private requests retain their meaning.
- Project enumeration provides evidence to the investigation instead of terminating compound count-and-owner questions. The planner continues looking for product, technical and delivery ownership.
- The answer language follows the original user question, independent of the rewritten search query. Prompts handle dialect, spelling variation, complete questions and distinguish missing search evidence from absent policy.
- Pure identity and social messages receive helpful local replies. Upload guidance describes Documents > Add document.
- Duplicate connector warnings are collapsed and resource limits are distinguished from read failures. Enumeration shares the request's connector limits.
- Grounding policy v14; database schema remains 0020. No content reset, graph enrichment, embeddings or synchronization jobs.

## Company corpus

30 new Confluence pages expand the existing 40 into a 70-page company hub. The content covers 42 employees, eight departments plus the Executive Office, project ownership, company strategy, annual and sick leave, working hours, remote work, expenses, equipment, onboarding, learning, three customer accounts, roadmap, six meeting notes, support guides and a weekly update. Existing project gates and dated role handovers remain consistent. Native account identities are not invented. Offline provenance identifies this as an authored demonstration company; it is excluded from the in-world narrative.

108 existing Jira descriptions and their 108 comments were normalized into company delivery records, retaining scope, owners, dates and acceptance requirements. Full native readback matched all intended bodies and comment IDs, with no remaining fictional/test-organization/dataset narrative. The 70 Confluence bodies also matched intended content after normalizing Markdown formatting and generated email links. Six company Markdown documents were uploaded through the installed API with visibility omitted, verifying its organization default; all six became search ready and readable by a colleague in the same organization.

## Verification and limits

Isolated API: 424 passed, 2 skipped. Browser acceptance passed for chat control removal, modal upload, multiple file selection, drag/drop, unsupported format, Escape/focus return, desktop/mobile layout, organization sharing and isolation. Frontend and backend images build. No new paid-model evaluation was run: the original trial has ended and its budget/unknown reservations must remain unchanged. Mock tests establish behavior, not a guarantee of real-model answer quality.

Confluence space display-name rename is blocked: Computer Use stopped because it could not reliably determine the Windows browser URL. The homepage title is AsterBridge Labs; the space settings name may still contain Test Organization. Do not claim that the settings rename succeeded.

Installed at http://127.0.0.1:5197 with final desktop/mobile smoke checks passing. Installed backend hashes match the reviewed source. The existing document and active chat were preserved; the six new organization documents bring the active document count to seven. Connector settings fingerprint, schema and inference usage fingerprint matched before/after installation. No model call was made by this delivery. Budget at the measured checkpoint: USD 6.3841810600 spent, USD 0.1836305200 held, USD 10 cap, paused=false. No unknown reservation was changed.

Evidence is in the chat workspace output/company-demo-2026-11-17, including source backups, consistent PostgreSQL dump, artifact archive, publication manifest, full corpus readback, test logs, screenshots, runtime checks and source-only authentication checks. An expired application Atlassian MCP credential was detected, then renewed after explicit user approval; installed reads passed for ATLAS-16, BEACON-26, HARBOR-30 and the new annual-leave page 753718. The new session expires 2026-11-18 01:54 Asia/Riyadh. AWS STS succeeded. Refresh tokens are not retained by the existing bounded login flow. The current expiring credential architecture is unchanged; durable organization service authentication remains deferred.
