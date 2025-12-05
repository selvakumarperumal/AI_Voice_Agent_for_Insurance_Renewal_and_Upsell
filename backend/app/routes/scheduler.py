"""
Scheduler Routes - API endpoints for call scheduling management
"""
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..services import scheduler_service
from ..schemas.scheduler import (
    SchedulerConfigResponse, SchedulerConfigUpdate,
    ScheduledCallResponse, ScheduledCallCreate,
    PendingCustomersResponse, SchedulerStatsResponse,
    TriggerNowResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


# =============================================================================
# SCHEDULER CONFIGURATION
# =============================================================================

@router.get("/config", response_model=SchedulerConfigResponse)
async def get_config(session: AsyncSession = Depends(get_session)):
    """Get current scheduler configuration."""
    config = await scheduler_service.get_scheduler_config(session)
    return SchedulerConfigResponse(
        enabled=config.enabled,
        daily_call_time=config.daily_call_time,
        days_before_expiry=config.days_before_expiry,
        max_calls_per_day=config.max_calls_per_day,
        max_concurrent_calls=config.max_concurrent_calls,
        retry_failed_after_hours=config.retry_failed_after_hours,
        max_retries_per_customer=config.max_retries_per_customer,
        skip_if_called_within_days=config.skip_if_called_within_days,
        updated_at=config.updated_at
    )


@router.put("/config", response_model=SchedulerConfigResponse)
async def update_config(
    data: SchedulerConfigUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update scheduler configuration."""
    config = await scheduler_service.update_scheduler_config(session, data)
    return SchedulerConfigResponse(
        enabled=config.enabled,
        daily_call_time=config.daily_call_time,
        days_before_expiry=config.days_before_expiry,
        max_calls_per_day=config.max_calls_per_day,
        max_concurrent_calls=config.max_concurrent_calls,
        retry_failed_after_hours=config.retry_failed_after_hours,
        max_retries_per_customer=config.max_retries_per_customer,
        skip_if_called_within_days=config.skip_if_called_within_days,
        updated_at=config.updated_at
    )


# =============================================================================
# PENDING CUSTOMERS
# =============================================================================

@router.get("/pending-customers", response_model=PendingCustomersResponse)
async def get_pending_customers(
    session: AsyncSession = Depends(get_session),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200)
):
    """Get customers with expiring policies who should be called."""
    customers = await scheduler_service.get_pending_customers(session, days, limit)
    return PendingCustomersResponse(
        count=len(customers),
        customers=customers
    )


# =============================================================================
# SCHEDULED CALLS
# =============================================================================

@router.get("/scheduled-calls", response_model=List[ScheduledCallResponse])
async def list_scheduled_calls(
    session: AsyncSession = Depends(get_session),
    scheduled_date: Optional[date] = None,
    status: Optional[str] = Query(None, pattern="^(pending|queued|completed|failed|cancelled|skipped)$"),
    customer_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """List scheduled calls with optional filters."""
    calls = await scheduler_service.get_scheduled_calls(
        session, scheduled_date, status, customer_id, limit
    )
    return [ScheduledCallResponse(**c) for c in calls]


@router.post("/scheduled-calls", response_model=ScheduledCallResponse)
async def create_scheduled_call(
    data: ScheduledCallCreate,
    session: AsyncSession = Depends(get_session)
):
    """Manually schedule a call for a customer."""
    scheduled_call = await scheduler_service.create_scheduled_call(session, data)
    
    # Get customer info for response
    calls = await scheduler_service.get_scheduled_calls(
        session, customer_id=data.customer_id, limit=1
    )
    if calls:
        return ScheduledCallResponse(**calls[0])
    
    return ScheduledCallResponse(
        id=scheduled_call.id,
        customer_id=scheduled_call.customer_id,
        scheduled_date=scheduled_call.scheduled_date,
        scheduled_time=scheduled_call.scheduled_time,
        status=scheduled_call.status,
        reason=scheduled_call.reason,
        priority=scheduled_call.priority,
        notes=scheduled_call.notes,
        created_at=scheduled_call.created_at
    )


@router.delete("/scheduled-calls/{scheduled_call_id}")
async def cancel_scheduled_call(
    scheduled_call_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Cancel a scheduled call."""
    try:
        success = await scheduler_service.cancel_scheduled_call(session, scheduled_call_id)
        if not success:
            raise HTTPException(status_code=404, detail="Scheduled call not found")
        return {"success": True, "message": "Scheduled call cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# SCHEDULER STATS & ACTIONS
# =============================================================================

@router.get("/stats", response_model=SchedulerStatsResponse)
async def get_stats(session: AsyncSession = Depends(get_session)):
    """Get scheduler statistics."""
    stats = await scheduler_service.get_scheduler_stats(session)
    return SchedulerStatsResponse(**stats)


@router.post("/trigger-now", response_model=TriggerNowResponse)
async def trigger_now(
    session: AsyncSession = Depends(get_session),
    days: int = Query(30, ge=1, le=365),
    max_calls: int = Query(20, ge=1, le=100)
):
    """Manually trigger the scheduler to call pending customers now."""
    try:
        # Import celery app and use send_task to avoid import-time connection issues
        from ..core.celery_app import celery_app
        
        # Use send_task to queue the task by name without importing the task module
        task = celery_app.send_task(
            "backend.app.tasks.scheduler.call_expiring_policies_task",
            args=[days, max_calls]
        )
        
        return TriggerNowResponse(
            success=True,
            message=f"Scheduler triggered for {days} days expiry window",
            task_id=task.id,
            queued_count=max_calls
        )
    except Exception as e:
        logger.error(f"Failed to trigger scheduler: {str(e)}")
        return TriggerNowResponse(
            success=False,
            message=f"Failed to trigger: {str(e)}",
            queued_count=0
        )


@router.delete("/cleanup")
async def cleanup_old_records(
    session: AsyncSession = Depends(get_session),
    days: int = Query(30, ge=7, le=365)
):
    """Clean up old scheduled call records."""
    deleted = await scheduler_service.cleanup_old_scheduled_calls(session, days)
    return {"success": True, "deleted": deleted}
