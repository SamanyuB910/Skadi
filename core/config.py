"""Core configuration management using Pydantic Settings."""
import os
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    database_url: str = Field(default="sqlite:///./skadi.db")
    
    # Training data
    training_data_dir: str = Field(default="./data")
    
    # Redis (Optional)
    redis_url: str = Field(default="redis://localhost:6379/0")
    use_redis: bool = Field(default=False)
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    
    # System Limits & Guardrails
    global_kill_switch: bool = Field(default=False)
    default_mode: Literal["advisory", "closed_loop"] = Field(default="advisory")
    write_rate_limit_s: int = Field(default=120)
    sla_latency_ms: float = Field(default=250.0)
    inlet_max_c: float = Field(default=28.0)
    rack_kw_cap: float = Field(default=12.0)
    
    # IMS/MMS Configuration
    ims_score_interval_s: int = Field(default=5)
    ims_tau_fast_percentile: int = Field(default=95)
    ims_tau_persist_percentile: int = Field(default=98)
    mms_ema_alpha: float = Field(default=0.3)
    mms_persist_ticks: int = Field(default=6)
    
    # Optimizer Configuration
    fast_loop_interval_s: int = Field(default=10)
    slow_loop_interval_s: int = Field(default=120)
    rollup_interval_s: int = Field(default=10)
    
    # Training Configuration
    training_data_dir: str = Field(default="./data")
    artifacts_dir: str = Field(default="./artifacts")
    ims_kmeans_clusters: int = Field(default=8)
    forecaster_horizon_min: int = Field(default=5)
    forecaster_n_lags: int = Field(default=12)
    
    # Report Configuration
    report_output_dir: str = Field(default="./reports")
    report_timezone: str = Field(default="UTC")
    
    # Demo/Simulation
    enable_mock_scenarios: bool = Field(default=True)
    mock_data_tick_s: int = Field(default=5)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        os.makedirs(self.training_data_dir, exist_ok=True)
        os.makedirs(self.artifacts_dir, exist_ok=True)
        os.makedirs(self.report_output_dir, exist_ok=True)


# Singleton instance
settings = Settings()
