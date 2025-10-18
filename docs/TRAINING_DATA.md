# Training Data Generation

This document explains how to generate synthetic training data for Skadi's IMS/MMS models.

## Overview

The `synthetic_data_generator.py` module creates realistic datacenter telemetry data with:

- **Nominal operational windows** (70% of samples) - healthy, stable operations
- **Anomalous patterns** (30% of samples):
  - Thermal events (5%) - overheating situations
  - High load (15%) - peak demand periods
  - Under-utilization (10%) - low load periods
  - Overcooling (3%) - excessive cooling waste
- **Temporal correlations** - time-of-day patterns (business hours vs off-hours)
- **Spatial correlations** - row-specific characteristics (Row C thermal spikes, Row E overcooling)

## Quick Start

### Generate All Training Datasets (Recommended)

```powershell
# Generate main, IMS, and validation datasets
python generate_training_data.py --all
```

This creates:
- `data/training_main.csv` - 1 week, 1-min resolution (main training set)
- `data/training_ims.csv` - 3 days, 30-sec resolution (IMS-specific)
- `data/validation.csv` - 1 day, 1-min resolution (validation set)

### Generate Custom Dataset

```powershell
# Generate 48 hours of data with 60-second ticks
python generate_training_data.py --output data/custom.csv --duration 48 --tick 60

# High-resolution short dataset (1 hour, 10-second ticks)
python generate_training_data.py --output data/high_res.csv --duration 1 --tick 10 --seed 123
```

## Dataset Structure

Each CSV contains the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `ts` | datetime | Timestamp (UTC) |
| `rack_id` | string | Rack identifier (e.g., "R-C-07") |
| `inlet_c` | float | Inlet air temperature (°C) |
| `outlet_c` | float | Outlet air temperature (°C) |
| `pdu_kw` | float | Power draw (kW) |
| `gpu_energy_j` | float | GPU energy consumption (Joules) |
| `tokens_ps` | float | Inference throughput (tokens/sec) |
| `latency_p95_ms` | float | 95th percentile latency (ms) |
| `queue_depth` | int | Request queue depth |
| `fan_rpm_pct` | float | Cooling fan speed (%) |
| `pump_rpm_pct` | float | Coolant pump speed (%) |
| `delta_t` | float | Temperature delta (outlet - inlet) |
| `gpu_power_kw` | float | GPU power consumption (kW) |

## Operational Profiles

The generator uses 5 operational profiles:

### 1. Nominal (70% base probability)
- **Inlet**: 21-24°C
- **Outlet**: 33-38°C
- **Power**: 6-10 kW
- **Tokens/s**: 7,000-10,000
- **Latency**: 150-220 ms
- **Status**: ✅ Healthy operation within SLA

### 2. High Load (15% during business hours)
- **Inlet**: 23-27°C
- **Outlet**: 38-45°C
- **Power**: 9-11.5 kW
- **Tokens/s**: 10,000-14,000
- **Latency**: 200-280 ms
- **Status**: ⚠️ Elevated but acceptable

### 3. Thermal Event (5% random spikes)
- **Inlet**: 26-30°C ⚠️ Near/above limit
- **Outlet**: 42-52°C
- **Power**: 10-12.5 kW
- **Tokens/s**: 9,000-12,000
- **Latency**: 220-350 ms ⚠️ SLA risk
- **Status**: 🔥 Requires immediate action

### 4. Under-Utilized (10% during off-hours)
- **Inlet**: 19-22°C
- **Outlet**: 28-33°C
- **Power**: 3-6 kW
- **Tokens/s**: 2,000-5,000
- **Latency**: 120-180 ms
- **Status**: 💤 Low load - optimization opportunity

### 5. Overcooled (3% random)
- **Inlet**: 17-20°C ❄️ Too cold
- **Outlet**: 30-35°C
- **Power**: 6.5-9.5 kW
- **Tokens/s**: 6,000-9,000
- **Latency**: 160-210 ms
- **Status**: 💨 Energy waste in cooling

## Temporal Patterns

### Business Hours (9 AM - 5 PM)
- 70% nominal operation
- 30% high load bursts
- 5% thermal events (uniform)

### Off-Hours (6 PM - 8 AM)
- 80% nominal operation
- 20% under-utilization
- 5% thermal events (uniform)

### Random Events (all hours)
- 5% thermal spikes
- 3% overcooling events

## Spatial Patterns

