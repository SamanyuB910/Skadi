# 🚀 Complete Vercel Deployment Guide

## ✅ Pre-Deployment Checklist (COMPLETED)
- [x] Code committed to GitHub (commit: 0316805)
- [x] Environment variables configured in code
- [x] Large files protected in .gitignore
- [x] Frontend uses `NEXT_PUBLIC_API_URL` environment variable
- [x] Both pages (analytics & heat-map) updated
- [x] Backend running successfully on localhost:8000
- [x] Frontend tested on localhost:3002

---

## 📦 What You Just Pushed to GitHub

**Repository**: https://github.com/SamanyuB910/Skadi
**Branch**: main
**Commit**: 0316805 - "Ready for Vercel deployment - ML analytics, environment variables, and deployment docs"

**Key Files Included**:
- ✅ Full Next.js frontend (`skadifrontend/Skaldi.-main/`)
- ✅ FastAPI backend (`api/`, `core/`, `optimizer/`, etc.)
- ✅ Deployment documentation (`DEPLOYMENT.md`, `VERCEL_CHECKLIST.md`)
- ✅ Environment variable templates (`.env.local.example`, `.env.example`)

**Protected (NOT pushed)**:
- 🚫 ML models (*.pkl)
- 🚫 Training data (*.csv, data/kaggle/)
- 🚫 Databases (*.db)
- 🚫 Visualizations (*.html)

---

## Part 1: Deploy Backend to Railway (Do This FIRST!)

### Why Railway?
- Free tier available ($5 free credit/month)
- Supports long-running processes (unlike Vercel)
- Easy deployment from GitHub
- Persistent storage for SQLite database
- Perfect for FastAPI applications

### Step-by-Step Backend Deployment

#### 1. Create Railway Account
1. Go to https://railway.app
2. Click "Login" → Sign in with your GitHub account
3. Authorize Railway to access your repositories

#### 2. Create New Project
1. Click "New Project" on Railway dashboard
2. Select "Deploy from GitHub repo"
3. Choose your repository: **SamanyuB910/Skadi**
4. Railway will detect it's a Python project

#### 3. Configure the Service
1. **Root Directory**: Leave blank (or set to `Skadi` if needed)
2. **Build Command**: Railway auto-detects from `requirements.txt`
3. **Start Command**: Set to:
   ```
   uvicorn api.app:app --host 0.0.0.0 --port $PORT
   ```
4. **Watch Paths**: Leave default (will auto-deploy on git push)

#### 4. Set Environment Variables (if needed)
Railway should work without additional env vars, but you can add:
- `PYTHON_VERSION=3.11` (if you want to specify Python version)

#### 5. Deploy and Wait
1. Railway will automatically start building
2. Wait 2-5 minutes for deployment
3. Watch the deployment logs for any errors

#### 6. Get Your Backend URL
1. Click on your service in Railway
2. Go to "Settings" tab
3. Under "Domains", click "Generate Domain"
4. You'll get a URL like: `https://skadi-production.up.railway.app`
5. **COPY THIS URL** - you'll need it for Vercel!

#### 7. Test Your Backend
Open a browser or use curl to test:
```
https://your-backend-url.railway.app/ml-analytics/performance-metrics
```
Should return JSON data with energy metrics.

---

## Part 2: Deploy Frontend to Vercel

### Step-by-Step Frontend Deployment

#### 1. Create Vercel Account
1. Go to https://vercel.com
2. Click "Sign Up" → Use your GitHub account
3. Authorize Vercel to access your repositories

#### 2. Import Your Project
1. From Vercel dashboard, click "Add New" → "Project"
2. Select "Import Git Repository"
3. Find and select: **SamanyuB910/Skadi**
4. Click "Import"

#### 3. Configure Build Settings
**CRITICAL**: You must set the correct root directory!

1. **Framework Preset**: Next.js (auto-detected)
2. **Root Directory**: 
   - Click "Edit" next to Root Directory
   - Set to: `skadifrontend/Skaldi.-main`
   - This is crucial! Without this, Vercel will fail to find your Next.js app

3. **Build Settings** (should auto-fill):
   - Build Command: `pnpm build`
   - Output Directory: `.next`
   - Install Command: `pnpm install`

4. **Node.js Version**: 18.x or newer (auto-detected)

#### 4. Set Environment Variables
**THIS IS THE MOST IMPORTANT STEP!**

1. Scroll down to "Environment Variables"
2. Add a new variable:
   - **Key**: `NEXT_PUBLIC_API_URL`
   - **Value**: `https://your-backend-url.railway.app` (from Railway, Step 6 above)
   - **Environment**: All (Production, Preview, Development)
3. Click "Add"

**Example**:
```
Key: NEXT_PUBLIC_API_URL
Value: https://skadi-production.up.railway.app
```

**⚠️ IMPORTANT**: Do NOT include a trailing slash!
- ✅ Correct: `https://skadi-production.up.railway.app`
- ❌ Wrong: `https://skadi-production.up.railway.app/`

#### 5. Deploy!
1. Click "Deploy"
2. Vercel will:
   - Clone your repository
   - Install dependencies with pnpm
   - Build your Next.js application
   - Deploy to their global CDN
3. Wait 2-5 minutes

#### 6. Monitor Deployment
1. Watch the build logs in real-time
2. Look for any errors (usually related to TypeScript or missing dependencies)
3. If successful, you'll see "✅ Build Completed"

#### 7. Get Your Frontend URL
1. Once deployed, Vercel gives you a URL like:
   - `https://skadi-xxx.vercel.app` (unique subdomain)
2. Click on the URL to visit your deployed site!

---

## Part 3: Verify Everything Works

