"""
Scheduler Service - Business logic for auto-scheduling calls

Handles scheduling calls to customers with expiring policies,
tracking scheduled calls, and managing scheduler configuration.
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from ..models import (
    ScheduledCall, SchedulerConfig, CustomerPolicy, 
    Customer, Policy, Call
)
from ..schemas.scheduler import (
    ScheduledCallCreate, ScheduledCallResponse, 
    PendingCustomer, SchedulerConfigUpdate
)

logger = logging.getLogger(__name__)


# =============================================================================
# SCHEDULER CONFIGURATION
# =============================================================================

async def get_scheduler_config(session: AsyncSession) -> SchedulerConfig:
    """Get the scheduler configuration, creating default if not exists."""
    result = await session.execute(
        select(SchedulerConfig).where(SchedulerConfig.id == "default")
    )
    config = result.scalar_one_or_none()
    
    if not config:
        config = SchedulerConfig(id="default")
        session.add(config)
        await session.commit()
        await session.refresh(config)
    
    return config


async def update_scheduler_config(
    session: AsyncSession, 
    data: SchedulerConfigUpdate
) -> SchedulerConfig:
    """Update scheduler configuration."""
    config = await get_scheduler_config(session)
    
    if data.enabled is not None:
        config.enabled = data.enabled
    if data.daily_call_time is not None:
        config.daily_call_time = data.daily_call_time
    if data.days_before_expiry is not None:
        config.days_before_expiry = data.days_before_expiry
    if data.max_calls_per_day is not None:
        config.max_calls_per_day = data.max_calls_per_day
    if data.max_concurrent_calls is not None:
        config.max_concurrent_calls = data.max_concurrent_calls
    if data.retry_failed_after_hours is not None:
        config.retry_failed_after_hours = data.retry_failed_after_hours
    if data.max_retries_per_customer is not None:
        config.max_retries_per_customer = data.max_retries_per_customer
    if data.skip_if_called_within_days is not None:
        config.skip_if_called_within_days = data.skip_if_called_within_days
    
    session.add(config)
    await session.commit()
    await session.refresh(config)
    
    logger.info(f"Updated scheduler config: enabled={config.enabled}")
    return config


# =============================================================================
# PENDING CUSTOMERS (to be called)
# =============================================================================

async def get_pending_customers(
    session: AsyncSession,
    days_before_expiry: int = 30,
    limit: int = 50
) -> List[PendingCustomer]:
    """
    Get customers with expiring policies who should be called.
    
    Filters out:
    - Customers already called today
    - Customers called within skip_if_called_within_days
    - Customers with cancelled/expired policies
    """
    config = await get_scheduler_config(session)
    
    today = date.today()
    expiry_cutoff = today + timedelta(days=days_before_expiry)
    skip_since = today - timedelta(days=config.skip_if_called_within_days)
    
    # Get customers with expiring policies
    stmt = (
        select(
            CustomerPolicy.customer_id,
            Customer.name.label("customer_name"),
            Customer.phone.label("customer_phone"),
            CustomerPolicy.policy_id,
            Policy.policy_name,
            CustomerPolicy.end_date
        )
        .join(Customer, CustomerPolicy.customer_id == Customer.id)
        .join(Policy, CustomerPolicy.policy_id == Policy.id)
        .where(
            CustomerPolicy.status == "active",
            CustomerPolicy.end_date >= today,
            CustomerPolicy.end_date <= expiry_cutoff
        )
        .order_by(CustomerPolicy.end_date)
    )
    
    result = await session.execute(stmt)
    expiring_policies = result.all()
    
    # Filter out recently called customers
    pending = []
    seen_customers = set()
    
    for row in expiring_policies:
        customer_id = row.customer_id
        
        if customer_id in seen_customers:
            continue
        
        # Check if customer was called recently
        call_check = await session.execute(
            select(Call)
            .where(
                Call.customer_id == customer_id,
                func.date(Call.started_at) >= skip_since
            )
            .limit(1)
        )
        recent_call = call_check.scalar_one_or_none()
        
        # Check if already scheduled today
        schedule_check = await session.execute(
            select(ScheduledCall)
            .where(
                ScheduledCall.customer_id == customer_id,
                ScheduledCall.scheduled_date == today,
                ScheduledCall.status.in_(["pending", "queued", "completed"])
            )
            .limit(1)
        )
        already_scheduled = schedule_check.scalar_one_or_none()
        
        if not recent_call and not already_scheduled:
            days_to_expiry = (row.end_date - today).days
            
            # Get call count for this customer
            call_count_result = await session.execute(
                select(func.count(Call.id))
                .where(Call.customer_id == customer_id)
            )
            call_count = call_count_result.scalar() or 0
            
            # Get last call date
            last_call_result = await session.execute(
                select(Call.started_at)
                .where(Call.customer_id == customer_id)
                .order_by(Call.started_at.desc())
                .limit(1)
            )
            last_call = last_call_result.scalar_one_or_none()
            last_call_date = last_call.date() if last_call else None
            
            pending.append(PendingCustomer(
                customer_id=customer_id,
                customer_name=row.customer_name,
                customer_phone=row.customer_phone,
                policy_id=row.policy_id,
                policy_name=row.policy_name,
                end_date=row.end_date,
                days_to_expiry=days_to_expiry,
                last_call_date=last_call_date,
                call_count=call_count
            ))
            seen_customers.add(customer_id)
        
        if len(pending) >= limit:
            break
    
    return pending


# =============================================================================
# SCHEDULED CALLS CRUD
# =============================================================================

async def create_scheduled_call(
    session: AsyncSession,
    data: ScheduledCallCreate
) -> ScheduledCall:
    """Create a new scheduled call."""
    scheduled_call = ScheduledCall(
        customer_id=data.customer_id,
        scheduled_date=data.scheduled_date,
        scheduled_time=data.scheduled_time,
        reason=data.reason,
        customer_policy_id=data.customer_policy_id,
        priority=data.priority,
        notes=data.notes,
        status="pending"
    )
    
    session.add(scheduled_call)
    await session.commit()
    await session.refresh(scheduled_call)
    
    logger.info(f"Created scheduled call for customer {data.customer_id}")
    return scheduled_call


async def get_scheduled_calls(
    session: AsyncSession,
    scheduled_date: Optional[date] = None,
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get scheduled calls with optional filters."""
    stmt = (
        select(ScheduledCall, Customer)
        .join(Customer, ScheduledCall.customer_id == Customer.id)
    )
    
    if scheduled_date:
        stmt = stmt.where(ScheduledCall.scheduled_date == scheduled_date)
    if status:
        stmt = stmt.where(ScheduledCall.status == status)
    if customer_id:
        stmt = stmt.where(ScheduledCall.customer_id == customer_id)
    
    stmt = stmt.order_by(
        ScheduledCall.scheduled_date.desc(),
        ScheduledCall.priority.desc(),
        ScheduledCall.created_at.desc()
    ).limit(limit)
    
    result = await session.execute(stmt)
    
    return [
        {
            "id": sc.id,
            "customer_id": sc.customer_id,
            "customer_name": c.name,
            "customer_phone": c.phone,
            "scheduled_date": sc.scheduled_date,
            "scheduled_time": sc.scheduled_time,
            "status": sc.status,
            "reason": sc.reason,
            "celery_task_id": sc.celery_task_id,
            "call_id": sc.call_id,
            "executed_at": sc.executed_at,
            "error_message": sc.error_message,
            "priority": sc.priority,
            "notes": sc.notes,
            "created_at": sc.created_at
        }
        for sc, c in result.all()
    ]


