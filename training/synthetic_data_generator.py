"""Synthetic training data generator for Skadi models.

This module creates realistic datacenter telemetry data with:
- Nominal operational windows
- Anomalous patterns (thermal events, overload, under-utilization)
- Temporal correlations and dependencies
- Seasonal and workload patterns
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from core.config import settings
from core.logging import logger


class SyntheticDataGenerator:
    """Generate synthetic datacenter telemetry for training."""
    
    # Rack configuration
    ROWS = ['A', 'B', 'C', 'D', 'E', 'F']
    RACKS_PER_ROW = 12
    
    def __init__(self, seed: int = 42):
        """Initialize generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        np.random.seed(seed)
        self.seed = seed
        
        # Operational profiles
        self.profiles = {
            'nominal': {
                'inlet_c': (21.0, 24.0),
                'outlet_c': (33.0, 38.0),
                'pdu_kw': (6.0, 10.0),
                'tokens_ps': (7000, 10000),
                'latency_p95_ms': (150, 220),
                'queue_depth': (15, 60),
                'fan_rpm_pct': (55, 75),
                'pump_rpm_pct': (50, 65)
            },
            'high_load': {
                'inlet_c': (23.0, 27.0),
                'outlet_c': (38.0, 45.0),
                'pdu_kw': (9.0, 11.5),
                'tokens_ps': (10000, 14000),
                'latency_p95_ms': (200, 280),
                'queue_depth': (60, 120),
                'fan_rpm_pct': (70, 90),
                'pump_rpm_pct': (60, 80)
            },
            'thermal_event': {
                'inlet_c': (26.0, 30.0),
                'outlet_c': (42.0, 52.0),
                'pdu_kw': (10.0, 12.5),
                'tokens_ps': (9000, 12000),
                'latency_p95_ms': (220, 350),
                'queue_depth': (80, 150),
                'fan_rpm_pct': (85, 100),
                'pump_rpm_pct': (75, 90)
            },
            'under_utilized': {
                'inlet_c': (19.0, 22.0),
                'outlet_c': (28.0, 33.0),
                'pdu_kw': (3.0, 6.0),
                'tokens_ps': (2000, 5000),
                'latency_p95_ms': (120, 180),
                'queue_depth': (5, 25),
                'fan_rpm_pct': (45, 60),
                'pump_rpm_pct': (40, 55)
            },
            'overcooled': {
                'inlet_c': (17.0, 20.0),
                'outlet_c': (30.0, 35.0),
                'pdu_kw': (6.5, 9.5),
                'tokens_ps': (6000, 9000),
                'latency_p95_ms': (160, 210),
                'queue_depth': (20, 50),
                'fan_rpm_pct': (75, 95),
                'pump_rpm_pct': (65, 85)
            }
        }
    
    def generate_sample(
        self,
        rack_id: str,
        ts: datetime,
        profile: str = 'nominal',
        noise_level: float = 0.05
    ) -> Dict:
        """Generate one telemetry sample.
        
        Args:
            rack_id: Rack identifier
            ts: Timestamp
            profile: Operational profile name
            noise_level: Noise factor (0-1)
            
        Returns:
            Telemetry sample dictionary
        """
        profile_ranges = self.profiles[profile]
        
        # Sample from ranges with noise
        def sample_range(key):
            low, high = profile_ranges[key]
            base = np.random.uniform(low, high)
            noise = np.random.normal(0, (high - low) * noise_level)
            return base + noise
        
        inlet_c = sample_range('inlet_c')
        outlet_c = max(inlet_c + 8, sample_range('outlet_c'))  # Ensure positive delta
        pdu_kw = sample_range('pdu_kw')
        tokens_ps = sample_range('tokens_ps')
        latency_p95_ms = sample_range('latency_p95_ms')
        queue_depth = int(max(1, sample_range('queue_depth')))
        fan_rpm_pct = np.clip(sample_range('fan_rpm_pct'), 40, 100)
        pump_rpm_pct = np.clip(sample_range('pump_rpm_pct'), 35, 90)
        
        # GPU energy (cumulative-like)
        # Power = pdu_kw * 0.7 (70% GPU, 30% aux)
        # Energy over 5s tick = Power * 5 * 1000 J
        gpu_power_kw = pdu_kw * 0.7
        gpu_energy_j = gpu_power_kw * 5 * 1000  # 5-second tick
        
        return {
            'ts': ts,
            'rack_id': rack_id,
            'inlet_c': round(inlet_c, 2),
            'outlet_c': round(outlet_c, 2),
            'pdu_kw': round(pdu_kw, 2),
            'gpu_energy_j': round(gpu_energy_j, 1),
            'tokens_ps': round(tokens_ps, 1),
            'latency_p95_ms': round(latency_p95_ms, 1),
            'queue_depth': queue_depth,
            'fan_rpm_pct': round(fan_rpm_pct, 1),
            'pump_rpm_pct': round(pump_rpm_pct, 1)
        }
    
    def generate_timeseries(
        self,
        start_ts: datetime,
        duration_hours: int,
        tick_seconds: int = 60,
        rack_ids: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Generate complete time series for training.
        
        Args:
            start_ts: Start timestamp
            duration_hours: Duration in hours
            tick_seconds: Time between samples
            rack_ids: List of rack IDs (defaults to all)
            
        Returns:
            DataFrame with telemetry data
        """
        if rack_ids is None:
            rack_ids = [f"R-{row}-{i:02d}" for row in self.ROWS for i in range(1, self.RACKS_PER_ROW + 1)]
        
        n_ticks = int(duration_hours * 3600 / tick_seconds)
        logger.info(f"Generating {n_ticks} ticks for {len(rack_ids)} racks ({n_ticks * len(rack_ids)} samples)")
        
        samples = []
        
        for tick in range(n_ticks):
            ts = start_ts + timedelta(seconds=tick * tick_seconds)
            hour_of_day = ts.hour
            
            # Determine profile based on time and probabilistic events
            base_profile = self._get_time_based_profile(hour_of_day, tick, n_ticks)
            
            for rack_id in rack_ids:
                # Row-specific modifiers
                row = rack_id.split('-')[1]
                profile = self._adjust_profile_for_row(base_profile, row, tick)
                
                sample = self.generate_sample(rack_id, ts, profile)
                samples.append(sample)
        
        df = pd.DataFrame(samples)
        logger.info(f"Generated dataset shape: {df.shape}")
        
        return df
    
    def _get_time_based_profile(self, hour: int, tick: int, total_ticks: int) -> str:
        """Determine operational profile based on time of day.
        
        Args:
            hour: Hour of day (0-23)
            tick: Current tick number
            total_ticks: Total number of ticks
            
        Returns:
            Profile name
        """
        # Inject thermal events randomly (5% probability)
        if np.random.random() < 0.05:
            return 'thermal_event'
        
        # Inject under-utilization periods (10% probability during off-hours)
        if hour in range(0, 6) and np.random.random() < 0.10:
            return 'under_utilized'
        
        # Inject overcooling events (3% probability)
        if np.random.random() < 0.03:
            return 'overcooled'
        
        # Business hours (9-17): high load
        if hour in range(9, 18):
            if np.random.random() < 0.3:
                return 'high_load'
            else:
                return 'nominal'
        
        # Off-hours: mostly nominal with occasional low load
        else:
            if np.random.random() < 0.2:
                return 'under_utilized'
            else:
                return 'nominal'
    
    def _adjust_profile_for_row(self, base_profile: str, row: str, tick: int) -> str:
        """Adjust profile based on row characteristics.
        
        Args:
            base_profile: Base operational profile
            row: Row identifier (A-F)
            tick: Current tick
            
        Returns:
            Adjusted profile name
        """
        # Row C: occasionally has thermal spikes (matches demo scenario)
        if row == 'C' and base_profile in ['nominal', 'high_load']:
            if np.random.random() < 0.08:  # 8% chance
                return 'thermal_event'
        
        # Row E: prone to overcooling
        if row == 'E' and base_profile == 'nominal':
            if np.random.random() < 0.15:  # 15% chance
                return 'overcooled'
        
        return base_profile
    
    def generate_training_dataset(
        self,
        output_path: str,
        duration_hours: int = 168,  # 1 week
        tick_seconds: int = 60
    ) -> str:
        """Generate complete training dataset and save to CSV.
        
        Args:
            output_path: Path to save CSV
            duration_hours: Duration in hours (default 1 week)
            tick_seconds: Sampling interval
            
        Returns:
            Path to saved file
        """
        logger.info(f"Generating training dataset: {duration_hours} hours, {tick_seconds}s ticks")
        
        # Start 1 week ago
        start_ts = datetime.utcnow() - timedelta(hours=duration_hours)
        
        # Generate data
        df = self.generate_timeseries(start_ts, duration_hours, tick_seconds)
        
        # Add derived features for training
        df['delta_t'] = df['outlet_c'] - df['inlet_c']
        df['gpu_power_kw'] = df['gpu_energy_j'] / (tick_seconds * 1000)
        
        # Save
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        logger.info(f"Training dataset saved: {output_path}")
        logger.info(f"Total samples: {len(df)}")
        
        # Print statistics
        self._print_statistics(df)
        
        return str(output_path)
    
    def _print_statistics(self, df: pd.DataFrame):
        """Print dataset statistics."""
        logger.info("=" * 60)
        logger.info("DATASET STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Time range: {df['ts'].min()} to {df['ts'].max()}")
        logger.info(f"Total samples: {len(df):,}")
        logger.info(f"Unique racks: {df['rack_id'].nunique()}")
        logger.info("")
        logger.info("Metric ranges:")
        for col in ['inlet_c', 'outlet_c', 'delta_t', 'pdu_kw', 'tokens_ps', 'latency_p95_ms']:
            if col in df.columns:
                logger.info(f"  {col:20s}: {df[col].min():8.2f} - {df[col].max():8.2f} (mean: {df[col].mean():8.2f})")
        logger.info("=" * 60)


def generate_all_training_data():
    """Generate all required training datasets."""
    generator = SyntheticDataGenerator(seed=42)
    
    data_dir = Path(settings.training_data_dir)
    data_dir.mkdir(exist_ok=True)
    
    logger.info("Generating synthetic training datasets...")
    
    # 1. Main training dataset (1 week, 1-min resolution)
    main_dataset = generator.generate_training_dataset(
        output_path=data_dir / "training_main.csv",
        duration_hours=168,  # 1 week
        tick_seconds=60
    )
    
    # 2. High-resolution dataset for IMS training (3 days, 30-sec resolution)
    ims_dataset = generator.generate_training_dataset(
        output_path=data_dir / "training_ims.csv",
        duration_hours=72,  # 3 days
        tick_seconds=30
    )
    
    # 3. Validation dataset (1 day, 1-min resolution)
    val_dataset = generator.generate_training_dataset(
        output_path=data_dir / "validation.csv",
        duration_hours=24,
        tick_seconds=60
    )
    
    logger.info("")
    logger.info("✅ All training datasets generated successfully!")
    logger.info(f"   Main training: {main_dataset}")
    logger.info(f"   IMS training: {ims_dataset}")
    logger.info(f"   Validation: {val_dataset}")
    
    return {
        'main': main_dataset,
        'ims': ims_dataset,
        'validation': val_dataset
    }


if __name__ == '__main__':
    # Generate all datasets
    datasets = generate_all_training_data()
