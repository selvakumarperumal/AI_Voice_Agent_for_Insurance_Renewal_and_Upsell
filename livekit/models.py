"""
Database Models for LiveKit Voice Agent.

These models mirror the backend models to read from the same database.
They are read-only for the voice agent.
"""
from datetime import datetime, date
from typing import Optional, List
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column, DateTime, Date, Text
from uuid import uuid4


class Customer(SQLModel, table=True):
    """Customer information."""
    __tablename__ = "customers"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    customer_code: Optional[str] = Field(default=None, unique=True, index=True)
    name: str = Field(nullable=False)
    email: Optional[str] = Field(default=None, index=True)
    phone: str = Field(unique=True, index=True, nullable=False)
    age: Optional[int] = Field(default=None)
    city: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None, sa_column=Column(Text))
    last_call_date: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    call_status: Optional[str] = Field(default=None)
    interested_in_renewal: Optional[bool] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))


class Product(SQLModel, table=True):
    """Insurance product catalog."""
    __tablename__ = "products"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    product_code: str = Field(unique=True, index=True)
    product_name: str = Field(nullable=False)
    product_type: str = Field(index=True)
    base_premium: int = Field(nullable=False)
    sum_assured_options: List[int] = Field(default=[], sa_column=Column(JSON))
    features: List[str] = Field(default=[], sa_column=Column(JSON))
    eligibility: dict = Field(default={}, sa_column=Column(JSON))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))


class Policy(SQLModel, table=True):
    """Customer's active insurance policies."""
    __tablename__ = "policies"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    policy_number: str = Field(unique=True, index=True)
    customer_id: str = Field(foreign_key="customers.id", index=True)
    product_id: str = Field(foreign_key="products.id", index=True)
    premium_amount: int = Field(nullable=False)
    sum_assured: int = Field(nullable=False)
    start_date: date = Field(sa_column=Column(Date, nullable=False))
    end_date: date = Field(sa_column=Column(Date, nullable=False, index=True))
    status: str = Field(default="active", index=True)
    renewal_reminder_sent: bool = Field(default=False)
    renewed_policy_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))


class Call(SQLModel, table=True):
    """Call log for tracking outbound calls."""
    __tablename__ = "calls"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    customer_id: str = Field(foreign_key="customers.id", index=True)
    customer_phone: str = Field(index=True)
    customer_name: str
    room_name: str = Field(index=True)
    status: str = Field(default="initiated")
    started_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    ended_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    duration_seconds: Optional[int] = Field(default=None)
    outcome: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    summary: Optional[str] = Field(default=None, sa_column=Column(Text))  # AI-generated summary
    transcript: Optional[str] = Field(default=None, sa_column=Column(Text))  # Full conversation transcript
    interested_product_id: Optional[str] = Field(default=None, foreign_key="products.id")
