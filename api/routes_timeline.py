"""Timeline data endpoints."""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from storage.db import get_db
from storage.models import Rollup1Min, OptimizerAction
from core.logging import logger


router = APIRouter()


@router.get("")
async def get_timeline(
    from_ts: str = Query(..., alias="from"),
    to: str = Query(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get timeline data for charts.
    
    Returns series for:
    - J/prompt
    - Latency P95
    - IMS deviation
    - Auxiliary power (fan/pump/chiller)
    - Action annotations
    
    Example:
    ```
    GET /timeline?from=2025-10-18T22:00:00Z&to=2025-10-18T23:00:00Z
    ```
    
    Returns:
    {
        "from": "2025-10-18T22:00:00Z",
        "to": "2025-10-18T23:00:00Z",
        "series": {
            "j_per_prompt": [[ts, value], ...],
            "latency_p95": [[ts, value], ...],
            "ims_deviation": [[ts, value], ...],
            "aux_kw": [[ts, value], ...]
        },
        "actions": [
            {"ts": "...", "action": "...", "reason": "..."},
            ...
        ]
    }
    """
    # Parse timestamps
    try:
        start_ts = datetime.fromisoformat(from_ts.replace('Z', '+00:00'))
        end_ts = datetime.fromisoformat(to.replace('Z', '+00:00'))
    except:
        return {"error": "Invalid timestamp format"}
    
    # Query rollups
    stmt = select(Rollup1Min).where(
        Rollup1Min.ts >= start_ts
    ).where(
        Rollup1Min.ts <= end_ts
    ).order_by(Rollup1Min.ts)
    
    result = await db.execute(stmt)
    rollups = result.scalars().all()
    
    # Build time series (aggregate across racks)
    ts_data = {}
    for rollup in rollups:
        ts_key = rollup.ts.isoformat()
        if ts_key not in ts_data:
            ts_data[ts_key] = {
                'j_per_prompt': [],
                'latency': [],
                'aux_kw': []
            }
        
        ts_data[ts_key]['j_per_prompt'].append(rollup.j_per_prompt_wh)
        if rollup.avg_latency_ms:
            ts_data[ts_key]['latency'].append(rollup.avg_latency_ms)
        ts_data[ts_key]['aux_kw'].append(rollup.aux_kw)
    
    # Aggregate
    series = {
        'j_per_prompt': [],
        'latency_p95': [],
        'aux_kw': []
    }
    
    for ts_key in sorted(ts_data.keys()):
        data = ts_data[ts_key]
        series['j_per_prompt'].append([ts_key, round(sum(data['j_per_prompt']) / len(data['j_per_prompt']), 3)])
        if data['latency']:
            series['latency_p95'].append([ts_key, round(sum(data['latency']) / len(data['latency']), 1)])
        series['aux_kw'].append([ts_key, round(sum(data['aux_kw']), 2)])
    
    # Get actions in time range
    stmt = select(OptimizerAction).where(
        OptimizerAction.ts >= start_ts
    ).where(
        OptimizerAction.ts <= end_ts
    ).order_by(OptimizerAction.ts)
    
    result = await db.execute(stmt)
    action_records = result.scalars().all()
    
    actions = [
        {
            'ts': a.ts.isoformat(),
            'action': a.action,
            'reason': a.reason,
            'pred_saving_pct': a.pred_saving_pct,
            'status': a.status
        }
        for a in action_records
    ]
    
    return {
        'from': start_ts.isoformat(),
        'to': end_ts.isoformat(),
        'series': series,
        'actions': actions
    }
