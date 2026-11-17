# Automatic chat rollout and restore

The application checkout is `C:/Users/manso/OneDrive/سطح المكتب/AWS ABA/ABA Project`.
The authorized preview is Compose project `linkmind-asterbridge-live`, port 5197, schema `0020_auto_chat`, policy `grounded-v13-automatic-source-investigation`.
Use the existing compose.yaml + chat-workspace tmp/linkmind-real-trial/compose.clean.yaml + tmp/chat-polish/compose.polish.yaml + tmp/source-boundary-fix/compose.live.yaml + tmp/auto-chat-2026-11-17/compose.auto-live.yaml. The last override enables LINKMIND_AUTO_CHAT=1 and selects linkmind-auto-chat-backend:local / linkmind-auto-chat-web:local. Keep the existing environment file, native connection IDs, artifact volume and original shared budget network; never print the resolved credential-bearing Compose configuration.

The dedicated isolated mock project is linkmind-auto-chat-tests at 5202. It has independent database/originals and no source networking, AWS configuration or shared budget. Its default legacy feature flags are off for compatibility regressions; the new UI explicitly creates auto conversations. Full API checks: `docker exec linkmind-auto-chat-tests-api-1 python -m pytest -q --tb=short apps/api/tests`.

Chat-workspace output/auto-chat-2026-11-17/backup-verification.json contains verified DB/original archive hashes, original image IDs and restored row-count/fingerprint checks. before-auto-chat.dump and before-auto-chat-artifacts.tar.gz are the matching restore pair. They contain private previous workspace content and are never indexed or committed.

To restore the pre-reset state, stop only this preview's API and worker, retain a separate snapshot of new content, restore the complete original DB dump into this preview's content database, restore the paired originals archive into its artifact volume, then start the exact original image IDs recorded in the manifest and original Compose configuration. A full restore is necessary; do not down-migrate destructively or merge old content into the fresh index. Keep the independently shared inference ledger untouched. Restoring application data never authorizes rewinding spend, clearing reservations or resuming a paused guard.
