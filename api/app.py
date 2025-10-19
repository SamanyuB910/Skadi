"""Main FastAPI application."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from core.logging import logger
from storage.db import init_db
from api import ws, routes_telemetry, routes_state, routes_heatmap, routes_timeline
from api import routes_ims, routes_optimizer, routes_actions, routes_mode, routes_demo, routes_reports
from api import routes_ml_heatmap, routes_ml_analytics


# Background tasks
background_tasks = {}


async def ingestion_rollups_task():
    """Background task for computing rollups."""
    from datetime import datetime, timedelta
    from storage.db import get_db_context
    from storage.rollups import compute_rollup_1min
    from storage.models import Rollup1Min
    
    logger.info("Starting ingestion rollups task")
    
    while True:
        try:
            await asyncio.sleep(settings.rollup_interval_s)
            
            # Compute rollups for last window
            end_ts = datetime.utcnow()
            start_ts = end_ts - timedelta(seconds=60)
            
            async with get_db_context() as session:
                rollups = await compute_rollup_1min(session, start_ts, end_ts)
                
                if rollups:
                    session.add_all(rollups)
                    await session.commit()
                    logger.debug(f"Computed {len(rollups)} rollups")
        
        except Exception as e:
            logger.error(f"Error in rollups task: {e}", exc_info=True)


async def ims_mms_loop_task():
    """Background task for IMS/MMS scoring."""
    from datetime import datetime, timedelta
    from storage.db import get_db_context
    from storage.models import TelemetryRaw, IMSScore, IMSModel
    from sqlalchemy import select, desc
    
    logger.info("Starting IMS/MMS loop task")
    
    # Load active IMS model
    ims_scorer = None
    mms_filters = {}  # Per-rack MMS filters
    
    while True:
        try:
            await asyncio.sleep(settings.ims_score_interval_s)
            
            # Load IMS model if not loaded
            if ims_scorer is None:
                async with get_db_context() as session:
                    stmt = select(IMSModel).where(IMSModel.is_active == True).order_by(desc(IMSModel.created_at)).limit(1)
                    result = await session.execute(stmt)
                    ims_model = result.scalar_one_or_none()
                    
                    if ims_model:
                        # Load model (simplified - in production, deserialize from DB)
                        from ims.train import IMSTrainer
                        from ims.score import IMSScorer
                        from mms.filter import MMSFilter
                        
                        # For demo, create a basic scorer
                        # Real implementation would deserialize from ims_model.centers_blob
                        logger.info(f"IMS model loaded: {ims_model.model_id}")
                        # ims_scorer = IMSScorer(...) # Placeholder
            
            # Score recent telemetry
            # (Simplified for demo)
            
        except Exception as e:
            logger.error(f"Error in IMS/MMS loop: {e}", exc_info=True)


async def fast_guardrail_loop_task():
    """Background task for fast guardrail responses."""
    from optimizer.fast_loop import FastGuardrailLoop
    
    logger.info("Starting fast guardrail loop task")
    fast_loop = FastGuardrailLoop()
    
    while True:
        try:
            await asyncio.sleep(settings.fast_loop_interval_s)
            
            # Get current state
            from api.routes_state import get_current_state
            state = await get_current_state()
            
            # Evaluate
            proposal = await fast_loop.evaluate(state)
            
            if proposal and settings.default_mode == "closed_loop":
                # Execute action (simplified)
                logger.info(f"Fast loop executing: {proposal}")
                # await execute_action(proposal)
            
            # Broadcast via WebSocket
            if proposal:
                await ws.broadcast_event({
                    'type': 'fast_guardrail',
                    'proposal': proposal
                })
        
        except Exception as e:
            logger.error(f"Error in fast guardrail loop: {e}", exc_info=True)


async def slow_optimizer_loop_task():
    """Background task for slow optimizer."""
    from optimizer.slow_loop import SlowOptimizerLoop
    
    logger.info("Starting slow optimizer loop task")
    slow_loop = SlowOptimizerLoop()
    
    while True:
        try:
            await asyncio.sleep(settings.slow_loop_interval_s)
            
            # Get current state
            from api.routes_state import get_current_state
            state = await get_current_state()
            
            # Optimize
            proposal = await slow_loop.optimize(state)
            
            if proposal and settings.default_mode == "closed_loop":
                # Execute action
                logger.info(f"Slow loop executing: {proposal}")
                # await execute_action(proposal)
            
            # Broadcast via WebSocket
            if proposal:
                await ws.broadcast_event({
                    'type': 'slow_optimizer',
                    'proposal': proposal
                })
        
        except Exception as e:
            logger.error(f"Error in slow optimizer loop: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    logger.info("Starting Skadi backend...")
    
    # Initialize database
    await init_db()
    
    # Start background tasks
    background_tasks['rollups'] = asyncio.create_task(ingestion_rollups_task())
    background_tasks['ims_mms'] = asyncio.create_task(ims_mms_loop_task())
    background_tasks['fast_guardrail'] = asyncio.create_task(fast_guardrail_loop_task())
    background_tasks['slow_optimizer'] = asyncio.create_task(slow_optimizer_loop_task())
    
    logger.info("All background tasks started")
    logger.info(f"Skadi backend ready on {settings.host}:{settings.port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Skadi backend...")
    
    # Cancel background tasks
    for name, task in background_tasks.items():
        logger.info(f"Cancelling task: {name}")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    logger.info("Skadi backend stopped")


# Create FastAPI app
app = FastAPI(
    title="Skadi - AI Datacenter Energy Optimizer",
    description="NASA-inspired backend for Measure → Decide → Act energy optimization",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ws.router, tags=["WebSocket"])
app.include_router(routes_telemetry.router, prefix="/telemetry", tags=["Telemetry"])
app.include_router(routes_state.router, prefix="/state", tags=["State"])
app.include_router(routes_heatmap.router, prefix="/heatmap", tags=["Heatmap"])
app.include_router(routes_ml_heatmap.router, prefix="/ml-heatmap", tags=["ML Heatmap"])
app.include_router(routes_ml_analytics.router, prefix="/ml-analytics", tags=["ML Analytics"])
app.include_router(routes_timeline.router, prefix="/timeline", tags=["Timeline"])
app.include_router(routes_ims.router, prefix="/ims", tags=["IMS"])
app.include_router(routes_optimizer.router, prefix="/optimizer", tags=["Optimizer"])
app.include_router(routes_actions.router, prefix="/actions", tags=["Actions"])
app.include_router(routes_mode.router, prefix="/mode", tags=["Mode"])
app.include_router(routes_demo.router, prefix="/demo", tags=["Demo"])
app.include_router(routes_reports.router, prefix="/report", tags=["Reports"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Skadi",
        "version": "1.0.0",
        "status": "operational",
        "mode": settings.default_mode,
        "kill_switch": settings.global_kill_switch
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
