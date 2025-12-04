"""Database Models for LiveKit Voice Agent (read-only, mirrors backend)."""
from datetime import datetime, date
from typing import Optional, List
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column, DateTime, Date, Text
from uuid import uuid4


class Customer(SQLModel, table=True):
    __tablename__ = "customers"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    customer_code: Optional[str] = Field(default=None, unique=True, index=True)
    name: str = Field(nullable=False)
    email: Optional[str] = Field(default=None, index=True)
    phone: str = Field(unique=True, index=True, nullable=False)
    age: Optional[int] = None
    city: Optional[str] = None
    address: Optional[str] = Field(default=None, sa_column=Column(Text))
    last_call_date: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    call_status: Optional[str] = None
    interested_in_renewal: Optional[bool] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))


class Product(SQLModel, table=True):
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
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))


class Policy(SQLModel, table=True):
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
    renewal_reminder_sent: bool = False
    renewed_policy_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))


class Call(SQLModel, table=True):
    __tablename__ = "calls"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    customer_id: str = Field(foreign_key="customers.id", index=True)
    customer_phone: str = Field(index=True)
    customer_name: str
    room_name: str = Field(index=True)
    status: str = Field(default="initiated")
    started_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    ended_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    duration_seconds: Optional[int] = None
    outcome: Optional[str] = None
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    transcript: Optional[str] = Field(default=None, sa_column=Column(Text))
    interested_product_id: Optional[str] = Field(default=None, foreign_key="products.id")
