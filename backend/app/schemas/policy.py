"""
Policy Schemas - Request/Response models for Policy API
"""
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel


class PolicyCreate(SQLModel):
    """Schema for creating a policy."""
    policy_number: str
    customer_id: str
    product_id: str
    premium_amount: int
    sum_assured: int
    start_date: date
    end_date: date


class PolicyUpdate(SQLModel):
    """Schema for updating a policy."""
    premium_amount: Optional[int] = None
    sum_assured: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None


class PolicyResponse(SQLModel):
    """Schema for policy response."""
    id: str
    policy_number: str
    customer_id: str
    product_id: str
    premium_amount: int
    sum_assured: int
    start_date: date
    end_date: date
    status: str
    renewal_reminder_sent: bool
    created_at: datetime


class PolicyWithDetails(SQLModel):
    """Schema for policy with product and customer details."""
    id: str
    policy_number: str
    customer_id: str
    premium_amount: int
    sum_assured: int
    start_date: date
    end_date: date
    status: str
    # Product info
    product_code: str
    product_name: str
    product_type: str
    # Customer info
    customer_name: str
    customer_phone: str
