"""
Scheduler Schemas - Request/Response models for Scheduler API
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel


class SchedulerConfigResponse(BaseModel):
    """Response model for scheduler configuration."""
    enabled: bool
    daily_call_time: str
    days_before_expiry: int
    max_calls_per_day: int
    max_concurrent_calls: int
    retry_failed_after_hours: int
    max_retries_per_customer: int
    skip_if_called_within_days: int
    updated_at: datetime


class SchedulerConfigUpdate(BaseModel):
    """Request model for updating scheduler configuration."""
    enabled: Optional[bool] = None
    daily_call_time: Optional[str] = None
    days_before_expiry: Optional[int] = None
    max_calls_per_day: Optional[int] = None
    max_concurrent_calls: Optional[int] = None
    retry_failed_after_hours: Optional[int] = None
    max_retries_per_customer: Optional[int] = None
    skip_if_called_within_days: Optional[int] = None


class ScheduledCallResponse(BaseModel):
    """Response model for a scheduled call."""
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    scheduled_date: date
    scheduled_time: Optional[str] = None
    status: str
    reason: str
    celery_task_id: Optional[str] = None
    call_id: Optional[str] = None
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    priority: int
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ScheduledCallCreate(BaseModel):
    """Request model for creating a scheduled call."""
    customer_id: str
    scheduled_date: date
    scheduled_time: Optional[str] = None
    reason: str = "manual"
    customer_policy_id: Optional[str] = None
    priority: int = 0
    notes: Optional[str] = None


class PendingCustomer(BaseModel):
    """Customer pending a scheduled call."""
    customer_id: str
    customer_name: str
    customer_phone: str
    policy_id: str
    policy_name: str
    end_date: date
    days_to_expiry: int
    last_call_date: Optional[date] = None
    call_count: int = 0


class PendingCustomersResponse(BaseModel):
    """Response for pending customers endpoint."""
    count: int
    customers: List[PendingCustomer]


class SchedulerStatsResponse(BaseModel):
    """Response model for scheduler statistics."""
    today: date
    scheduled_today: int
    completed_today: int
    failed_today: int
    pending_today: int
    total_pending: int
    next_scheduled_time: Optional[str] = None
    scheduler_enabled: bool


class TriggerNowResponse(BaseModel):
    """Response for manual trigger."""
    success: bool
    message: str
    task_id: Optional[str] = None
    queued_count: int = 0
