"""
Call Schemas - Request/Response models for Call API
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel


class CallSummary(SQLModel):
    """Schema for call summary from AI agent."""
    outcome: Optional[str] = None
    notes: Optional[str] = None
    interested_product_id: Optional[str] = None


class CallResponse(SQLModel):
    """Schema for call response."""
    id: str
    customer_id: str
    customer_phone: str
    customer_name: str
    room_name: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    outcome: Optional[str]
    notes: Optional[str]
    summary: Optional[str]  # AI-generated summary
    transcript: Optional[str]  # Full conversation transcript
    interested_product_id: Optional[str]
