"""ML-based heatmap data endpoint for IMS anomaly detection."""
from typing import Dict, Any, List
import pickle
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
from core.logging import logger
from ims.train import IMSTrainer
from ims.score import IMSScorer
from ingestors.kaggle_datasets import KaggleDatasetManager


router = APIRouter()


# Global model cache
_model_cache = {
    'scorer': None,
    'model_path': None,
    'loaded_at': None
}


def load_latest_model() -> IMSScorer:
    """Load the latest trained IMS model."""
    artifacts_dir = os.path.join(os.path.dirname(__file__), '..', 'artifacts')
    
    if not os.path.exists(artifacts_dir):
        logger.warning("No artifacts directory found - using synthetic fallback")
        return None
    
    # Find latest model file
    model_files = [f for f in os.listdir(artifacts_dir) if f.endswith('.pkl')]
    if not model_files:
        logger.warning("No trained IMS models available - using synthetic fallback")
        return None
    
    # Sort by modification time (most recent first)
    model_files.sort(key=lambda f: os.path.getmtime(os.path.join(artifacts_dir, f)), reverse=True)
    latest_model = os.path.join(artifacts_dir, model_files[0])
    
    # Check cache
    if (_model_cache['scorer'] is not None and 
        _model_cache['model_path'] == latest_model):
        logger.debug(f"Using cached model: {model_files[0]}")
        return _model_cache['scorer']
    
    # Load model using IMSTrainer's load method
    logger.info(f"Loading IMS model: {model_files[0]}")
    trainer = IMSTrainer.load(latest_model)
    scorer = IMSScorer(trainer)
    
    # Update cache
    _model_cache['scorer'] = scorer
    _model_cache['model_path'] = latest_model
    _model_cache['loaded_at'] = datetime.now()
    
    logger.info(f"Model loaded - τ_fast={trainer.tau_fast:.3f}, τ_persist={trainer.tau_persist:.3f}")
    
    return scorer


def generate_rack_grid_data(scorer: IMSScorer) -> List[Dict[str, Any]]:
    """Generate telemetry data for 8x12 rack grid.
    
    Uses realistic datacenter patterns from KaggleDatasetManager.
    """
    # Generate realistic datacenter data using the same method as training
    kaggle_mgr = KaggleDatasetManager()
    df = kaggle_mgr.prepare_ims_training_data()
    
    # Sample 96 records (one per rack in 8x12 grid)
    if len(df) > 96:
        df = df.sample(n=96, random_state=None).reset_index(drop=True)
    
    # Score each sample
    racks = []
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    cols = list(range(1, 13))
    
    for idx, (row, col) in enumerate([(r, c) for r in rows for c in cols]):
        if idx >= len(df):
            break
        
        sample_data = df.iloc[idx]
        
        # Create sample dictionary for scoring
        sample = {
            'inlet_c': sample_data['inlet_c'],
            'outlet_c': sample_data['outlet_c'],
            'delta_t': sample_data['delta_t'],
            'pdu_kw': sample_data['pdu_kw'],
            'tokens_ps': sample_data['tokens_ps'],
            'latency_p95_ms': sample_data['latency_p95_ms'],
            'queue_depth': sample_data['queue_depth'],
            'fan_rpm_pct': sample_data['fan_rpm_pct'],
            'pump_rpm_pct': sample_data['pump_rpm_pct']
        }
        
        # Score the sample
        deviation = scorer.score_sample(sample)
        status = scorer.classify_deviation(deviation)
        
        # Helper function to safely convert floats and handle NaN/Inf
        def safe_float(value, decimals=1, default=0.0):
            try:
                f = float(value)
                if np.isnan(f) or np.isinf(f):
                    return default
                return round(f, decimals)
            except (ValueError, TypeError):
                return default
        
        rack = {
            'id': f'{row}{col}',
            'row': rows.index(row),
            'col': col - 1,
            'temp': safe_float(sample_data['inlet_c'], 1, 23.0),
            'deviation': safe_float(deviation, 3, 0.0),
            'status': status,
            'load': safe_float(sample_data['pdu_kw'] / 12.0 * 100, 0, 50.0),  # Convert kW to % of 12kW max
            'metrics': {
                'inlet_c': safe_float(sample_data['inlet_c'], 1, 23.0),
                'outlet_c': safe_float(sample_data['outlet_c'], 1, 35.0),
                'delta_t': safe_float(sample_data['delta_t'], 1, 12.0),
                'pdu_kw': safe_float(sample_data['pdu_kw'], 2, 6.0),
                'tokens_ps': safe_float(sample_data['tokens_ps'], 0, 1000.0),
                'latency_p95_ms': safe_float(sample_data['latency_p95_ms'], 1, 50.0),
                'queue_depth': safe_float(sample_data['queue_depth'], 1, 5.0),
                'fan_rpm_pct': safe_float(sample_data['fan_rpm_pct'], 1, 60.0),
                'pump_rpm_pct': safe_float(sample_data['pump_rpm_pct'], 1, 55.0)
            }
        }
        
        racks.append(rack)
    
    return racks


