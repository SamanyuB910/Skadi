"""IMS (Inductive Monitoring System) training module."""
import pickle
from datetime import datetime
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import MiniBatchKMeans
from core.config import settings
from core.logging import logger
from core.errors import IMSNotTrainedException


class IMSTrainer:
    """Train IMS model on nominal, efficient operational windows."""
    
    FEATURE_COLUMNS = [
        'inlet_c',
        'outlet_c',
        'delta_t',
        'pdu_kw',
        'gpu_power_kw',
        'tokens_ps',
        'latency_p95_ms',
        'queue_depth',
        'fan_rpm_pct',
        'pump_rpm_pct'
    ]
    
    def __init__(self, n_clusters: int = None):
        """Initialize IMS trainer.
        
        Args:
            n_clusters: Number of k-means clusters (default from config)
        """
        self.n_clusters = n_clusters or settings.ims_kmeans_clusters
        self.scaler = StandardScaler()
        self.kmeans = MiniBatchKMeans(
            n_clusters=self.n_clusters,
            random_state=42,
            batch_size=1024,
            n_init=10
        )
        self.tau_fast = None
        self.tau_persist = None
        self.features = self.FEATURE_COLUMNS.copy()
    
    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare feature matrix from dataframe.
        
        Args:
            df: Dataframe with raw telemetry columns
            
        Returns:
            Feature matrix
        """
        # Calculate derived features
        if 'delta_t' not in df.columns:
            df['delta_t'] = df['outlet_c'] - df['inlet_c']
        
        # GPU power from energy (J/s = W, then to kW)
        if 'gpu_power_kw' not in df.columns and 'gpu_energy_j' in df.columns:
            # Assume energy is cumulative; take diff and divide by time window
            df['gpu_power_kw'] = df['gpu_energy_j'].diff().fillna(0) / 1000.0
        
        # Select features
        X = df[self.features].values
        
        # Handle missing values
        X = np.nan_to_num(X, nan=0.0)
        
        return X
    
    def filter_nominal_windows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter dataframe to nominal, efficient operational windows.
        
        Nominal criteria:
        - Inlet temperature within limits
        - No throttling (latency within SLA)
        - Stable operation (low variance in key metrics)
        
        Args:
            df: Input dataframe
            
        Returns:
            Filtered dataframe with nominal windows
        """
        # Inlet within limits
        mask = df['inlet_c'] <= settings.inlet_max_c
        
        # Latency within SLA
        mask &= df['latency_p95_ms'] <= settings.sla_latency_ms
        
        # Positive delta T (proper cooling)
        if 'delta_t' in df.columns:
            mask &= df['delta_t'] > 0
        else:
            mask &= (df['outlet_c'] - df['inlet_c']) > 0
        
        # Reasonable power draw (not idle, not overloaded)
        mask &= df['pdu_kw'] > 2.0  # Not idle
        mask &= df['pdu_kw'] < settings.rack_kw_cap * 0.95  # Not overloaded
        
        nominal_df = df[mask].copy()
        
        logger.info(f"Filtered {len(nominal_df)} nominal samples from {len(df)} total")
        
        return nominal_df
    
    def train(self, df: pd.DataFrame, skip_nominal_filter: bool = False) -> Dict[str, Any]:
        """Train IMS model on nominal data.
        
        Args:
            df: Training dataframe with telemetry data
            skip_nominal_filter: If True, skip nominal window filtering
            
        Returns:
            Training metrics and metadata
        """
        logger.info(f"Starting IMS training with {len(df)} samples...")
        
        # Filter to nominal windows (or skip if requested)
        if skip_nominal_filter:
            logger.warning("Skipping nominal window filtering - using all data")
            nominal_df = df.copy()
        else:
            nominal_df = self.filter_nominal_windows(df)
        
        if len(nominal_df) < 100:
            raise IMSNotTrainedException(
                f"Insufficient nominal samples: {len(nominal_df)} < 100",
                {"total_samples": len(df), "nominal_samples": len(nominal_df)}
            )
        
        # Prepare features
        X = self.prepare_features(nominal_df)
        
        # Fit scaler
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit k-means
        self.kmeans.fit(X_scaled)
        
        # Compute deviation scores on training data
        deviations = self._compute_deviations(X_scaled)
        
        # Set thresholds
        self.tau_fast = np.percentile(deviations, settings.ims_tau_fast_percentile)
        self.tau_persist = np.percentile(deviations, settings.ims_tau_persist_percentile)
        
        metrics = {
            'training_samples': len(nominal_df),
            'n_clusters': self.n_clusters,
            'tau_fast': float(self.tau_fast),
            'tau_persist': float(self.tau_persist),
            'mean_deviation': float(np.mean(deviations)),
            'median_deviation': float(np.median(deviations)),
            'std_deviation': float(np.std(deviations))
        }
        
        logger.info(f"IMS training complete: {metrics}")
        
        return metrics
    
    def _compute_deviations(self, X_scaled: np.ndarray) -> np.ndarray:
        """Compute deviation scores (min distance to cluster centers).
        
        Args:
            X_scaled: Scaled feature matrix
            
        Returns:
            Array of deviation scores
        """
        # Compute distances to all centers
        distances = self.kmeans.transform(X_scaled)
        
        # Take minimum distance as deviation score
        deviations = np.min(distances, axis=1)
        
        return deviations
    
    def save(self, model_id: str, output_path: str):
        """Save trained model to disk.
        
        Args:
            model_id: Unique model identifier
            output_path: Path to save model artifacts
        """
        model_data = {
            'model_id': model_id,
            'created_at': datetime.utcnow().isoformat(),
            'n_clusters': self.n_clusters,
            'tau_fast': self.tau_fast,
            'tau_persist': self.tau_persist,
            'features': self.features,
            'scaler': self.scaler,
            'kmeans': self.kmeans
        }
        
        with open(output_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"IMS model saved to {output_path}")
    
    @classmethod
    def load(cls, model_path: str) -> 'IMSTrainer':
        """Load trained model from disk.
        
        Args:
            model_path: Path to model artifacts
            
        Returns:
            Loaded IMSTrainer instance
        """
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        trainer = cls(n_clusters=model_data['n_clusters'])
        trainer.scaler = model_data['scaler']
        trainer.kmeans = model_data['kmeans']
        trainer.tau_fast = model_data['tau_fast']
        trainer.tau_persist = model_data['tau_persist']
        trainer.features = model_data['features']
        
        logger.info(f"IMS model loaded from {model_path}")
        
        return trainer
