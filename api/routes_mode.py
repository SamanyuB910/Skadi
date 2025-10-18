"""Mode control endpoints."""
from typing import Dict, Any, Literal
from fastapi import APIRouter
from pydantic import BaseModel
from core.config import settings
from core.logging import logger


router = APIRouter()


class ModeRequest(BaseModel):
    """Mode change request."""
    mode: Literal["advisory", "closed_loop"]


@router.post("")
async def set_mode(request: ModeRequest) -> Dict[str, Any]:
    """Set system mode (advisory or closed_loop).
    
    Example:
    ```json
    {"mode": "closed_loop"}
    ```
    """
    old_mode = settings.default_mode
    settings.default_mode = request.mode
    
    logger.warning(f"Mode changed: {old_mode} -> {request.mode}")
    
    return {
        'old_mode': old_mode,
        'new_mode': request.mode,
        'message': f"System mode set to {request.mode}"
    }


@router.get("")
async def get_mode() -> Dict[str, Any]:
    """Get current system mode."""
    return {
        'mode': settings.default_mode,
        'kill_switch': settings.global_kill_switch
    }
