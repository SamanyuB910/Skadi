# Skadi Quick Start Guide

## 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

## 2. Setup Environment

```powershell
# Copy and edit .env
cp .env.example .env
```

## 3. Start Backend

```powershell
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

Server runs at: http://localhost:8000

API docs at: http://localhost:8000/docs

## 4. (Optional) Generate Mock Data

In a separate terminal:

```powershell
python quickstart.py
```

This will generate continuous mock telemetry for 72 racks (6 rows × 12 racks).

## 5. Test Demo Scenarios

### Heat Spike in Row C

```powershell
# Start scenario
curl -X POST http://localhost:8000/demo/scenario `
  -H "Content-Type: application/json" `
  -d '{\"scenario\":\"add_ai_nodes_row_c\",\"action\":\"start\",\"duration_s\":300}'

# Check state
curl http://localhost:8000/state/overview

# Stop scenario
curl -X POST http://localhost:8000/demo/scenario `
  -H "Content-Type: application/json" `
  -d '{\"scenario\":\"add_ai_nodes_row_c\",\"action\":\"stop\"}'
```

### Over-Cooled Row E

```powershell
curl -X POST http://localhost:8000/demo/scenario `
  -H "Content-Type: application/json" `
  -d '{\"scenario\":\"overcooled_row_e\",\"action\":\"start\",\"duration_s\":300}'
```

## 6. Connect Frontend

WebSocket: `ws://localhost:8000/ws/events`

REST API: `http://localhost:8000/`

## 7. Run Tests

```powershell
pytest tests/ -v
```

## Quick API Examples

### Ingest Telemetry
```powershell
curl -X POST http://localhost:8000/telemetry `
  -H "Content-Type: application/json" `
  -d '{\"samples\":[{\"ts\":\"2025-10-18T23:11:00Z\",\"rack_id\":\"R-C-07\",\"inlet_c\":24.8,\"outlet_c\":36.2,\"pdu_kw\":8.6,\"gpu_energy_j\":45250,\"tokens_ps\":9800,\"latency_p95_ms\":180,\"fan_rpm_pct\":62,\"pump_rpm_pct\":55,\"queue_depth\":42}]}'
```

### Get State
```powershell
curl http://localhost:8000/state/overview
```

### Get Heatmap
```powershell
curl "http://localhost:8000/heatmap?type=inlet&ts=now"
```

### Set Mode
```powershell
curl -X POST http://localhost:8000/mode `
  -H "Content-Type: application/json" `
  -d '{\"mode\":\"closed_loop\"}'
```

### Generate Report
```powershell
curl -X POST http://localhost:8000/report/judges
```
