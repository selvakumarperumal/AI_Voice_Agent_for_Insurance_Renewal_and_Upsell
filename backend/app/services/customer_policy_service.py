"""CustomerPolicy Service - Database operations for customer-policy subscriptions."""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models import CustomerPolicy, Policy, Product, Customer
from ..schemas import CustomerPolicyCreate, CustomerPolicyUpdate, CustomerPolicyWithDetails

logger = logging.getLogger(__name__)


async def attach_policy_to_customer(
    session: AsyncSession, 
    customer_id: str, 
    data: CustomerPolicyCreate
) -> CustomerPolicy:
    """Attach a policy to a customer."""
    # Verify customer exists
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise ValueError("Customer not found")
    
    # Verify policy exists and get defaults
    policy_result = await session.execute(
        select(Policy).where(Policy.id == data.policy_id)
    )
    policy = policy_result.scalar_one_or_none()
    if not policy:
        raise ValueError("Policy not found")
    
    if not policy.is_active:
        raise ValueError("Policy is not active")
    
    customer_policy = CustomerPolicy(
        customer_id=customer_id,
        policy_id=data.policy_id,
        start_date=data.start_date,
        end_date=data.end_date,
        premium_amount=data.premium_amount or policy.base_premium,
        sum_assured=data.sum_assured or policy.base_sum_assured,
        status="active"
    )
    
    session.add(customer_policy)
    await session.commit()
    await session.refresh(customer_policy)
    return customer_policy


async def get_customer_policies(
    session: AsyncSession, 
    customer_id: str,
    status: Optional[str] = None
) -> List[CustomerPolicyWithDetails]:
    """Get all policies for a customer with details."""
    stmt = (
        select(CustomerPolicy, Policy, Product)
        .join(Policy, CustomerPolicy.policy_id == Policy.id)
        .join(Product, Policy.product_id == Product.id)
        .where(CustomerPolicy.customer_id == customer_id)
    )
    if status:
        stmt = stmt.where(CustomerPolicy.status == status)
    
    result = await session.execute(stmt.order_by(CustomerPolicy.end_date))
    today = date.today()
    
    return [
        CustomerPolicyWithDetails(
            id=cp.id,
            customer_id=cp.customer_id,
            customer_name="",  # Will fill if needed
            policy_id=cp.policy_id,
            policy_number=p.policy_number,
            policy_name=p.policy_name,
            product_name=pr.product_name,
            product_type=pr.product_type,
            start_date=cp.start_date,
            end_date=cp.end_date,
            premium_amount=cp.premium_amount,
            sum_assured=cp.sum_assured,
            status=cp.status,
            days_to_expiry=(cp.end_date - today).days if cp.status == "active" else None
        )
        for cp, p, pr in result.all()
    ]


async def get_expiring_customer_policies(
    session: AsyncSession, 
    days: int = 30
) -> List[CustomerPolicyWithDetails]:
    """Get customer policies expiring within specified days."""
    today = date.today()
    end_date_cutoff = today + timedelta(days=days)
    
    stmt = (
        select(CustomerPolicy, Policy, Product, Customer)
        .join(Policy, CustomerPolicy.policy_id == Policy.id)
        .join(Product, Policy.product_id == Product.id)
        .join(Customer, CustomerPolicy.customer_id == Customer.id)
        .where(
            CustomerPolicy.status == "active",
            CustomerPolicy.end_date >= today,
            CustomerPolicy.end_date <= end_date_cutoff
        )
        .order_by(CustomerPolicy.end_date)
    )
    
    result = await session.execute(stmt)
    
    return [
        CustomerPolicyWithDetails(
            id=cp.id,
            customer_id=cp.customer_id,
            customer_name=c.name,
            policy_id=cp.policy_id,
            policy_number=p.policy_number,
            policy_name=p.policy_name,
            product_name=pr.product_name,
            product_type=pr.product_type,
            start_date=cp.start_date,
            end_date=cp.end_date,
            premium_amount=cp.premium_amount,
            sum_assured=cp.sum_assured,
            status=cp.status,
            days_to_expiry=(cp.end_date - today).days
        )
        for cp, p, pr, c in result.all()
    ]


async def detach_policy_from_customer(
    session: AsyncSession, 
    customer_id: str, 
    policy_id: str
) -> bool:
    """Detach (cancel) a policy from a customer by policy_id."""
    stmt = select(CustomerPolicy).where(
        CustomerPolicy.customer_id == customer_id,
        CustomerPolicy.policy_id == policy_id,
        CustomerPolicy.status == "active"
    )
    result = await session.execute(stmt)
    customer_policy = result.scalar_one_or_none()
    
    if not customer_policy:
        return False
    
    customer_policy.status = "cancelled"
    session.add(customer_policy)
    await session.commit()
    return True


async def detach_policy_by_id(
    session: AsyncSession, 
    customer_id: str, 
    customer_policy_id: str
) -> bool:
    """Detach (cancel) a specific customer policy subscription by its ID."""
    stmt = select(CustomerPolicy).where(
        CustomerPolicy.id == customer_policy_id,
        CustomerPolicy.customer_id == customer_id,
        CustomerPolicy.status == "active"
    )
    result = await session.execute(stmt)
    customer_policy = result.scalar_one_or_none()
    
    if not customer_policy:
        return False
    
    customer_policy.status = "cancelled"
    session.add(customer_policy)
    await session.commit()
    return True


async def update_customer_policy(
    session: AsyncSession,
    customer_policy_id: str,
    data: CustomerPolicyUpdate
) -> Optional[CustomerPolicy]:
    """Update a customer policy subscription."""
    result = await session.execute(
        select(CustomerPolicy).where(CustomerPolicy.id == customer_policy_id)
    )
    customer_policy = result.scalar_one_or_none()
    
    if not customer_policy:
        return None
    
    if data.start_date is not None:
        customer_policy.start_date = data.start_date
    if data.end_date is not None:
        customer_policy.end_date = data.end_date
    if data.premium_amount is not None:
        customer_policy.premium_amount = data.premium_amount
    if data.sum_assured is not None:
        customer_policy.sum_assured = data.sum_assured
    if data.status is not None:
        customer_policy.status = data.status
    
    session.add(customer_policy)
    await session.commit()
    await session.refresh(customer_policy)
    return customer_policy
