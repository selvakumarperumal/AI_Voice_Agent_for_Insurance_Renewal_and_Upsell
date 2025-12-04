"""
Policy Service Module

Handles all policy operations.
Policies are specific insurance contracts between customers and the company.
"""
import logging
from datetime import date, timedelta
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models import Policy, Customer, Product
from ..schemas import PolicyCreate, PolicyWithDetails


logger = logging.getLogger(__name__)


# =============================================================================
# POLICY CRUD OPERATIONS
# =============================================================================

async def create_policy(session: AsyncSession, data: PolicyCreate) -> Policy:
    """
    Create a new policy for a customer.
    
    Args:
        session: Database session
        data: Policy creation data
        
    Returns:
        Created Policy object
        
    Raises:
        ValueError: If policy number exists or customer/product not found
    """
    # Check if policy number exists
    existing = await get_policy_by_number(session, data.policy_number)
    if existing:
        raise ValueError(f"Policy {data.policy_number} already exists")
    
    # Verify customer exists
    stmt = select(Customer).where(Customer.id == data.customer_id)
    result = await session.execute(stmt)
    customer = result.scalar_one_or_none()
    if not customer:
        raise ValueError(f"Customer {data.customer_id} not found")
    
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
    
    logger.info(f"Created policy: {policy.policy_number} for customer {customer.name}")
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
    customer_id: Optional[str] = None,
    product_id: Optional[str] = None,
    status: Optional[str] = None
) -> List[Policy]:
    """
    List policies with optional filters.
    
    Args:
        session: Database session
        customer_id: Filter by customer
        product_id: Filter by product
        status: Filter by status (active, expired, cancelled)
    """
    stmt = select(Policy)
    
    if customer_id:
        stmt = stmt.where(Policy.customer_id == customer_id)
    if product_id:
        stmt = stmt.where(Policy.product_id == product_id)
    if status:
        stmt = stmt.where(Policy.status == status)
    
    stmt = stmt.order_by(Policy.end_date.desc())
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_customer_policies(session: AsyncSession, customer_id: str) -> List[Policy]:
    """Get all policies for a customer."""
    return await list_policies(session, customer_id=customer_id)


async def get_policy_with_details(session: AsyncSession, policy_id: str) -> Optional[PolicyWithDetails]:
    """
    Get policy with product and customer details.
    
    Returns a PolicyWithDetails object with joined data.
    """
    stmt = (
        select(Policy, Product, Customer)
        .join(Product, Policy.product_id == Product.id)
        .join(Customer, Policy.customer_id == Customer.id)
        .where(Policy.id == policy_id)
    )
    
    result = await session.execute(stmt)
    row = result.first()
    
    if not row:
        return None
    
    policy, product, customer = row
    
    return PolicyWithDetails(
        id=policy.id,
        policy_number=policy.policy_number,
        customer_id=policy.customer_id,
        premium_amount=policy.premium_amount,
        sum_assured=policy.sum_assured,
        start_date=policy.start_date,
        end_date=policy.end_date,
        status=policy.status,
        product_code=product.product_code,
        product_name=product.product_name,
        product_type=product.product_type,
        customer_name=customer.name,
        customer_phone=customer.phone,
    )


async def update_policy(
    session: AsyncSession,
    policy_id: str,
    premium_amount: Optional[int] = None,
    sum_assured: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None
) -> Optional[Policy]:
    """Update a policy."""
    policy = await get_policy(session, policy_id)
    if not policy:
        return None
    
    if premium_amount is not None:
        policy.premium_amount = premium_amount
    if sum_assured is not None:
        policy.sum_assured = sum_assured
    if start_date is not None:
        policy.start_date = start_date
    if end_date is not None:
        policy.end_date = end_date
    if status is not None:
        policy.status = status
    
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    
    logger.info(f"Updated policy: {policy.policy_number}")
    return policy


async def cancel_policy(session: AsyncSession, policy_id: str) -> Optional[Policy]:
    """Cancel a policy."""
    policy = await get_policy(session, policy_id)
    if not policy:
        return None
    
    policy.status = "cancelled"
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    
    logger.info(f"Cancelled policy: {policy.policy_number}")
    return policy


# =============================================================================
# EXPIRING POLICIES
# =============================================================================

async def get_expiring_policies(
    session: AsyncSession,
    days: int = 30,
    limit: int = 100
) -> List[PolicyWithDetails]:
    """
    Get policies expiring within the specified days.
    
    Returns PolicyWithDetails with customer and product info.
    """
    today = date.today()
    end_date = today + timedelta(days=days)
    
    stmt = (
        select(Policy, Product, Customer)
        .join(Product, Policy.product_id == Product.id)
        .join(Customer, Policy.customer_id == Customer.id)
        .where(
            Policy.end_date >= today,
            Policy.end_date <= end_date,
            Policy.status == "active"
        )
        .order_by(Policy.end_date)
        .limit(limit)
    )
    
    result = await session.execute(stmt)
    
    policies = []
    for row in result.all():
        policy, product, customer = row
        policies.append(PolicyWithDetails(
            id=policy.id,
            policy_number=policy.policy_number,
            customer_id=policy.customer_id,
            premium_amount=policy.premium_amount,
            sum_assured=policy.sum_assured,
            start_date=policy.start_date,
            end_date=policy.end_date,
            status=policy.status,
            product_code=product.product_code,
            product_name=product.product_name,
            product_type=product.product_type,
            customer_name=customer.name,
            customer_phone=customer.phone,
        ))
    
    return policies


async def renew_policy(
    session: AsyncSession,
    old_policy_id: str,
    new_premium: int,
    new_end_date: date
) -> Optional[Policy]:
    """
    Renew an existing policy by creating a new one.
    
    Args:
        session: Database session
        old_policy_id: Policy to renew
        new_premium: New premium amount
        new_end_date: New end date
        
    Returns:
        New Policy object
    """
    old_policy = await get_policy(session, old_policy_id)
    if not old_policy:
        return None
    
    # Generate new policy number
    new_policy_number = f"{old_policy.policy_number}-R{date.today().year}"
    
    # Create new policy
    new_policy = Policy(
        policy_number=new_policy_number,
        customer_id=old_policy.customer_id,
        product_id=old_policy.product_id,
        premium_amount=new_premium,
        sum_assured=old_policy.sum_assured,
        start_date=old_policy.end_date + timedelta(days=1),
        end_date=new_end_date,
        status="active"
    )
    session.add(new_policy)
    
    # Update old policy
    old_policy.status = "renewed"
    session.add(old_policy)
    
    await session.commit()
    await session.refresh(new_policy)
    
    logger.info(f"Renewed policy {old_policy.policy_number} -> {new_policy.policy_number}")
    return new_policy
