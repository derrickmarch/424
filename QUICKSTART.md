# Quick Start - Account Verification System

Get your automatic account verification system running in 5 minutes!

## What This Does

Automatically calls businesses to verify if customer accounts exist. Runs continuously in a loop, processing pending verifications from your database.

## Setup (5 Steps)

### 1. Install
```bash
cd account_verifier
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WEBHOOK_BASE_URL=https://your-domain.com
OPENAI_API_KEY=sk-xxxxx
SECRET_KEY=your-secret-key

# Auto-calling settings
ENABLE_AUTO_CALLING=true
CALL_LOOP_INTERVAL_MINUTES=5
BATCH_SIZE_PER_LOOP=10
```

### 3. Initialize Database
```bash
python scripts/init_db.py
python scripts/create_sample_data.py
```

### 4. Run
```bash
python main.py
```

### 5. Access
- **API Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

## Test It

### Test Without Real Calls
```bash
curl -X POST "http://localhost:8001/api/twilio/test-call/ver_001"
```

### Check Schedule Status
```bash
curl "http://localhost:8001/api/verifications/schedule/status"
```

### View Statistics
```bash
curl "http://localhost:8001/api/verifications/stats/summary"
```

## How Auto-Calling Works

Once started, the system:
1. ✅ Automatically checks database every 5 minutes (configurable)
2. ✅ Finds pending verifications
3. ✅ Calls businesses to verify accounts
4. ✅ Stores results back to database
5. ✅ Repeats forever until stopped

**No manual intervention needed!** Just keep adding records to the database.

## Add Your Data

### Option A: CSV Import
```bash
# Download template
curl "http://localhost:8001/api/csv/template" -o template.csv

# Edit template.csv with your data

# Import
curl -X POST "http://localhost:8001/api/csv/import" -F "file=@template.csv"
```

### Option B: API
```bash
curl -X POST "http://localhost:8001/api/verifications/" \
  -H "Content-Type: application/json" \
  -d '{
    "verification_id": "ver_001",
    "customer_name": "John Doe",
    "customer_phone": "+12125551234",
    "company_name": "Electric Company",
    "company_phone": "+18005551234",
    "customer_email": "john@email.com"
  }'
```

## Manual Controls

Even with auto-calling enabled:

### Trigger Batch Immediately
```bash
curl -X POST "http://localhost:8001/api/verifications/schedule/trigger"
```

### Check What's Running
```bash
curl "http://localhost:8001/api/verifications/schedule/status"
```

### View All Verifications
```bash
curl "http://localhost:8001/api/verifications/"
```

## Key Differences from Reservation System

| Feature | Account Verifier | Reservation System |
|---------|-----------------|-------------------|
| Port | **8001** | 8000 |
| Auto Loop | **✅ Built-in** | Manual batch only |
| Purpose | Verify accounts exist | Confirm reservations |
| Question Asked | "Do you have account for X?" | "Is reservation confirmed?" |

## Configuration

### Adjust Loop Frequency
```bash
# In .env
CALL_LOOP_INTERVAL_MINUTES=10  # Every 10 minutes
BATCH_SIZE_PER_LOOP=20         # Process 20 per batch
```

### Disable Auto-Calling
```bash
# In .env
ENABLE_AUTO_CALLING=false
```

Then manually trigger when ready:
```bash
curl -X POST "http://localhost:8001/api/verifications/batch/start"
```

## Monitoring

### Check Health
```bash
curl "http://localhost:8001/health"
```

Response shows if scheduler is running:
```json
{
  "status": "healthy",
  "scheduler_running": true,
  "auto_calling_enabled": true
}
```

### View Results
```bash
# Export to CSV
curl "http://localhost:8001/api/csv/export" -o results.csv

# Or view specific verification
curl "http://localhost:8001/api/verifications/ver_001"
```

## Running with Reservation System

Both can run together:

```bash
# Terminal 1
cd callagent2
python main.py          # Port 8000

# Terminal 2
cd account_verifier
python main.py          # Port 8001
```

## Next Steps

1. ✅ System is running and auto-calling is enabled
2. ✅ Add your verification requests (CSV or API)
3. ✅ Let it run - it processes automatically
4. ✅ Monitor results via API or CSV export
5. ✅ Handle any "needs_human" cases manually

## Common Issues

### Scheduler not starting
- Check `ENABLE_AUTO_CALLING=true` in `.env`
- Restart application
- Check logs for errors

### No calls being made
- Ensure records have `status: pending`
- Wait for next scheduled run
- Or trigger manually

### Webhook errors
- Use ngrok for local testing: `ngrok http 8001`
- Update `TWILIO_WEBHOOK_BASE_URL` in `.env`

## Summary

**That's it!** Your account verification system is now:
- ✅ Running on http://localhost:8001
- ✅ Automatically processing verifications every 5 minutes
- ✅ Pulling data from the database
- ✅ Storing results automatically

Just add records and let it work! 🚀
