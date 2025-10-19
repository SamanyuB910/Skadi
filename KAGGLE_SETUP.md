# Kaggle Dataset Setup Guide

This guide helps you download the REAL datacenter datasets from Kaggle.

## Datasets We Use

1. **Data Centre Hot Corridor Temperature Prediction**
   - URL: https://www.kaggle.com/datasets/mbjunior/data-centre-hot-corridor-temperature-prediction
   - Contains: Hot/cold aisle temperatures at 1-5 min cadence
   - Size: ~30 days of real datacenter temperature monitoring

2. **Data Center Cold Source Control Dataset**
   - URL: https://www.kaggle.com/datasets/programmer3/data-center-cold-source-control-dataset
   - Contains: Chiller operations, setpoints, RPM, power consumption
   - Size: Cooling system telemetry with response models

## Quick Setup (5 minutes)

### Step 1: Get Kaggle API Token

1. Go to https://www.kaggle.com/
2. Sign in or create an account (free)
3. Go to Settings: https://www.kaggle.com/settings
4. Scroll to **API** section
5. Click **Create New API Token**
6. Save the downloaded `kaggle.json` file

### Step 2: Install Kaggle API Token

**Windows:**
```powershell
# Create the .kaggle directory
New-Item -Path "$env:USERPROFILE\.kaggle" -ItemType Directory -Force

# Copy kaggle.json to the directory
Copy-Item "Downloads\kaggle.json" "$env:USERPROFILE\.kaggle\kaggle.json"
```

**Linux/Mac:**
```bash
mkdir -p ~/.kaggle
cp ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

### Step 3: Download Datasets

```powershell
# Run the download script
python download_kaggle_datasets.py
```

This will download:
- Hot corridor temperature data → `data/kaggle_real/dc_hot_corridor/`
- Cold source control data → `data/kaggle_real/cold_source_control/`

### Step 4: Train Model on Real Data

```powershell
# Train IMS model with downloaded datasets
python train_ims_with_kaggle_data.py
```

### Step 5: Generate Visualizations

```powershell
# Create heatmaps with real-data-trained model
python generate_visualizations.py
```

## Verify Installation

Check if kaggle.json exists:

```powershell
# Windows
Test-Path "$env:USERPROFILE\.kaggle\kaggle.json"

# Should return: True
```

```bash
# Linux/Mac
ls -la ~/.kaggle/kaggle.json

# Should show the file
```

## Troubleshooting

### Error: "Could not find kaggle.json"

**Solution:** Make sure the file is in the right location:
- Windows: `C:\Users\YOUR_USERNAME\.kaggle\kaggle.json`
- Linux/Mac: `~/.kaggle/kaggle.json`

### Error: "403 Forbidden"

**Solution:** You need to accept the dataset terms:
1. Visit the dataset page on Kaggle
2. Click "Download" button (you don't actually download, just accept terms)
3. Try the script again

### Error: "kaggle command not found"

**Solution:** Kaggle package is already installed in your virtual environment. Use Python:
```powershell
python download_kaggle_datasets.py
```

## Alternative: Manual Download

If you prefer to download manually:

1. **Hot Corridor Dataset:**
   - Go to: https://www.kaggle.com/datasets/mbjunior/data-centre-hot-corridor-temperature-prediction
   - Click "Download" button
   - Extract to: `data/kaggle_real/dc_hot_corridor/`

2. **Cold Source Dataset:**
   - Go to: https://www.kaggle.com/datasets/programmer3/data-center-cold-source-control-dataset
   - Click "Download" button
   - Extract to: `data/kaggle_real/cold_source_control/`

Then run: `python train_ims_with_kaggle_data.py`

## What If I Don't Have Kaggle Access?

No problem! The training script will automatically use high-quality **realistic datacenter simulations** based on published research and real operational patterns. These simulations model:

- Daily/weekly temperature cycles
- Business hours vs off-hours workload
- Thermal events and anomalies
- Cooling system responses
- Realistic power consumption patterns

Run: `python train_ims_with_kaggle_data.py`

The script will detect no real data and use simulations automatically.

## Dataset Information

### Hot Corridor Temperature Dataset

**Features typically include:**
- Timestamp
- Hot aisle temperature (°C)
- Cold aisle temperature (°C)  
- Humidity
- Cooling setpoints

**Cadence:** 1-5 minute intervals

### Cold Source Control Dataset

**Features typically include:**
- Timestamp
- Chiller power (kW)
- Supply temperature (°C)
- Return temperature (°C)
- Fan RPM / Speed (%)
- Pump RPM / Speed (%)
- Setpoint values

**Cadence:** Real-time control data

## Next Steps

After setup:
1. ✅ Download datasets
2. ✅ Train IMS model: `python train_ims_with_kaggle_data.py`
3. ✅ Generate heatmaps: `python generate_visualizations.py`
4. ✅ Run dashboard: `python run_dashboard.py`

## Support

- Kaggle API Docs: https://github.com/Kaggle/kaggle-api
- Kaggle Setup: https://www.kaggle.com/docs/api
- Dataset Issues: Contact dataset authors on Kaggle

---

**Ready?** Follow Step 1 above to get your API token! 🚀