async def get_synthetic_heatmap() -> "HeatmapResponse":
    """Generate synthetic heatmap data when no model is available."""
    import random
    
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    cols = list(range(1, 13))
    
    racks = []
    for row_idx, row in enumerate(rows):
        for col_idx, col in enumerate(cols, start=0):
            # Generate realistic synthetic data
            temp = round(random.uniform(20.0, 28.0), 1)
            power = round(random.uniform(180.0, 280.0), 1)
            inlet_temp = round(random.uniform(18.0, 24.0), 1)
            outlet_temp = round(random.uniform(25.0, 32.0), 1)
            delta_t = round(outlet_temp - inlet_temp, 1)
            
            # Synthetic deviation score
            deviation = round(random.uniform(1.0, 4.5), 3)
            
            # Determine status based on deviation
            if deviation >= 3.0:
                status = 'critical'
                color = '#dc2626'
            elif deviation >= 2.5:
                status = 'warning'
                color = '#f59e0b'
            else:
                status = 'nominal'
                color = '#10b981'
            
            racks.append({
                'id': f"{row}{col}",
                'row': row_idx,  # Numeric index 0-7
                'col': col_idx,  # Numeric index 0-11
                'temp': temp,
                'power': power,
                'inlet_temp': inlet_temp,
                'outlet_temp': outlet_temp,
                'delta_t': delta_t,
                'deviation': deviation,
                'status': status,
                'color': color,
                'load': round(power / 280.0 * 100, 0)  # % of max power
            })
    
    # Calculate stats
    deviations = [r['deviation'] for r in racks]
    temps = [r['temp'] for r in racks]
    
    status_counts = {
        'nominal': len([r for r in racks if r['status'] == 'nominal']),
        'warning': len([r for r in racks if r['status'] == 'warning']),
        'critical': len([r for r in racks if r['status'] == 'critical'])
    }
    
    stats = {
        'avg_temp': round(float(np.mean(temps)), 1),
        'min_temp': round(float(np.min(temps)), 1),
        'max_temp': round(float(np.max(temps)), 1),
        'avg_deviation': round(float(np.mean(deviations)), 3),
        'min_deviation': round(float(np.min(deviations)), 3),
        'max_deviation': round(float(np.max(deviations)), 3),
        'hotspots': status_counts['critical'] + status_counts['warning'],
        'coolzones': status_counts['nominal'],
        'total_racks': len(racks),
        'status_distribution': status_counts,
        'tau_fast_adjusted': 2.5,
        'tau_persist_adjusted': 3.0
    }
    
    model_info = {
        'model_name': 'IMS Synthetic Fallback',
        'loaded_at': datetime.now().isoformat(),
        'tau_fast': 2.376,
        'tau_persist': 2.667,
        'features': ['inlet_temp', 'outlet_temp', 'delta_t', 'power_draw'],
        'n_clusters': 3
    }
    
    return HeatmapResponse(
        timestamp=datetime.now().isoformat(),
        model_info=model_info,
        racks=racks,
        stats=stats,
        thresholds={
            'tau_fast': 2.376,
            'tau_persist': 2.667,
            'tau_fast_adjusted': 2.5,
            'tau_persist_adjusted': 3.0
        }
    )


