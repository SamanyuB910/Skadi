"""Tests for IMS module."""
import pytest
import numpy as np
import pandas as pd
from ims.train import IMSTrainer
from ims.score import IMSScorer
from core.errors import IMSNotTrainedException


def test_ims_trainer_initialization():
    """Test IMS trainer initialization."""
    trainer = IMSTrainer(n_clusters=5)
    assert trainer.n_clusters == 5
    assert trainer.tau_fast is None
    assert trainer.tau_persist is None


def test_ims_training_nominal_data():
    """Test IMS training on nominal data."""
    # Generate synthetic nominal data
    np.random.seed(42)
    n_samples = 500
    
    data = {
        'ts': pd.date_range('2025-01-01', periods=n_samples, freq='1min'),
        'rack_id': ['R-A-01'] * n_samples,
        'inlet_c': np.random.normal(22.0, 0.5, n_samples),
        'outlet_c': np.random.normal(35.0, 1.0, n_samples),
        'pdu_kw': np.random.normal(8.0, 0.5, n_samples),
        'gpu_energy_j': np.random.normal(40000, 2000, n_samples),
        'tokens_ps': np.random.normal(8000, 500, n_samples),
        'latency_p95_ms': np.random.normal(180, 10, n_samples),
        'queue_depth': np.random.randint(20, 50, n_samples),
        'fan_rpm_pct': np.random.normal(65, 3, n_samples),
        'pump_rpm_pct': np.random.normal(58, 3, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    trainer = IMSTrainer(n_clusters=5)
    metrics = trainer.train(df)
    
    assert metrics['training_samples'] > 0
    assert trainer.tau_fast > 0
    assert trainer.tau_persist > trainer.tau_fast
    assert metrics['n_clusters'] == 5


def test_ims_deviation_scoring():
    """Test IMS deviation scoring."""
    # Generate and train on nominal data
    np.random.seed(42)
    n_samples = 300
    
    data = {
        'ts': pd.date_range('2025-01-01', periods=n_samples, freq='1min'),
        'rack_id': ['R-A-01'] * n_samples,
        'inlet_c': np.random.normal(22.0, 0.5, n_samples),
        'outlet_c': np.random.normal(35.0, 1.0, n_samples),
        'pdu_kw': np.random.normal(8.0, 0.5, n_samples),
        'gpu_energy_j': np.random.normal(40000, 2000, n_samples),
        'tokens_ps': np.random.normal(8000, 500, n_samples),
        'latency_p95_ms': np.random.normal(180, 10, n_samples),
        'queue_depth': np.random.randint(20, 50, n_samples),
        'fan_rpm_pct': np.random.normal(65, 3, n_samples),
        'pump_rpm_pct': np.random.normal(58, 3, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    trainer = IMSTrainer(n_clusters=5)
    trainer.train(df)
    
    scorer = IMSScorer(trainer)
    
    # Test nominal sample (should have low deviation)
    nominal_sample = {
        'inlet_c': 22.0,
        'outlet_c': 35.0,
        'pdu_kw': 8.0,
        'gpu_energy_j': 40000,
        'tokens_ps': 8000,
        'latency_p95_ms': 180,
        'queue_depth': 35,
        'fan_rpm_pct': 65,
        'pump_rpm_pct': 58
    }
    
    deviation_nominal = scorer.score_sample(nominal_sample)
    assert deviation_nominal < trainer.tau_fast
    
    # Test anomalous sample (should have high deviation)
    anomalous_sample = {
        'inlet_c': 30.0,  # Very high
        'outlet_c': 50.0,  # Very high
        'pdu_kw': 11.0,  # High
        'gpu_energy_j': 60000,  # High
        'tokens_ps': 12000,  # High
        'latency_p95_ms': 350,  # High
        'queue_depth': 150,  # High
        'fan_rpm_pct': 95,  # High
        'pump_rpm_pct': 85  # High
    }
    
    deviation_anomalous = scorer.score_sample(anomalous_sample)
    assert deviation_anomalous > deviation_nominal


def test_ims_scorer_without_training():
    """Test that scorer raises error if model not trained."""
    trainer = IMSTrainer()
    
    with pytest.raises(IMSNotTrainedException):
        scorer = IMSScorer(trainer)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
