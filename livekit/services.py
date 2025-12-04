"""Database Services for LiveKit Voice Agent."""
import logging
from datetime import date, datetime
from typing import Optional, List
from dataclasses import dataclass

from sqlmodel import select
from database import get_session
from models import Customer, Policy, Product, Call

logger = logging.getLogger(__name__)


@dataclass
class CustomerInfo:
    id: str
    name: str
    phone: str
    email: Optional[str]
    age: Optional[int]
    city: Optional[str]


@dataclass
class PolicyInfo:
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
    id: str
    product_code: str
    product_name: str
    product_type: str
    base_premium: int
    sum_assured_options: List[int]
    features: List[str]
    eligibility: dict
    description: Optional[str]


# Customer Services
async def get_customer_by_phone(phone: str) -> Optional[CustomerInfo]:
    """Get customer by phone number."""
    async with get_session() as session:
        result = await session.execute(select(Customer).where(Customer.phone == phone))
        customer = result.scalar_one_or_none()
        if not customer:
            return None
        return CustomerInfo(
            id=customer.id, name=customer.name, phone=customer.phone,
            email=customer.email, age=customer.age, city=customer.city
        )


# Policy Services
async def get_customer_policies(customer_id: str) -> List[PolicyInfo]:
    """Get all active policies for a customer."""
    async with get_session() as session:
        stmt = (
            select(Policy, Product)
            .join(Product, Policy.product_id == Product.id)
            .where(Policy.customer_id == customer_id, Policy.status == "active")
            .order_by(Policy.end_date)
        )
        result = await session.execute(stmt)
        today = date.today()
        return [
            PolicyInfo(
                id=p.id, policy_number=p.policy_number, product_id=pr.id,
                product_name=pr.product_name, product_type=pr.product_type,
                product_code=pr.product_code, premium_amount=p.premium_amount,
                sum_assured=p.sum_assured, start_date=p.start_date, end_date=p.end_date,
                days_to_expiry=(p.end_date - today).days, status=p.status
            )
            for p, pr in result.all()
        ]


async def get_expiring_policies(customer_id: str, days: int = 30) -> List[PolicyInfo]:
    """Get policies expiring within specified days."""
    policies = await get_customer_policies(customer_id)
    return [p for p in policies if 0 <= p.days_to_expiry <= days]


async def get_policy_by_phone(phone: str) -> List[PolicyInfo]:
    """Get policies by phone number."""
    customer = await get_customer_by_phone(phone)
    return await get_customer_policies(customer.id) if customer else []


async def get_expiring_policies_by_phone(phone: str, days: int = 30) -> List[PolicyInfo]:
    """Get expiring policies by phone number."""
    customer = await get_customer_by_phone(phone)
    return await get_expiring_policies(customer.id, days) if customer else []


# Product Services
async def get_all_products(product_type: Optional[str] = None, active_only: bool = True) -> List[ProductInfo]:
    """Get all available products."""
    async with get_session() as session:
        stmt = select(Product)
        if active_only:
            stmt = stmt.where(Product.is_active == True)
        if product_type:
            stmt = stmt.where(Product.product_type == product_type)
        result = await session.execute(stmt.order_by(Product.product_type, Product.product_name))
        return [
            ProductInfo(
                id=p.id, product_code=p.product_code, product_name=p.product_name,
                product_type=p.product_type, base_premium=p.base_premium,
                sum_assured_options=p.sum_assured_options or [], features=p.features or [],
                eligibility=p.eligibility or {}, description=p.description
            )
            for p in result.scalars().all()
        ]


async def get_product_by_id(product_id: str) -> Optional[ProductInfo]:
    """Get product by ID."""
    async with get_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        p = result.scalar_one_or_none()
        if not p:
            return None
        return ProductInfo(
            id=p.id, product_code=p.product_code, product_name=p.product_name,
            product_type=p.product_type, base_premium=p.base_premium,
            sum_assured_options=p.sum_assured_options or [], features=p.features or [],
            eligibility=p.eligibility or {}, description=p.description
        )


async def get_renewal_options(product_type: str) -> List[ProductInfo]:
    """Get renewal options for a product type."""
    return await get_all_products(product_type=product_type, active_only=True)


async def get_upsell_options(current_product_id: str) -> List[ProductInfo]:
    """Get upsell options (higher tier products)."""
    current = await get_product_by_id(current_product_id)
    if not current:
        return []
    products = await get_all_products(product_type=current.product_type)
    return [p for p in products if p.id != current_product_id and p.base_premium > current.base_premium]


# Call Services
async def get_call_by_room(room_name: str) -> Optional[Call]:
    """Get call record by room name."""
    async with get_session() as session:
        result = await session.execute(
            select(Call).where(Call.room_name == room_name).order_by(Call.started_at.desc())
        )
        return result.scalar_one_or_none()


async def update_call_status(
    room_name: str, status: str, outcome: Optional[str] = None,
    notes: Optional[str] = None, summary: Optional[str] = None,
    transcript: Optional[str] = None, interested_product_id: Optional[str] = None
) -> Optional[Call]:
    """Update call status and outcome."""
    async with get_session() as session:
        result = await session.execute(
            select(Call).where(Call.room_name == room_name).order_by(Call.started_at.desc())
        )
        call = result.scalar_one_or_none()
        if not call:
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
        return call


# Formatters
def format_policies_for_agent(policies: List[PolicyInfo]) -> str:
    """Format policies for agent context."""
    if not policies:
        return "No active policies."
    lines = []
    for p in policies:
        urgency = ""
        if p.days_to_expiry <= 0:
            urgency = " (EXPIRED)"
        elif p.days_to_expiry <= 7:
            urgency = f" (EXPIRING IN {p.days_to_expiry} DAYS - URGENT)"
        elif p.days_to_expiry <= 30:
            urgency = f" (EXPIRING IN {p.days_to_expiry} DAYS)"
        lines.append(
            f"- {p.policy_number}: {p.product_name} ({p.product_type})\n"
            f"  Premium: ₹{p.premium_amount:,}/yr, Coverage: ₹{p.sum_assured:,}\n"
            f"  Valid: {p.start_date} to {p.end_date}{urgency}"
        )
    return "\n\n".join(lines)


def format_products_for_agent(products: List[ProductInfo]) -> str:
    """Format products for agent context."""
    if not products:
        return "No products available."
    lines = []
    for p in products:
        features = ", ".join(p.features[:3]) if p.features else "Standard coverage"
        coverage = ", ".join([f"₹{o:,}" for o in p.sum_assured_options[:3]]) if p.sum_assured_options else "Flexible"
        lines.append(
            f"- {p.product_name} ({p.product_code}) - {p.product_type}\n"
            f"  Base: ₹{p.base_premium:,}/yr, Coverage: {coverage}\n"
            f"  Features: {features}"
        )
    return "\n\n".join(lines)
