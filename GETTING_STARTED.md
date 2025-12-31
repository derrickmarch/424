# Getting Started

A quick guide to run, test, and use the Account Verification system.

## 1) Requirements
- Python 3.11+ (locally) or Render.com
- Twilio account (trial or paid)
- OpenAI key (optional)

## 2) Environment Variables
Create a `.env` in the project root (local) or set these in Render Environment:

```
# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
TWILIO_WEBHOOK_BASE_URL=https://your-app.onrender.com

# App
APP_ENV=production
RENDER=true
TEST_MODE=true
TEST_PHONE_NUMBER=+19092028031

# Optional
OPENAI_API_KEY=sk-...
```

## 3) Run Locally
```
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```
Open http://localhost:8001

## 4) One-Account Real Call Test (Standalone)
Use the single-file tester to place a real call to your verified number (trial-safe):

```
pip install twilio
python simple_test.py
```
Choose option 2 and type YES to confirm. You’ll see live status updates.

## 5) Real-Time Monitoring (During Calls)
- REST: `GET /api/call-monitor/active-calls`
- REST: `GET /api/call-monitor/call/{call_sid}`
- WS:   `ws://.../api/call-monitor/ws/call/{call_sid}` (live updates)

## 6) Auto-Queue (Instant Hangup + Next)
Start automatic processing of pending verifications:
```
curl -X POST "https://your-app/api/auto-queue/start"
```
Stop:
```
curl -X POST "https://your-app/api/auto-queue/stop"
```
Status:
```
curl "https://your-app/api/auto-queue/status"
```

## 7) Bulk Operations
- POST `/api/bulk/delete`   → delete multiple verifications
- POST `/api/bulk/retry`    → reset multiple to pending
- POST `/api/bulk/priority` → set priority in batch
- POST `/api/bulk/export`   → download CSV

## 8) Advanced Search
- GET `/api/search/verifications?q=John&status=pending&sort_by=created_at&sort_order=desc`
- GET `/api/search/suggest?query=jo`
- GET `/api/search/filters/options`

## 9) Analytics
- GET `/api/analytics/dashboard-stats`
- GET `/api/analytics/trends?days=30`
- GET `/api/analytics/performance`
- GET `/api/analytics/company-stats`

## 10) Audit Logs
- GET `/api/audit/logs`
- GET `/api/audit/activity/{user_id}`

## 11) Deployment (Render)
- Push to GitHub → Render auto-deploys
- Ensure env vars are set (see section 2)
- Health: `GET /health`

## 12) Admin Login (Default)
- Username: `admin`
- Password: `admin123`
(Change it in Settings after first login.)

---
Questions or issues? See RENDER_QUICKSTART.md and TEST_MODE_GUIDE.md.
