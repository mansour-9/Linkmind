# AWS session and model recovery — November 17, 2026

The user reported that AWS login had expired and the model could not answer. Local AWS CLI 2.38.5 and a network-authorized STS check confirmed expiry. The app's most recent failed operation was query_understanding at 04:51:36 UTC, error LoginRefreshRequired. Its unknown reservation paused the original shared spend guard.

The user explicitly approved aws login --profile default, resuming the original USD 10 guard without clearing/resetting reservations, and one new answer test with max 3 operations/USD 0.50 conservative reservations. AWS login completed and STS verified the default-profile identity. Only the API was recreated to read the refreshed credentials; model configuration, source permissions and content were unchanged.

The guard was unpaused with exact baseline checks. Existing 4 unknown calls/USD 0.1190066200 remain unchanged. No budget clone, cap increase, reservation release or AWS infrastructure/IAM change occurred.

One new main-chat Live Only question was tested: «ما الشروط المطلوبة في ATLAS-16 قبل إطلاق النسخة التجريبية؟».

Results:

- The Bedrock answer operation succeeded: 5,703 input tokens, 546 output tokens, end_turn, USD 0.0278289000.
- The independent answer_verification operation returned content_filtered/content_blocked: 3,373 input tokens, zero output tokens, USD 0.0111309000.
- The installed handler returned ModelResponseError and did not save or display an unverified answer. No paid retry was made. This proves restored AWS authentication and successful answer-model invocation, but does not establish a successful end-to-end verified answer for this case. The provider did not supply a more specific filtering reason in the recorded response.

Total: 2 settled operations, USD 0.0389598000 actual, USD 0.2179584 conservative reservations, 11.87 seconds. Original cumulative guard: USD 5.6806804600 spent, USD 0.1190066200 still held, USD 10 limit, paused=false. No new unknown usage arose.

Remaining limitation: the one authorized model test was stopped by provider filtering during verification. Keep the exact-citation, semantic verification and source-policy safeguards enabled. Any additional agent-run paid diagnostic requires a new bounded authorization; do not automatically repeat this paid case. Interactive user testing remains governed by the same original budget.
