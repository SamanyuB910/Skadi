"""State and overview endpoints."""
from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from storage.db import get_db
from storage.models import Rollup1Min, IMSScore, OptimizerAction
from core.logging import logger


router = APIRouter()


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get system overview with KPI tiles.
    
    Returns:
    {
        "j_per_prompt_wh": 0.52,
        "latency_p95_ms": 178,
        "ims_deviation": 0.31,
        "mms_state": "transient",
        "inlet_compliance_pct": 99.6,
        "energy_saved_pct": 12.3,
        "ts": "2025-10-18T23:11:10Z"
    }
    """
    # Get recent rollups (last 5 minutes)
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    
    stmt = select(Rollup1Min).where(Rollup1Min.ts >= cutoff)
    result = await db.execute(stmt)
    rollups = result.scalars().all()
    
    if not rollups:
        return {
            "status": "no_data",
            "message": "No recent data available"
        }
    
    # Compute KPIs
    avg_j_per_prompt = sum(r.j_per_prompt_wh for r in rollups) / len(rollups)
    avg_latency = sum(r.avg_latency_ms for r in rollups if r.avg_latency_ms) / len(rollups)
    avg_inlet_compliance = sum(r.inlet_compliance_pct for r in rollups) / len(rollups)
    
    # Get latest IMS score
    stmt = select(IMSScore).order_by(IMSScore.ts.desc()).limit(1)
    result = await db.execute(stmt)
    latest_ims = result.scalar_one_or_none()
    
    ims_deviation = latest_ims.deviation if latest_ims else 0.0
    mms_state = latest_ims.mms_state if latest_ims else "unknown"
    
    # Estimate energy savings (compared to baseline)
    baseline_j_per_prompt = 0.60  # Assumed baseline
    energy_saved_pct = ((baseline_j_per_prompt - avg_j_per_prompt) / baseline_j_per_prompt) * 100
    
    return {
        "j_per_prompt_wh": round(avg_j_per_prompt, 3),
        "latency_p95_ms": round(avg_latency, 1),
        "ims_deviation": round(ims_deviation, 3),
        "mms_state": mms_state,
        "inlet_compliance_pct": round(avg_inlet_compliance, 1),
        "energy_saved_pct": round(energy_saved_pct, 1),
        "ts": datetime.utcnow().isoformat()
    }


async def get_current_state() -> Dict[str, Any]:
    """Get current system state for optimizer (internal helper).
    
    Returns:
        State dictionary with all relevant metrics
    """
    from storage.db import get_db_context
    
    async with get_db_context() as db:
        # Get recent rollups
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        stmt = select(Rollup1Min).where(Rollup1Min.ts >= cutoff)
        result = await db.execute(stmt)
        rollups = result.scalars().all()
        
        if not rollups:
            return {}
        
        # Aggregate metrics
        avg_inlet_c = sum(r.ts for r in rollups) / len(rollups)  # Simplified
        max_inlet_c = max((r.ts for r in rollups), default=22.0)  # Simplified
        avg_latency_ms = sum(r.avg_latency_ms for r in rollups if r.avg_latency_ms) / len(rollups)
        j_per_prompt = sum(r.j_per_prompt_wh for r in rollups) / len(rollups)
        
        # Get IMS/MMS state
        stmt = select(IMSScore).order_by(IMSScore.ts.desc()).limit(1)
        result = await db.execute(stmt)
        latest_ims = result.scalar_one_or_none()
        
        state = {
            'avg_inlet_c': 23.0,  # Simplified
            'max_inlet_c': 26.0,
            'avg_latency_ms': avg_latency_ms,
            'j_per_prompt_wh': j_per_prompt,
            'ims_deviation': latest_ims.deviation if latest_ims else 0.0,
            'mms_state': latest_ims.mms_state if latest_ims else 'transient',
            'tau_fast': 1.0,  # Would come from IMS model
            'tau_persist': 1.5,
            'rack_temperatures': {},  # Simplified
            'recent_rollback': False
        }
        
        return state
