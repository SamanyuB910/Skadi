"""IMS training and management endpoints."""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from storage.db import get_db
from storage.models import TelemetryRaw, IMSModel
from ims.train import IMSTrainer
from core.logging import logger
import pickle
import pandas as pd


router = APIRouter()


class TrainRequest(BaseModel):
    """IMS training request."""
    start_ts: Optional[str] = None
    end_ts: Optional[str] = None
    n_clusters: Optional[int] = None


@router.post("/train")
async def train_ims(
    request: TrainRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Train or retrain IMS model on selected window.
    
    Returns:
    {
        "model_id": "ims_20251018_231145",
        "tau_fast": 1.23,
        "tau_persist": 1.87,
        "features": [...],
        "training_samples": 5432,
        "status": "trained"
    }
    """
    # Parse timestamps
    if request.start_ts:
        start_ts = datetime.fromisoformat(request.start_ts.replace('Z', '+00:00'))
    else:
        start_ts = datetime.utcnow() - timedelta(days=7)
    
    if request.end_ts:
        end_ts = datetime.fromisoformat(request.end_ts.replace('Z', '+00:00'))
    else:
        end_ts = datetime.utcnow()
    
    # Query training data
    stmt = select(TelemetryRaw).where(
        TelemetryRaw.ts >= start_ts
    ).where(
        TelemetryRaw.ts <= end_ts
    )
    
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    if len(records) < 100:
        raise HTTPException(status_code=400, detail=f"Insufficient data: {len(records)} samples < 100")
    
    # Convert to DataFrame
    data = []
    for r in records:
        data.append({
            'ts': r.ts,
            'rack_id': r.rack_id,
            'inlet_c': r.inlet_c,
            'outlet_c': r.outlet_c,
            'pdu_kw': r.pdu_kw,
            'gpu_energy_j': r.gpu_energy_j,
            'tokens_ps': r.tokens_ps,
            'latency_p95_ms': r.latency_p95_ms,
            'queue_depth': r.queue_depth or 0,
            'fan_rpm_pct': r.fan_rpm_pct or 65,
            'pump_rpm_pct': r.pump_rpm_pct or 55
        })
    
    df = pd.DataFrame(data)
    
    # Train IMS
    trainer = IMSTrainer(n_clusters=request.n_clusters)
    metrics = trainer.train(df)
    
    # Save to database
    model_id = f"ims_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    ims_model = IMSModel(
        model_id=model_id,
        features_json=trainer.features,
        centers_blob=pickle.dumps(trainer.kmeans.cluster_centers_),
        scale_blob=pickle.dumps({
            'mean': trainer.scaler.mean_.tolist(),
            'scale': trainer.scaler.scale_.tolist()
        }),
        tau_fast=trainer.tau_fast,
        tau_persist=trainer.tau_persist,
        n_clusters=trainer.n_clusters,
        training_samples=metrics['training_samples'],
        metrics_json=metrics,
        is_active=True
    )
    
    # Deactivate old models
    stmt = select(IMSModel).where(IMSModel.is_active == True)
    result = await db.execute(stmt)
    old_models = result.scalars().all()
    for old in old_models:
        old.is_active = False
    
    db.add(ims_model)
    await db.commit()
    
    logger.info(f"IMS model trained and saved: {model_id}")
    
    return {
        'model_id': model_id,
        'tau_fast': trainer.tau_fast,
        'tau_persist': trainer.tau_persist,
        'features': trainer.features,
        'training_samples': metrics['training_samples'],
        'n_clusters': trainer.n_clusters,
        'status': 'trained',
        'metrics': metrics
    }


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    """List all IMS models."""
    stmt = select(IMSModel).order_by(IMSModel.created_at.desc())
    result = await db.execute(stmt)
    models = result.scalars().all()
    
    return {
        'models': [
            {
                'model_id': m.model_id,
                'created_at': m.created_at.isoformat(),
                'tau_fast': m.tau_fast,
                'tau_persist': m.tau_persist,
                'n_clusters': m.n_clusters,
                'training_samples': m.training_samples,
                'is_active': m.is_active
            }
            for m in models
        ]
    }
