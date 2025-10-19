# 🎯 QUICK START: Vercel Deployment (TL;DR)

## ✅ Step 1: Backend → Railway (5 minutes)

1. **Go to Railway**: https://railway.app
2. **Login** with GitHub
3. **New Project** → Deploy from GitHub → Select `SamanyuB910/Skadi`
4. **Start Command**: `uvicorn api.app:app --host 0.0.0.0 --port $PORT`
5. **Generate Domain** → Copy the URL (e.g., `https://skadi-production.up.railway.app`)
6. **Test**: Visit `https://your-url.railway.app/ml-analytics/performance-metrics`

---

## ✅ Step 2: Frontend → Vercel (5 minutes)

1. **Go to Vercel**: https://vercel.com
2. **Login** with GitHub
3. **Import Project** → Select `SamanyuB910/Skadi`
4. **Root Directory**: `skadifrontend/Skaldi.-main` ⚠️ CRITICAL!
5. **Environment Variable**:
   ```
   Key:   NEXT_PUBLIC_API_URL
   Value: https://your-railway-url.railway.app
   ```
6. **Deploy** → Wait 3 minutes
7. **Visit**: `https://your-project.vercel.app`

---

## ✅ Step 3: Test (2 minutes)

Visit these pages on your Vercel URL:
- `/` - Home page
- `/analytics` - Should show colorful charts
- `/heat-map` - Should show thermal heatmap

Open DevTools (F12) → Network tab:
- All API calls should go to your Railway URL
- All should return 200 OK

---

## 🚨 Most Common Mistake

**Forgetting to set Root Directory in Vercel!**

If deployment fails with "No Next.js build found":
1. Vercel → Settings → General
2. Root Directory: `skadifrontend/Skaldi.-main`
3. Save → Redeploy

---

## 📱 Your URLs

After deployment, you'll have:
- **Live Website**: `https://your-project.vercel.app`
- **Backend API**: `https://your-backend.railway.app`
- **GitHub**: https://github.com/SamanyuB910/Skadi

---

## 🎉 Done!

Total time: ~10-15 minutes

For detailed instructions, see: `VERCEL_DEPLOYMENT_GUIDE.md`
