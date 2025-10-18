"""Optimizer control endpoints."""
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from storage.db import get_db
from optimizer.slow_loop import SlowOptimizerLoop
from api.routes_state import get_current_state
from core.logging import logger


router = APIRouter()


@router.post("/tick")
async def run_optimizer_tick(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Run slow optimizer loop once (manual trigger).
    
    Returns:
    {
        "proposals": [
            {
                "action": "increase_batch_window",
                "params": {"delta_ms": 30},
                "pred_saving_pct": 6.0,
                "reason": "..."
            },
            ...
        ],
        "picked": {
            "action": "increase_batch_window",
            "params": {"delta_ms": 30},
            "pred_saving_pct": 6.0,
            "reason": "..."
        }
    }
    """
    logger.info("Manual optimizer tick requested")
    
    # Get current state
    state = await get_current_state()
    
    # Run optimizer
    optimizer = SlowOptimizerLoop()
    proposal = await optimizer.optimize(state)
    
    if not proposal:
        return {
            'status': 'no_action',
            'message': 'No optimization action recommended',
            'proposals': [],
            'picked': None
        }
    
    # For demo, generate a few alternate proposals
    from optimizer.policies import ActionPolicy
    policy = ActionPolicy()
    candidates = policy.generate_candidates(state)
    ranked = policy.rank_candidates(candidates)
    
    proposals = [
        {
            'action': c.action,
            'params': c.params,
            'pred_saving_pct': c.pred_saving_pct,
            'reason': c.reason,
            'risk_score': c.risk_score
        }
        for c in ranked[:5]  # Top 5
    ]
    
    return {
        'status': 'ok',
        'proposals': proposals,
        'picked': proposal
    }
