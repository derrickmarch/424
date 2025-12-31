# Account Verification System

[![Open in Render](https://render.com/images/deploy-to-render-button.svg)](https://dashboard.render.com/)

> Live Demo: https://four24-a0es.onrender.com

Screenshots and API collection are in the `docs/` folder.

An automated voice calling agent that verifies customer accounts with businesses. The system calls companies, provides customer information (name and phone), and checks if accounts exist in their system.

## Features

- **Automated Account Verification**: Call businesses to verify if customer accounts exist
- **AI-Powered Conversations**: Natural language interactions using OpenAI
- **Automatic Looping Calls**: Scheduled batch processing that runs continuously
- **Database-Driven**: Pulls verification requests from database automatically
- **CSV Import/Export**: Bulk data management
- **Retry Logic**: Automatic retry with exponential backoff
- **Real-time Status**: Track verification status and results
- **Compliance**: Recording consent, call logging, blocklist management

## Key Difference from Reservation System

This is a **separate sub-project** focused on account verification rather than reservation management:

| Feature | Account Verifier | Reservation Agent |
|---------|-----------------|-------------------|
| Purpose | Verify account existence | Confirm/modify reservations |
| Information Provided | Name + Phone | Reservation details |
| Primary Question | "Does this account exist?" | "Is reservation confirmed?" |
| Loop Scheduling | ✅ Built-in automatic looping | Manual batch processing |
| Port | 8001 | 8000 |

## Architecture

```
┌────────────────────────────────────────────┐
│         Auto-Scheduler (Loops)             │
│  Runs every N minutes automatically        │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│         Database (Pending Records)          │
│  Pulls N verifications per batch           │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│         Call Orchestrator                   │
│  Processes batch sequentially              │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│         Twilio → AI Agent → Company         │
│  "Do you have account for [NAME]?"         │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│         Results Stored in Database          │
│  verified / not_found / needs_human        │
└────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies
```bash
cd account_verifier
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

**Key Settings:**
```bash
# Twilio & OpenAI credentials (same as reservation system)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
OPENAI_API_KEY=...

# Auto-calling loop settings
ENABLE_AUTO_CALLING=true
CALL_LOOP_INTERVAL_MINUTES=5
BATCH_SIZE_PER_LOOP=10
```

### 3. Initialize Database
```bash
python scripts/init_db.py
python scripts/create_sample_data.py
```

### 4. Run the System
```bash
python main.py
```

Server starts at: **http://localhost:8001** (note: different port from reservation system)

## Auto-Calling Loop

The system automatically processes pending verifications on a schedule:

### How It Works

1. **Scheduler starts** when application launches (if `ENABLE_AUTO_CALLING=true`)
2. **Every N minutes** (configured by `CALL_LOOP_INTERVAL_MINUTES`):
   - Fetches pending verifications from database
   - Processes up to `BATCH_SIZE_PER_LOOP` records
   - Makes calls and stores results
   - Schedules next run
3. **Continues indefinitely** until application stops

### Configuration

```bash
# Enable/disable automatic calling
ENABLE_AUTO_CALLING=true

# How often to run (in minutes)
CALL_LOOP_INTERVAL_MINUTES=5

# How many verifications per batch
BATCH_SIZE_PER_LOOP=10
```

### Manual Control

Even with auto-calling enabled, you can manually trigger batches:

```bash
# Trigger immediate batch (doesn't wait for schedule)
curl -X POST "http://localhost:8001/api/verifications/schedule/trigger"

# Check schedule status
curl "http://localhost:8001/api/verifications/schedule/status"
```

## API Endpoints

### Verification Management
- `POST /api/verifications/` - Create verification request
- `GET /api/verifications/` - List verifications
- `GET /api/verifications/{id}` - Get specific verification
- `GET /api/verifications/stats/summary` - System statistics
- `POST /api/verifications/batch/start` - Manually start batch
- `POST /api/verifications/{id}/retry` - Retry failed verification

### Schedule Control
- `GET /api/verifications/schedule/status` - Check scheduler status
- `POST /api/verifications/schedule/trigger` - Trigger immediate batch

### CSV Operations
- `POST /api/csv/import` - Import verifications from CSV
- `GET /api/csv/export` - Export verifications to CSV
- `GET /api/csv/template` - Download CSV template

### Testing
- `POST /api/twilio/test-call/{id}` - Test without real call

### System
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

## CSV Format

### Import Template

```csv
verification_id,customer_name,customer_phone,company_name,company_phone,customer_email,account_number,verification_instruction,priority
ver_001,John Doe,+12125551234,Electric Company,+18005551234,john@email.com,ACC123,Check if account is active,1
ver_002,Jane Smith,+13105559876,Insurance Co,+18005559876,jane@email.com,POL456,Verify policy status,0
```

**Required columns:**
- `verification_id` - Unique ID
- `customer_name` - Customer's name
- `customer_phone` - Customer's phone (E.164 format)
- `company_name` - Company to call
- `company_phone` - Company's phone (E.164 format)

**Optional columns:**
- `customer_email` - Customer's email
- `customer_address` - Customer's address
- `account_number` - Account number if known
- `verification_instruction` - Special instructions
- `priority` - Priority (higher = processed first)

## Usage Examples

### 1. Add Single Verification
```bash
curl -X POST "http://localhost:8001/api/verifications/" \
  -H "Content-Type: application/json" \
  -d '{
    "verification_id": "ver_001",
    "customer_name": "John Doe",
    "customer_phone": "+12125551234",
    "company_name": "Electric Utility Company",
    "company_phone": "+18005551234",
    "customer_email": "john@email.com",
    "account_number": "ELEC123456",
    "priority": 1
  }'
```

### 2. Import from CSV
```bash
curl -X POST "http://localhost:8001/api/csv/import" \
  -F "file=@verifications.csv"
```

### 3. Check System Status
```bash
curl "http://localhost:8001/api/verifications/stats/summary"
```

### 4. View Schedule Status
```bash
curl "http://localhost:8001/api/verifications/schedule/status"
```

Response:
```json
{
  "is_running": true,
  "last_run_at": "2025-01-29T10:00:00",
  "next_run_at": "2025-01-29T10:05:00",
  "total_processed": 45,
  "total_successful": 38,
  "total_failed": 7
}
```

### 5. Trigger Immediate Batch
```bash
curl -X POST "http://localhost:8001/api/verifications/schedule/trigger"
```

### 6. Test Without Real Call
```bash
curl -X POST "http://localhost:8001/api/twilio/test-call/ver_001"
```

## Verification States

```
PENDING ──────► System will call soon
    │
    ▼
CALLING ──────► Currently on the phone
    │
    ├──► VERIFIED ─────► Account found ✅
    │
    ├──► NOT_FOUND ────► No account ❌
    │
    ├──► NEEDS_HUMAN ──► Manual follow-up needed 👤
    │
    └──► FAILED ───────► Error occurred ⚠️
```

## Call Outcomes

| Outcome | Meaning | Next Action |
|---------|---------|-------------|
| `account_found` | Account exists | None - verified! |
| `account_not_found` | No account in system | Customer needs to create account |
| `needs_verification` | Needs more info | Additional verification required |
| `needs_human` | Complex situation | Manual follow-up |
| `voicemail` | Got voicemail | Will retry automatically |
| `no_answer` | No answer | Will retry automatically |
| `failed` | Technical error | Check logs |

## AI Agent Behavior

### What the Agent Says
```
"Hi! This is an automated assistant calling to verify account information.
We're checking if you have an account on file for [CUSTOMER NAME].
The phone number we have is [PHONE NUMBER].
Can you confirm if this account exists in your system?"
```

### What the Agent Will Do
✅ Provide customer name and phone  
✅ Ask if account exists  
✅ Confirm account status if found  
✅ Note any important details  
✅ Thank the business and end politely  

### What the Agent Won't Do
❌ Provide payment information  
❌ Share sensitive personal data  
❌ Make changes to accounts  
❌ Argue or pressure  

## Configuration Options

### Call Settings
```bash
MAX_CONCURRENT_CALLS=1        # Calls at same time
MAX_RETRY_ATTEMPTS=2          # Retry failed calls
RETRY_BACKOFF_MINUTES=15,120  # Wait 15min, then 2hrs
CALL_TIMEOUT_SECONDS=300      # Max call duration
```

### Loop Settings
```bash
ENABLE_AUTO_CALLING=true           # Enable automatic loop
CALL_LOOP_INTERVAL_MINUTES=5       # Run every 5 minutes
BATCH_SIZE_PER_LOOP=10            # Process 10 per batch
```

### Compliance
```bash
ENABLE_CALL_RECORDING=true         # Record calls
REQUIRE_RECORDING_CONSENT=true     # Ask for consent
ENABLE_TRANSCRIPTION=true          # Store transcripts
```

## Running Alongside Reservation System

Both systems can run simultaneously:

```bash
# Terminal 1: Reservation System
cd callagent2
python main.py        # Runs on port 8000

# Terminal 2: Account Verifier
cd account_verifier
python main.py        # Runs on port 8001
```

They share the same Twilio and OpenAI credentials but use separate databases.

## Monitoring

### View Statistics
```bash
curl "http://localhost:8001/api/verifications/stats/summary"
```

### Check Schedule
```bash
curl "http://localhost:8001/api/verifications/schedule/status"
```

### View Specific Verification
```bash
curl "http://localhost:8001/api/verifications/ver_001"
```

### Export Results
```bash
curl "http://localhost:8001/api/csv/export" -o results.csv
```

## Troubleshooting

### Auto-calling not starting
- Check `ENABLE_AUTO_CALLING=true` in `.env`
- Check logs for scheduler errors
- Verify `/health` shows `"scheduler_running": true`

### No verifications being processed
- Ensure records have `status=pending`
- Check `BATCH_SIZE_PER_LOOP` setting
- Verify enough time passed since last run

### Calls failing
- Same troubleshooting as reservation system
- Check Twilio credentials
- Verify phone number format (E.164)

## Cost Estimates

Similar to reservation system:
- **Per call**: ~$0.13-0.25
- **100 calls/month**: ~$80-130

## Development

### Test Mode
```bash
# Test without real calls
curl -X POST "http://localhost:8001/api/twilio/test-call/ver_001"
```

### Disable Auto-calling
```bash
# In .env
ENABLE_AUTO_CALLING=false
```

Then manually trigger batches when ready.

## Production Deployment

Follow similar steps as reservation system:
1. Use PostgreSQL database
2. Set `APP_ENV=production`
3. Configure HTTPS webhooks
4. Set appropriate loop interval
5. Monitor scheduler status

## Docker Deployment

```bash
# Add to docker-compose.yml
account_verifier:
  build: ./account_verifier
  ports:
    - "8001:8001"
  env_file:
    - ./account_verifier/.env
```

## API Documentation

Full interactive docs available at:
- http://localhost:8001/docs

## Summary

This Account Verification System:
- ✅ Runs independently from reservation system
- ✅ Has built-in automatic looping scheduler
- ✅ Pulls data from database automatically
- ✅ Processes batches on configurable intervals
- ✅ Shares Twilio/OpenAI credentials
- ✅ Uses different port (8001 vs 8000)
- ✅ Focused on account existence verification
- ✅ Can run simultaneously with reservation system

**Start automatically processing verifications with just:**
```bash
python main.py
```

The scheduler handles the rest! 🎉
