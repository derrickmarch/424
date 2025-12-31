# Render.com Quick Start Guide

## 🚀 Deploy in 5 Minutes

### Step 1: Push to GitHub (if not already done)

```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

**Note:** Your `.env` file is NOT pushed (it's in `.gitignore`). This is correct!

---

### Step 2: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Authorize Render to access your repositories

---

### Step 3: Deploy from Dashboard

1. **Click "New +" → "Web Service"**

2. **Connect Repository**
   - Select your `account-verifier` repository
   - Click "Connect"

3. **Configure Service** (most settings auto-detected):
   - **Name**: `account-verifier`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. **Add Environment Variables** (click "Advanced"):

   **Essential Variables (Add These):**
   ```
   TWILIO_ACCOUNT_SID=your_account_sid_here
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_PHONE_NUMBER=+1234567890
   TWILIO_WEBHOOK_BASE_URL=https://YOUR-APP.onrender.com
   
   OPENAI_API_KEY=your_openai_key_here
   
   TEST_MODE=true
   TEST_PHONE_NUMBER=+19092028031
   
   APP_ENV=production
   RENDER=true
   ```

   **Important:** Replace `YOUR-APP.onrender.com` with your actual Render URL after deployment!

5. **Click "Create Web Service"**

---

### Step 4: Wait for Deployment

- Watch the logs as Render builds your app
- Takes ~2-5 minutes
- You'll get a URL like: `https://account-verifier-xxxx.onrender.com`

---

### Step 5: Update Twilio Webhook URL

1. Go back to **Render Dashboard** → **Environment**
2. Update `TWILIO_WEBHOOK_BASE_URL` with your new Render URL
3. Save changes (service will restart)

---

### Step 6: Test Your App

1. **Visit your app**: `https://your-app.onrender.com`
2. **Login**:
   - Username: `admin`
   - Password: `admin123`
3. **Change password immediately!**

---

## ✅ You're Live!

### What Works Now:

✅ **Test Mode Active** - Calls go to your verified number only
✅ **No .env File Needed** - Uses Render environment variables
✅ **Database Runtime Settings** - Toggle test mode without restart
✅ **Auto-Deploy** - Push to GitHub, Render deploys automatically

---

## 🔄 Toggle Test Mode (On Render)

### Method 1: Via App UI (Instant, No Restart)

1. Login to your app
2. Go to **Settings** page
3. Click **Toggle Test Mode**
4. ✅ Changes apply immediately

**Note:** This uses database runtime settings. Survives app restarts!

### Method 2: Via Render Dashboard (Permanent)

1. Go to Render Dashboard
2. Select your service
3. Click **Environment** tab
4. Change `TEST_MODE` to `true` or `false`
5. Save (service restarts automatically)

---

## 📱 Twilio Webhook Setup

After deployment, configure Twilio:

1. Go to [Twilio Console](https://console.twilio.com/)
2. Phone Numbers → Manage → Active Numbers
3. Click your number
4. **Voice Configuration**:
   - **A Call Comes In**: Webhook
   - **URL**: `https://your-app.onrender.com/api/twilio/voice?verification_id={verification_id}`
   - **HTTP**: POST
   
5. **Status Callback**:
   - **URL**: `https://your-app.onrender.com/api/twilio/status-callback`
   - **HTTP**: POST

---

## 🐛 Troubleshooting

### App Sleeping (Free Tier)

**Issue:** App takes ~30 seconds to wake up on first request

**Solution:**
- Use a service like [UptimeRobot](https://uptimerobot.com) to ping every 5 minutes
- Or upgrade to Starter plan ($7/month) for always-on

### "Failed to toggle mode: .env file not found"

**This is normal on Render!** ✅

The system automatically:
- Detects Render environment
- Uses database runtime settings
- Allows instant toggle without restart

### Environment Variable Not Working

**Check:**
1. Spelling (case-sensitive)
2. Saved changes
3. Service restarted
4. View logs for errors

### Can't Login

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

**If locked out:**
- Check logs for errors
- Redeploy service
- Database might have reset

---

## 💰 Pricing

### Free Tier (Good for Testing)
- ✅ 750 hours/month free
- ⚠️ App sleeps after 15 min inactivity
- ✅ Perfect for development

### Starter Plan ($7/month - Recommended)
- ✅ Always-on (no sleep)
- ✅ Better performance
- ✅ Custom domain support

---

## 🔒 Security Checklist

After deployment:

- [ ] Change admin password
- [ ] Update `SECRET_KEY` (or let Render generate)
- [ ] Verify Twilio credentials are correct
- [ ] Set `APP_ENV=production`
- [ ] Enable HTTPS (automatic on Render)
- [ ] Review environment variables

---

## 📊 Monitoring

### Application Health

Check: `https://your-app.onrender.com/health`

Response:
```json
{
  "status": "healthy",
  "service": "account-verifier",
  "environment": "production",
  "auto_calling_enabled": false,
  "scheduler_running": false
}
```

### Logs

View in Render Dashboard:
- **Logs** tab shows real-time application output
- Filter by level (info, error, warning)
- Download logs for debugging

---

## 🔄 Updating Your App

### Deploy Updates

```bash
# Make changes locally
git add .
git commit -m "Your update description"
git push origin main
```

Render automatically:
1. Detects the push
2. Builds new version
3. Deploys with zero downtime (paid plans)

### View Deployment

- **Events** tab shows all deployments
- Click to view logs
- Rollback if needed

---

## 🎯 Next Steps

1. **Test a verification**: Add a record and initiate a call
2. **Review settings**: Configure auto-calling, retry logic, etc.
3. **Import CSV**: Bulk upload verification records
4. **Monitor usage**: Check Twilio and OpenAI costs
5. **Upgrade Twilio**: Remove trial restrictions when ready

---

## 📚 Additional Resources

- **Full Guide**: See `RENDER_DEPLOYMENT_GUIDE.md`
- **Test Mode**: See `TEST_MODE_GUIDE.md`
- **Render Docs**: [render.com/docs](https://render.com/docs)

---

## 🆘 Need Help?

**Common Issues:**
- `.env file not found` → Normal on Render! Uses database settings
- App won't start → Check logs, verify environment variables
- Test mode not working → Check `TEST_MODE` and `TEST_PHONE_NUMBER` env vars
- Twilio errors → Verify credentials, webhook URLs

**Still Stuck?**
1. Check application logs in Render dashboard
2. Review `RENDER_DEPLOYMENT_GUIDE.md`
3. Verify all environment variables are set correctly

---

## ✨ Summary

You now have:
- ✅ App deployed on Render.com
- ✅ No `.env` file needed
- ✅ Test mode working with verified number
- ✅ Database runtime settings for instant toggle
- ✅ Auto-deploy on git push
- ✅ Free tier for testing

**Enjoy your cloud-deployed account verification system!** 🎉
