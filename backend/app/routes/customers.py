"""
Customer Routes - API endpoints for customer management
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..schemas import (
    CustomerCreate, CustomerResponse,
    CustomerPolicyCreate, CustomerPolicyResponse, CustomerPolicyWithDetails
)
from ..services import customer_service
from ..services import customer_policy_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/customers", tags=["Customers"])


# =============================================================================
# CUSTOMER POLICY ENDPOINTS (attach/detach/list policies)
# =============================================================================

@router.get(
    "/{customer_id}/policies",
    response_model=List[CustomerPolicyWithDetails],
    summary="Get customer's policies"
)
async def get_customer_policies(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    status_filter: Optional[str] = Query(None, alias="status")
):
    """Get all policies attached to a customer."""
    customer = await customer_service.get_customer(session, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    return await customer_policy_service.get_customer_policies(session, customer_id, status=status_filter)


@router.post(
    "/{customer_id}/policies",
    response_model=CustomerPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach policy to customer"
)
async def attach_policy(
    customer_id: str,
    data: CustomerPolicyCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Attach a policy to a customer.
    
    Example:
    ```json
    {
        "policy_id": "uuid-here",
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "premium_amount": 25000,
        "sum_assured": 500000
    }
    ```
    """
    try:
        cp = await customer_policy_service.attach_policy_to_customer(session, customer_id, data)
        return cp
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{customer_id}/policies/{customer_policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Detach policy from customer"
)
async def detach_policy(
    customer_id: str,
    customer_policy_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Detach (cancel) a customer policy subscription by its ID."""
    success = await customer_policy_service.detach_policy_by_id(session, customer_id, customer_policy_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer policy not found")


# =============================================================================
# EXPIRING POLICIES
# =============================================================================

@router.get(
    "/expiring-policies",
    response_model=List[CustomerPolicyWithDetails],
    summary="Get policies expiring soon"
)
async def get_expiring_policies(
    session: AsyncSession = Depends(get_session),
    days: int = Query(30, description="Number of days to check", ge=1, le=365)
):
    """Get all customer policies expiring within specified days."""
    return await customer_policy_service.get_expiring_customer_policies(session, days=days)


# =============================================================================
# CUSTOMER CRUD
# =============================================================================

@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new customer"
)
async def create_customer(
    data: CustomerCreate,
    session: AsyncSession = Depends(get_session)
):
    """Add a new customer to the system."""
    try:
        customer = await customer_service.create_customer(session, data)
        return customer
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "",
    response_model=List[CustomerResponse],
    summary="List customers"
)
async def list_customers(
    session: AsyncSession = Depends(get_session),
    city: Optional[str] = Query(None, description="Filter by city")
):
    """List all customers with optional filters."""
    return await customer_service.list_customers(session, city=city)


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer by ID"
)
async def get_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a single customer by ID."""
    customer = await customer_service.get_customer(session, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update a customer"
)
async def update_customer(
    customer_id: str,
    data: dict,
    session: AsyncSession = Depends(get_session)
):
    """Update customer information."""
    customer = await customer_service.update_customer(
        session,
        customer_id,
        name=data.get("name"),
        email=data.get("email"),
        phone=data.get("phone"),
        age=data.get("age"),
        city=data.get("city"),
        address=data.get("address")
    )
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a customer"
)
async def delete_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Delete a customer by ID."""
    deleted = await customer_service.delete_customer(session, customer_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
