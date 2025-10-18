# Quick Start: Using Trained Models

## ⚡ Fast Path to Running System

### 1. Start the Backend (30 seconds)

```powershell
# Navigate to project
cd "c:\VS Code Projects\SkadiHackATL\Skadi"

# Start FastAPI server
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

**What happens**: Backend loads `ims_20251018_131449.pkl` automatically and starts all background loops.

### 2. Verify System is Running (10 seconds)

Open browser to: **http://localhost:8000/docs**

Try these endpoints:
- `GET /health` - Should return `{"status": "healthy"}`
- `GET /ims/models` - Should show loaded IMS model
- `GET /state/overview` - Should show system KPIs

### 3. Send Test Data (20 seconds)

In another PowerShell terminal:

```powershell
# Generate 5 minutes of live data
python demo_generator.py --duration 5
```

**What happens**: 
- Telemetry posted to `/telemetry/batch` every second
- IMS scores computed in background
- MMS classifies deviations
- Optimizer evaluates actions
- WebSocket streams events

### 4. Watch Real-Time Events (optional)

In browser console at **http://localhost:8000/docs**:

1. Expand `GET /ws/events` WebSocket endpoint
2. Click "Try it out" → "Execute"
3. Watch live stream of telemetry, IMS scores, and actions

### 5. Trigger Demo Scenario (30 seconds)

```python
import httpx

# Cause heat spike in Row C
httpx.post("http://localhost:8000/demo/scenario", json={
    "scenario": "heat_spike",
    "duration_minutes": 2
})

# Watch optimizer respond
actions = httpx.get("http://localhost:8000/actions/log?limit=10")
for action in actions.json()['actions']:
    print(f"{action['ts']}: {action['action_type']} - {action['reason']}")
```

## 🎯 Key Endpoints

### Telemetry Ingestion
```python
POST /telemetry/batch
{
  "samples": [
    {
      "ts": "2025-10-18T13:00:00Z",
      "rack_id": "R-C-07",
      "inlet_c": 24.5,
      "outlet_c": 38.2,
      "pdu_kw": 9.1,
      "gpu_energy_j": 31850,
      "tokens_ps": 8500,
      "latency_p95_ms": 195,
      "queue_depth": 45,
      "fan_rpm_pct": 68,
      "pump_rpm_pct": 58
    }
  ]
}
```

### System State
```python
GET /state/overview
# Returns: current temps, power, latency, IMS scores, optimizer status

GET /heatmap
# Returns: rack grid with current metrics

GET /timeline?metric=inlet_c&minutes=30
# Returns: time series data
```

### IMS Model
```python
GET /ims/models
# Returns: loaded model info (model_id, thresholds, training stats)

GET /ims/scores?limit=20
# Returns: recent deviation scores

POST /ims/train
{
  "n_clusters": 8,
  "data_source": "database",
  "window_hours": 24
}
# Trains new model from recent data
```

### Optimizer
```python
GET /actions/log?limit=20
# Returns: recent actions taken

POST /actions/apply
{
  "action_type": "fan_rpm",
  "params": {"delta_pct": -5.0},
  "reason": "Manual test"
}
# Manually trigger action

POST /optimizer/tick
# Force immediate optimizer evaluation
```

### Demo Scenarios
```python
POST /demo/scenario
{
  "scenario": "heat_spike",  # or "overcooled"
  "duration_minutes": 3
}
# Injects anomaly pattern

GET /demo/status
# Check active scenario
```

### Reports
```python
GET /report/judges
# Comprehensive JSON report with:
# - System state
# - Anomaly timeline
# - Actions taken
# - Model performance
```

## 📊 Expected Behavior

### Nominal Operation
- **D(x)**: 1.2 - 2.0 (below τ_fast)
- **MMS**: Transient classification
- **Optimizer**: No actions needed
- **Metrics**: inlet < 24°C, latency < 200ms

### Thermal Event
- **D(x)**: 2.3 - 3.5 (above τ_fast)
- **MMS**: Persistent after 6 ticks (~30s)
- **Optimizer**: Proposes cooling actions
  - Increase fan speed +5%
  - Reduce supply temp -1°C
  - Shift traffic away from hot rack
- **Metrics**: inlet > 26°C, latency > 250ms

### Overcooled
- **D(x)**: 2.0 - 2.8 (above τ_fast)
- **MMS**: Persistent classification
- **Optimizer**: Proposes efficiency actions
  - Reduce fan speed -5%
  - Increase supply temp +1°C
- **Metrics**: inlet < 20°C, excessive fan RPM

## 🔍 Monitoring Commands

### Check Model Status
```powershell
# List models
dir artifacts

