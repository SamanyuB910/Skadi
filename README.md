# Skadi - AI Datacenter Energy Optimizer

**Backend-only implementation** proving "**Measure → Decide → Act**" for reducing energy-per-prompt in AI server rooms using NASA-inspired technologies.

> ✅ **Trained models ready!** See [QUICKSTART_MODELS.md](QUICKSTART_MODELS.md) and [docs/TRAINING_COMPLETE.md](docs/TRAINING_COMPLETE.md)

## 🎯 Mission

Minimize **J/prompt (Wh/prompt)** while maintaining SLA compliance using:

* **FOSS** (Fiber Optic Sensing System) → Dense temperature telemetry
* **IMS** (Inductive Monitoring System) → Learns nominal efficient behavior, outputs deviation score D(x)
* **MMS** (Meta Monitoring System) → Classifies IMS deviations as Transient vs Persistent to reduce false actions

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Figma)                        │
│              Consumes JSON/WebSocket APIs                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Ingest    │  │     IMS     │  │     MMS     │        │
│  │  Telemetry  │  │  Deviation  │  │   Filter    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                │                 │                │
│         ▼                ▼                 ▼                │
│  ┌──────────────────────────────────────────────┐          │
│  │         Fast Guardrail Loop (5-10s)         │          │
│  │  • Thermal routing                           │          │
│  │  • Admission control                         │          │
│  │  • Pre-cool intent                           │          │
│  └──────────────────────────────────────────────┘          │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────────────────────────────────────┐          │
│  │       Slow Optimizer Loop (1-5 min)         │          │
│  │  • Batch window tuning                       │          │
│  │  • Fan/pump RPM optimization                 │          │
│  │  • Supply temp adjustment                    │          │
│  │  • Traffic rebalancing                       │          │
│  └──────────────────────────────────────────────┘          │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────────────────────────────────────┐          │
│  │    Action Executors (Mock for Demo)         │          │
│  │  • Scheduler (routing/batching)              │          │
│  │  • BMS (setpoint/RPM)                        │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   SQLite/Postgres│
                    │   Time-series DB │
                    └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

* Python 3.11+
* pip or poetry

### Installation

```powershell
# Clone repository
cd c:\VS Code Projects\SkadiHackATL\Skadi

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
```

### Run Locally

```powershell
# Start server
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

Server runs at: `http://localhost:8000`

API docs: `http://localhost:8000/docs`

### Run with Docker

```powershell
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f skadi
```

## 📊 Data & Training

### Public Datasets

Place CSV files in `./data/`:

1. **DC Temperatures**: Kaggle "datacenter temperature" datasets
2. **Cooling Operations**: ASHRAE building data, chiller logs
3. **Workload Traces**: 
   - Google Cluster 2019: https://github.com/google/cluster-data
   - Alibaba GPU traces: https://github.com/alibaba/clusterdata
4. **Sensor Networks**: Intel Berkeley Lab dataset

### Dataset Mixer

Align streams into unified training format:

```powershell
python -m training.dataset_mixer
```

Output columns:
```
ts, rack_id, inlet_c, outlet_c, pdu_kw, chiller_kw, fan_kw, pump_kw,
gpu_energy_j, tokens_ps, latency_p95_ms, queue_depth, fan_rpm_pct, 
pump_rpm_pct, j_per_prompt_wh
```

### Train IMS Model

```powershell
python -m training.train_ims --data ./data/mixed_dataset.csv --n-clusters 8
```

This trains the IMS model on nominal operational windows and computes thresholds:
* `tau_fast` (95th percentile)
* `tau_persist` (98th percentile)

## 🔌 API Reference

### WebSocket

**`GET /ws/events`** - Real-time event stream

```json
{
  "ts": "2025-10-18T23:11:10Z",
  "kpis": {
    "j_per_prompt_wh": 0.52,
    "latency_p95_ms": 178,
    "inlet_compliance_pct": 99.6
  },
  "ims": {
    "deviation": 0.31,
    "mms_state": "transient"
  },
  "last_action": {
    "action": "increase_batch_window",
    "delta": "+30ms",
    "pred_saving_pct": 8.2
  }
}
```

### Telemetry Ingestion

**`POST /telemetry`** - Ingest telemetry (batch allowed)

