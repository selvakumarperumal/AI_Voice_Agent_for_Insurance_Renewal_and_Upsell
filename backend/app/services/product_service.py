"""
Product Service Module

Handles all product catalog operations.
Products are insurance offerings that can be sold to customers.
"""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models import Product
from ..schemas import ProductCreate


logger = logging.getLogger(__name__)


# =============================================================================
# PRODUCT CRUD OPERATIONS
# =============================================================================

async def create_product(session: AsyncSession, data: ProductCreate) -> Product:
    """
    Create a new insurance product.
    
    Args:
        session: Database session
        data: Product creation data
        
    Returns:
        Created Product object
        
    Raises:
        ValueError: If product code already exists
    """
    # Check if product code exists
    existing = await get_product_by_code(session, data.product_code)
    if existing:
        raise ValueError(f"Product with code {data.product_code} already exists")
    
    product = Product(**data.model_dump())
    session.add(product)
    await session.commit()
    await session.refresh(product)
    
    logger.info(f"Created product: {product.product_name} ({product.product_code})")
    return product


async def get_product(session: AsyncSession, product_id: str) -> Optional[Product]:
    """Get a product by ID."""
    stmt = select(Product).where(Product.id == product_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_product_by_code(session: AsyncSession, product_code: str) -> Optional[Product]:
    """Get a product by its code."""
    stmt = select(Product).where(Product.product_code == product_code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_products(
    session: AsyncSession,
    product_type: Optional[str] = None,
    is_active: Optional[bool] = None
) -> List[Product]:
    """
    List all products, optionally filtered by type and status.
    
    Args:
        session: Database session
        product_type: Filter by type (Health, Life, Motor, Home)
        is_active: Filter by active status (None = all, True = active only, False = inactive only)
    """
    stmt = select(Product)
    
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)
    
    if product_type:
        stmt = stmt.where(Product.product_type == product_type)
    
    stmt = stmt.order_by(Product.product_type, Product.product_name)
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_product(
    session: AsyncSession,
    product_id: str,
    name: Optional[str] = None,
    base_premium: Optional[int] = None,
    sum_assured_options: Optional[List[int]] = None,
    features: Optional[List[str]] = None,
    eligibility: Optional[dict] = None,
    is_active: Optional[bool] = None
) -> Optional[Product]:
    """
    Update a product.
    
    Args:
        session: Database session
        product_id: Product ID to update
        name: New product name
        base_premium: New base premium
        sum_assured_options: New coverage options
        features: New features list
        eligibility: New eligibility criteria
        is_active: Active status
    """
    product = await get_product(session, product_id)
    if not product:
        return None
    
    # Update only provided fields
    if name is not None:
        product.product_name = name
    if base_premium is not None:
        product.base_premium = base_premium
    if sum_assured_options is not None:
        product.sum_assured_options = sum_assured_options
    if features is not None:
        product.features = features
    if eligibility is not None:
        product.eligibility = eligibility
    if is_active is not None:
        product.is_active = is_active
    
    session.add(product)
    await session.commit()
    await session.refresh(product)
    
    logger.info(f"Updated product: {product.product_code}")
    return product


async def delete_product(session: AsyncSession, product_id: str) -> bool:
    """
    Delete a product (or deactivate if has policies).
    
    Args:
        session: Database session
        product_id: Product ID to delete
        
    Returns:
        True if deleted/deactivated, False if not found
    """
    product = await get_product(session, product_id)
    if not product:
        return False
    
    # For safety, we deactivate instead of delete
    product.is_active = False
    session.add(product)
    await session.commit()
    
    logger.info(f"Deactivated product: {product.product_code}")
    return True


async def get_product_types(session: AsyncSession) -> List[str]:
    """Get list of distinct product types."""
    stmt = select(Product.product_type).distinct()
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]
