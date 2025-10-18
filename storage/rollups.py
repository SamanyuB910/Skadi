"""Rollup computation utilities."""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import TelemetryRaw, Rollup1Min
from core.logging import logger


async def compute_rollup_1min(
    session: AsyncSession,
    start_ts: datetime,
    end_ts: datetime
) -> List[Rollup1Min]:
    """Compute 1-minute rollups from raw telemetry.
    
    Args:
        session: Database session
        start_ts: Start timestamp
        end_ts: End timestamp
        
    Returns:
        List of computed rollup records
    """
    # Query raw telemetry in the time window
    stmt = select(TelemetryRaw).where(
        and_(
            TelemetryRaw.ts >= start_ts,
            TelemetryRaw.ts < end_ts
        )
    )
    result = await session.execute(stmt)
    records = result.scalars().all()
    
    if not records:
        return []
    
    # Group by rack_id
    racks: Dict[str, List[TelemetryRaw]] = {}
    for record in records:
        if record.rack_id not in racks:
            racks[record.rack_id] = []
        racks[record.rack_id].append(record)
    
    rollups = []
    
    for rack_id, rack_records in racks.items():
        if not rack_records:
            continue
            
        # Calculate aggregates
        n = len(rack_records)
        
        # Energy per prompt (Wh/prompt)
        # gpu_energy_j is cumulative energy in joules
        # Convert to Wh: J / 3600 = Wh
        total_gpu_energy_wh = sum(r.gpu_energy_j for r in rack_records) / 3600.0
        
        # Auxiliary power (assume pdu_kw includes fan/pump/chiller proportionally)
        avg_pdu_kw = sum(r.pdu_kw for r in rack_records) / n
        window_duration_h = (end_ts - start_ts).total_seconds() / 3600.0
        aux_energy_wh = avg_pdu_kw * window_duration_h * 1000  # kW -> Wh
        
        # Total energy
        total_energy_wh = total_gpu_energy_wh + aux_energy_wh
        
        # Estimate prompts from tokens (assume ~100 tokens per prompt average)
        total_tokens = sum(r.tokens_ps for r in rack_records) * window_duration_h * 3600
        prompts = max(1, total_tokens / 100.0)  # Avoid division by zero
        
        j_per_prompt_wh = total_energy_wh / prompts
        
        # Delta T
        avg_inlet_c = sum(r.inlet_c for r in rack_records) / n
        avg_outlet_c = sum(r.outlet_c for r in rack_records) / n
        delta_t_c = avg_outlet_c - avg_inlet_c
        
        # Inlet compliance (percentage of readings within limits)
        from core.config import settings
        compliant = sum(1 for r in rack_records if r.inlet_c <= settings.inlet_max_c)
        inlet_compliance_pct = (compliant / n) * 100.0
        
        # Auxiliary kW (simplified as average PDU)
        aux_kw = avg_pdu_kw * 0.3  # Assume 30% of PDU is aux (fan/pump/chiller)
        
        # Throttles (count high latency events as proxy)
        throttles = sum(1 for r in rack_records if r.latency_p95_ms > settings.sla_latency_ms)
        
        # Average metrics
        avg_latency_ms = sum(r.latency_p95_ms for r in rack_records) / n
        avg_tokens_ps = sum(r.tokens_ps for r in rack_records) / n
        
        rollup = Rollup1Min(
            ts=start_ts,
            rack_id=rack_id,
            j_per_prompt_wh=j_per_prompt_wh,
            delta_t_c=delta_t_c,
            throttles=throttles,
            inlet_compliance_pct=inlet_compliance_pct,
            aux_kw=aux_kw,
            avg_latency_ms=avg_latency_ms,
            avg_tokens_ps=avg_tokens_ps
        )
        
        rollups.append(rollup)
    
    return rollups


async def get_recent_rollups(
    session: AsyncSession,
    minutes: int = 10,
    rack_id: str = None
) -> List[Rollup1Min]:
    """Fetch recent rollups for analysis.
    
    Args:
        session: Database session
        minutes: Number of minutes to look back
        rack_id: Optional rack filter
        
    Returns:
        List of rollup records
    """
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    
    stmt = select(Rollup1Min).where(Rollup1Min.ts >= cutoff)
    
    if rack_id:
        stmt = stmt.where(Rollup1Min.rack_id == rack_id)
    
    stmt = stmt.order_by(Rollup1Min.ts.desc())
    
    result = await session.execute(stmt)
    return result.scalars().all()
