# Render.com Deployment Guide

## Overview

This guide explains how to deploy the Account Verifier system to Render.com, a cloud platform that doesn't use `.env` files.

## Why No .env Files on Render?

- ❌ `.env` files are **never** pushed to GitHub (in `.gitignore` for security)
- ✅ Render uses **Environment Variables** configured in the dashboard
- ✅ Database runtime settings allow **hot-reload** without restarts

## Deployment Steps

### 1. Push Code to GitHub

Make sure your code is in a GitHub repository:

```bash
# Initialize git (if not already done)
git init

# Add all files (except .env - it's in .gitignore)
git add .

# Commit changes
git commit -m "Initial commit for Render deployment"

# Push to GitHub
git remote add origin https://github.com/yourusername/your-repo.git
git push -u origin main
```

**Important**: The `.env` file will NOT be pushed (it's in `.gitignore`). This is correct!

### 2. Create Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure the service:

**Basic Settings:**
- **Name**: `account-verifier` (or your preferred name)
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Instance Type:**
- Start with **Free** tier for testing
- Upgrade to **Starter** or higher for production

### 3. Configure Environment Variables

In Render dashboard, go to **Environment** tab and add these variables:

#### Required Variables

```env
# Database (Render provides PostgreSQL, or use SQLite)
DATABASE_URL=sqlite:///./account_verifier.db

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WEBHOOK_BASE_URL=https://your-app.onrender.com

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8001
APP_ENV=production
SECRET_KEY=your-secure-secret-key-here-change-this

# Test Mode Configuration
TEST_MODE=true
TEST_PHONE_NUMBER=+19092028031

# Call Settings
MAX_CONCURRENT_CALLS=1
MAX_RETRY_ATTEMPTS=2
RETRY_BACKOFF_MINUTES=30,240
CALL_TIMEOUT_SECONDS=300

# Looping Call Settings
ENABLE_AUTO_CALLING=false
CALL_LOOP_INTERVAL_MINUTES=5
BATCH_SIZE_PER_LOOP=3

# Compliance Settings
ENABLE_CALL_RECORDING=false
REQUIRE_RECORDING_CONSENT=false
ENABLE_TRANSCRIPTION=false

# Notification Settings
ADMIN_EMAIL=your-email@example.com
ADMIN_PHONE=+19092028031

# Render Detection (auto-set by Render)
RENDER=true
```

#### Get Your Render App URL

After creating the service, Render will give you a URL like:
- `https://account-verifier-xxxx.onrender.com`

Update `TWILIO_WEBHOOK_BASE_URL` with this URL.

### 4. Deploy

1. Click **Create Web Service**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Start the application
3. Monitor the logs during deployment

### 5. Verify Deployment

Once deployed, test your application:

1. **Check Health Endpoint**:
   ```
   https://your-app.onrender.com/health
   ```
   Should return: `{"status": "healthy", ...}`

2. **Access Dashboard**:
   ```
   https://your-app.onrender.com/
   ```

3. **Login with Default Credentials**:
   - Username: `admin`
   - Password: `admin123`
   - ⚠️ **Change password immediately after first login!**

## Test Mode on Render

### How It Works

Since there's no `.env` file on Render, the system uses **database runtime settings**:

1. **Environment Variable** (`TEST_MODE=true`) sets the initial mode
2. **Database Override** allows toggling without restart
3. **Hot-Reload** changes take effect immediately

### Toggle Test Mode

**Option 1: Via UI (Recommended)**
1. Log in to your app
2. Go to **Settings** page
3. Click **Toggle Test Mode**
4. ✅ Changes apply immediately (no restart needed)

**Option 2: Via Render Dashboard (Permanent)**
1. Go to Render dashboard
2. Select your service
3. Navigate to **Environment** tab
4. Change `TEST_MODE` value
5. Click **Save Changes**
6. Service restarts automatically

### Important Notes

- 🔄 **UI Toggle**: Uses database (instant, no restart)
- 🔄 **Dashboard Toggle**: Updates env var (requires restart)
- ✅ **UI toggle is temporary** - survives app restarts but database resets will lose it
- ✅ **Dashboard toggle is permanent** - persists across everything

## Database Setup

### Option 1: SQLite (Default - Simple)

```env
DATABASE_URL=sqlite:///./account_verifier.db
```

**Pros:**
- ✅ No setup required
- ✅ Works out of the box
- ✅ Good for testing

**Cons:**
- ⚠️ Data persists only on disk (may reset on deployments)
- ⚠️ Not suitable for high traffic

### Option 2: PostgreSQL (Recommended for Production)

1. In Render dashboard, create a **PostgreSQL** database
2. Copy the **Internal Database URL**
3. Set `DATABASE_URL` to this value:
   ```env
   DATABASE_URL=postgresql://user:password@host/database
   ```

**Pros:**
- ✅ Data persists across deployments
- ✅ Better performance
- ✅ Production-ready

## Twilio Webhook Configuration

After deployment, update Twilio webhooks:

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to your phone number settings
3. Update webhook URLs:
   - **Voice URL**: `https://your-app.onrender.com/api/twilio/voice?verification_id={verification_id}`
   - **Status Callback**: `https://your-app.onrender.com/api/twilio/status-callback`

## Troubleshooting

### "Failed to toggle mode: .env file not found"

**This is normal on Render!** ✅

The system automatically:
- Detects it's running on Render
- Uses database runtime settings instead
- Allows toggling without `.env` file

### Application Won't Start

**Check Logs:**
1. Go to Render dashboard
2. Click on your service
3. View **Logs** tab
4. Look for error messages

**Common Issues:**
- Missing environment variables
- Invalid Twilio credentials
- Database connection errors

### Test Mode Not Working

**Solution:**
1. Check `TEST_MODE` environment variable in Render dashboard
2. Ensure `TEST_PHONE_NUMBER` is set and verified in Twilio
3. Try toggling via UI (Settings page)
4. Check application logs

### Database Resets on Deployment

**Issue:** Using SQLite and data disappears after redeployment

**Solution:**
- Switch to PostgreSQL (recommended)
- Or use Render Disk for persistent SQLite storage

## Environment Variable Management

### Viewing Current Settings

```bash
# Access your Render shell
# In Render dashboard: Shell tab

# Check environment variables
echo $TEST_MODE
echo $TWILIO_ACCOUNT_SID
```

### Updating Settings

**Via Render Dashboard:**
1. Go to **Environment** tab
2. Edit variable value
3. Click **Save**
4. Service restarts automatically

**Via API (Runtime Override):**
- Use the Settings UI in your app
- Changes take effect immediately
- No restart required

## Security Best Practices

### 1. Change Default Admin Password

```bash
# After first login
1. Go to Settings → User Management
2. Change admin password
3. Create additional user accounts as needed
```

### 2. Secure Environment Variables

- ✅ Never commit `.env` to GitHub
- ✅ Use Render's encrypted environment variables
- ✅ Rotate API keys periodically
- ✅ Use strong SECRET_KEY value

### 3. API Keys

Store sensitive keys in Render environment variables:
- `TWILIO_AUTH_TOKEN`
- `OPENAI_API_KEY`
- `SECRET_KEY`

### 4. Webhook Security

In production:
- Enable Twilio signature validation
- Use HTTPS only
- Implement rate limiting

## Monitoring

### Application Health

Monitor via:
1. **Render Metrics**: CPU, memory, response times
2. **Application Logs**: Errors and warnings
3. **Health Endpoint**: `/health`

### Twilio Usage

Monitor via:
1. **Twilio Console**: Call logs, usage, balance
2. **App Dashboard**: Verification status, call results
3. **Usage API**: `/api/usage`

## Scaling

### Free Tier Limitations

- App sleeps after 15 minutes of inactivity
- Wakes up on first request (slower response)
- 750 hours/month free

### Upgrading for Production

**Starter Plan ($7/month):**
- ✅ No sleep/spin-down
- ✅ Always available
- ✅ Custom domains
- ✅ Better performance

**Standard Plan ($25/month):**
- ✅ More resources
- ✅ Scaling options
- ✅ Priority support

## Updating Your App

### Deploy Updates

```bash
# On your local machine
git add .
git commit -m "Update description"
git push origin main
```

Render automatically:
1. Detects the push
2. Rebuilds the app
3. Deploys new version
4. Zero-downtime deployment (on paid plans)

### Rolling Back

In Render dashboard:
1. Go to **Events** tab
2. Find previous successful deploy
3. Click **Rollback**

## Cost Estimation

### Free Tier
- Web Service: Free (750 hours/month)
- PostgreSQL: Free (90 days, then $7/month)
- Total: **$0** (first 90 days)

### Production Setup
- Web Service (Starter): $7/month
- PostgreSQL (Starter): $7/month
- Twilio: Pay-as-you-go (varies)
- OpenAI: Pay-as-you-go (varies)
- Total: **~$14/month** + usage costs

## Support

### Render Support
- [Render Documentation](https://render.com/docs)
- [Render Community](https://community.render.com/)
- Support tickets (paid plans)

### Application Support
- Check `TEST_MODE_GUIDE.md` for test mode help
- Review application logs
- GitHub Issues (if applicable)

## Summary

✅ **No .env files needed** - Use Render environment variables
✅ **Database runtime settings** - Toggle test mode without restart
✅ **Auto-deploy** - Push to GitHub, Render deploys
✅ **Free tier available** - Great for testing
✅ **Easy scaling** - Upgrade when ready
✅ **Secure** - Encrypted environment variables

Your app is now ready for production on Render.com! 🚀
