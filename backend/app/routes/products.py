"""
Product Routes - API endpoints for product management
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..schemas import ProductCreate, ProductResponse
from ..services import product_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new product"
)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Add a new insurance product.
    
    Example:
    ```json
    {
        "product_code": "HEALTH_BASIC",
        "product_name": "Health Basic Plan",
        "product_type": "Health",
        "base_premium": 5000,
        "sum_assured_options": [100000, 200000, 500000],
        "features": ["Cashless hospitalization"],
        "eligibility": {"min_age": 18, "max_age": 65}
    }
    ```
    """
    try:
        product = await product_service.create_product(session, data)
        return product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "",
    response_model=List[ProductResponse],
    summary="List products"
)
async def list_products(
    session: AsyncSession = Depends(get_session),
    product_type: Optional[str] = Query(None, description="Filter by type (Health, Life, Motor, etc.)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """List all products with optional filters."""
    return await product_service.list_products(session, product_type=product_type, is_active=is_active)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID"
)
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a single product by ID."""
    product = await product_service.get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product"
)
async def update_product(
    product_id: str,
    data: dict,
    session: AsyncSession = Depends(get_session)
):
    """Update product information."""
    product = await product_service.update_product(
        session,
        product_id,
        name=data.get("name"),
        base_premium=data.get("base_premium"),
        sum_assured_options=data.get("sum_assured_options"),
        features=data.get("features"),
        eligibility=data.get("eligibility"),
        is_active=data.get("is_active")
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product"
)
async def delete_product(
    product_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Delete (deactivate) a product by ID."""
    deleted = await product_service.delete_product(session, product_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
