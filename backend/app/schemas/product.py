"""
Product Schemas - Request/Response models for Product API
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel


class ProductCreate(SQLModel):
    """Schema for creating a product."""
    product_code: str
    product_name: str
    product_type: str  # Health, Life, Motor, Home
    base_premium: int
    sum_assured_options: List[int] = []
    features: List[str] = []
    eligibility: dict = {}
    description: Optional[str] = None
    min_age: Optional[int] = 18
    max_age: Optional[int] = 65


class ProductUpdate(SQLModel):
    """Schema for updating a product."""
    product_name: Optional[str] = None
    base_premium: Optional[int] = None
    sum_assured_options: Optional[List[int]] = None
    features: Optional[List[str]] = None
    eligibility: Optional[dict] = None
    description: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(SQLModel):
    """Schema for product response."""
    id: str
    product_code: str
    product_name: str
    product_type: str
    base_premium: int
    sum_assured_options: List[int]
    features: List[str]
    eligibility: dict
    description: Optional[str]
    min_age: Optional[int]
    max_age: Optional[int]
    is_active: bool
    created_at: datetime