```json
{
  "samples": [{
    "ts": "2025-10-18T23:11:00Z",
    "rack_id": "R-C-07",
    "inlet_c": 24.8,
    "outlet_c": 36.2,
    "pdu_kw": 8.6,
    "gpu_energy_j": 45250,
    "tokens_ps": 9800,
    "latency_p95_ms": 180,
    "fan_rpm_pct": 62,
    "pump_rpm_pct": 55,
    "queue_depth": 42
  }]
}
```

### State & Monitoring

**`GET /state/overview`** - KPI dashboard

```json
{
  "j_per_prompt_wh": 0.52,
  "latency_p95_ms": 178,
  "ims_deviation": 0.31,
  "mms_state": "transient",
  "inlet_compliance_pct": 99.6,
  "energy_saved_pct": 12.3
}
```

**`GET /heatmap?type=inlet&ts=now`** - Rack temperature grid

**`GET /timeline?from=...&to=...`** - Time series with action annotations

### IMS Training

**`POST /ims/train`** - Train IMS model

```json
{
  "start_ts": "2025-10-10T00:00:00Z",
  "end_ts": "2025-10-17T00:00:00Z",
  "n_clusters": 8
}
```

**`GET /ims/models`** - List trained models

### Optimizer Control

**`POST /optimizer/tick`** - Manual optimizer run

Returns:
```json
{
  "proposals": [...],
  "picked": {
    "action": "increase_batch_window",
    "params": {"delta_ms": 30},
    "pred_saving_pct": 6.0,
    "reason": "..."
  }
}
```

### Actions

**`POST /actions/apply`** - Execute or recommend action

```json
{
  "action": "increase_batch_window",
  "params": {"delta_ms": 30},
  "target": "system",
  "reason": "Improve throughput efficiency",
  "pred_saving_pct": 6.0
}
```

**`GET /actions/log`** - Action audit trail

### Mode Control

**`POST /mode`** - Set operating mode

```json
{"mode": "advisory"}  // or "closed_loop"
```

**`GET /mode`** - Get current mode

### Demo Scenarios

**`POST /demo/scenario`** - Start/stop demo scenarios

```json
{
  "scenario": "add_ai_nodes_row_c",  // or "overcooled_row_e"
  "action": "start",
  "duration_s": 300
}
```

**Scenarios:**
* `add_ai_nodes_row_c`: Heat spike in Row C (adds 2 AI nodes)
* `overcooled_row_e`: Over-cooled Row E (low inlet, high fan RPM)

**`GET /demo/scenarios`** - List active scenarios

### Reports

**`POST /report/judges`** - Generate comprehensive JSON report

Includes:
* KPI summary
* Energy savings attribution
* Action log with predicted vs realized savings
* System performance metrics
* Chart references

## 🧪 Testing

```powershell
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_ims.py -v
pytest tests/test_optimizer.py -v
pytest tests/test_api.py -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

## 🎬 Demo Acceptance Criteria

### Heat Spike Scenario

```powershell
# 1. Start scenario
curl -X POST http://localhost:8000/demo/scenario \
  -H "Content-Type: application/json" \
  -d '{"scenario":"add_ai_nodes_row_c","action":"start","duration_s":300}'

# 2. Observe (via WebSocket or polling /state/overview)
# - IMS deviation D(x) rises
# - MMS state flips to "persistent"
# - Fast loop proposes routing/admission control
# - Slow loop picks safe action (batch +30ms, fan -3%, supply +0.5°C)

# 3. Expected outcomes (within 1-2 optimizer cycles):
# - J/prompt drops by 5-10%
# - P95 latency stays < 250ms (SLA)
# - Inlet compliance ≥ 99%
# - Actions logged with predicted vs realized savings
```

### Over-Cooled Aisle Scenario

```powershell
# 1. Start scenario
curl -X POST http://localhost:8000/demo/scenario \
  -H "Content-Type: application/json" \
  -d '{"scenario":"overcooled_row_e","action":"start","duration_s":300}'

# 2. Observe
# - Row E has low inlet temps, high fan RPM
# - Optimizer detects thermal margin
# - Proposes fan RPM reduction + supply temp increase

