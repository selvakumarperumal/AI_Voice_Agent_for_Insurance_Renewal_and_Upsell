"""
CustomerPolicy Model - Junction table for Customer-Policy many-to-many relationship
"""
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime
from uuid import uuid4


class CustomerPolicy(SQLModel, table=True):
    """
    Junction table linking customers to policies.
    
    A policy is a template (e.g., "Family Health Shield - Basic Plan").
    Each CustomerPolicy represents a customer's subscription to that policy
    with their specific dates and status.
    """
    __tablename__ = "customer_policies"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    
    # Foreign keys
    customer_id: str = Field(foreign_key="customers.id", index=True)
    policy_id: str = Field(foreign_key="policies.id", index=True)
    
    # Subscription details
    start_date: date = Field(nullable=False)
    end_date: date = Field(nullable=False)
    premium_amount: int = Field(nullable=False)  # Customer-specific premium
    sum_assured: int = Field(nullable=False)  # Customer-specific coverage
    
    # Status: active, expired, cancelled
    status: str = Field(default="active", index=True)
    
    # Renewal tracking
    renewal_reminder_sent: bool = Field(default=False)
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
