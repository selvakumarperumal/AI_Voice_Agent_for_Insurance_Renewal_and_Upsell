"""
Customer Schemas - Request/Response models for Customer API
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel


class CustomerCreate(SQLModel):
    """Schema for creating a customer."""
    name: str
    phone: str  # E.164 format: +919123456789
    email: Optional[str] = None
    customer_code: Optional[str] = None
    age: Optional[int] = None
    city: Optional[str] = None
    address: Optional[str] = None


class CustomerUpdate(SQLModel):
    """Schema for updating a customer."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    city: Optional[str] = None
    address: Optional[str] = None


class CustomerResponse(SQLModel):
    """Schema for customer response."""
    id: str
    customer_code: Optional[str]
    name: str
    email: Optional[str]
    phone: str
    age: Optional[int]
    city: Optional[str]
    address: Optional[str]
    last_call_date: Optional[datetime]
    call_status: Optional[str]
    interested_in_renewal: Optional[bool]
    created_at: datetime
