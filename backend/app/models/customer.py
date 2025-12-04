"""
Customer Model - Customer Information
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, Text
from uuid import uuid4


class Customer(SQLModel, table=True):
    """
    Customer information.
    
    Stores customer personal details and contact information.
    Customers can have multiple policies.
    """
    __tablename__ = "customers"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    
    # Customer identification
    customer_code: Optional[str] = Field(default=None, unique=True, index=True)  # e.g., "CUST001"
    
    # Personal info
    name: str = Field(nullable=False)
    email: Optional[str] = Field(default=None, index=True)
    phone: str = Field(unique=True, index=True, nullable=False)  # E.164 format
    
    # Additional info
    age: Optional[int] = Field(default=None)
    city: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Call tracking (for renewal campaigns)
    last_call_date: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    call_status: Optional[str] = Field(default=None)  # pending, calling, completed, failed
    interested_in_renewal: Optional[bool] = Field(default=None)
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
