"""
Database Services for LiveKit Voice Agent.

Provides functions to query customer, policy, and product information
from the PostgreSQL database during voice calls.
"""
import logging
from datetime import date, timedelta, datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from database import get_session
from models import Customer, Policy, Product, Call

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES FOR STRUCTURED RESPONSES
# =============================================================================

@dataclass
class CustomerInfo:
    """Customer information for the agent."""
    id: str
    name: str
    phone: str
    email: Optional[str]
    age: Optional[int]
    city: Optional[str]


@dataclass
class PolicyInfo:
    """Policy information with product details."""
    id: str
    policy_number: str
    product_id: str
    product_name: str
    product_type: str
    product_code: str
    premium_amount: int
    sum_assured: int
    start_date: date
    end_date: date
    days_to_expiry: int
    status: str


@dataclass
class ProductInfo:
    """Product information for recommendations."""
    id: str
    product_code: str
    product_name: str
    product_type: str
    base_premium: int
    sum_assured_options: List[int]
    features: List[str]
    eligibility: dict
    description: Optional[str]


# =============================================================================
# CUSTOMER SERVICES
# =============================================================================

async def get_customer_by_phone(phone: str) -> Optional[CustomerInfo]:
    """
    Get customer information by phone number.
    
    Args:
        phone: Phone number in E.164 format (e.g., "+919123456789")
        
    Returns:
        CustomerInfo or None if not found
    """
    async with get_session() as session:
        stmt = select(Customer).where(Customer.phone == phone)
        result = await session.execute(stmt)
        customer = result.scalar_one_or_none()
        
        if not customer:
            logger.warning(f"Customer not found for phone: {phone}")
            return None
        
        logger.info(f"Found customer: {customer.name} ({customer.phone})")
        
        return CustomerInfo(
            id=customer.id,
            name=customer.name,
            phone=customer.phone,
            email=customer.email,
            age=customer.age,
            city=customer.city
        )

# =============================================================================
# POLICY SERVICES
# =============================================================================

async def get_customer_policies(customer_id: str) -> List[PolicyInfo]:
    """
    Get all active policies for a customer.
    
    Args:
        customer_id: Customer UUID
        
    Returns:
        List of PolicyInfo objects
    """
    async with get_session() as session:
        stmt = (
            select(Policy, Product)
            .join(Product, Policy.product_id == Product.id)
            .where(
                Policy.customer_id == customer_id,
                Policy.status == "active"
            )
            .order_by(Policy.end_date)
        )
        result = await session.execute(stmt)
        
        policies = []
        today = date.today()
        
        for row in result.all():
            policy, product = row
            days_to_expiry = (policy.end_date - today).days
            
            policies.append(PolicyInfo(
                id=policy.id,
                policy_number=policy.policy_number,
                product_id=product.id,
                product_name=product.product_name,
                product_type=product.product_type,
                product_code=product.product_code,
                premium_amount=policy.premium_amount,
                sum_assured=policy.sum_assured,
                start_date=policy.start_date,
                end_date=policy.end_date,
                days_to_expiry=days_to_expiry,
                status=policy.status
            ))
        
        logger.info(f"Found {len(policies)} active policies for customer {customer_id}")
        return policies


async def get_expiring_policies(customer_id: str, days: int = 30) -> List[PolicyInfo]:
    """
    Get policies expiring within specified days.
    
    Args:
        customer_id: Customer UUID
        days: Number of days to look ahead (default 30)
        
    Returns:
        List of PolicyInfo objects for expiring policies
    """
    all_policies = await get_customer_policies(customer_id)
    
    expiring = [p for p in all_policies if 0 <= p.days_to_expiry <= days]
    
    logger.info(f"Found {len(expiring)} expiring policies (within {days} days)")
    return expiring


async def get_policy_by_phone(phone: str) -> List[PolicyInfo]:
    """
    Get all active policies for a customer by phone number.
    
    Args:
        phone: Customer phone number
        
    Returns:
        List of PolicyInfo objects
    """
    customer = await get_customer_by_phone(phone)
    if not customer:
        return []
    
    return await get_customer_policies(customer.id)


async def get_expiring_policies_by_phone(phone: str, days: int = 30) -> List[PolicyInfo]:
    """
    Get expiring policies for a customer by phone number.
    
    Args:
        phone: Customer phone number
        days: Number of days to look ahead
        
    Returns:
        List of PolicyInfo objects for expiring policies
    """
    customer = await get_customer_by_phone(phone)
    if not customer:
        return []
    
    return await get_expiring_policies(customer.id, days)


# =============================================================================
# PRODUCT SERVICES
# =============================================================================

async def get_all_products(product_type: Optional[str] = None, active_only: bool = True) -> List[ProductInfo]:
    """
    Get all available products.
    
    Args:
        product_type: Filter by type (Health, Life, Motor, Home)
        active_only: Only return active products
        
    Returns:
        List of ProductInfo objects
    """
    async with get_session() as session:
        stmt = select(Product)
        
        if active_only:
            stmt = stmt.where(Product.is_active == True)
        if product_type:
            stmt = stmt.where(Product.product_type == product_type)
        
        stmt = stmt.order_by(Product.product_type, Product.product_name)
        result = await session.execute(stmt)
        
        products = []
        for product in result.scalars().all():
            products.append(ProductInfo(
                id=product.id,
                product_code=product.product_code,
                product_name=product.product_name,
                product_type=product.product_type,
                base_premium=product.base_premium,
                sum_assured_options=product.sum_assured_options or [],
                features=product.features or [],
                eligibility=product.eligibility or {},
                description=product.description
            ))
        
        return products


