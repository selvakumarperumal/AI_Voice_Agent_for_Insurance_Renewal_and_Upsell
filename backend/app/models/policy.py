"""
Policy Model - Insurance Policy Templates
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime
from uuid import uuid4


class Policy(SQLModel, table=True):
    """
    Insurance policy template.
    
    A policy is a configured offering based on a product.
    Multiple customers can subscribe to the same policy via CustomerPolicy.
    
    Example:
        - Policy: "Family Health Shield - Basic Plan 2024"
        - Product: "Family Health Shield"
        - Customers subscribe via CustomerPolicy table
    """
    __tablename__ = "policies"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    
    # Policy identification
    policy_number: str = Field(unique=True, index=True)  # e.g., "HLT/2024/001234"
    policy_name: str = Field(default="")  # e.g., "Family Health Basic 2024"
    
    # Product reference
    product_id: str = Field(foreign_key="products.id", index=True)
    
    # Default terms (can be customized per customer in CustomerPolicy)
    base_premium: int = Field(nullable=False)  # Default annual premium in INR
    base_sum_assured: int = Field(nullable=False)  # Default coverage amount in INR
    
    # Policy duration (default)
    duration_months: int = Field(default=12)  # Default policy duration
    
    # Status: active, inactive
    is_active: bool = Field(default=True)
    
    # Description
    description: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

