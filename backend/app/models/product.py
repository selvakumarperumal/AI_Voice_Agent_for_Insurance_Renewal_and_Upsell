"""
Product Model - Insurance Products Catalog
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column, DateTime, Text
from uuid import uuid4


class Product(SQLModel, table=True):
    """
    Insurance product catalog.
    
    Companies can add different insurance products here.
    Each product defines the base terms, and customers buy policies
    based on these products with customized options.
    
    Example products:
        - Family Health Shield (Health Insurance)
        - Term Life Protector (Life Insurance)
        - Comprehensive Car Cover (Motor Insurance)
    """
    __tablename__ = "products"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    
    # Product identification
    product_code: str = Field(unique=True, index=True)  # e.g., "PROD001"
    product_name: str = Field(nullable=False)  # e.g., "Family Health Shield"
    product_type: str = Field(index=True)  # Health, Life, Motor, Home
    
    # Pricing
    base_premium: int = Field(nullable=False)  # Base annual premium in INR
    
    # Coverage options (stored as JSON array)
    sum_assured_options: List[int] = Field(default=[], sa_column=Column(JSON))
    
    # Features (stored as JSON array)
    features: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Eligibility criteria (stored as JSON object)
    eligibility: dict = Field(default={}, sa_column=Column(JSON))
    
    # Product description
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Status
    is_active: bool = Field(default=True)  # Can be deactivated
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
