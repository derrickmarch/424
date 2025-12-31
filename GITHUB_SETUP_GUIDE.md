# 🚀 GitHub Setup Guide - Connect Your Terminal

## 📋 Prerequisites

Before starting, make sure you have:
- [ ] GitHub account created
- [ ] Git installed on your computer
- [ ] Your project folder open in terminal

---

## 🔍 Step 1: Check if Git is Installed

Open your terminal and run:

```bash
git --version
```

**Expected output:**
```
git version 2.x.x
```

**If not installed:**
- **Windows:** Download from https://git-scm.com/download/win
- **Mac:** Run `brew install git` or download from https://git-scm.com
- **Linux:** Run `sudo apt-get install git`

---

## 🎯 Step 2: Configure Git (First Time Only)

Tell Git who you are:

```bash
# Set your name
git config --global user.name "Your Name"

# Set your email (use your GitHub email)
git config --global user.email "your.email@example.com"

# Verify it worked
git config --global user.name
git config --global user.email
```

**Example:**
```bash
git config --global user.name "John Doe"
git config --global user.email "john@example.com"
```

---

## 📦 Step 3: Initialize Git Repository

In your project folder:

```bash
# Navigate to your project (if not already there)
cd path/to/your/project

# Initialize Git
git init

# Check status
git status
```

You should see a list of files to be committed.

---

## 🌐 Step 4: Create Repository on GitHub

1. Go to https://github.com
2. Click the **"+"** icon (top right)
3. Select **"New repository"**
4. Fill in:
   - **Repository name:** `account-verifier` (or your preferred name)
   - **Description:** "Account Verification System with Twilio & OpenAI"
   - **Private:** ✅ Recommended for production
   - **DO NOT** initialize with README (your code already has one)
5. Click **"Create repository"**

GitHub will show you commands - **keep this page open!**

---

## 🔑 Step 5: Connect to GitHub (Authentication)

You have **2 options**:

### **Option A: Personal Access Token (Recommended)**

#### 5A.1: Create Token on GitHub
1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Give it a name: `Render Deployment`
4. Set expiration: `90 days` (or your preference)
5. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (if using GitHub Actions)
6. Click **"Generate token"**
7. **COPY THE TOKEN NOW!** (You won't see it again)
   - Format: `ghp_xxxxxxxxxxxxxxxxxxxx`

#### 5A.2: Use Token for Authentication
When you push, use this format:
```bash
git remote add origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/YOUR_REPO.git
```

**Example:**
```bash
git remote add origin https://ghp_abc123xyz789@github.com/johndoe/account-verifier.git
```

---

### **Option B: SSH Keys (More Secure, One-Time Setup)**

#### 5B.1: Generate SSH Key
```bash
# Generate new SSH key
ssh-keygen -t ed25519 -C "your.email@example.com"

# Press Enter to accept default location
# Enter a passphrase (optional but recommended)
# Press Enter again to confirm

# Start SSH agent
eval "$(ssh-agent -s)"

# Add your SSH key
ssh-add ~/.ssh/id_ed25519
```

#### 5B.2: Add SSH Key to GitHub
```bash
# Copy your public key
# On Mac/Linux:
cat ~/.ssh/id_ed25519.pub

# On Windows (Git Bash):
cat ~/.ssh/id_ed25519.pub

# Or on Windows (PowerShell):
Get-Content ~/.ssh/id_ed25519.pub | Set-Clipboard
```

**Then on GitHub:**
1. Go to: https://github.com/settings/keys
2. Click **"New SSH key"**
3. Title: `My Computer`
4. Key type: `Authentication Key`
5. Paste your public key
6. Click **"Add SSH key"**

#### 5B.3: Test SSH Connection
```bash
ssh -T git@github.com
```

Should see:
```
Hi username! You've successfully authenticated...
```

---

## 📤 Step 6: Connect and Push Your Code

### If Using HTTPS (Option A - Token):
```bash
# Add remote repository (replace with your details)
git remote add origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/YOUR_REPO.git

# Add all files
git add .

# Commit
git commit -m "Initial commit - Production ready"

# Set branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

### If Using SSH (Option B):
```bash
# Add remote repository (replace with your username/repo)
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO.git

# Add all files
git add .

# Commit
git commit -m "Initial commit - Production ready"

# Set branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

---

## ✅ Step 7: Verify Upload

1. Go to your GitHub repository URL
2. Refresh the page
3. You should see all your files! 🎉

---

## 🔄 Future Pushes (After Initial Setup)

Once connected, pushing is easy:

```bash
# Add changed files
git add .

# Commit with message
git commit -m "Fix pandas version"

# Push
git push
```

That's it! No token or setup needed again.

---

## 🆘 Common Issues & Solutions

### **Issue 1: "remote origin already exists"**
```bash
# Remove existing remote
git remote remove origin

# Add it again with correct URL
git remote add origin YOUR_URL
```

### **Issue 2: "Authentication failed"**
```bash
# HTTPS: Check your token is correct
# SSH: Run ssh -T git@github.com to test

# If token expired, generate a new one and update:
git remote set-url origin https://NEW_TOKEN@github.com/USER/REPO.git
```

### **Issue 3: "Permission denied (publickey)"**
```bash
# Your SSH key isn't added
# Re-run Step 5B to add SSH key to GitHub
```

### **Issue 4: "Can't find git command"**
```bash
# Git not installed
# Download and install from https://git-scm.com
```

---

## 💡 Quick Reference

### Check Git Status
```bash
git status
```

### Add Files
```bash
git add .                    # Add all files
git add filename.txt         # Add specific file
```

### Commit
```bash
git commit -m "Your message here"
```

### Push
```bash
git push                     # After initial setup
git push origin main         # Full command
```

### View Remote
```bash
git remote -v               # See your GitHub URL
```

---

## 🎯 Your Exact Commands (Template)

Replace `YOUR_USERNAME` and `YOUR_REPO`:

```bash
# 1. Configure Git (first time only)
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# 2. Initialize (if not done)
git init

# 3. Add remote (choose HTTPS or SSH)
# HTTPS:
git remote add origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/YOUR_REPO.git
# OR SSH:
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO.git

# 4. Add, commit, and push
git add .
git commit -m "Production-ready deployment"
git branch -M main
git push -u origin main
```

---

## ✨ After Your First Push

Every future update is just:
```bash
git add .
git commit -m "Your changes description"
git push
```

Simple! 🚀

---

## 🔒 Security Tips

1. ✅ Use **Personal Access Token** or **SSH** (not password)
2. ✅ Make repository **private** for production
3. ✅ Never commit `.env` files (already protected by `.gitignore`)
4. ✅ Set token expiration (regenerate periodically)
5. ✅ Don't share your token publicly

---

## 📚 Need More Help?

- **GitHub Docs:** https://docs.github.com/en/get-started
- **Git Basics:** https://git-scm.com/book/en/v2
- **SSH Keys:** https://docs.github.com/en/authentication/connecting-to-github-with-ssh

---

**You're ready to push your code to GitHub! Follow the steps above and let me know if you hit any issues!** 🎉
