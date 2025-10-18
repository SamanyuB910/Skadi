"""Slow optimizer loop for strategic energy optimization."""
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.config import settings
from core.logging import logger
from optimizer.policies import ActionPolicy, ActionCandidate


class SlowOptimizerLoop:
    """Strategic optimizer for minimizing J/prompt with safety constraints."""
    
    def __init__(self):
        """Initialize slow optimizer loop."""
        self.policy = ActionPolicy()
        self.last_action_ts = {}
    
    async def optimize(
        self,
        current_state: Dict[str, Any],
        forecaster=None
    ) -> Optional[Dict[str, Any]]:
        """Run optimization cycle to minimize J/prompt.
        
        Args:
            current_state: Current system state
            forecaster: Optional forecaster model for predictions
            
        Returns:
            Selected action or None
        """
        # Check kill switch
        if settings.global_kill_switch:
            logger.warning("Global kill switch engaged - no optimization")
            return None
        
        # Check if system is stable enough to optimize
        mms_state = current_state.get('mms_state', 'transient')
        avg_latency_ms = current_state.get('avg_latency_ms', 180)
        j_per_prompt = current_state.get('j_per_prompt_wh', 0.5)
        
        # Don't optimize if system is unstable
        if mms_state == 'persistent':
            logger.info("Skipping slow optimization - MMS state is persistent")
            return None
        
        if avg_latency_ms > settings.sla_latency_ms * 0.95:
            logger.info("Skipping slow optimization - latency near SLA")
            return None
        
        logger.info(f"Running slow optimization (current J/prompt: {j_per_prompt:.3f} Wh)")
        
        # Generate candidates
        candidates = self.policy.generate_candidates(
            current_state,
            objective="reduce_j_per_prompt"
        )
        
        if not candidates:
            logger.info("No optimization candidates available")
            return None
        
        # Filter by guardrails
        safe_candidates = self._apply_guardrails(candidates, current_state, forecaster)
        
        if not safe_candidates:
            logger.warning("All candidates rejected by guardrails")
            return None
        
        # Rank and select best
        ranked = self.policy.rank_candidates(safe_candidates)
        best = ranked[0]
        
        # Rate limiting (slow loop: respect write rate limit)
        target_key = f"{best.action}:{best.target}"
        if target_key in self.last_action_ts:
            elapsed = (datetime.utcnow() - self.last_action_ts[target_key]).total_seconds()
            if elapsed < settings.write_rate_limit_s:
                logger.info(f"Rate limited: {target_key} (last action {elapsed:.0f}s ago)")
                return None
        
        self.last_action_ts[target_key] = datetime.utcnow()
        
        proposal = {
            'action': best.action,
            'params': best.params,
            'target': best.target,
            'pred_saving_pct': best.pred_saving_pct,
            'pred_latency_impact_ms': best.pred_latency_impact_ms,
            'reason': best.reason,
            'loop': 'slow',
            'ts': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Slow optimizer proposal: {proposal}")
        
        return proposal
    
    def _apply_guardrails(
        self,
        candidates: List[ActionCandidate],
        current_state: Dict[str, Any],
        forecaster
    ) -> List[ActionCandidate]:
        """Apply safety guardrails to filter candidates.
        
        Args:
            candidates: List of action candidates
            current_state: Current state
            forecaster: Optional forecaster for predictions
            
        Returns:
            Filtered list of safe candidates
        """
        safe = []
        
        max_inlet_c = current_state.get('max_inlet_c', 22.0)
        avg_latency_ms = current_state.get('avg_latency_ms', 180)
        deviation = current_state.get('ims_deviation', 0.0)
        tau_persist = current_state.get('tau_persist', 2.0)
        
        for candidate in candidates:
            # Guardrail 1: Inlet temperature must stay below limit
            predicted_inlet = max_inlet_c + candidate.pred_inlet_change_c
            if predicted_inlet > settings.inlet_max_c:
                logger.debug(f"Rejected {candidate.action}: inlet would exceed {settings.inlet_max_c}°C")
                continue
            
            # Guardrail 2: Latency must stay within SLA
            predicted_latency = avg_latency_ms + candidate.pred_latency_impact_ms
            if predicted_latency > settings.sla_latency_ms:
                logger.debug(f"Rejected {candidate.action}: latency would exceed SLA")
                continue
            
            # Guardrail 3: Don't push IMS deviation toward tau_persist
            # (Simplified: assume actions that increase temp also increase deviation)
            if candidate.pred_inlet_change_c > 1.0 and deviation > tau_persist * 0.7:
                logger.debug(f"Rejected {candidate.action}: would increase deviation risk")
                continue
            
            # Guardrail 4: High-risk actions require extra caution
            if candidate.risk_score > 0.6 and current_state.get('recent_rollback', False):
                logger.debug(f"Rejected {candidate.action}: too risky after recent rollback")
                continue
            
            safe.append(candidate)
        
        logger.info(f"Guardrails: {len(safe)}/{len(candidates)} candidates passed")
        return safe