class HeatmapResponse(BaseModel):
    """Heatmap API response model."""
    timestamp: str
    model_info: Dict[str, Any]
    racks: List[Dict[str, Any]]
    stats: Dict[str, Any]
    thresholds: Dict[str, float]


@router.get("/ims-anomaly", response_model=HeatmapResponse)
async def get_ims_anomaly_heatmap() -> HeatmapResponse:
    """Get ML-based anomaly heatmap data.
    
    Returns:
        Heatmap data with IMS deviation scores for each rack in 8x12 grid
    """
    try:
        # Load model (returns None if not available)
        scorer = load_latest_model()
        
        if scorer is None:
            # Use synthetic fallback when no model is available
            return await get_synthetic_heatmap()
        
        # Generate rack data
        racks = generate_rack_grid_data(scorer)
        
        # Calculate statistics with safe handling
        deviations = [r['deviation'] for r in racks if not (np.isnan(r['deviation']) or np.isinf(r['deviation']))]
        temps = [r['temp'] for r in racks if not (np.isnan(r['temp']) or np.isinf(r['temp']))]
        
        # Count status types
        status_counts = {
            'nominal': len([r for r in racks if r['status'] == 'nominal']),
            'warning': len([r for r in racks if r['status'] == 'warning']),
            'critical': len([r for r in racks if r['status'] == 'critical'])
        }
        
        # Get thresholds
        thresholds = scorer.get_thresholds()
        
        # Adaptive thresholds based on actual distribution (with safe defaults)
        tau_fast_adjusted = float(np.percentile(deviations, 70)) if len(deviations) > 0 else 2.5
        tau_persist_adjusted = float(np.percentile(deviations, 90)) if len(deviations) > 0 else 3.0
        
        stats = {
            'avg_temp': round(float(np.mean(temps)), 1) if len(temps) > 0 else 23.0,
            'min_temp': round(float(np.min(temps)), 1) if len(temps) > 0 else 20.0,
            'max_temp': round(float(np.max(temps)), 1) if len(temps) > 0 else 26.0,
            'avg_deviation': round(float(np.mean(deviations)), 3) if len(deviations) > 0 else 2.0,
            'min_deviation': round(float(np.min(deviations)), 3) if len(deviations) > 0 else 1.0,
            'max_deviation': round(float(np.max(deviations)), 3) if len(deviations) > 0 else 3.0,
            'hotspots': status_counts['critical'] + status_counts['warning'],
            'coolzones': status_counts['nominal'],
            'total_racks': len(racks),
            'status_distribution': status_counts,
            'tau_fast_adjusted': round(tau_fast_adjusted, 3),
            'tau_persist_adjusted': round(tau_persist_adjusted, 3)
        }
        
        model_info = {
            'model_name': os.path.basename(_model_cache['model_path']),
            'loaded_at': _model_cache['loaded_at'].isoformat(),
            'tau_fast': round(float(thresholds['tau_fast']), 3) if not (np.isnan(thresholds['tau_fast']) or np.isinf(thresholds['tau_fast'])) else 2.5,
            'tau_persist': round(float(thresholds['tau_persist']), 3) if not (np.isnan(thresholds['tau_persist']) or np.isinf(thresholds['tau_persist'])) else 3.0,
            'features': scorer.trainer.features,
            'n_clusters': scorer.trainer.n_clusters
        }
        
        return HeatmapResponse(
            timestamp=datetime.now().isoformat(),
            model_info=model_info,
            racks=racks,
            stats=stats,
            thresholds={
                'tau_fast': model_info['tau_fast'],
                'tau_persist': model_info['tau_persist'],
                'tau_fast_adjusted': stats['tau_fast_adjusted'],
                'tau_persist_adjusted': stats['tau_persist_adjusted']
            }
        )
    
    except Exception as e:
        logger.error(f"Error generating heatmap: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate heatmap: {str(e)}")


@router.get("/health")
async def health_check():
    """Check if ML heatmap service is ready."""
    try:
        scorer = load_latest_model()
        return {
            'status': 'ready',
            'model': os.path.basename(_model_cache['model_path']),
            'loaded_at': _model_cache['loaded_at'].isoformat()
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
