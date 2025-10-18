"""SQLAlchemy database models for Skadi system."""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean, 
    Text, JSON, Index, LargeBinary
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class TelemetryRaw(Base):
    """Raw telemetry data from racks."""
    __tablename__ = "telemetry_raw"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, nullable=False, index=True)
    rack_id = Column(String(32), nullable=False, index=True)
    inlet_c = Column(Float, nullable=False)
    outlet_c = Column(Float, nullable=False)
    pdu_kw = Column(Float, nullable=False)
    gpu_energy_j = Column(Float, nullable=False)
    tokens_ps = Column(Float, nullable=False)
    latency_p95_ms = Column(Float, nullable=False)
    fan_rpm_pct = Column(Float, nullable=True)
    pump_rpm_pct = Column(Float, nullable=True)
    queue_depth = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_telemetry_ts_rack', 'ts', 'rack_id'),
    )


class Rollup1Min(Base):
    """1-minute aggregated rollups."""
    __tablename__ = "rollups_1m"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, nullable=False, index=True)
    rack_id = Column(String(32), nullable=False, index=True)
    j_per_prompt_wh = Column(Float, nullable=False)
    delta_t_c = Column(Float, nullable=False)
    throttles = Column(Integer, default=0)
    inlet_compliance_pct = Column(Float, nullable=False)
    aux_kw = Column(Float, nullable=False)
    avg_latency_ms = Column(Float, nullable=True)
    avg_tokens_ps = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_rollup_ts_rack', 'ts', 'rack_id'),
    )


class IMSModel(Base):
    """IMS model artifacts and metadata."""
    __tablename__ = "ims_model"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    features_json = Column(JSON, nullable=False)  # List of feature names
    centers_blob = Column(LargeBinary, nullable=False)  # Pickled k-means centers
    scale_blob = Column(LargeBinary, nullable=False)  # Pickled scaler
    tau_fast = Column(Float, nullable=False)
    tau_persist = Column(Float, nullable=False)
    n_clusters = Column(Integer, nullable=False)
    training_samples = Column(Integer, nullable=False)
    metrics_json = Column(JSON, nullable=True)  # Training metrics
    is_active = Column(Boolean, default=True)


class OptimizerAction(Base):
    """Log of optimizer actions and decisions."""
    __tablename__ = "optimizer_actions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, nullable=False, index=True)
    action = Column(String(64), nullable=False)  # e.g., "increase_batch_window"
    params_json = Column(JSON, nullable=False)  # Action-specific parameters
    reason = Column(Text, nullable=True)  # Why this action was taken
    pred_saving_pct = Column(Float, nullable=True)  # Predicted energy savings
    status = Column(String(32), nullable=False)  # applied, rejected, rolled_back
    mode = Column(String(16), nullable=False)  # advisory or closed_loop
    target = Column(String(64), nullable=True)  # rack_id, row, or system-wide
    metrics_before_json = Column(JSON, nullable=True)  # KPIs before action
    metrics_after_json = Column(JSON, nullable=True)  # KPIs after action
    realized_saving_pct = Column(Float, nullable=True)  # Actual savings
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_action_ts_status', 'ts', 'status'),
    )


class Settings(Base):
    """System settings and configuration."""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(16), nullable=False)  # str, int, float, bool
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())


class IMSScore(Base):
    """IMS deviation scores over time."""
    __tablename__ = "ims_scores"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, nullable=False, index=True)
    rack_id = Column(String(32), nullable=False, index=True)
    deviation = Column(Float, nullable=False)
    mms_state = Column(String(16), nullable=False)  # transient or persistent
    mms_ema = Column(Float, nullable=False)
    model_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_ims_ts_rack', 'ts', 'rack_id'),
    )
