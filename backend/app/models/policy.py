"""
Policy Model - Customer's Active Policies
"""
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, Date
from uuid import uuid4


class Policy(SQLModel, table=True):
    """
    Customer's active insurance policies.
    
    A policy is a specific instance of a product purchased by a customer.
    It has customized terms like:
        - Specific sum assured (from product options)
        - Premium (may vary based on customer profile)
        - Start and end dates
    """
    __tablename__ = "policies"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    
    # Policy identification
    policy_number: str = Field(unique=True, index=True)  # e.g., "HLT/2024/001234"
    
    # Relationships
    customer_id: str = Field(foreign_key="customers.id", index=True)
    product_id: str = Field(foreign_key="products.id", index=True)
    
    # Policy terms
    premium_amount: int = Field(nullable=False)  # Annual premium in INR
    sum_assured: int = Field(nullable=False)  # Coverage amount in INR
    
    # Policy period
    start_date: date = Field(sa_column=Column(Date, nullable=False))
    end_date: date = Field(sa_column=Column(Date, nullable=False, index=True))
    
    # Status
    status: str = Field(default="active", index=True)  # active, expired, cancelled, renewed
    
    # Renewal tracking
    renewal_reminder_sent: bool = Field(default=False)
    renewed_policy_id: Optional[str] = Field(default=None)  # Links to new policy if renewed
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
