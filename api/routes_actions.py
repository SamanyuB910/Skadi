"""Actions management endpoints."""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from storage.db import get_db
from storage.models import OptimizerAction
from optimizer.executors import scheduler_executor, bms_executor
from core.config import settings
from core.logging import logger


router = APIRouter()


class ApplyActionRequest(BaseModel):
    """Action application request."""
    action: str
    params: Dict[str, Any]
    target: str = "system"
    reason: str = ""
    pred_saving_pct: float = 0.0


@router.post("/apply")
async def apply_action(
    request: ApplyActionRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Apply or recommend action (mode respected).
    
    Example:
    ```json
    {
        "action": "increase_batch_window",
        "params": {"delta_ms": 30},
        "target": "system",
        "reason": "Increase throughput efficiency",
        "pred_saving_pct": 6.0
    }
    ```
    """
    mode = settings.default_mode  # Could also read from DB settings
    
    if settings.global_kill_switch:
        raise HTTPException(status_code=403, detail="Global kill switch engaged")
    
    # Log action intent
    action_record = OptimizerAction(
        ts=datetime.utcnow(),
        action=request.action,
        params_json=request.params,
        reason=request.reason,
        pred_saving_pct=request.pred_saving_pct,
        status='pending',
        mode=mode,
        target=request.target
    )
    
    db.add(action_record)
    await db.commit()
    await db.refresh(action_record)
    
    result = None
    
    # Execute if in closed_loop mode
    if mode == "closed_loop":
        try:
            # Route to appropriate executor
            if request.action == "increase_batch_window":
                result = await scheduler_executor.increase_batch_window(request.params['delta_ms'])
            elif request.action == "shift_traffic_to_cool_row":
                result = await scheduler_executor.shift_traffic(
                    request.params['traffic_pct'],
                    request.params.get('target_racks', [])
                )
            elif request.action == "pause_low_priority_jobs":
                result = await scheduler_executor.pause_jobs(
                    request.params['priority_threshold'],
                    request.params.get('max_pause_pct', 10)
                )
            elif request.action == "decrease_fan_rpm":
                result = await bms_executor.set_fan_rpm(request.params['delta_pct'])
            elif request.action == "increase_supply_temp":
                result = await bms_executor.set_supply_temp(request.params['delta_c'])
            elif request.action == "increase_cdu_pump":
                result = await bms_executor.set_pump_rpm(request.params['delta_pct'])
            else:
                raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
            
            # Update status
            action_record.status = result.get('status', 'applied')
            await db.commit()
            
            logger.info(f"Action applied: {request.action} -> {result.get('status')}")
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)
            action_record.status = 'failed'
            await db.commit()
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Advisory mode - just log
        action_record.status = 'advisory'
        await db.commit()
        logger.info(f"Action recommended (advisory mode): {request.action}")
    
    return {
        'action_id': action_record.id,
        'action': request.action,
        'mode': mode,
        'status': action_record.status,
        'execution_result': result,
        'ts': action_record.ts.isoformat()
    }


@router.get("/log")
async def get_action_log(
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get action audit trail.
    
    Returns recent actions with timestamps, status, and outcomes.
    """
    stmt = select(OptimizerAction).order_by(
        OptimizerAction.ts.desc()
    ).limit(limit)
    
    result = await db.execute(stmt)
    actions = result.scalars().all()
    
    return {
        'actions': [
            {
                'id': a.id,
                'ts': a.ts.isoformat(),
                'action': a.action,
                'params': a.params_json,
                'reason': a.reason,
                'pred_saving_pct': a.pred_saving_pct,
                'realized_saving_pct': a.realized_saving_pct,
                'status': a.status,
                'mode': a.mode,
                'target': a.target
            }
            for a in actions
        ]
    }
