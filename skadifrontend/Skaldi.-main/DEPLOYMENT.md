# Deployment Guide for Skadi Platform

## Overview
Skadi is a two-part application that requires separate deployments:
1. **Frontend** (Next.js) → Deploy to Vercel
2. **Backend** (FastAPI) → Deploy to Railway, Render, or cloud provider

## Frontend Deployment (Vercel)

### Prerequisites
- GitHub account
- Vercel account (sign up at https://vercel.com)
- Repository pushed to GitHub

### Steps

1. **Push to GitHub**
   ```bash
   cd skadifrontend/Skaldi.-main
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Import to Vercel**
   - Go to https://vercel.com/dashboard
   - Click "Add New Project"
   - Import your GitHub repository
   - Select the `skadifrontend/Skaldi.-main` directory as the root

3. **Configure Environment Variables**
   - In Vercel project settings → Environment Variables
   - Add the following variable:
     ```
     NEXT_PUBLIC_API_URL=https://your-backend-url.com
     ```
   - Replace `your-backend-url.com` with your actual backend API URL (see Backend Deployment below)

4. **Build Settings**
   - Framework Preset: Next.js
   - Build Command: `pnpm build` (default)
   - Output Directory: `.next` (default)
   - Install Command: `pnpm install` (default)

5. **Deploy**
   - Click "Deploy"
   - Wait for build to complete
   - Your frontend will be live at `https://your-project.vercel.app`

### Local Development
Create a `.env.local` file in the frontend root:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Backend Deployment

### ⚠️ Important Notes
- **Vercel is NOT suitable for the FastAPI backend** because:
  - Vercel uses serverless functions (limited execution time)
  - The backend has long-running background tasks (optimizer loops, data ingestion)
  - SQLite database needs persistent storage
  - ML model loading requires more memory than serverless allows

### Recommended Hosting Options

#### Option 1: Railway (Easiest)
Railway provides persistent storage and supports long-running processes.

1. **Prepare for Railway**
   - Add `railway.json` to the Skadi root directory:
     ```json
     {
       "$schema": "https://railway.app/railway.schema.json",
       "build": {
         "builder": "NIXPACKS"
       },
       "deploy": {
         "startCommand": "uvicorn api.app:app --host 0.0.0.0 --port $PORT",
         "restartPolicyType": "ON_FAILURE",
         "restartPolicyMaxRetries": 10
       }
     }
     ```

2. **Deploy**
   - Go to https://railway.app
   - Click "Start a New Project"
   - Connect your GitHub repository
   - Select the Skadi root directory
   - Railway will auto-detect Python and deploy
   - You'll get a URL like `https://your-project.railway.app`

3. **Configure Frontend**
   - Copy the Railway URL
   - Update `NEXT_PUBLIC_API_URL` in Vercel to point to this URL
   - Redeploy frontend on Vercel

#### Option 2: Render
1. Create a new Web Service on https://render.com
2. Connect your GitHub repository
3. Configure:
   - Root Directory: `Skadi` (or leave blank if repo root)
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn api.app:app --host 0.0.0.0 --port $PORT`
4. Deploy and copy the URL to Vercel environment variables

#### Option 3: AWS/GCP/Azure
For production deployments, consider:
- **AWS**: EC2 instance with systemd service
- **GCP**: Compute Engine or Cloud Run
- **Azure**: App Service or Container Instances

See `PRODUCTION_DEPLOYMENT.md` for detailed cloud deployment guides.

## Environment Variables Reference

### Frontend (Next.js)
| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `https://api.skadi.com` |

### Backend (FastAPI)
The backend currently uses local file paths and SQLite. For production:
- Consider PostgreSQL for the database
- Use environment variables for model paths
- Configure CORS to allow your Vercel domain

## Verification

### Test the Deployment
1. Visit your Vercel URL
2. Check the Analytics page - should load real data
3. Check the Heat Map page - should display thermal data
4. Open browser DevTools → Network tab
5. Verify API calls go to your backend URL (not localhost)

### Common Issues

**Issue**: Charts not loading
- **Solution**: Check browser console for CORS errors. Update backend CORS settings to allow your Vercel domain.

**Issue**: "Failed to fetch" errors
- **Solution**: Verify `NEXT_PUBLIC_API_URL` is set correctly in Vercel and backend is running.

**Issue**: Old localhost URLs still appearing
- **Solution**: Rebuild frontend on Vercel (Environment variables need rebuild to take effect).

## Rollback Plan
If deployment fails:
1. Keep localhost development running
2. Check Vercel deployment logs for build errors
3. Verify environment variables are set correctly
4. Test backend URL directly (should return JSON response)

## Next Steps
After successful deployment:
1. Set up custom domain in Vercel
2. Configure SSL certificates (automatic with Vercel)
3. Set up monitoring and logging
4. Consider adding authentication
5. Set up CI/CD pipeline for automatic deployments

## Support
- Frontend issues: Check Vercel deployment logs
- Backend issues: Check Railway/Render logs
- API connectivity: Verify CORS and environment variables
