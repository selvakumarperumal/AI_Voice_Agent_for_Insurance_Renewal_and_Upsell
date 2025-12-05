"""
Policy Schemas - Request/Response models for Policy API (Template model)
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel


class PolicyCreate(SQLModel):
    """Schema for creating a policy template."""
    policy_number: str
    policy_name: str
    product_id: str
    base_premium: int
    base_sum_assured: int
    duration_months: int = 12
    description: Optional[str] = None


class PolicyUpdate(SQLModel):
    """Schema for updating a policy template."""
    policy_name: Optional[str] = None
    base_premium: Optional[int] = None
    base_sum_assured: Optional[int] = None
    duration_months: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PolicyResponse(SQLModel):
    """Schema for policy template response."""
    id: str
    policy_number: str
    policy_name: str
    product_id: str
    base_premium: int
    base_sum_assured: int
    duration_months: int
    is_active: bool
    description: Optional[str]
    created_at: datetime


class PolicyWithProduct(SQLModel):
    """Schema for policy with product details."""
    id: str
    policy_number: str
    policy_name: str
    product_id: str
    product_name: str
    product_type: str
    base_premium: int
    base_sum_assured: int
    duration_months: int
    is_active: bool
    description: Optional[str]

