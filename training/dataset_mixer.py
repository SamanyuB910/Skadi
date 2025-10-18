"""Dataset mixer for aligning and preprocessing training data."""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from core.config import settings
from core.logging import logger


class DatasetMixer:
    """Mix and align multiple data sources for training."""
    
    def __init__(self, output_resolution_s: int = 60):
        """Initialize dataset mixer.
        
        Args:
            output_resolution_s: Output time resolution in seconds
        """
        self.resolution_s = output_resolution_s
    
    def load_dc_temps(self, filepath: str) -> pd.DataFrame:
        """Load datacenter temperature traces.
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            DataFrame with columns: ts, rack_id, inlet_c, outlet_c
        """
        logger.info(f"Loading DC temps from {filepath}")
        
        # Placeholder for actual loading
        # Real implementation would load from Kaggle/public dataset
        # Example columns: timestamp, rack_id, sensor_type, temperature_c
        
        df = pd.read_csv(filepath, parse_dates=['ts'])
        return df
    
    def load_cooling_ops(self, filepath: str) -> pd.DataFrame:
        """Load cooling operations data.
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            DataFrame with cooling metrics
        """
        logger.info(f"Loading cooling ops from {filepath}")
        df = pd.read_csv(filepath, parse_dates=['ts'])
        return df
    
    def load_workload_traces(self, filepath: str) -> pd.DataFrame:
        """Load workload traces (Google/Alibaba cluster data).
        
        Args:
            filepath: Path to trace file
            
        Returns:
            DataFrame with workload metrics
        """
        logger.info(f"Loading workload traces from {filepath}")
        df = pd.read_csv(filepath, parse_dates=['ts'])
        return df
    
    def align_and_mix(
        self,
        dc_temps: pd.DataFrame,
        cooling_ops: Optional[pd.DataFrame] = None,
        workload_traces: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Align multiple streams into unified frame.
        
        Args:
            dc_temps: Temperature data
            cooling_ops: Optional cooling operations data
            workload_traces: Optional workload data
            
        Returns:
            Unified DataFrame with all features
        """
        logger.info("Aligning and mixing datasets...")
        
        # Resample to target resolution
        dc_temps['ts'] = pd.to_datetime(dc_temps['ts'])
        dc_temps = dc_temps.set_index('ts')
        
        # Group by rack and resample
        resampled_frames = []
        for rack_id, group in dc_temps.groupby('rack_id'):
            resampled = group.resample(f'{self.resolution_s}s').mean()
            resampled['rack_id'] = rack_id
            resampled_frames.append(resampled)
        
        mixed = pd.concat(resampled_frames).reset_index()
        
        # Add cooling ops if available
        if cooling_ops is not None:
            cooling_ops['ts'] = pd.to_datetime(cooling_ops['ts'])
            cooling_ops = cooling_ops.set_index('ts').resample(f'{self.resolution_s}s').mean().reset_index()
            mixed = mixed.merge(cooling_ops, on='ts', how='left')
        
        # Add workload if available
        if workload_traces is not None:
            workload_traces['ts'] = pd.to_datetime(workload_traces['ts'])
            workload_traces = workload_traces.set_index('ts').resample(f'{self.resolution_s}s').sum().reset_index()
            mixed = mixed.merge(workload_traces, on='ts', how='left')
        
        # Fill missing values
        mixed = mixed.fillna(method='ffill').fillna(method='bfill')
        
        logger.info(f"Mixed dataset shape: {mixed.shape}")
        return mixed
    
    def compute_j_per_prompt(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute J/prompt (energy per prompt) over rolling windows.
        
        Args:
            df: Input dataframe with energy and token metrics
            
        Returns:
            DataFrame with j_per_prompt_wh column added
        """
        logger.info("Computing J/prompt...")
        
        # Ensure required columns exist
        required = ['gpu_energy_j', 'tokens_ps', 'pdu_kw']
        missing = [c for c in required if c not in df.columns]
        if missing:
            logger.warning(f"Missing columns for J/prompt: {missing}. Using defaults.")
            if 'gpu_energy_j' not in df.columns:
                df['gpu_energy_j'] = 40000  # Default
            if 'tokens_ps' not in df.columns:
                df['tokens_ps'] = 8000
            if 'pdu_kw' not in df.columns:
                df['pdu_kw'] = 8.0
        
        # Calculate energy components
        # GPU energy (J -> Wh)
        df['gpu_energy_wh'] = df['gpu_energy_j'] / 3600.0
        
        # Auxiliary energy (fan/pump/chiller ~30% of PDU)
        df['aux_kw'] = df['pdu_kw'] * 0.3
        window_duration_h = self.resolution_s / 3600.0
        df['aux_energy_wh'] = df['aux_kw'] * window_duration_h * 1000
        
        # Total energy
        df['total_energy_wh'] = df['gpu_energy_wh'] + df['aux_energy_wh']
        
        # Prompts (tokens / avg_tokens_per_prompt)
        avg_tokens_per_prompt = 100
        df['prompts'] = (df['tokens_ps'] * self.resolution_s) / avg_tokens_per_prompt
        df['prompts'] = df['prompts'].clip(lower=1)  # Avoid division by zero
        
        # J/prompt
        df['j_per_prompt_wh'] = df['total_energy_wh'] / df['prompts']
        
        logger.info(f"J/prompt range: {df['j_per_prompt_wh'].min():.3f} - {df['j_per_prompt_wh'].max():.3f} Wh")
        
        return df
    
    def export(self, df: pd.DataFrame, output_path: str):
        """Export mixed dataset to CSV.
        
        Args:
            df: Mixed dataframe
            output_path: Output file path
        """
        df.to_csv(output_path, index=False)
        logger.info(f"Exported mixed dataset to {output_path}")


# Placeholder function to document data sources
def download_public_datasets():
    """Download or document public dataset sources.
    
    Datasets needed:
    1. DC corridor temperatures: Search Kaggle for "datacenter temperature"
       - Example: https://www.kaggle.com/datasets (search datacenter/server room temps)
    
    2. Cooling operations: Industrial HVAC/chiller datasets
       - ASHRAE datasets, building management system logs
    
    3. Workload traces:
       - Google Cluster 2019: https://github.com/google/cluster-data
       - Alibaba Cluster Trace: https://github.com/alibaba/clusterdata
    
    4. Indoor sensor networks:
       - Intel Berkeley Lab: http://db.csail.mit.edu/labdata/labdata.html
    
    Place downloaded CSVs in ./data/ directory with structure:
    - data/dc_temps.csv
    - data/cooling_ops.csv
    - data/workload_traces.csv
    """
    data_dir = Path(settings.training_data_dir)
    data_dir.mkdir(exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("PUBLIC DATASET SOURCES")
    logger.info("=" * 60)
    logger.info("1. DC Temperatures: Kaggle 'datacenter temperature' datasets")
    logger.info("2. Cooling Ops: ASHRAE building data, chiller logs")
    logger.info("3. Workload Traces: Google/Alibaba cluster traces (GitHub)")
    logger.info("4. Sensor Networks: Intel Berkeley Lab dataset")
    logger.info("=" * 60)
    logger.info(f"Place CSV files in: {data_dir.absolute()}")
    logger.info("=" * 60)
