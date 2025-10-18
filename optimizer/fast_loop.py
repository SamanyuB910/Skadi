"""Fast guardrail loop for immediate corrections."""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from core.config import settings
from core.logging import logger
from core.errors import GuardrailViolationException
from optimizer.policies import ActionPolicy, ActionCandidate


class FastGuardrailLoop:
    """Fast-response loop for immediate thermal/IMS violations."""
    
    def __init__(self):
        """Initialize fast guardrail loop."""
        self.policy = ActionPolicy()
        self.last_action_ts = {}  # Track last action per target
    
    async def evaluate(self, current_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate state and propose immediate corrections if needed.
        
        Args:
            current_state: Current system state with metrics
            
        Returns:
            Proposed action dict or None if no intervention needed
        """
        deviation = current_state.get('ims_deviation', 0.0)
        mms_state = current_state.get('mms_state', 'transient')
        tau_fast = current_state.get('tau_fast', 1.0)
        max_inlet_c = current_state.get('max_inlet_c', 22.0)
        
        # Check kill switch
        if settings.global_kill_switch:
            logger.warning("Global kill switch engaged - no actions")
            return None
        
        # Trigger conditions for fast loop
        needs_action = False
        reason = []
        
        if deviation > tau_fast:
            needs_action = True
            reason.append(f"IMS deviation {deviation:.3f} > tau_fast {tau_fast:.3f}")
        
        if mms_state == 'persistent':
            needs_action = True
            reason.append("MMS state is PERSISTENT")
        
        if max_inlet_c > settings.inlet_max_c - 0.5:
            needs_action = True
            reason.append(f"Inlet temp {max_inlet_c:.2f}°C near limit")
        
        if not needs_action:
            return None
        
        logger.warning(f"Fast guardrail triggered: {'; '.join(reason)}")
        
        # Generate and select best action
        candidates = self.policy.generate_candidates(current_state, objective="stabilize")
        
        if not candidates:
            logger.warning("No viable candidates from fast guardrail")
            return None
        
        # Filter candidates by risk (fast loop prefers low-risk actions)
        safe_candidates = [c for c in candidates if c.risk_score < 0.5]
        if not safe_candidates:
            safe_candidates = candidates  # Fall back to all if none are safe
        
        ranked = self.policy.rank_candidates(safe_candidates)
        best = ranked[0]
        
        # Check rate limiting
        target_key = f"{best.action}:{best.target}"
        if target_key in self.last_action_ts:
            elapsed = (datetime.utcnow() - self.last_action_ts[target_key]).total_seconds()
            if elapsed < 60:  # Fast loop rate limit: 1 min
                logger.info(f"Rate limited: {target_key} (last action {elapsed:.0f}s ago)")
                return None
        
        self.last_action_ts[target_key] = datetime.utcnow()
        
        proposal = {
            'action': best.action,
            'params': best.params,
            'target': best.target,
            'pred_saving_pct': best.pred_saving_pct,
            'reason': '; '.join(reason) + f" → {best.reason}",
            'loop': 'fast',
            'ts': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Fast guardrail proposal: {proposal}")
        
        return proposal
