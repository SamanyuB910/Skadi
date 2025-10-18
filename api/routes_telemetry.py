"""Telemetry ingestion endpoints."""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from storage.db import get_db
from storage.models import TelemetryRaw
from core.logging import logger


router = APIRouter()


class TelemetrySample(BaseModel):
    """Telemetry sample model."""
    ts: str = Field(..., description="ISO timestamp")
    rack_id: str = Field(..., description="Rack identifier")
    inlet_c: float = Field(..., description="Inlet temperature (°C)")
    outlet_c: float = Field(..., description="Outlet temperature (°C)")
    pdu_kw: float = Field(..., description="PDU power (kW)")
    gpu_energy_j: float = Field(..., description="GPU energy (Joules)")
    tokens_ps: float = Field(..., description="Tokens per second")
    latency_p95_ms: float = Field(..., description="P95 latency (ms)")
    fan_rpm_pct: float = Field(None, description="Fan RPM (%)")
    pump_rpm_pct: float = Field(None, description="Pump RPM (%)")
    queue_depth: int = Field(None, description="Request queue depth")


class TelemetryBatch(BaseModel):
    """Batch of telemetry samples."""
    samples: List[TelemetrySample]


@router.post("")
async def ingest_telemetry(
    batch: TelemetryBatch,
    db: AsyncSession = Depends(get_db)
):
    """Ingest telemetry data (batch allowed).
    
    Example:
    ```json
    {
        "samples": [{
            "ts": "2025-10-18T23:11:00Z",
            "rack_id": "R-C-07",
            "inlet_c": 24.8,
            "outlet_c": 36.2,
            "pdu_kw": 8.6,
            "gpu_energy_j": 45250,
            "tokens_ps": 9800,
            "latency_p95_ms": 180,
            "fan_rpm_pct": 62,
            "pump_rpm_pct": 55,
            "queue_depth": 42
        }]
    }
    ```
    """
    records = []
    
    for sample in batch.samples:
        try:
            ts = datetime.fromisoformat(sample.ts.replace('Z', '+00:00'))
        except ValueError:
            ts = datetime.utcnow()
        
        record = TelemetryRaw(
            ts=ts,
            rack_id=sample.rack_id,
            inlet_c=sample.inlet_c,
            outlet_c=sample.outlet_c,
            pdu_kw=sample.pdu_kw,
            gpu_energy_j=sample.gpu_energy_j,
            tokens_ps=sample.tokens_ps,
            latency_p95_ms=sample.latency_p95_ms,
            fan_rpm_pct=sample.fan_rpm_pct,
            pump_rpm_pct=sample.pump_rpm_pct,
            queue_depth=sample.queue_depth
        )
        records.append(record)
    
    db.add_all(records)
    await db.commit()
    
    logger.info(f"Ingested {len(records)} telemetry samples")
    
    return {
        "status": "ok",
        "ingested": len(records)
    }


@router.post("/single")
async def ingest_single(
    sample: TelemetrySample,
    db: AsyncSession = Depends(get_db)
):
    """Ingest single telemetry sample."""
    batch = TelemetryBatch(samples=[sample])
    return await ingest_telemetry(batch, db)
