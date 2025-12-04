"""
Call Model - Call History
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, Text
from uuid import uuid4


class Call(SQLModel, table=True):
    """
    Call log for tracking outbound calls.
    
    Records all calls made to customers for renewals or upsells.
    """
    __tablename__ = "calls"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    
    # Relationships
    customer_id: str = Field(foreign_key="customers.id", index=True)
    
    # Call info
    customer_phone: str = Field(index=True)
    customer_name: str
    room_name: str = Field(index=True)  # LiveKit room name
    
    # Call status
    status: str = Field(default="initiated")  # initiated, in_progress, completed, failed, no_answer
    
    # Timing
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    ended_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    duration_seconds: Optional[int] = Field(default=None)
    
    # Outcome
    outcome: Optional[str] = Field(default=None)  # interested, not_interested, callback, upsell_accepted
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Call summary and transcript
    summary: Optional[str] = Field(default=None, sa_column=Column(Text))  # AI-generated summary
    transcript: Optional[str] = Field(default=None, sa_column=Column(Text))  # Full conversation transcript
    
    # If customer was interested in a specific product
    interested_product_id: Optional[str] = Field(default=None, foreign_key="products.id")
