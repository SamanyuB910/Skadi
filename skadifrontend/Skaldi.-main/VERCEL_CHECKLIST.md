# Pre-Deployment Checklist for Vercel

## ✅ Files Ready to Commit

### Frontend Files (Safe to commit)
- [x] All `.tsx` and `.ts` files
- [x] `package.json` and `pnpm-lock.yaml`
- [x] `next.config.ts` and `tailwind.config.ts`
- [x] `.env.local.example` (template only, not actual values)
- [x] `.env.example` (production template)
- [x] `DEPLOYMENT.md` (deployment instructions)

### Backend Files (Safe to commit)
- [x] All `.py` source files in `api/`, `core/`, `ims/`, `optimizer/`, etc.
- [x] `requirements.txt`
- [x] `docker-compose.yml` and `Dockerfile`
- [x] Configuration files (`IMPLEMENTATION.md`, `README.md`)

### Protected Files (NOT committed - verified in .gitignore)
- [x] `*.pkl` - ML models (5 files)
- [x] `*.csv` - Training data (3 files)
- [x] `data/kaggle/` - Kaggle datasets (2 directories)
- [x] `visualizations/*.html` - Generated charts (9 files)
- [x] `*.db` - SQLite databases
- [x] `.env.local` - Local environment secrets

## 🔧 Configuration Completed

### Environment Variables
- [x] Created `.env.local.example` with `NEXT_PUBLIC_API_URL=http://localhost:8000`
- [x] Created `.env.example` with production template
- [x] Updated `analytics/page.tsx` to use `process.env.NEXT_PUBLIC_API_URL`
- [x] Updated `heat-map/page.tsx` to use `process.env.NEXT_PUBLIC_API_URL`
- [x] All hardcoded `localhost:8000` URLs replaced

### Code Updates
- [x] Analytics page fetches real ML data from backend
- [x] Charts use bright colors for dark theme (#ef4444, #22c55e, #3b82f6, #f59e0b)
- [x] Day-of-week variance in analytics (weekends low, mid-week peak)
- [x] Heat map displays IMS model anomaly data

## 📋 Before Deploying to Vercel

### 1. Test Local Build
```powershell
cd "c:\VS Code Projects\SkadiHackATL\Skadi\skadifrontend\Skaldi.-main"
pnpm build
```
- [ ] Build completes without errors
- [ ] No TypeScript compilation errors

### 2. Verify Backend is Running
```powershell
cd "c:\VS Code Projects\SkadiHackATL\Skadi"
# Check if backend is running on http://localhost:8000
curl http://localhost:8000/ml-analytics/performance-metrics
```
- [ ] Returns 200 OK with JSON data

### 3. Test Frontend Locally
```powershell
# In skadifrontend/Skaldi.-main directory
pnpm dev
```
- [ ] Navigate to http://localhost:3000/analytics
- [ ] Navigate to http://localhost:3000/heat-map
- [ ] Both pages load data successfully

### 4. Commit to Git
```powershell
cd "c:\VS Code Projects\SkadiHackATL"
git status  # Verify no large files (.pkl, .csv, .html)
git add .
git commit -m "Ready for Vercel deployment - environment variables configured"
git push
```
- [ ] No models, datasets, or visualizations staged
- [ ] Pushed to GitHub successfully

### 5. Deploy Frontend to Vercel
- [ ] Import project from GitHub
- [ ] Set root directory: `Skadi/skadifrontend/Skaldi.-main`
- [ ] Add environment variable: `NEXT_PUBLIC_API_URL=<your-backend-url>`
- [ ] Deploy and verify

### 6. Deploy Backend (Choose One)

#### Option A: Railway
- [ ] Create new project on railway.app
- [ ] Connect GitHub repository
- [ ] Set root directory to `Skadi`
- [ ] Copy Railway URL to Vercel's `NEXT_PUBLIC_API_URL`
- [ ] Redeploy Vercel frontend

#### Option B: Render
- [ ] Create web service on render.com
- [ ] Build: `pip install -r requirements.txt`
- [ ] Start: `uvicorn api.app:app --host 0.0.0.0 --port $PORT`
- [ ] Copy Render URL to Vercel's `NEXT_PUBLIC_API_URL`
- [ ] Redeploy Vercel frontend

## ⚠️ Important Notes

### Two-Part Deployment Required
1. **Frontend (Vercel)**: Hosts the Next.js application
2. **Backend (Railway/Render/Cloud)**: Hosts the FastAPI server

**You cannot deploy both to Vercel!** The backend needs:
- Long-running processes (optimizer loops)
- Persistent storage (SQLite database)
- ML model loading (large memory)
- Background tasks (data ingestion)

### Environment Variable Must Match
The `NEXT_PUBLIC_API_URL` in Vercel **must** point to your deployed backend URL:
- ❌ NOT `http://localhost:8000` (won't work in production)
- ✅ YES `https://your-project.railway.app` or `https://your-project.onrender.com`

### After Setting Environment Variables
You **must rebuild** the frontend on Vercel for changes to take effect:
1. Go to Vercel dashboard
2. Navigate to Deployments
3. Click "Redeploy" on the latest deployment

## 🎯 Success Criteria

### Deployment is successful when:
- [ ] Vercel frontend loads without errors
- [ ] Analytics page displays real-time data
- [ ] Heat map page shows thermal anomaly data
- [ ] Browser DevTools shows API calls going to backend URL (not localhost)
- [ ] No CORS errors in console
- [ ] Charts render with bright colors
- [ ] Data refreshes every 30 seconds

### If Something Breaks:
1. Check Vercel deployment logs for build errors
2. Check backend logs (Railway/Render dashboard)
3. Verify `NEXT_PUBLIC_API_URL` is set correctly
4. Test backend URL directly in browser (should return JSON)
5. Check browser console for specific errors

## 📚 Documentation
- Full deployment guide: `DEPLOYMENT.md`
- Git protection details: `GITIGNORE_PROTECTION.md`
- Project overview: `README.md`

## 🚀 Ready to Deploy?
If all checkboxes above are complete, your application is **ready for Vercel deployment**!

Follow the steps in `DEPLOYMENT.md` for detailed instructions.
