"""Analytics Routes - Call statistics and reporting."""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..core.database import get_session
from ..models import Call

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/calls/summary")
async def get_call_summary(session: AsyncSession = Depends(get_session), days: int = Query(30)):
    """Get call statistics for the period."""
    cutoff = datetime.now() - timedelta(days=days)
    calls = list((await session.execute(select(Call).where(Call.started_at >= cutoff))).scalars().all())
    
    if not calls:
        return {"period_days": days, "total_calls": 0, "completed_calls": 0, "success_rate": 0, "average_duration_seconds": 0, "calls_by_status": {}}
    
    total = len(calls)
    completed = [c for c in calls if c.status == "completed"]
    with_duration = [c for c in completed if c.duration_seconds]
    avg_dur = sum(c.duration_seconds for c in with_duration) / len(with_duration) if with_duration else 0
    status_counts = {}
    for c in calls:
        status_counts[c.status] = status_counts.get(c.status, 0) + 1
    
    return {
        "period_days": days, "total_calls": total, "completed_calls": len(completed),
        "failed_calls": sum(1 for c in calls if c.status == "failed"),
        "success_rate": round(len(completed) / total * 100, 2),
        "average_duration_seconds": round(avg_dur, 1), "calls_by_status": status_counts
    }


@router.get("/calls/outcomes")
async def get_call_outcomes(session: AsyncSession = Depends(get_session), days: int = Query(30)):
    """Get call outcome distribution."""
    cutoff = datetime.now() - timedelta(days=days)
    calls = list((await session.execute(select(Call).where(Call.started_at >= cutoff, Call.outcome.isnot(None)))).scalars().all())
    
    outcomes = {}
    for c in calls:
        if c.outcome:
            outcomes[c.outcome] = outcomes.get(c.outcome, 0) + 1
    total = len(calls) or 1
    
    return {
        "period_days": days, "total_with_outcome": len(calls),
        "outcome_counts": outcomes,
        "outcome_percentages": {k: round(v / total * 100, 1) for k, v in outcomes.items()}
    }


@router.get("/conversion")
async def get_conversion_rate(session: AsyncSession = Depends(get_session), days: int = Query(30)):
    """Get conversion rate metrics."""
    cutoff = datetime.now() - timedelta(days=days)
    calls = list((await session.execute(select(Call).where(Call.started_at >= cutoff))).scalars().all())
    completed = [c for c in calls if c.status == "completed"]
    
    if not completed:
        return {"period_days": days, "total_calls": len(calls), "completed_calls": 0, "renewal_conversion_rate": 0, "upsell_conversion_rate": 0, "engagement_rate": 0}
    
    tc = len(completed)
    interested = sum(1 for c in completed if c.outcome == "interested")
    upsell = sum(1 for c in completed if c.outcome == "upsell_accepted")
    callback = sum(1 for c in completed if c.outcome == "callback")
    
    return {
        "period_days": days, "total_calls": len(calls), "completed_calls": tc,
        "renewal_conversion_rate": round(interested / tc * 100, 2),
        "upsell_conversion_rate": round(upsell / tc * 100, 2),
        "callback_rate": round(callback / tc * 100, 2),
        "engagement_rate": round((interested + upsell + callback) / tc * 100, 2),
        "counts": {"interested": interested, "upsell_accepted": upsell, "callback": callback,
                   "not_interested": sum(1 for c in completed if c.outcome == "not_interested")}
    }


@router.get("/daily")
async def get_daily_trends(session: AsyncSession = Depends(get_session), days: int = Query(7, le=30)):
    """Get daily call trends."""
    cutoff = datetime.now() - timedelta(days=days)
    calls = list((await session.execute(select(Call).where(Call.started_at >= cutoff).order_by(Call.started_at))).scalars().all())
    
    daily = {}
    for c in calls:
        d = c.started_at.strftime("%Y-%m-%d") if c.started_at else "unknown"
        if d not in daily:
            daily[d] = {"total": 0, "completed": 0, "interested": 0}
        daily[d]["total"] += 1
        if c.status == "completed":
            daily[d]["completed"] += 1
        if c.outcome in ("interested", "upsell_accepted"):
            daily[d]["interested"] += 1
    
    return {
        "period_days": days,
        "daily_trends": [
            {"date": d, "total_calls": v["total"], "completed": v["completed"], "conversions": v["interested"],
             "success_rate": round(v["completed"] / v["total"] * 100, 1) if v["total"] else 0}
            for d, v in sorted(daily.items())
        ]
    }
