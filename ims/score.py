"""IMS scoring module for real-time deviation detection."""
from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd
from core.logging import logger
from core.errors import IMSNotTrainedException
from ims.train import IMSTrainer


class IMSScorer:
    """Score telemetry data for deviations from nominal behavior."""
    
    def __init__(self, trainer: IMSTrainer):
        """Initialize scorer with trained model.
        
        Args:
            trainer: Trained IMSTrainer instance
        """
        if trainer.tau_fast is None or trainer.tau_persist is None:
            raise IMSNotTrainedException("IMS model has not been trained")
        
        self.trainer = trainer
    
    def score_sample(self, sample: Dict[str, float]) -> float:
        """Score a single telemetry sample.
        
        Args:
            sample: Dictionary with telemetry values
            
        Returns:
            Deviation score D(x)
        """
        # Convert to dataframe
        df = pd.DataFrame([sample])
        
        # Prepare features
        X = self.trainer.prepare_features(df)
        
        # Scale
        X_scaled = self.trainer.scaler.transform(X)
        
        # Compute deviation
        distances = self.trainer.kmeans.transform(X_scaled)
        deviation = float(np.min(distances, axis=1)[0])
        
        return deviation
    
    def score_batch(self, samples: List[Dict[str, float]]) -> np.ndarray:
        """Score multiple telemetry samples.
        
        Args:
            samples: List of telemetry dictionaries
            
        Returns:
            Array of deviation scores
        """
        if not samples:
            return np.array([])
        
        # Convert to dataframe
        df = pd.DataFrame(samples)
        
        # Prepare features
        X = self.trainer.prepare_features(df)
        
        # Scale
        X_scaled = self.trainer.scaler.transform(X)
        
        # Compute deviations
        distances = self.trainer.kmeans.transform(X_scaled)
        deviations = np.min(distances, axis=1)
        
        return deviations
    
    def classify_deviation(self, deviation: float) -> str:
        """Classify deviation level.
        
        Args:
            deviation: Deviation score
            
        Returns:
            Classification: 'nominal', 'warning', or 'critical'
        """
        if deviation < self.trainer.tau_fast:
            return 'nominal'
        elif deviation < self.trainer.tau_persist:
            return 'warning'
        else:
            return 'critical'
    
    def get_thresholds(self) -> Dict[str, float]:
        """Get current threshold values.
        
        Returns:
            Dictionary with tau_fast and tau_persist
        """
        return {
            'tau_fast': self.trainer.tau_fast,
            'tau_persist': self.trainer.tau_persist
        }
