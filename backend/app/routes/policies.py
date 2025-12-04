"""
Policy Routes - API endpoints for policy management
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..schemas import PolicyCreate, PolicyUpdate, PolicyResponse, PolicyWithDetails
from ..services import policy_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/policies", tags=["Policies"])


@router.post(
    "",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new policy"
)
async def create_policy(
    data: PolicyCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new policy for a customer.
    
    Example:
    ```json
    {
        "policy_number": "POL-2024-001",
        "customer_id": "uuid-here",
        "product_id": "uuid-here",
        "premium_amount": 5000,
        "sum_assured": 500000,
        "start_date": "2024-01-01",
        "end_date": "2025-01-01"
    }
    ```
    """
    try:
        policy = await policy_service.create_policy(session, data)
        return policy
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "",
    response_model=List[PolicyResponse],
    summary="List policies"
)
async def list_policies(
    session: AsyncSession = Depends(get_session),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    policy_status: Optional[str] = Query(None, alias="status", description="Filter by status")
):
    """List all policies with optional filters."""
    return await policy_service.list_policies(
        session,
        customer_id=customer_id,
        product_id=product_id,
        status=policy_status
    )


@router.get(
    "/expiring-soon",
    response_model=List[PolicyResponse],
    summary="Get policies expiring within N days"
)
async def get_expiring_policies(
    session: AsyncSession = Depends(get_session),
    days: int = Query(30, description="Number of days to check for expiration")
):
    """Get policies that are expiring within the specified number of days."""
    return await policy_service.get_expiring_policies(session, days=days)


@router.get(
    "/{policy_id}",
    response_model=PolicyResponse,
    summary="Get policy by ID"
)
async def get_policy(
    policy_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a single policy by ID."""
    policy = await policy_service.get_policy(session, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.get(
    "/{policy_id}/details",
    response_model=PolicyWithDetails,
    summary="Get policy with full details"
)
async def get_policy_with_details(
    policy_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get policy with customer and product details."""
    policy = await policy_service.get_policy_with_details(session, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.put(
    "/{policy_id}",
    response_model=PolicyResponse,
    summary="Update a policy"
)
async def update_policy(
    policy_id: str,
    data: PolicyUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update policy information including dates, premium, sum assured, and status."""
    policy = await policy_service.update_policy(
        session,
        policy_id,
        status=data.status,
        premium_amount=data.premium_amount,
        sum_assured=data.sum_assured,
        start_date=data.start_date,
        end_date=data.end_date
    )
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.post(
    "/{policy_id}/renew",
    response_model=PolicyResponse,
    summary="Renew a policy"
)
async def renew_policy(
    policy_id: str,
    data: dict,
    session: AsyncSession = Depends(get_session)
):
    """Renew an existing policy."""
    try:
        policy = await policy_service.renew_policy(
            session,
            policy_id,
            new_premium=data.get("new_premium"),
            extension_months=data.get("extension_months", 12)
        )
        if not policy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
        return policy
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
