"""
Call Routes - API endpoints for call management and LiveKit SIP calling
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..schemas import CallSummary, CallResponse
from ..services import call_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calls", tags=["Calls"])


@router.post(
    "/initiate/{customer_id}",
    response_model=CallResponse,
    summary="Initiate a call to a customer"
)
async def initiate_call(
    customer_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Initiate an AI-powered outbound call to a customer using LiveKit SIP.
    
    The call will:
    1. Create a new call record
    2. Set up a LiveKit room with AI agent
    3. Place the outbound SIP call to the customer
    """
    try:
        call = await call_service.initiate_call(session, customer_id)
        return call
    except ValueError as e:
        error_msg = str(e)
        # Distinguish between customer not found vs call failed
        if "Customer not found" in error_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            # Call failed (busy, no answer, SIP error, etc.)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg)
    except Exception as e:
        logger.error(f"Failed to initiate call: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate call"
        )


@router.get(
    "",
    response_model=List[CallResponse],
    summary="List calls"
)
async def list_calls(
    session: AsyncSession = Depends(get_session),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    call_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(100, le=500, description="Limit number of results")
):
    """List all calls with optional filters."""
    return await call_service.list_calls(
        session,
        customer_id=customer_id,
        status=call_status,
        limit=limit
    )


@router.get(
    "/{call_id}",
    response_model=CallResponse,
    summary="Get call by ID"
)
async def get_call(
    call_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a single call by ID."""
    call = await call_service.get_call(session, call_id)
    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")
    return call


@router.put(
    "/{call_id}/summary",
    response_model=CallResponse,
    summary="Update call summary and outcome"
)
async def update_call_summary(
    call_id: str,
    data: CallSummary,
    session: AsyncSession = Depends(get_session)
):
    """
    Update the call with summary, outcome, and notes after the call ends.
    
    This is typically called by the AI agent after the conversation completes.
    """
    call = await call_service.update_call_summary(
        session,
        call_id,
        outcome=data.outcome,
        notes=data.notes,
        interested_product_id=data.interested_product_id
    )
    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")
    return call


@router.put(
    "/{call_id}/status",
    response_model=CallResponse,
    summary="Update call status"
)
async def update_call_status(
    call_id: str,
    data: dict,
    session: AsyncSession = Depends(get_session)
):
    """
    Update the status of a call.
    
    Statuses: pending, in_progress, completed, failed
    """
    new_status = data.get("status")
    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status is required"
        )
    
    call = await call_service.update_call_status(session, call_id, status=new_status)
    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")
    return call


@router.post(
    "/batch",
    response_model=List[CallResponse],
    summary="Initiate calls to multiple customers"
)
async def batch_initiate_calls(
    data: dict,
    session: AsyncSession = Depends(get_session)
):
    """
    Initiate calls to multiple customers in batch.
    
    Example:
    ```json
    {
        "customer_ids": ["uuid-1", "uuid-2", "uuid-3"]
    }
    ```
    """
    customer_ids = data.get("customer_ids", [])
    if not customer_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customer_ids list is required"
        )
    
    results = []
    for customer_id in customer_ids:
        try:
            call = await call_service.initiate_call(session, customer_id)
            results.append(call)
        except Exception as e:
            logger.warning(f"Failed to initiate call for {customer_id}: {e}")
    
    return results
