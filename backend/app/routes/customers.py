"""
Customer Routes - API endpoints for customer management
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..schemas import CustomerCreate, CustomerResponse
from ..services import customer_service, policy_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get(
    "/expiring-policies",
    response_model=List[CustomerResponse],
    summary="Get customers with expiring policies"
)
async def get_customers_with_expiring_policies(
    session: AsyncSession = Depends(get_session),
    days: int = Query(30, description="Number of days to check for policy expiration", ge=1, le=365)
):
    """
    Get all customers whose policies are expiring within the specified number of days.
    
    This is useful for:
    - Generating call lists for renewal campaigns
    - Sending reminder notifications
    - Planning outreach activities
    
    Returns unique customers (no duplicates even if they have multiple expiring policies).
    """
    return await customer_service.get_customers_with_expiring_policies(session, days=days)


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
    """
    Add a new customer to the system.
    
    Example:
    ```json
    {
        "customer_code": "CUST001",
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+919876543210",
        "age": 35,
        "city": "Mumbai",
        "address": "123 Main Street"
    }
    ```
    """
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