### Test Your Deployed Website

#### 1. Home Page
Visit: `https://your-project.vercel.app`
- Should load without errors
- Should see the Skadi homepage

#### 2. Analytics Page
Visit: `https://your-project.vercel.app/analytics`
- **Expected**: Charts with bright colors (red, green, amber, blue, purple)
- **Expected**: Data showing variance (weekends lower, mid-week higher)
- **Check**: Open DevTools (F12) → Network tab
  - Should see requests to your Railway backend URL
  - All requests should return 200 OK

#### 3. Heat Map Page
Visit: `https://your-project.vercel.app/heat-map`
- **Expected**: Colored heatmap grid
- **Expected**: "IMS Kaggle Realistic" model name
- **Check**: DevTools → Network tab
  - Should see request to `/ml-heatmap/ims-anomaly`
  - Should return 200 OK

#### 4. Check for Errors
Open Browser Console (F12):
- **Expected**: No red error messages
- **Expected**: Successful API calls
- **Possible Warning**: "metadataBase not set" - this is normal, ignore it

### Common Issues and Solutions

#### Issue: "Failed to fetch" or "Network Error"
**Cause**: Backend URL not set or incorrect
**Solution**:
1. Go to Vercel → Your Project → Settings → Environment Variables
2. Verify `NEXT_PUBLIC_API_URL` is set correctly
3. Redeploy: Deployments tab → Click "..." → "Redeploy"

#### Issue: Charts not loading
**Cause**: CORS error from backend
**Solution**: 
1. Check Railway logs for CORS errors
2. Your backend should have CORS enabled (already configured in `api/app.py`)
3. If needed, add your Vercel domain to CORS allowed origins

#### Issue: 404 on deployment
**Cause**: Root directory not set correctly
**Solution**:
1. Go to Vercel → Settings → General
2. Set Root Directory to: `skadifrontend/Skaldi.-main`
3. Redeploy

#### Issue: Build fails with "pnpm not found"
**Cause**: Vercel using wrong package manager
**Solution**:
1. Add `pnpm-lock.yaml` to root (already included)
2. Vercel should auto-detect pnpm
3. Or manually set in Settings → Build & Development Settings

---

## Part 4: Post-Deployment Setup

### Optional Enhancements

#### 1. Add Custom Domain (Vercel)
1. Go to Vercel → Your Project → Settings → Domains
2. Add your custom domain (e.g., `skadi.yourdomain.com`)
3. Follow DNS configuration instructions
4. SSL certificate is automatic!

#### 2. Set Up Auto-Deployments
Already configured! Every time you push to GitHub:
- Railway will auto-deploy backend
- Vercel will auto-deploy frontend

#### 3. Monitor Performance
- **Vercel Analytics**: Settings → Analytics → Enable
- **Railway Logs**: Dashboard → Your Service → View Logs

#### 4. Set Up Environment-Specific URLs
You can add different backend URLs for preview vs production:
1. Vercel → Environment Variables
2. Add separate values for Production and Preview

---

## 📋 Quick Reference

### Your URLs After Deployment
- **Frontend**: `https://your-project.vercel.app`
- **Backend**: `https://your-backend.railway.app`
- **GitHub Repo**: https://github.com/SamanyuB910/Skadi

### Key Commands for Updates
```powershell
# After making code changes
cd "c:\VS Code Projects\SkadiHackATL\Skadi"
git add .
git commit -m "Your update message"
git push origin main

# This will automatically trigger:
# - Railway to redeploy backend
# - Vercel to redeploy frontend
```

### Environment Variable Reference
| Platform | Variable | Value |
|----------|----------|-------|
| Vercel | `NEXT_PUBLIC_API_URL` | Your Railway backend URL |
| Railway | (none required) | Auto-configured |

---

## 🎉 Success Criteria

Your deployment is successful when:
- ✅ Frontend loads at your Vercel URL
- ✅ Analytics page shows charts with real data
- ✅ Heat map page displays thermal anomaly grid
- ✅ No console errors in browser DevTools
- ✅ All API calls return 200 OK
- ✅ Data auto-refreshes every 30 seconds

---

## 🆘 Need Help?

### Vercel Documentation
- https://vercel.com/docs
- https://vercel.com/docs/concepts/projects/environment-variables

### Railway Documentation
- https://docs.railway.app
- https://docs.railway.app/deploy/deployments

### Check Logs
- **Vercel**: Dashboard → Deployments → Click deployment → View Function Logs
- **Railway**: Dashboard → Your Service → View Logs

### Common Log Locations
- Frontend build errors: Vercel deployment logs
- Runtime errors: Browser console (F12)
- Backend errors: Railway logs

---

## 🔄 Rollback Plan

If something goes wrong:

### Rollback Frontend (Vercel)
1. Go to Vercel → Deployments
2. Find a previous working deployment
3. Click "..." → "Promote to Production"

### Rollback Backend (Railway)
1. Go to Railway → Deployments
2. Find previous deployment
3. Click "Redeploy"

### Rollback Code (GitHub)
```powershell
git log  # Find the commit hash to revert to
git reset --hard <commit-hash>
git push origin main --force
```

---

## 🎯 Next Steps After Deployment

1. **Share your live URL** with the hackathon judges!
2. **Monitor performance** in Vercel and Railway dashboards
3. **Add more features** and push to GitHub (auto-deploys)
4. **Set up custom domain** if you have one
5. **Enable analytics** to track usage

---

**Deployed by**: SamanyuB910
**Repository**: https://github.com/SamanyuB910/Skadi
**Commit**: 0316805
**Date**: October 18, 2025

Good luck with your deployment! 🚀
