"""
ScheduledCall Model - Tracks scheduled and executed calls
"""
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, Text
from uuid import uuid4


class ScheduledCall(SQLModel, table=True):
    """
    Tracks scheduled calls for the auto-scheduler.
    
    Records when calls are scheduled, their status, and execution results.
    """
    __tablename__ = "scheduled_calls"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    
    # Customer reference
    customer_id: str = Field(foreign_key="customers.id", index=True)
    
    # Scheduling info
    scheduled_date: date = Field(index=True)  # Date when call should be made
    scheduled_time: Optional[str] = Field(default=None)  # Time preference (HH:MM)
    
    # Status tracking
    status: str = Field(default="pending", index=True)  # pending, queued, completed, failed, cancelled, skipped
    
    # Reason for the call
    reason: str = Field(default="expiring_policy")  # expiring_policy, follow_up, manual, renewal_reminder
    
    # Task tracking
    celery_task_id: Optional[str] = Field(default=None, index=True)  # Celery task ID if queued
    
    # Related records
    call_id: Optional[str] = Field(default=None, foreign_key="calls.id")  # Resulting call record
    customer_policy_id: Optional[str] = Field(default=None, foreign_key="customer_policies.id")  # Related policy
    
    # Execution details
    executed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Metadata
    priority: int = Field(default=0)  # Higher = more urgent
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )


class SchedulerConfig(SQLModel, table=True):
    """
    Stores scheduler configuration settings.
    
    Single-row table for global scheduler settings.
    """
    __tablename__ = "scheduler_config"
    
    id: str = Field(default="default", primary_key=True)
    
    # Enable/disable scheduler
    enabled: bool = Field(default=True)
    
    # Schedule settings
    daily_call_time: str = Field(default="10:00")  # Time to make calls (HH:MM in IST)
    days_before_expiry: int = Field(default=30)  # How many days before expiry to start calling
    
    # Limits
    max_calls_per_day: int = Field(default=50)  # Maximum calls per day
    max_concurrent_calls: int = Field(default=5)  # Maximum concurrent calls
    
    # Retry settings
    retry_failed_after_hours: int = Field(default=24)  # Retry failed calls after X hours
    max_retries_per_customer: int = Field(default=3)  # Max call attempts per customer per policy
    
    # Skip settings
    skip_if_called_within_days: int = Field(default=7)  # Don't call if customer was called recently
    
    # Timestamps
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