async def cancel_scheduled_call(
    session: AsyncSession,
    scheduled_call_id: str
) -> bool:
    """Cancel a scheduled call."""
    result = await session.execute(
        select(ScheduledCall).where(ScheduledCall.id == scheduled_call_id)
    )
    scheduled_call = result.scalar_one_or_none()
    
    if not scheduled_call:
        return False
    
    if scheduled_call.status not in ["pending", "queued"]:
        raise ValueError("Can only cancel pending or queued calls")
    
    scheduled_call.status = "cancelled"
    session.add(scheduled_call)
    await session.commit()
    
    logger.info(f"Cancelled scheduled call {scheduled_call_id}")
    return True


async def update_scheduled_call_status(
    session: AsyncSession,
    scheduled_call_id: str,
    status: str,
    call_id: Optional[str] = None,
    task_id: Optional[str] = None,
    error_message: Optional[str] = None
) -> Optional[ScheduledCall]:
    """Update a scheduled call status."""
    result = await session.execute(
        select(ScheduledCall).where(ScheduledCall.id == scheduled_call_id)
    )
    scheduled_call = result.scalar_one_or_none()
    
    if not scheduled_call:
        return None
    
    scheduled_call.status = status
    if call_id:
        scheduled_call.call_id = call_id
    if task_id:
        scheduled_call.celery_task_id = task_id
    if error_message:
        scheduled_call.error_message = error_message
    if status in ["completed", "failed"]:
        scheduled_call.executed_at = datetime.utcnow()
    
    session.add(scheduled_call)
    await session.commit()
    await session.refresh(scheduled_call)
    
    return scheduled_call


# =============================================================================
# SCHEDULER STATISTICS
# =============================================================================

async def get_scheduler_stats(session: AsyncSession) -> Dict[str, Any]:
    """Get scheduler statistics for today."""
    today = date.today()
    config = await get_scheduler_config(session)
    
    # Count scheduled calls by status for today
    scheduled_today = await session.execute(
        select(func.count(ScheduledCall.id))
        .where(ScheduledCall.scheduled_date == today)
    )
    
    completed_today = await session.execute(
        select(func.count(ScheduledCall.id))
        .where(
            ScheduledCall.scheduled_date == today,
            ScheduledCall.status == "completed"
        )
    )
    
    failed_today = await session.execute(
        select(func.count(ScheduledCall.id))
        .where(
            ScheduledCall.scheduled_date == today,
            ScheduledCall.status == "failed"
        )
    )
    
    pending_today = await session.execute(
        select(func.count(ScheduledCall.id))
        .where(
            ScheduledCall.scheduled_date == today,
            ScheduledCall.status.in_(["pending", "queued"])
        )
    )
    
    total_pending = await session.execute(
        select(func.count(ScheduledCall.id))
        .where(ScheduledCall.status.in_(["pending", "queued"]))
    )
    
    return {
        "today": today,
        "scheduled_today": scheduled_today.scalar() or 0,
        "completed_today": completed_today.scalar() or 0,
        "failed_today": failed_today.scalar() or 0,
        "pending_today": pending_today.scalar() or 0,
        "total_pending": total_pending.scalar() or 0,
        "next_scheduled_time": config.daily_call_time if config.enabled else None,
        "scheduler_enabled": config.enabled
    }


# =============================================================================
# CLEANUP
# =============================================================================

async def cleanup_old_scheduled_calls(
    session: AsyncSession,
    days: int = 30
) -> int:
    """Delete old scheduled call records."""
    cutoff_date = date.today() - timedelta(days=days)
    
    result = await session.execute(
        select(ScheduledCall)
        .where(ScheduledCall.scheduled_date < cutoff_date)
    )
    old_records = result.scalars().all()
    
    count = len(old_records)
    for record in old_records:
        await session.delete(record)
    
    await session.commit()
    
    logger.info(f"Cleaned up {count} old scheduled call records")
    return count
