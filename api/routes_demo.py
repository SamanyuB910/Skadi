"""Demo scenario endpoints."""
from typing import Dict, Any, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ingestors.mock_generators import MockDataGenerator
from core.logging import logger


router = APIRouter()


# Global mock generator instance
mock_generator = MockDataGenerator()


class ScenarioRequest(BaseModel):
    """Scenario control request."""
    scenario: Literal["add_ai_nodes_row_c", "overcooled_row_e"]
    action: Literal["start", "stop"]
    duration_s: int = 300


@router.post("/scenario")
async def control_scenario(request: ScenarioRequest) -> Dict[str, Any]:
    """Start or stop demo scenarios.
    
    Scenarios:
    - "add_ai_nodes_row_c": Heat spike in Row C (2 AI nodes added)
    - "overcooled_row_e": Over-cooled Row E (low inlet, high fan RPM)
    
    Example:
    ```json
    {
        "scenario": "add_ai_nodes_row_c",
        "action": "start",
        "duration_s": 300
    }
    ```
    """
    if request.action == "start":
        scenario_id = mock_generator.start_scenario(request.scenario, request.duration_s)
        
        logger.info(f"Demo scenario started: {request.scenario}")
        
        return {
            'status': 'started',
            'scenario_id': scenario_id,
            'scenario': request.scenario,
            'duration_s': request.duration_s,
            'message': f"Scenario {request.scenario} is now active"
        }
    
    elif request.action == "stop":
        # Stop all scenarios of this type
        active = mock_generator.get_active_scenarios()
        stopped = []
        
        for sid, s in active.items():
            if s['type'] == request.scenario:
                mock_generator.stop_scenario(sid)
                stopped.append(sid)
        
        if not stopped:
            raise HTTPException(status_code=404, detail="No active scenario of this type")
        
        logger.info(f"Demo scenario stopped: {request.scenario}")
        
        return {
            'status': 'stopped',
            'scenario': request.scenario,
            'stopped_ids': stopped,
            'message': f"Scenario {request.scenario} stopped"
        }


@router.get("/scenarios")
async def list_scenarios() -> Dict[str, Any]:
    """List active demo scenarios."""
    active = mock_generator.get_active_scenarios()
    
    return {
        'active_scenarios': [
            {
                'scenario_id': sid,
                'type': s['type'],
                'start_ts': s['start_ts'].isoformat(),
                'duration_s': s['duration_s']
            }
            for sid, s in active.items()
        ]
    }
