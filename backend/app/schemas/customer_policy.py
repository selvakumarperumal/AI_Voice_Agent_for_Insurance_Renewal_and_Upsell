"""
CustomerPolicy Schemas - Request/Response models for CustomerPolicy API
"""
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel


class CustomerPolicyCreate(SQLModel):
    """Schema for attaching a policy to a customer."""
    policy_id: str
    start_date: date
    end_date: date
    premium_amount: Optional[int] = None  # Uses policy default if not specified
    sum_assured: Optional[int] = None  # Uses policy default if not specified


class CustomerPolicyUpdate(SQLModel):
    """Schema for updating a customer's policy subscription."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    premium_amount: Optional[int] = None
    sum_assured: Optional[int] = None
    status: Optional[str] = None


class CustomerPolicyResponse(SQLModel):
    """Schema for customer policy subscription response."""
    id: str
    customer_id: str
    policy_id: str
    start_date: date
    end_date: date
    premium_amount: int
    sum_assured: int
    status: str
    renewal_reminder_sent: bool
    created_at: datetime


class CustomerPolicyWithDetails(SQLModel):
    """Customer policy with policy and product details."""
    id: str
    customer_id: str
    customer_name: str
    policy_id: str
    policy_number: str
    policy_name: str
    product_name: str
    product_type: str
    start_date: date
    end_date: date
    premium_amount: int
    sum_assured: int
    status: str
    days_to_expiry: Optional[int] = None
