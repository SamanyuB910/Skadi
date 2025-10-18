"""Report generation endpoints."""
from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from storage.db import get_db
from storage.models import OptimizerAction, Rollup1Min
from core.config import settings
from core.logging import logger
import json


router = APIRouter()


@router.post("/judges")
async def generate_judges_report(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Generate comprehensive report for judges (PDF/JSON).
    
    Includes:
    - KPI summary
    - Energy savings attribution
    - Action log
    - Chart references
    - System performance
    
    Returns JSON report with optional PDF generation.
    """
    logger.info("Generating judges report...")
    
    # Time window: last 24 hours
    end_ts = datetime.utcnow()
    start_ts = end_ts - timedelta(hours=24)
    
    # Query rollups
    stmt = select(Rollup1Min).where(
        Rollup1Min.ts >= start_ts
    ).order_by(Rollup1Min.ts)
    result = await db.execute(stmt)
    rollups = result.scalars().all()
    
    # Query actions
    stmt = select(OptimizerAction).where(
        OptimizerAction.ts >= start_ts
    ).order_by(OptimizerAction.ts)
    result = await db.execute(stmt)
    actions = result.scalars().all()
    
    # Compute KPIs
    if rollups:
        avg_j_per_prompt = sum(r.j_per_prompt_wh for r in rollups) / len(rollups)
        avg_latency = sum(r.avg_latency_ms for r in rollups if r.avg_latency_ms) / len(rollups)
        avg_compliance = sum(r.inlet_compliance_pct for r in rollups) / len(rollups)
    else:
        avg_j_per_prompt = 0.0
        avg_latency = 0.0
        avg_compliance = 0.0
    
    # Energy savings
    baseline_j_per_prompt = 0.60
    energy_saved_pct = ((baseline_j_per_prompt - avg_j_per_prompt) / baseline_j_per_prompt) * 100
    
    # Action summary
    action_summary = {
        'total_actions': len(actions),
        'applied': sum(1 for a in actions if a.status == 'applied'),
        'advisory': sum(1 for a in actions if a.status == 'advisory'),
        'rejected': sum(1 for a in actions if a.status == 'rejected'),
        'by_type': {}
    }
    
    for action in actions:
        action_summary['by_type'][action.action] = action_summary['by_type'].get(action.action, 0) + 1
    
    # Predicted vs realized savings
    total_pred_savings = sum(a.pred_saving_pct or 0 for a in actions if a.status == 'applied')
    total_realized_savings = sum(a.realized_saving_pct or 0 for a in actions if a.realized_saving_pct)
    
    report = {
        'generated_at': datetime.utcnow().isoformat(),
        'period': {
            'start': start_ts.isoformat(),
            'end': end_ts.isoformat()
        },
        'kpis': {
            'j_per_prompt_wh': round(avg_j_per_prompt, 3),
            'latency_p95_ms': round(avg_latency, 1),
            'inlet_compliance_pct': round(avg_compliance, 1),
            'energy_saved_pct': round(energy_saved_pct, 1)
        },
        'savings_attribution': {
            'baseline_j_per_prompt': baseline_j_per_prompt,
            'current_j_per_prompt': avg_j_per_prompt,
            'reduction_pct': energy_saved_pct,
            'total_predicted_savings_pct': round(total_pred_savings, 1),
            'total_realized_savings_pct': round(total_realized_savings, 1)
        },
        'actions': action_summary,
        'action_log': [
            {
                'ts': a.ts.isoformat(),
                'action': a.action,
                'status': a.status,
                'pred_saving_pct': a.pred_saving_pct,
                'reason': a.reason
            }
            for a in actions[-20:]  # Last 20
        ],
        'system_performance': {
            'mode': settings.default_mode,
            'kill_switch': settings.global_kill_switch,
            'data_points': len(rollups),
            'actions_executed': action_summary['applied']
        },
        'charts': {
            'timeline_url': f'/timeline?from={start_ts.isoformat()}&to={end_ts.isoformat()}',
            'heatmap_url': '/heatmap?type=inlet&ts=now'
        }
    }
    
    logger.info("Judges report generated successfully")
    
    return report


@router.get("/judges/pdf")
async def download_judges_report_pdf(db: AsyncSession = Depends(get_db)):
    """Download judges report as PDF (placeholder).
    
    Real implementation would use ReportLab/WeasyPrint to generate PDF.
    """
    # For demo, return JSON
    report = await generate_judges_report(db)
    
    # In production, generate actual PDF using ReportLab/WeasyPrint
    # from reportlab.pdfgen import canvas
    # ...
    
    return Response(
        content=json.dumps(report, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=skadi_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )
