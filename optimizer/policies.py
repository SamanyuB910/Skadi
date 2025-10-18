"""Action execution policies and candidate generation."""
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np
from core.config import settings
from core.logging import logger


@dataclass
class ActionCandidate:
    """Represents a candidate action for the optimizer."""
    action: str  # Action type
    params: Dict[str, Any]  # Action parameters
    target: str  # Target (rack_id, row, or "system")
    pred_saving_pct: float  # Predicted energy savings %
    pred_latency_impact_ms: float  # Predicted latency change
    pred_inlet_change_c: float  # Predicted inlet temp change
    risk_score: float  # Risk assessment (0-1, lower is safer)
    reason: str  # Justification


class ActionPolicy:
    """Generate and evaluate action candidates."""
    
    # Action types and their parameter ranges
    ACTION_TYPES = {
        'increase_batch_window': {
            'delta_ms': [20, 30, 40],  # Increase batch window by N ms
            'max_delta': 50
        },
        'decrease_fan_rpm': {
            'delta_pct': [-3, -4, -5],  # Reduce fan speed by N%
            'min_rpm': 45
        },
        'increase_supply_temp': {
            'delta_c': [0.5, 1.0],  # Raise supply temp by N°C
            'max_temp': 24.0
        },
        'shift_traffic_to_cool_row': {
            'traffic_pct': [10, 15, 20, 25],  # Shift N% of traffic
            'min_delta_t_margin': 3.0  # Target row must have margin
        },
        'pause_low_priority_jobs': {
            'priority_threshold': [3, 4],  # Pause jobs with priority >= N
            'max_pause_pct': 15  # Don't pause more than N% of jobs
        },
        'increase_cdu_pump': {
            'delta_pct': [3, 5],  # Increase pump speed by N%
            'max_rpm': 85
        }
    }
    
    def __init__(self):
        """Initialize action policy."""
        pass
    
    def generate_candidates(
        self,
        current_state: Dict[str, Any],
        objective: str = "reduce_j_per_prompt"
    ) -> List[ActionCandidate]:
        """Generate candidate actions based on current state.
        
        Args:
            current_state: Current system metrics and conditions
            objective: Optimization objective
            
        Returns:
            List of action candidates
        """
        candidates = []
        
        # Extract state variables
        avg_inlet_c = current_state.get('avg_inlet_c', 22.0)
        max_inlet_c = current_state.get('max_inlet_c', 26.0)
        avg_latency_ms = current_state.get('avg_latency_ms', 180)
        deviation = current_state.get('ims_deviation', 0.0)
        mms_state = current_state.get('mms_state', 'transient')
        inlet_margin_c = settings.inlet_max_c - max_inlet_c
        
        # 1. Batch window increases (if latency has margin)
        if avg_latency_ms < settings.sla_latency_ms * 0.85:
            for delta in self.ACTION_TYPES['increase_batch_window']['delta_ms']:
                latency_impact = delta * 0.4  # Rough estimate
                if avg_latency_ms + latency_impact < settings.sla_latency_ms:
                    candidates.append(ActionCandidate(
                        action='increase_batch_window',
                        params={'delta_ms': delta},
                        target='system',
                        pred_saving_pct=delta * 0.2,  # ~0.2% per ms
                        pred_latency_impact_ms=latency_impact,
                        pred_inlet_change_c=0.1,  # Slight temp increase
                        risk_score=0.2,
                        reason=f"Increase batch window by {delta}ms to improve throughput efficiency"
                    ))
        
        # 2. Fan RPM reduction (if inlet margin exists)
        if inlet_margin_c > 2.0:
            for delta_pct in self.ACTION_TYPES['decrease_fan_rpm']['delta_pct']:
                temp_increase = abs(delta_pct) * 0.15  # ~0.15°C per 1% RPM
                if max_inlet_c + temp_increase < settings.inlet_max_c:
                    candidates.append(ActionCandidate(
                        action='decrease_fan_rpm',
                        params={'delta_pct': delta_pct},
                        target='system',
                        pred_saving_pct=abs(delta_pct) * 1.2,  # ~1.2% per 1% RPM
                        pred_latency_impact_ms=0.0,
                        pred_inlet_change_c=temp_increase,
                        risk_score=0.3,
                        reason=f"Reduce fan RPM by {abs(delta_pct)}% (safe thermal margin)"
                    ))
        
        # 3. Supply temperature increase (if margin allows)
        if inlet_margin_c > 3.0:
            for delta_c in self.ACTION_TYPES['increase_supply_temp']['delta_c']:
                if avg_inlet_c + delta_c < settings.inlet_max_c - 1.0:
                    candidates.append(ActionCandidate(
                        action='increase_supply_temp',
                        params={'delta_c': delta_c},
                        target='system',
                        pred_saving_pct=delta_c * 4.0,  # ~4% per °C
                        pred_latency_impact_ms=0.0,
                        pred_inlet_change_c=delta_c,
                        risk_score=0.4,
                        reason=f"Raise supply temp by {delta_c}°C to save chiller energy"
                    ))
        
        # 4. Traffic shifting (if deviation is high or temps uneven)
        if deviation > 0.5 or mms_state == 'persistent':
            # Find cool vs hot rows from current state
            rack_temps = current_state.get('rack_temperatures', {})
            if rack_temps:
                cool_racks = [r for r, t in rack_temps.items() if t < avg_inlet_c - 1.0]
                if cool_racks:
                    for traffic_pct in self.ACTION_TYPES['shift_traffic_to_cool_row']['traffic_pct']:
                        candidates.append(ActionCandidate(
                            action='shift_traffic_to_cool_row',
                            params={'traffic_pct': traffic_pct, 'target_racks': cool_racks[:3]},
                            target='routing',
                            pred_saving_pct=traffic_pct * 0.15,
                            pred_latency_impact_ms=5.0,  # Small routing overhead
                            pred_inlet_change_c=-0.3,  # Better distribution
                            risk_score=0.25,
                            reason=f"Shift {traffic_pct}% traffic to cooler racks to balance thermal load"
                        ))
        
        # 5. Pause low-priority jobs (emergency response for persistent deviation)
        if mms_state == 'persistent':
            for priority_thresh in self.ACTION_TYPES['pause_low_priority_jobs']['priority_threshold']:
                candidates.append(ActionCandidate(
                    action='pause_low_priority_jobs',
                    params={'priority_threshold': priority_thresh, 'max_pause_pct': 10},
                    target='scheduler',
                    pred_saving_pct=8.0,
                    pred_latency_impact_ms=-20.0,  # Improves latency for remaining
                    pred_inlet_change_c=-1.5,  # Reduces load
                    risk_score=0.7,  # Higher risk due to service impact
                    reason=f"Pause priority>={priority_thresh} jobs to reduce thermal stress"
                ))
        
        # 6. Pump speed increase (for better cooling distribution)
        if max_inlet_c > settings.inlet_max_c - 1.0:
            for delta_pct in self.ACTION_TYPES['increase_cdu_pump']['delta_pct']:
                candidates.append(ActionCandidate(
                    action='increase_cdu_pump',
                    params={'delta_pct': delta_pct},
                    target='cooling',
                    pred_saving_pct=-delta_pct * 0.5,  # Costs energy, but helps thermal
                    pred_latency_impact_ms=0.0,
                    pred_inlet_change_c=-0.4,
                    risk_score=0.35,
                    reason=f"Increase pump {delta_pct}% to improve coolant circulation"
                ))
        
        logger.info(f"Generated {len(candidates)} action candidates")
        return candidates
    
    def rank_candidates(
        self,
        candidates: List[ActionCandidate],
        weights: Dict[str, float] = None
    ) -> List[ActionCandidate]:
        """Rank candidates by a composite score.
        
        Args:
            candidates: List of action candidates
            weights: Scoring weights (default: favor savings, penalize risk)
            
        Returns:
            Sorted list of candidates (best first)
        """
        if not candidates:
            return []
        
        if weights is None:
            weights = {
                'saving_pct': 1.0,
                'risk_score': -0.8,
                'latency_impact': -0.3
            }
        
        for candidate in candidates:
            score = (
                weights['saving_pct'] * candidate.pred_saving_pct +
                weights['risk_score'] * candidate.risk_score +
                weights['latency_impact'] * abs(candidate.pred_latency_impact_ms) / 100.0
            )
            candidate.score = score
        
        ranked = sorted(candidates, key=lambda c: c.score, reverse=True)
        
        return ranked
