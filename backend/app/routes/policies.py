"""
Policy Routes - API endpoints for policy TEMPLATE management
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..schemas import PolicyCreate, PolicyUpdate, PolicyResponse, PolicyWithProduct
from ..services import policy_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/policies", tags=["Policies"])


@router.post(
    "",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new policy template"
)
async def create_policy(
    data: PolicyCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new policy template.
    
    Example:
    ```json
    {
        "policy_number": "POL-2024-001",
        "policy_name": "Family Health Basic 2024",
        "product_id": "uuid-here",
        "base_premium": 25000,
        "base_sum_assured": 500000,
        "duration_months": 12,
        "description": "Basic health coverage for families"
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
    summary="List policy templates"
)
async def list_policies(
    session: AsyncSession = Depends(get_session),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """List all policy templates with optional filters."""
    return await policy_service.list_policies(
        session,
        product_id=product_id,
        is_active=is_active
    )


@router.get(
    "/with-products",
    response_model=List[PolicyWithProduct],
    summary="List policy templates with product details"
)
async def list_policies_with_products(
    session: AsyncSession = Depends(get_session),
    is_active: Optional[bool] = Query(True, description="Filter by active status")
):
    """List policy templates with product details for selection."""
    return await policy_service.list_policies_with_products(session, is_active=is_active)


@router.get(
    "/{policy_id}",
    response_model=PolicyResponse,
    summary="Get policy by ID"
)
async def get_policy(
    policy_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a single policy template by ID."""
    policy = await policy_service.get_policy(session, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.put(
    "/{policy_id}",
    response_model=PolicyResponse,
    summary="Update a policy template"
)
async def update_policy(
    policy_id: str,
    data: PolicyUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update policy template information."""
    policy = await policy_service.update_policy(
        session,
        policy_id,
        policy_name=data.policy_name,
        base_premium=data.base_premium,
        base_sum_assured=data.base_sum_assured,
        duration_months=data.duration_months,
        description=data.description,
        is_active=data.is_active
    )
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.delete(
    "/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a policy template"
)
async def delete_policy(
    policy_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Deactivate a policy template (soft delete)."""
    success = await policy_service.delete_policy(session, policy_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
