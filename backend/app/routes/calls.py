"""Call Routes - Optimized API endpoints."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..schemas import CallSummary, CallResponse
from ..services import call_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calls", tags=["Calls"])


@router.post("/initiate/{customer_id}", response_model=CallResponse)
async def initiate(customer_id: str, session: AsyncSession = Depends(get_session)):
    """Fire call to customer - returns immediately."""
    try:
        return await call_service.initiate_call(session, customer_id)
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 503, detail=str(e))


@router.get("", response_model=List[CallResponse])
async def list_all(
    session: AsyncSession = Depends(get_session),
    customer_id: Optional[str] = None,
    status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, le=500)
):
    return await call_service.list_calls(session, customer_id, status, limit)


@router.get("/{call_id}", response_model=CallResponse)
async def get_one(call_id: str, session: AsyncSession = Depends(get_session)):
    call = await call_service.get_call(session, call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Not found")
    return call


@router.put("/{call_id}/summary", response_model=CallResponse)
async def update_summary(call_id: str, data: CallSummary, session: AsyncSession = Depends(get_session)):
    call = await call_service.update_summary(session, call_id, data.outcome, data.notes, data.interested_product_id)
    if not call:
        raise HTTPException(status_code=404, detail="Not found")
    return call


@router.put("/{call_id}/status", response_model=CallResponse)
async def update_status(call_id: str, data: dict, session: AsyncSession = Depends(get_session)):
    if not data.get("status"):
        raise HTTPException(status_code=400, detail="Status required")
    call = await call_service.update_status(session, call_id, data["status"])
    if not call:
        raise HTTPException(status_code=404, detail="Not found")
    return call


@router.post("/batch/expiring")
async def batch_expiring(session: AsyncSession = Depends(get_session), days: int = 30, limit: int = 10):
    """Batch call all customers with expiring policies."""
    return await call_service.batch_call_expiring(session, days, limit)
