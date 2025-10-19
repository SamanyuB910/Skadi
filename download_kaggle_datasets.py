"""Download real Kaggle datasets for datacenter training.

This script downloads actual Kaggle datasets:
1. Data centre corridor temperatures (hot/cold aisle)
2. Cooling operations (chillers, air side telemetry)
3. ASHRAE building energy data

Requirements:
- Kaggle API token (~/.kaggle/kaggle.json)
- pip install kaggle
"""
import subprocess
import sys
from pathlib import Path
import pandas as pd
import zipfile
import shutil
from core.logging import logger


class KaggleDatasetDownloader:
    """Download real datacenter datasets from Kaggle."""
    
    def __init__(self, data_dir: str = "data/kaggle_real"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if kaggle is installed
        try:
            import kaggle
            self.kaggle_available = True
            logger.info("✓ Kaggle API is available")
        except ImportError:
            self.kaggle_available = False
            logger.warning("⚠️  Kaggle API not installed. Run: pip install kaggle")
    
    def download_ashrae_building_energy(self) -> Path:
        """Download ASHRAE Great Energy Predictor III dataset.
        
        This dataset contains:
        - Building meter readings (electricity, chilled water, etc.)
        - Weather data
        - Building metadata
        
        Dataset: https://www.kaggle.com/c/ashrae-energy-prediction
        """
        logger.info("Downloading ASHRAE Building Energy dataset...")
        
        output_dir = self.data_dir / "ashrae_building_energy"
        output_dir.mkdir(exist_ok=True)
        
        if (output_dir / "train.csv").exists():
            logger.info("✓ ASHRAE dataset already downloaded")
            return output_dir
        
        if not self.kaggle_available:
            logger.error("Kaggle API not available. Cannot download.")
            return None
        
        try:
            # Download competition data
            logger.info("Downloading from Kaggle (this may take a while)...")
            subprocess.run([
                "kaggle", "competitions", "download",
                "-c", "ashrae-energy-prediction",
                "-p", str(output_dir)
            ], check=True)
            
            # Extract zip files
            for zip_file in output_dir.glob("*.zip"):
                logger.info(f"Extracting {zip_file.name}...")
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(output_dir)
                zip_file.unlink()  # Remove zip after extraction
            
            logger.info(f"✓ Downloaded to {output_dir}")
            return output_dir
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download ASHRAE dataset: {e}")
            logger.info("You may need to accept competition rules at: https://www.kaggle.com/c/ashrae-energy-prediction")
            return None
    
    def download_datacenter_temperature_monitoring(self) -> Path:
        """Download datacenter hot corridor temperature dataset.
        
        Dataset: Data Centre Hot Corridor Temperature Prediction
        https://www.kaggle.com/datasets/mbjunior/data-centre-hot-corridor-temperature-prediction
        """
        logger.info("Downloading datacenter hot corridor temperature dataset...")
        
        dataset_name = "mbjunior/data-centre-hot-corridor-temperature-prediction"
        output_dir = self.data_dir / "dc_hot_corridor"
        output_dir.mkdir(exist_ok=True)
        
        if list(output_dir.glob("*.csv")):
            logger.info("✓ Hot corridor dataset already downloaded")
            return output_dir
        
        try:
            logger.info(f"Downloading: {dataset_name}")
            subprocess.run([
                "kaggle", "datasets", "download",
                "-d", dataset_name,
                "-p", str(output_dir),
                "--unzip"
            ], check=True)
            
            logger.info(f"✓ Downloaded hot corridor temperature data to {output_dir}")
            return output_dir
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Could not download {dataset_name}: {e}")
            logger.info("Make sure you have Kaggle API credentials set up")
            return None
    
    def download_cold_source_control_dataset(self) -> Path:
        """Download cold source control dataset (chiller operations).
        
        Dataset: Data Center Cold Source Control Dataset
        https://www.kaggle.com/datasets/programmer3/data-center-cold-source-control-dataset
        """
        logger.info("Downloading data center cold source control dataset...")
        
        dataset_name = "programmer3/data-center-cold-source-control-dataset"
        output_dir = self.data_dir / "cold_source_control"
        output_dir.mkdir(exist_ok=True)
        
        if list(output_dir.glob("*.csv")):
            logger.info("✓ Cold source control dataset already downloaded")
            return output_dir
        
        try:
            logger.info(f"Downloading: {dataset_name}")
            subprocess.run([
                "kaggle", "datasets", "download",
                "-d", dataset_name,
                "-p", str(output_dir),
                "--unzip"
            ], check=True)
            
            logger.info(f"✓ Downloaded cold source control data to {output_dir}")
            return output_dir
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Could not download {dataset_name}: {e}")
            logger.info("Make sure you have Kaggle API credentials set up")
            return None
    
    def download_ibm_building_energy(self) -> Path:
        """Download IBM Building Energy dataset from Kaggle.
        
        Contains HVAC and cooling system telemetry.
        """
        logger.info("Downloading IBM Building Energy dataset...")
        
        output_dir = self.data_dir / "ibm_building_energy"
        output_dir.mkdir(exist_ok=True)
        
        try:
            subprocess.run([
                "kaggle", "datasets", "download",
                "-d", "claytonmiller/buildingdatagenomeproject2",
                "-p", str(output_dir),
                "--unzip"
            ], check=True)
            
            logger.info(f"✓ Downloaded to {output_dir}")
            return output_dir
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Could not download IBM dataset: {e}")
            return None
    
    def process_ashrae_for_training(self, ashrae_dir: Path) -> pd.DataFrame:
        """Process ASHRAE data into training format.
        
        Focus on chilled water meters (cooling) and extract:
        - Timestamps
        - Cooling load (kW)
        - Temperature patterns
        """
        logger.info("Processing ASHRAE data for training...")
        
        # Load meter readings
        train_file = ashrae_dir / "train.csv"
        if not train_file.exists():
            logger.error(f"Train file not found: {train_file}")
            return None
        
        logger.info("Loading meter readings...")
        df = pd.read_csv(train_file)
        
        # Filter to chilled water meters (meter type 2)
        logger.info("Filtering to chilled water (cooling) meters...")
        cooling_df = df[df['meter'] == 2].copy()
        
        # Load building metadata
        building_file = ashrae_dir / "building_metadata.csv"
        if building_file.exists():
            buildings = pd.read_csv(building_file)
            cooling_df = cooling_df.merge(buildings, on='building_id', how='left')
        
        # Load weather data
        weather_file = ashrae_dir / "weather_train.csv"
        if weather_file.exists():
            weather = pd.read_csv(weather_file)
            weather['timestamp'] = pd.to_datetime(weather['timestamp'])
            cooling_df['timestamp'] = pd.to_datetime(cooling_df['timestamp'])
            cooling_df = pd.merge_asof(
                cooling_df.sort_values('timestamp'),
                weather.sort_values('timestamp'),
                on='timestamp',
                by='site_id',
                direction='nearest'
            )
        
        # Convert to Skadi format
        logger.info("Converting to Skadi format...")
        
        # Sample to manageable size (1 site, 30 days)
        if 'site_id' in cooling_df.columns:
            site_0 = cooling_df[cooling_df['site_id'] == 0].copy()
            # Get first 30 days
            site_0 = site_0.sort_values('timestamp').head(30 * 24 * 4)  # 15-min intervals
        else:
            site_0 = cooling_df.head(30 * 24 * 4)
        
        # Rename columns
        training_df = pd.DataFrame({
            'timestamp': pd.to_datetime(site_0['timestamp']),
            'chiller_kw': site_0['meter_reading'],  # kWh readings
            'outdoor_temp_c': site_0.get('air_temperature', 20),
            'humidity_pct': site_0.get('dew_temperature', 50),
            'wind_speed_ms': site_0.get('wind_speed', 0),
        })
        
        # Derive cooling system parameters
        # Estimate supply/return temps based on load
        training_df['supply_temp_c'] = 7 + (training_df['chiller_kw'] / training_df['chiller_kw'].max()) * 3
        training_df['return_temp_c'] = training_df['supply_temp_c'] + 8 + (training_df['chiller_kw'] / training_df['chiller_kw'].max()) * 5
        training_df['delta_t'] = training_df['return_temp_c'] - training_df['supply_temp_c']
        
        # Estimate RPM from load
        load_pct = training_df['chiller_kw'] / training_df['chiller_kw'].max() * 100
        training_df['fan_rpm_pct'] = 40 + load_pct * 0.5
        training_df['pump_rpm_pct'] = 35 + load_pct * 0.6
        
        logger.info(f"✓ Processed {len(training_df)} samples")
        return training_df


def main():
    """Download and process real Kaggle datasets."""
    print("=" * 70)
    print("KAGGLE DATASET DOWNLOADER FOR SKADI")
    print("=" * 70)
    print()
    print("This script downloads REAL datacenter and building energy datasets")
    print("from Kaggle for training the IMS model.")
    print()
    print("Prerequisites:")
    print("  1. Kaggle account: https://www.kaggle.com/")
    print("  2. Kaggle API token: https://www.kaggle.com/docs/api")
    print("  3. Place kaggle.json in ~/.kaggle/ (or %USERPROFILE%\\.kaggle\\)")
    print("  4. Install: pip install kaggle")
    print()
    
    downloader = KaggleDatasetDownloader()
    
    if not downloader.kaggle_available:
        print("❌ Kaggle API not available!")
        print()
        print("To install:")
        print("  pip install kaggle")
        print()
        print("To setup API token:")
        print("  1. Go to: https://www.kaggle.com/settings")
        print("  2. Click 'Create New API Token'")
        print("  3. Save kaggle.json to ~/.kaggle/ directory")
        print()
        return
    
    # Download datasets
    print("=" * 70)
    print("DOWNLOADING DATASETS")
    print("=" * 70)
    print()
    
    # 1. Hot Corridor Temperature (REQUIRED)
    print("1. Data Centre Hot Corridor Temperature Prediction")
    print("   https://www.kaggle.com/datasets/mbjunior/data-centre-hot-corridor-temperature-prediction")
    print("-" * 70)
    hot_corridor_dir = downloader.download_datacenter_temperature_monitoring()
    print()
    
    # 2. Cold Source Control (REQUIRED)
    print("2. Data Center Cold Source Control Dataset")
    print("   https://www.kaggle.com/datasets/programmer3/data-center-cold-source-control-dataset")
    print("-" * 70)
    cold_source_dir = downloader.download_cold_source_control_dataset()
    print()
    
    # 3. ASHRAE Building Energy (optional, for additional cooling data)
    print("3. ASHRAE Great Energy Predictor III (Optional - Additional Cooling Data)")
    print("-" * 70)
    print("Skipping ASHRAE download (optional dataset, large download)")
    print("Using hot corridor + cold source datasets instead")
    ashrae_dir = None
    print()
    
    # Process downloaded data
    print("=" * 70)
    print("PROCESSING DOWNLOADED DATA")
    print("=" * 70)
    print()
    
    if hot_corridor_dir:
        print(f"✓ Hot corridor data: {hot_corridor_dir}")
        csv_files = list(hot_corridor_dir.glob("*.csv"))
        for f in csv_files:
            print(f"  • {f.name} ({f.stat().st_size / 1024:.1f} KB)")
    
    if cold_source_dir:
        print(f"✓ Cold source control data: {cold_source_dir}")
        csv_files = list(cold_source_dir.glob("*.csv"))
        for f in csv_files:
            print(f"  • {f.name} ({f.stat().st_size / 1024:.1f} KB)")
    
    print()
    print("=" * 70)
    print("DOWNLOAD COMPLETE!")
    print("=" * 70)
    print()
    
    if hot_corridor_dir or cold_source_dir:
        print("✓ Successfully downloaded real Kaggle datasets!")
        print()
        print("Next steps:")
        print("  1. Train model with real data: python train_ims_with_kaggle_data.py")
        print("  2. Generate visualizations: python generate_visualizations.py")
        print()
    else:
        print("⚠️  No datasets were downloaded. Check your Kaggle API setup.")
        print()
        print("Setup instructions:")
        print("  1. Create Kaggle account: https://www.kaggle.com/")
        print("  2. Get API token: https://www.kaggle.com/settings (Create New API Token)")
        print("  3. Save kaggle.json to: %USERPROFILE%\\.kaggle\\kaggle.json")
        print("  4. Install Kaggle CLI: pip install kaggle")
        print()


if __name__ == '__main__':
    main()
