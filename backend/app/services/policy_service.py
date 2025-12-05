"""
Policy Service Module - For Policy Templates

Handles policy template operations.
Policies are templates that customers can subscribe to via CustomerPolicy.
"""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models import Policy, Product
from ..schemas import PolicyCreate, PolicyWithProduct

logger = logging.getLogger(__name__)


async def create_policy(session: AsyncSession, data: PolicyCreate) -> Policy:
    """Create a new policy template."""
    # Check if policy number exists
    existing = await get_policy_by_number(session, data.policy_number)
    if existing:
        raise ValueError(f"Policy {data.policy_number} already exists")
    
    # Verify product exists
    stmt = select(Product).where(Product.id == data.product_id)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise ValueError(f"Product {data.product_id} not found")
    
    policy = Policy(**data.model_dump())
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    
    logger.info(f"Created policy template: {policy.policy_number}")
    return policy


async def get_policy(session: AsyncSession, policy_id: str) -> Optional[Policy]:
    """Get a policy by ID."""
    stmt = select(Policy).where(Policy.id == policy_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_policy_by_number(session: AsyncSession, policy_number: str) -> Optional[Policy]:
    """Get a policy by its number."""
    stmt = select(Policy).where(Policy.policy_number == policy_number)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_policies(
    session: AsyncSession,
    product_id: Optional[str] = None,
    is_active: Optional[bool] = None
) -> List[Policy]:
    """List policy templates with optional filters."""
    stmt = select(Policy)
    
    if product_id:
        stmt = stmt.where(Policy.product_id == product_id)
    if is_active is not None:
        stmt = stmt.where(Policy.is_active == is_active)
    
    stmt = stmt.order_by(Policy.policy_name)
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_policies_with_products(
    session: AsyncSession,
    is_active: Optional[bool] = True
) -> List[PolicyWithProduct]:
    """List policy templates with product details."""
    stmt = (
        select(Policy, Product)
        .join(Product, Policy.product_id == Product.id)
    )
    
    if is_active is not None:
        stmt = stmt.where(Policy.is_active == is_active)
    
    stmt = stmt.order_by(Policy.policy_name)
    
    result = await session.execute(stmt)
    
    return [
        PolicyWithProduct(
            id=p.id,
            policy_number=p.policy_number,
            policy_name=p.policy_name,
            product_id=p.product_id,
            product_name=pr.product_name,
            product_type=pr.product_type,
            base_premium=p.base_premium,
            base_sum_assured=p.base_sum_assured,
            duration_months=p.duration_months,
            is_active=p.is_active,
            description=p.description
        )
        for p, pr in result.all()
    ]


async def update_policy(
    session: AsyncSession,
    policy_id: str,
    policy_name: Optional[str] = None,
    base_premium: Optional[int] = None,
    base_sum_assured: Optional[int] = None,
    duration_months: Optional[int] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Optional[Policy]:
    """Update a policy template."""
    policy = await get_policy(session, policy_id)
    if not policy:
        return None
    
    if policy_name is not None:
        policy.policy_name = policy_name
    if base_premium is not None:
        policy.base_premium = base_premium
    if base_sum_assured is not None:
        policy.base_sum_assured = base_sum_assured
    if duration_months is not None:
        policy.duration_months = duration_months
    if description is not None:
        policy.description = description
    if is_active is not None:
        policy.is_active = is_active
    
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    
    logger.info(f"Updated policy template: {policy.policy_number}")
    return policy


async def delete_policy(session: AsyncSession, policy_id: str) -> bool:
    """Deactivate a policy template (soft delete)."""
    policy = await get_policy(session, policy_id)
    if not policy:
        return False
    
    policy.is_active = False
    session.add(policy)
    await session.commit()
    
    logger.info(f"Deactivated policy template: {policy.policy_number}")
    return True
