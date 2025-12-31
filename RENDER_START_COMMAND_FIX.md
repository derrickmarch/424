# 🔧 Fix Render Start Command - Quick Guide

## ❌ Problem

Your app built successfully but won't start:
```
bash: line 1: gunicorn: command not found
```

**Cause:** Render is trying to use `gunicorn` instead of `python main.py`

---

## ✅ Solution - Fix in Dashboard (2 Minutes)

### Step 1: Go to Render Dashboard
Visit: https://dashboard.render.com

### Step 2: Select Your Service
Click on your service name (e.g., "account-verifier")

### Step 3: Go to Settings
Click the **"Settings"** tab in the left sidebar

### Step 4: Find Start Command
Scroll down to **"Build & Deploy"** section

### Step 5: Update Start Command
Find the field labeled **"Start Command"**

**Current value (wrong):**
```
gunicorn main:app
```

**Change to:**
```
python main.py
```

### Step 6: Save
Click **"Save Changes"** button at the bottom

### Step 7: Wait for Redeploy
Render will automatically redeploy your service with the correct command (~1-2 minutes)

---

## 📊 What You'll See

### In the Logs:
```
==> Deploying...
==> Running 'python main.py'
2025-12-31 13:35:00 INFO:     Started server process
2025-12-31 13:35:00 INFO:     Waiting for application startup.
2025-12-31 13:35:01 INFO:     Application startup complete.
2025-12-31 13:35:01 INFO:     Uvicorn running on http://0.0.0.0:8001
✅ Your service is live
```

### Status Will Change:
```
❌ Deploy failed → ⏳ Deploying → ✅ Live
```

---

## 🎯 Alternative: Delete and Recreate with Blueprint

If you want to use the `render.yaml` configuration properly:

### Option 1: Update Existing Service (Recommended)
Just follow the steps above - easiest and fastest!

### Option 2: Create New Service via Blueprint
1. Delete current service (if you want to start fresh)
2. Dashboard → **"New +"** → **"Blueprint"**
3. Select your GitHub repo: **derrickmarch/424**
4. Render reads `render.yaml` automatically
5. Click **"Apply"**
6. Everything configured correctly from the start!

---

## ⚠️ Why This Happened

When you create a Web Service manually (not via Blueprint):
- Render auto-detects the start command
- For Python apps with FastAPI, it assumes `gunicorn`
- But your app uses `uvicorn` (built into main.py)
- So you need to manually set: `python main.py`

When you use Blueprint (render.yaml):
- Render reads `startCommand: python main.py` from the file
- Everything works automatically!

---

## 🚀 After Fix

Once the start command is corrected and redeployed:

1. **Access Your App:**
   - URL: `https://your-service.onrender.com`

2. **Login:**
   - Username: `admin`
   - Password: `admin123`

3. **Change Password:** ⚠️ Do this first!

4. **Add API Keys:** Via Settings UI

5. **Start Testing!**

---

## 💡 Pro Tip

To avoid this in the future:
- Always deploy via **Blueprint** when you have a `render.yaml`
- Or manually set the start command during service creation
- The start command is: `python main.py`

---

**Go fix it now! It'll take 2 minutes and your app will be live!** 🎉
