"""Call Routes - API endpoints for call management."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..schemas import CallSummary, CallResponse
from ..services import call_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calls", tags=["Calls"])


@router.post("/initiate/{customer_id}", response_model=CallResponse)
async def initiate_call(customer_id: str, session: AsyncSession = Depends(get_session)):
    """Initiate AI call to customer via LiveKit SIP."""
    try:
        return await call_service.initiate_call(session, customer_id)
    except ValueError as e:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(status_code=code, detail=str(e))
    except Exception as e:
        logger.error(f"Call failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate call")


@router.get("", response_model=List[CallResponse])
async def list_calls(
    session: AsyncSession = Depends(get_session),
    customer_id: Optional[str] = Query(None),
    call_status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, le=500)
):
    """List calls with optional filters."""
    return await call_service.list_calls(session, customer_id=customer_id, status=call_status, limit=limit)


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(call_id: str, session: AsyncSession = Depends(get_session)):
    """Get call by ID."""
    call = await call_service.get_call(session, call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.put("/{call_id}/summary", response_model=CallResponse)
async def update_call_summary(call_id: str, data: CallSummary, session: AsyncSession = Depends(get_session)):
    """Update call summary after completion."""
    call = await call_service.update_call_summary(
        session, call_id, outcome=data.outcome, notes=data.notes, interested_product_id=data.interested_product_id
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.put("/{call_id}/status", response_model=CallResponse)
async def update_call_status(call_id: str, data: dict, session: AsyncSession = Depends(get_session)):
    """Update call status."""
    if not data.get("status"):
        raise HTTPException(status_code=400, detail="Status required")
    call = await call_service.update_call_status(session, call_id, status=data["status"])
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.post("/batch", response_model=List[CallResponse])
async def batch_initiate_calls(data: dict, session: AsyncSession = Depends(get_session)):
    """Batch initiate calls to multiple customers."""
    customer_ids = data.get("customer_ids", [])
    if not customer_ids:
        raise HTTPException(status_code=400, detail="customer_ids required")
    
    results = []
    for cid in customer_ids:
        try:
            results.append(await call_service.initiate_call(session, cid))
        except Exception as e:
            logger.warning(f"Batch call failed for {cid}: {e}")
    return results
