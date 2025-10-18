"""Tests for optimizer module."""
import pytest
from optimizer.policies import ActionPolicy, ActionCandidate
from optimizer.fast_loop import FastGuardrailLoop
from optimizer.slow_loop import SlowOptimizerLoop


def test_action_policy_generates_candidates():
    """Test action candidate generation."""
    policy = ActionPolicy()
    
    current_state = {
        'avg_inlet_c': 23.0,
        'max_inlet_c': 25.0,
        'avg_latency_ms': 180,
        'ims_deviation': 0.5,
        'mms_state': 'transient',
        'rack_temperatures': {}
    }
    
    candidates = policy.generate_candidates(current_state)
    
    assert len(candidates) > 0
    assert all(isinstance(c, ActionCandidate) for c in candidates)


def test_action_candidate_ranking():
    """Test candidate ranking."""
    policy = ActionPolicy()
    
    candidates = [
        ActionCandidate(
            action='increase_batch_window',
            params={'delta_ms': 30},
            target='system',
            pred_saving_pct=6.0,
            pred_latency_impact_ms=12.0,
            pred_inlet_change_c=0.1,
            risk_score=0.2,
            reason='Test'
        ),
        ActionCandidate(
            action='decrease_fan_rpm',
            params={'delta_pct': -5},
            target='system',
            pred_saving_pct=6.0,
            pred_latency_impact_ms=0.0,
            pred_inlet_change_c=0.75,
            risk_score=0.3,
            reason='Test'
        )
    ]
    
    ranked = policy.rank_candidates(candidates)
    
    assert len(ranked) == 2
    # Lower risk should rank higher with same savings
    assert ranked[0].risk_score <= ranked[1].risk_score


@pytest.mark.asyncio
async def test_fast_guardrail_triggers():
    """Test fast guardrail triggering."""
    loop = FastGuardrailLoop()
    
    # State with high deviation (should trigger)
    state_high_deviation = {
        'ims_deviation': 2.0,
        'mms_state': 'persistent',
        'tau_fast': 1.0,
        'max_inlet_c': 27.0,
        'avg_inlet_c': 24.0,
        'avg_latency_ms': 180,
        'rack_temperatures': {}
    }
    
    proposal = await loop.evaluate(state_high_deviation)
    
    assert proposal is not None
    assert 'action' in proposal
    assert 'reason' in proposal


@pytest.mark.asyncio
async def test_slow_optimizer_respects_guardrails():
    """Test slow optimizer guardrail enforcement."""
    loop = SlowOptimizerLoop()
    
    # State near SLA limit (should not optimize aggressively)
    state_near_sla = {
        'avg_inlet_c': 23.0,
        'max_inlet_c': 27.5,  # Near limit
        'avg_latency_ms': 240,  # Near SLA
        'j_per_prompt_wh': 0.55,
        'ims_deviation': 0.3,
        'mms_state': 'transient',
        'tau_fast': 1.0,
        'tau_persist': 1.5,
        'rack_temperatures': {},
        'recent_rollback': False
    }
    
    proposal = await loop.optimize(state_near_sla)
    
    # Should either return None or very conservative action
    if proposal:
        assert proposal['pred_inlet_change_c'] < 1.0  # Conservative temp change


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