async def get_product_by_id(product_id: str) -> Optional[ProductInfo]:
    """
    Get product by ID.
    
    Args:
        product_id: Product UUID
        
    Returns:
        ProductInfo or None
    """
    async with get_session() as session:
        stmt = select(Product).where(Product.id == product_id)
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            return None
        
        return ProductInfo(
            id=product.id,
            product_code=product.product_code,
            product_name=product.product_name,
            product_type=product.product_type,
            base_premium=product.base_premium,
            sum_assured_options=product.sum_assured_options or [],
            features=product.features or [],
            eligibility=product.eligibility or {},
            description=product.description
        )


async def get_renewal_options(product_type: str) -> List[ProductInfo]:
    """
    Get renewal options for a product type.
    
    Args:
        product_type: Type of insurance (Health, Life, Motor, Home)
        
    Returns:
        List of ProductInfo objects
    """
    return await get_all_products(product_type=product_type, active_only=True)


async def get_upsell_options(current_product_id: str) -> List[ProductInfo]:
    """
    Get upsell options (higher tier products of same type).
    
    Args:
        current_product_id: Current product ID
        
    Returns:
        List of ProductInfo objects for upsell
    """
    current_product = await get_product_by_id(current_product_id)
    if not current_product:
        return []
    
    # Get all products of same type with higher premium
    all_products = await get_all_products(product_type=current_product.product_type)
    
    upsell_options = [
        p for p in all_products 
        if p.id != current_product_id and p.base_premium > current_product.base_premium
    ]
    
    return upsell_options


# =============================================================================
# CALL SERVICES
# =============================================================================

async def get_call_by_room(room_name: str) -> Optional[Call]:
    """
    Get call record by room name.
    
    Args:
        room_name: LiveKit room name
        
    Returns:
        Call object or None
    """
    async with get_session() as session:
        stmt = select(Call).where(Call.room_name == room_name).order_by(Call.started_at.desc())
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def update_call_status(
    room_name: str,
    status: str,
    outcome: Optional[str] = None,
    notes: Optional[str] = None,
    summary: Optional[str] = None,
    transcript: Optional[str] = None,
    interested_product_id: Optional[str] = None
) -> Optional[Call]:
    """
    Update call status and outcome.
    
    Args:
        room_name: LiveKit room name
        status: New status (in_progress, completed, failed)
        outcome: Call outcome (interested, not_interested, callback, etc.)
        notes: Brief notes about the call
        summary: AI-generated summary of the conversation
        transcript: Full conversation transcript
        interested_product_id: Product customer is interested in
        
    Returns:
        Updated Call object or None
    """
    async with get_session() as session:
        stmt = select(Call).where(Call.room_name == room_name).order_by(Call.started_at.desc())
        result = await session.execute(stmt)
        call = result.scalar_one_or_none()
        
        if not call:
            logger.warning(f"Call not found for room: {room_name}")
            return None
        
        call.status = status
        if outcome:
            call.outcome = outcome
        if notes:
            call.notes = notes
        if summary:
            call.summary = summary
        if transcript:
            call.transcript = transcript
        if interested_product_id:
            call.interested_product_id = interested_product_id
        if status == "completed":
            call.ended_at = datetime.utcnow()
            if call.started_at:
                call.duration_seconds = int((call.ended_at - call.started_at).total_seconds())
        
        session.add(call)
        await session.commit()
        await session.refresh(call)
        
        logger.info(f"Updated call {room_name}: status={status}, outcome={outcome}")
        return call


# =============================================================================
# FORMATTED OUTPUT FOR AGENT
# =============================================================================

def format_policies_for_agent(policies: List[PolicyInfo]) -> str:
    """
    Format policies as a readable string for the agent's context.
    
    Args:
        policies: List of PolicyInfo objects
        
    Returns:
        Formatted string for agent instructions
    """
    if not policies:
        return "No active policies found."
    
    lines = []
    for p in policies:
        expiry_status = ""
        if p.days_to_expiry <= 0:
            expiry_status = " (EXPIRED)"
        elif p.days_to_expiry <= 7:
            expiry_status = f" (EXPIRING IN {p.days_to_expiry} DAYS - URGENT)"
        elif p.days_to_expiry <= 30:
            expiry_status = f" (EXPIRING IN {p.days_to_expiry} DAYS)"
        
        lines.append(
            f"- Policy: {p.policy_number}\n"
            f"  Product: {p.product_name} ({p.product_type})\n"
            f"  Premium: ₹{p.premium_amount:,}/year\n"
            f"  Sum Assured: ₹{p.sum_assured:,}\n"
            f"  Valid: {p.start_date} to {p.end_date}{expiry_status}"
        )
    
    return "\n\n".join(lines)


def format_products_for_agent(products: List[ProductInfo]) -> str:
    """
    Format products as a readable string for the agent's context.
    
    Args:
        products: List of ProductInfo objects
        
    Returns:
        Formatted string for agent instructions
    """
    if not products:
        return "No products available."
    
    lines = []
    for p in products:
        features_str = ", ".join(p.features[:3]) if p.features else "Standard coverage"
        coverage_str = ", ".join([f"₹{opt:,}" for opt in p.sum_assured_options[:3]]) if p.sum_assured_options else "Flexible"
        
        lines.append(
            f"- {p.product_name} ({p.product_code})\n"
            f"  Type: {p.product_type}\n"
            f"  Base Premium: ₹{p.base_premium:,}/year\n"
            f"  Coverage Options: {coverage_str}\n"
            f"  Key Features: {features_str}"
        )
    
    return "\n\n".join(lines)
