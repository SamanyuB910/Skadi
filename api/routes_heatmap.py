"""Heatmap data endpoints."""
from typing import Dict, Any, List, Literal
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from storage.db import get_db
from storage.models import TelemetryRaw
from core.logging import logger


router = APIRouter()


@router.get("")
async def get_heatmap(
    type: Literal["inlet", "outlet", "delta_t", "power"] = Query("inlet"),
    ts: str = Query("now"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get rack grid heatmap data.
    
    Args:
        type: Metric type (inlet, outlet, delta_t, power)
        ts: Timestamp (ISO or "now")
        
    Returns:
    {
        "type": "inlet",
        "ts": "2025-10-18T23:11:10Z",
        "grid": {
            "R-A-01": {"value": 22.3, "status": "normal"},
            "R-A-02": {"value": 23.1, "status": "normal"},
            ...
        },
        "stats": {
            "min": 21.5,
            "max": 26.8,
            "avg": 23.4
        }
    }
    """
    # Parse timestamp
    if ts == "now":
        target_ts = datetime.utcnow()
    else:
        try:
            target_ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except:
            target_ts = datetime.utcnow()
    
    # Query recent telemetry (last 2 minutes)
    start_ts = target_ts - timedelta(minutes=2)
    
    stmt = select(TelemetryRaw).where(TelemetryRaw.ts >= start_ts).where(TelemetryRaw.ts <= target_ts)
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    if not records:
        return {
            "type": type,
            "ts": target_ts.isoformat(),
            "grid": {},
            "stats": {"min": 0, "max": 0, "avg": 0},
            "message": "No data available"
        }
    
    # Build grid
    grid = {}
    values = []
    
    # Get latest value per rack
    rack_latest = {}
    for record in records:
        if record.rack_id not in rack_latest or record.ts > rack_latest[record.rack_id].ts:
            rack_latest[record.rack_id] = record
    
    for rack_id, record in rack_latest.items():
        if type == "inlet":
            value = record.inlet_c
            status = "warning" if value > 26 else "critical" if value > 28 else "normal"
        elif type == "outlet":
            value = record.outlet_c
            status = "warning" if value > 45 else "critical" if value > 50 else "normal"
        elif type == "delta_t":
            value = record.outlet_c - record.inlet_c
            status = "warning" if value < 8 or value > 18 else "normal"
        elif type == "power":
            value = record.pdu_kw
            status = "warning" if value > 10 else "critical" if value > 11.5 else "normal"
        else:
            value = 0
            status = "unknown"
        
        grid[rack_id] = {
            "value": round(value, 2),
            "status": status
        }
        values.append(value)
    
    # Compute stats
    stats = {
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "avg": round(sum(values) / len(values), 2)
    }
    
    return {
        "type": type,
        "ts": target_ts.isoformat(),
        "grid": grid,
        "stats": stats
    }