# Check latest model
python -c "from ims.train import IMSTrainer; m = IMSTrainer.load('artifacts/ims_20251018_131449.pkl'); print(f'Clusters: {m.n_clusters}, tau_fast: {m.tau_fast:.3f}')"
```

### Watch Logs
```powershell
# Backend will log:
# - Telemetry received
# - IMS scores computed
# - MMS state changes
# - Optimizer proposals
# - Actions executed
```

### Query Database
```python
import asyncio
from sqlalchemy import select
from storage.db import get_session
from storage.models import IMSScore, OptimizerAction

async def check_activity():
    async with get_session() as session:
        # Recent IMS scores
        scores = await session.execute(
            select(IMSScore).order_by(IMSScore.ts.desc()).limit(10)
        )
        for score in scores.scalars():
            print(f"{score.rack_id}: D(x)={score.deviation:.3f}, level={score.level}")
        
        # Recent actions
        actions = await session.execute(
            select(OptimizerAction).order_by(OptimizerAction.ts.desc()).limit(5)
        )
        for action in actions.scalars():
            print(f"{action.ts}: {action.action_type} - {action.reason}")

asyncio.run(check_activity())
```

## 🚨 Troubleshooting

### Backend won't start
```powershell
# Check if port is in use
netstat -ano | findstr :8000

# Kill process if needed
taskkill /PID <pid> /F

# Try different port
uvicorn api.app:app --host 0.0.0.0 --port 8001
```

### No IMS scores appearing
```python
# Check if model loaded
import httpx
resp = httpx.get("http://localhost:8000/ims/models")
print(resp.json())

# If empty, model may not be loading
# Check artifacts/ directory exists and has .pkl file
```

### Optimizer not proposing actions
- **Check**: Is IMS model loaded? (`GET /ims/models`)
- **Check**: Are deviation scores above thresholds? (`GET /ims/scores`)
- **Check**: Is MMS detecting persistence? (Look for D(x) > 2.19 for 6+ ticks)
- **Check**: Background loop running? (Should see logs every 10s)

### Demo scenario not working
```python
# Check scenario status
httpx.get("http://localhost:8000/demo/status")

# Clear scenario
httpx.delete("http://localhost:8000/demo/scenario")

# Try again
httpx.post("http://localhost:8000/demo/scenario", json={
    "scenario": "heat_spike",
    "duration_minutes": 2
})
```

## 📚 Documentation References

- **Architecture**: `README.md`
- **Training Data**: `docs/TRAINING_DATA.md`
- **Training Complete**: `docs/TRAINING_COMPLETE.md`
- **Full Setup**: `QUICKSTART.md`
- **Implementation**: `IMPLEMENTATION.md`

## 🎓 Understanding the Output

### IMS Deviation Score (D(x))
- **Range**: 0.0 - 10.0+ (typical: 0.5 - 4.0)
- **Interpretation**:
  - `< 2.19`: Nominal (green)
  - `2.19 - 2.47`: Warning (yellow, fast loop triggers)
  - `> 2.47`: Critical (red, persistent anomaly)

### MMS State
- **Transient**: Deviation not sustained (< 6 ticks)
- **Persistent**: Sustained anomaly (≥ 6 ticks at 30s intervals = 3 minutes)

### Optimizer Actions
- **Guardrail**: Immediate safety response (< 10s)
- **Strategic**: Longer-term optimization (1-5 min)
- **Types**: fan_rpm, pump_rpm, supply_temp, batch_window, traffic_shift, pause_jobs

---

**Ready to test the full system!** 🎉

Start with: `uvicorn api.app:app --reload` and explore the API at **http://localhost:8000/docs**
