# Loom Video Walkthrough Script

## Title
Account Verifier – From Zero to Verified in Minutes (Live Demo)

## Outline (5–7 minutes)

1) Intro (15s)
- Hi, this is a quick tour of the Account Verifier web app.
- I’ll show you how to upload records, auto-call companies, and see results live.

2) Login & Dashboard (45s)
- Go to https://four24-a0es.onrender.com
- Log in as admin (mention changing password in Settings).
- Show dashboard stats: total verifications, success rate, calls today.

3) Add/Import Records (60s)
- Show Add Verification page to add a single record.
- Show CSV Import: upload a small CSV and confirm it appears under Verifications.

4) Real-Time Call Monitoring (60s)
- Start Auto-Queue: trigger /api/auto-queue/start via the UI or Postman.
- Open the Monitoring panel (or call monitor API) to see active calls.
- Explain instant hangup on verified → moves to next call automatically.

5) Live Demo of a Test Call (60–90s)
- Run simple_test.py locally, choose option 2 to place a real call to verified number.
- Show live status updates and final call details.
- Mention Twilio trial restriction (verified numbers only).

6) Search, Bulk Ops, and Analytics (60–90s)
- Use Advanced Search to filter by company/status.
- Run Bulk Retry/Delete to manage multiple records.
- Show Analytics: dashboard stats, trends, and company breakdown.

7) Audit Trail & Settings (30s)
- Show audit logs for recent actions.
- Mention test/live mode toggle and environment configs.

8) Wrap-up (15s)
- App is live on Render, supports real-time monitoring and auto-queue.
- Repo contains GETTING_STARTED.md and a Postman collection.
- Thanks for watching – contact me for help or onboarding!