# 3. Expected outcomes:
# - Fan RPM drops 3-5%
# - Supply temp increases 0.5-1.0°C
# - J/prompt drops (less cooling energy)
# - Latency unchanged
# - Inlet temps rise slightly but stay within limits
```

## 🛡️ Guardrails & Safety

1. **Global Kill Switch** - Disables all actions
2. **Advisory Mode (Default)** - Logs recommendations without execution
3. **Rate Limiting** - Max 1 setpoint change per device per 120s
4. **SLA Protection** - Reject actions that would violate latency SLA
5. **Thermal Limits** - Enforce inlet temperature < 28°C (configurable)
6. **Auto-Rollback** - Revert if metrics worsen post-action
7. **Audit Trail** - All actions logged with justification

## 📁 Project Structure

```
Skadi/
├── api/                    # FastAPI routes
│   ├── app.py             # Main application
│   ├── ws.py              # WebSocket
│   ├── routes_*.py        # REST endpoints
├── core/                   # Core utilities
│   ├── config.py          # Settings
│   ├── logging.py         # Logging
│   ├── errors.py          # Exceptions
├── storage/                # Database layer
│   ├── models.py          # SQLAlchemy models
│   ├── db.py              # Connection management
│   ├── rollups.py         # Aggregation logic
├── ims/                    # IMS module
│   ├── train.py           # Training
│   ├── score.py           # Scoring
├── mms/                    # MMS module
│   ├── filter.py          # EMA + hysteresis
├── optimizer/              # Optimization logic
│   ├── policies.py        # Action candidates
│   ├── fast_loop.py       # Fast guardrail
│   ├── slow_loop.py       # Strategic optimizer
│   ├── executors/         # Mock executors
├── ingestors/              # Data ingestion
│   ├── mock_generators.py # Mock telemetry
│   ├── foss.py            # FOSS adapter
├── training/               # Training scripts
│   ├── dataset_mixer.py   # Data alignment
│   ├── train_ims.py       # IMS training
├── tests/                  # Test suites
│   ├── test_ims.py
│   ├── test_optimizer.py
│   ├── test_api.py
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── README.md
```

## 🔧 Configuration

Edit `.env` to configure:

```ini
# Database
DATABASE_URL=sqlite:///./skadi.db

# System Limits
SLA_LATENCY_MS=250
INLET_MAX_C=28.0
RACK_KW_CAP=12.0

# IMS/MMS
IMS_TAU_FAST_PERCENTILE=95
IMS_TAU_PERSIST_PERCENTILE=98
MMS_EMA_ALPHA=0.3
MMS_PERSIST_TICKS=6

# Optimizer
FAST_LOOP_INTERVAL_S=10
SLOW_LOOP_INTERVAL_S=120
WRITE_RATE_LIMIT_S=120

# Mode
DEFAULT_MODE=advisory
GLOBAL_KILL_SWITCH=false
```

## 📈 Key Metrics

* **J/prompt (Wh/prompt)**: Total energy divided by prompts served
* **IMS Deviation D(x)**: Distance from nominal cluster centers
* **MMS State**: Transient vs Persistent classification
* **Inlet Compliance %**: Percentage of temps within limit
* **Energy Saved %**: Reduction vs baseline (0.60 Wh/prompt)

## 🤝 Integration with Frontend

Frontend (Figma-designed UI) should:

1. **Connect to WebSocket** at `/ws/events` for real-time updates
2. **Call REST APIs** for:
   - Telemetry submission (if live data available)
   - KPI dashboard (`/state/overview`)
   - Rack heatmaps (`/heatmap`)
   - Timeline charts (`/timeline`)
   - Action logs (`/actions/log`)
   - Mode control (`/mode`)
   - Demo scenarios (`/demo/scenario`)
3. **Display**:
   - Live KPI tiles
   - Rack grid heatmap
   - Time series graphs (J/prompt, latency, IMS deviation)
   - Action stream with annotations
   - Energy savings attribution

## 📝 License

See [LICENSE](LICENSE)

## 🎯 HackATL 2025

This backend demonstrates:
✅ NASA-inspired monitoring (FOSS/IMS/MMS)  
✅ Measure → Decide → Act workflow  
✅ Energy optimization with SLA protection  
✅ Real-time WebSocket streaming  
✅ Comprehensive REST API  
✅ Mock scenarios for demo  
✅ Audit trail and reporting  
✅ Production-ready architecture  

**No frontend code included** - designed to integrate with Figma-built UI via stable JSON/WebSocket APIs.

---

**Built for NASA HackATL 2025** 🚀
