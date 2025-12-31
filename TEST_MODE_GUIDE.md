# Test Mode Guide

## Overview

The Account Verifier system supports **TEST MODE** and **LIVE MODE** to help you safely develop and test without making real calls to unverified numbers.

## Why Test Mode?

Twilio **trial/test accounts** have restrictions:
- ✅ Can only call **verified phone numbers**
- ❌ Cannot call arbitrary phone numbers
- 💰 Limited trial credit

**Test Mode** solves this by:
1. Always calling your verified test number (configured in `.env`)
2. Simulating call completion and conversation
3. Fetching real Twilio account balance (when available)
4. Preventing accidental charges for unverified numbers

## Configuration

### 1. Environment Variables

Add to your `.env` file:

```env
# Testing Mode (true = mock calls, false = real calls)
TEST_MODE=true

# Test Mode Configuration
# When TEST_MODE=true, all calls will be made to this verified test number
TEST_PHONE_NUMBER=+19092028031
```

### 2. Twilio Account Setup

For trial accounts:
1. Log into [Twilio Console](https://console.twilio.com)
2. Go to **Phone Numbers** → **Verified Caller IDs**
3. Add your test phone number (e.g., `+19092028031`)
4. Verify the number via SMS/call
5. Add the verified number to `TEST_PHONE_NUMBER` in `.env`

## Test Mode vs Live Mode

| Feature | Test Mode 🧪 | Live Mode 📞 |
|---------|-------------|-------------|
| **Calls Made To** | Always test number (configured) | Actual target numbers |
| **Twilio API** | Real API for balance only | Real API for all operations |
| **Call Simulation** | Yes (mock conversations) | No (real calls) |
| **Account Balance** | Fetches real balance | Fetches real balance |
| **Safe for Trial Accounts** | ✅ Yes | ❌ No (will fail) |
| **Cost** | Free (no real calls) | Charges apply |

## How It Works

### Test Mode (TEST_MODE=true)

When you initiate a call in test mode:

1. **Number Override**: Target number is replaced with `TEST_PHONE_NUMBER`
   ```
   Original Target: +15551234567 (Company)
   Actual Call To:  +19092028031 (Your verified test number)
   ```

2. **Mock Call Simulation**:
   - Generates a mock Call SID
   - Simulates call completion after 3-8 seconds
   - Generates random conversation transcript
   - Updates verification status automatically

3. **Real Account Info**:
   - Fetches actual Twilio balance (when API allows)
   - Shows account status and type
   - Displays usage statistics (when available)

### Live Mode (TEST_MODE=false)

⚠️ **Only use with upgraded Twilio accounts**

- Makes real calls to target phone numbers
- Uses real Twilio API for all operations
- Charges apply based on Twilio pricing
- Requires verified phone numbers OR upgraded account

## Toggling Modes

### Via UI (Development)

1. Log in to the dashboard
2. Go to **Settings** page
3. Look for "Test Mode" toggle
4. Click **Toggle Mode**
5. **Restart the application** for changes to take effect

### Via Environment Variable (Production/Render)

For cloud deployments (e.g., Render.com):

1. Go to your Render dashboard
2. Select your service
3. Navigate to **Environment** tab
4. Change `TEST_MODE` value:
   - `true` for Test Mode
   - `false` for Live Mode
5. Click **Save Changes**
6. Service will automatically restart

## Limitations

### Trial Account Limitations

Twilio trial accounts have API restrictions:

- ❌ **Balance API**: Returns 403 error (not accessible)
- ❌ **Usage API**: Returns 403 error (not accessible)
- ✅ **Account Info**: Basic info available
- ✅ **Call API**: Works with verified numbers only

The system gracefully handles these limitations with fallback values.

### Test Mode Limitations

- Mock conversations are randomly generated (not real)
- Cannot test actual company interactions
- Simulated call outcomes may not reflect real scenarios
- Test number will receive actual calls in test mode

## Best Practices

### During Development

1. ✅ Keep `TEST_MODE=true`
2. ✅ Use test mode for UI/UX testing
3. ✅ Verify data flow with mock calls
4. ✅ Test error handling and edge cases

### Before Production

1. ⚠️ Upgrade Twilio account (remove trial restrictions)
2. ⚠️ Verify all target numbers OR upgrade to standard account
3. ⚠️ Set `TEST_MODE=false`
4. ⚠️ Monitor Twilio balance and usage
5. ⚠️ Test with small batch first

### In Production

1. 📞 Use `TEST_MODE=false` for real operations
2. 📊 Monitor call logs and results
3. 💰 Track Twilio spending
4. 🔄 Use test mode for debugging specific issues

## Troubleshooting

### "Failed to toggle mode: .env file not found"

**Solution**: 
- Ensure `.env` file exists in project root
- Check file permissions (must be readable/writable)
- In production, use platform environment variables instead

### "Resource not accessible with Test Account Credentials"

**Solution**: 
- This is normal for trial accounts
- System provides fallback information
- Upgrade to standard account for full API access

### Calls not working in test mode

**Solution**:
1. Verify `TEST_PHONE_NUMBER` is correct in `.env`
2. Ensure the number is verified in Twilio Console
3. Check Twilio credentials are valid
4. Review application logs for errors

### Restart required after toggle

**Solution**:
- Environment variables are loaded at startup
- Must restart application after changing `.env`
- In production, service auto-restarts after env changes

## Example Workflow

### Initial Setup (First Time)

```bash
# 1. Configure .env
echo "TEST_MODE=true" >> .env
echo "TEST_PHONE_NUMBER=+19092028031" >> .env

# 2. Start application
python main.py

# 3. Test calls go to your verified number
# 4. No charges applied
```

### Testing to Production

```bash
# Development Phase
TEST_MODE=true  # Safe testing with mock calls

# Staging Phase (if upgraded account)
TEST_MODE=false  # Test with small batch of real calls

# Production
TEST_MODE=false  # Full operation with real calls
```

## Support

For issues or questions:
- Check Twilio Console for account status
- Review application logs for detailed errors
- Verify environment variables are set correctly
- Ensure Twilio credentials are valid

## Summary

✅ **Test Mode** = Safe development with mock calls
📞 **Live Mode** = Production use with real calls
🔄 **Toggle easily** via UI or environment variables
💰 **Save money** by testing without charges
🛡️ **Trial-friendly** works with Twilio trial accounts
