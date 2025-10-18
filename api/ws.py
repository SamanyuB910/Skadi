"""WebSocket endpoint for real-time event streaming."""
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.logging import logger
import json
import asyncio


router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected (total: {len(self.active_connections)})")
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected (remaining: {len(self.active_connections)})")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        if not self.active_connections:
            return
        
        json_message = json.dumps(message)
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(json_message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


@router.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time events.
    
    Streams:
    {
        "ts": "2025-10-18T23:11:10Z",
        "kpis": {
            "j_per_prompt_wh": 0.52,
            "latency_p95_ms": 178,
            "inlet_compliance_pct": 99.6
        },
        "ims": {
            "deviation": 0.31,
            "mms_state": "transient"
        },
        "last_action": {
            "action": "increase_batch_window",
            "delta": "+30ms",
            "pred_saving_pct": 8.2
        }
    }
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Echo back for now (could handle client commands)
            await websocket.send_json({"echo": data})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


async def broadcast_event(event: dict):
    """Broadcast event to all connected clients.
    
    Args:
        event: Event dictionary to broadcast
    """
    await manager.broadcast(event)
