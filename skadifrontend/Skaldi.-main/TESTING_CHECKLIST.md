# Website Testing Checklist

## Server Status
✅ Backend running on: **http://localhost:8000**
✅ Frontend running on: **http://localhost:3002**

## Manual Testing Steps

### 1. Home Page
- [ ] Navigate to http://localhost:3002
- [ ] Verify the page loads without errors
- [ ] Check browser console (F12) - should have no red errors

### 2. Analytics Page
- [ ] Navigate to http://localhost:3002/analytics
- [ ] **Charts should appear:**
  - Energy Consumption (bars in red/green)
  - Latency Impact (amber line)
  - Throughput (blue line)
  - Cost Savings (purple bars)
- [ ] **Check colors are bright and visible** (not black/dark)
- [ ] **Verify data variance:**
  - Weekend bars should be lower (Saturday/Sunday)
  - Mid-week bars should be higher (Tuesday/Wednesday)
- [ ] **Open browser console (F12):**
  - Should see successful fetch: `GET http://localhost:8000/ml-analytics/performance-metrics` → Status 200
  - No CORS errors
  - No "localhost:8000" appearing in any error messages

### 3. Heat Map Page
- [ ] Navigate to http://localhost:3002/heat-map
- [ ] **Heatmap should display:**
  - Grid of colored cells (representing racks)
  - Color intensity showing anomaly scores
  - Temperature/power readings
- [ ] **Verify model info:**
  - Should show "IMS Kaggle Realistic" model
  - Timestamp should be recent
- [ ] **Open browser console (F12):**
  - Should see successful fetch: `GET http://localhost:8000/ml-heatmap/ims-anomaly` → Status 200
  - No CORS errors

### 4. Environment Variable Test
This is the most important test for Vercel deployment readiness!

- [ ] **Open browser DevTools (F12) → Network tab**
- [ ] Refresh the Analytics page
- [ ] **Click on the request to `performance-metrics`**
- [ ] **Verify the Request URL shows:**
  - ✅ `http://localhost:8000/ml-analytics/performance-metrics`
  - (This confirms the environment variable is working)
- [ ] Refresh the Heat Map page
- [ ] **Click on the request to `ims-anomaly`**
- [ ] **Verify the Request URL shows:**
  - ✅ `http://localhost:8000/ml-heatmap/ims-anomaly`

### 5. API Direct Test
Test the backend APIs directly:

#### Analytics API:
```powershell
python -c "import requests; r = requests.get('http://localhost:8000/ml-analytics/performance-metrics'); print(f'Status: {r.status_code}'); print(r.json()['summary'] if r.ok else 'Error')"
```
Expected: Status 200 + summary data showing energy savings

#### Heatmap API:
```powershell
python -c "import requests; r = requests.get('http://localhost:8000/ml-heatmap/ims-anomaly'); print(f'Status: {r.status_code}'); print(r.json()['model_info']['name'] if r.ok else 'Error')"
```
Expected: Status 200 + "IMS Kaggle Realistic"

### 6. Data Refresh Test
- [ ] Stay on Analytics page for 30 seconds
- [ ] Charts should auto-refresh (watch the timestamp)
- [ ] Stay on Heat Map page for 30 seconds
- [ ] Heatmap should auto-refresh

## Success Criteria

### All tests pass when:
✅ No console errors (red messages)
✅ Charts display with bright colors
✅ Data shows realistic variance (weekends lower)
✅ API calls go to `localhost:8000` (not hardcoded)
✅ Heat map shows colored grid with anomaly data
✅ Model name shows "IMS Kaggle Realistic"
✅ Pages auto-refresh every 30 seconds

## Common Issues

### Issue: Charts not loading
**Solution**: Check if backend is running on port 8000
```powershell
netstat -ano | findstr :8000
```

### Issue: CORS errors in console
**Solution**: Backend should have CORS enabled. Check `api/app.py` has:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    ...
)
```

### Issue: Environment variable not working
**Check**: Look in Network tab - if you see `http://localhost:8000`, the env var is working correctly

### Issue: Charts are all black/dark
**This should be FIXED** - we updated colors to bright hex codes. If still dark, clear browser cache.

## After Testing

If all tests pass:
1. ✅ Code is ready to commit
2. ✅ Ready for Vercel deployment
3. ✅ Follow steps in `VERCEL_CHECKLIST.md`

If any tests fail:
1. Note which specific test failed
2. Check browser console for error messages
3. Check backend terminal for error logs
4. Report the specific error for debugging