### Row-Specific Characteristics
- **Row A-B**: Standard operation
- **Row C**: 8% thermal event probability (hot spot)
- **Row D**: Standard operation
- **Row E**: 15% overcooling probability (cold aisle)
- **Row F**: Standard operation

## Expected Statistics

For 1 week of data (72 racks × 10,080 minutes):

| Metric | Min | Max | Mean |
|--------|-----|-----|------|
| Inlet Temp | ~17°C | ~30°C | ~22°C |
| Outlet Temp | ~28°C | ~52°C | ~36°C |
| Delta T | ~8°C | ~18°C | ~12°C |
| Power | ~3 kW | ~12.5 kW | ~8 kW |
| Tokens/sec | ~2,000 | ~14,000 | ~8,000 |
| Latency | ~120 ms | ~350 ms | ~200 ms |

## Training IMS Models

After generating data, train IMS models:

```powershell
# Train on IMS-specific dataset (3 days, high resolution)
python -m training.train_ims --data data/training_ims.csv --n-clusters 8

# Train on main dataset (1 week, standard resolution)
python -m training.train_ims --data data/training_main.csv --n-clusters 10 --seed 42
```

## Validation

Verify generated data quality:

```python
import pandas as pd

# Load dataset
df = pd.read_csv('data/training_main.csv')

# Check shape
print(f"Samples: {len(df):,}")
print(f"Racks: {df['rack_id'].nunique()}")
print(f"Duration: {df['ts'].max() - df['ts'].min()}")

# Check for anomalies
thermal_events = df[df['inlet_c'] > 26].shape[0]
overcooled = df[df['inlet_c'] < 20].shape[0]
high_latency = df[df['latency_p95_ms'] > 250].shape[0]

print(f"\nAnomaly distribution:")
print(f"  Thermal events: {thermal_events:,} ({100*thermal_events/len(df):.1f}%)")
print(f"  Overcooled: {overcooled:,} ({100*overcooled/len(df):.1f}%)")
print(f"  High latency: {high_latency:,} ({100*high_latency/len(df):.1f}%)")

# Visualize
df.groupby('rack_id')['inlet_c'].mean().hist(bins=20)
```

## API Integration

Load generated data into Skadi backend:

```python
import pandas as pd
import httpx
import asyncio

async def load_training_data():
    df = pd.read_csv('data/training_main.csv')
    
    # Batch upload
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(0, len(df), 100):
            batch = df.iloc[i:i+100].to_dict('records')
            resp = await client.post(
                'http://localhost:8000/telemetry/batch',
                json={'samples': batch}
            )
            print(f"Batch {i//100}: {resp.status_code}")

asyncio.run(load_training_data())
```

## Troubleshooting

### Issue: Dataset too large
**Solution**: Reduce duration or increase tick interval
```powershell
python generate_training_data.py --duration 24 --tick 300  # 24 hours, 5-min ticks
```

### Issue: Not enough anomalies
**Solution**: Generate longer duration or multiple datasets with different seeds
```powershell
python generate_training_data.py --duration 336 --seed 42  # 2 weeks
```

### Issue: Need reproducibility
**Solution**: Always use the same seed
```powershell
python generate_training_data.py --seed 42 --all
```

## Next Steps

1. ✅ Generate training data: `python generate_training_data.py --all`
2. ✅ Review dataset: `pandas.read_csv('data/training_ims.csv')`
3. ✅ Train IMS: `python -m training.train_ims --data data/training_ims.csv`
4. ✅ Validate model: Check `artifacts/` for model files
5. ✅ Start backend: `uvicorn api.app:app --reload`
6. ✅ Test live scoring: Send telemetry via API

## Advanced Usage

### Custom Profile Distributions

Edit `synthetic_data_generator.py` to adjust profile probabilities:

```python
# Increase thermal event probability
if np.random.random() < 0.10:  # Changed from 0.05
    return 'thermal_event'
```

### Add New Profiles

Define custom operational profiles:

```python
self.profiles['custom_profile'] = {
    'inlet_c': (20.0, 25.0),
    'outlet_c': (35.0, 40.0),
    # ... other ranges
}
```

### Multi-Site Generation

Generate data for different datacenters:

```python
# Site A: Cold climate
generator_a = SyntheticDataGenerator(seed=42)
# Adjust base temperatures in profiles

# Site B: Hot climate  
generator_b = SyntheticDataGenerator(seed=43)
# Higher base temperatures
```

---

**Ready to train?** Run `python generate_training_data.py --all` to get started! 🚀
