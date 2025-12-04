"""
Customer Service Module

Handles all customer-related database operations.
This service is called by routes - routes should NOT do direct DB commits.

Flow:
    Route -> Service -> Database
    Route receives request -> Service handles business logic & DB -> Returns result
"""
import logging
from datetime import date, timedelta
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models import Customer, Policy
from ..schemas import CustomerCreate


logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOMER CRUD OPERATIONS
# =============================================================================

async def create_customer(session: AsyncSession, data: CustomerCreate) -> Customer:
    """
    Create a new customer in the database.
    
    Args:
        session: Database session (injected by FastAPI)
        data: Customer creation data from request
        
    Returns:
        Created Customer object
        
    Raises:
        ValueError: If customer with same phone already exists
    """
    # Check if phone already exists
    existing = await get_customer_by_phone(session, data.phone)
    if existing:
        raise ValueError("Customer with this phone already exists")
    
    # Check if email already exists
    if data.email:
        existing_email = await get_customer_by_email(session, data.email)
        if existing_email:
            raise ValueError("Customer with this email already exists")
    
    # Create new customer
    customer = Customer(**data.model_dump())
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    
    logger.info(f"Created customer: {customer.name} ({customer.phone})")
    return customer


async def get_customer(session: AsyncSession, customer_id: str) -> Optional[Customer]:
    """
    Get a customer by their ID.
    
    Args:
        session: Database session
        customer_id: UUID of the customer
        
    Returns:
        Customer object or None if not found
    """
    stmt = select(Customer).where(Customer.id == customer_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_customer_by_phone(session: AsyncSession, phone: str) -> Optional[Customer]:
    """
    Get a customer by their phone number.
    
    Args:
        session: Database session
        phone: Phone number (E.164 format)
        
    Returns:
        Customer object or None if not found
    """
    stmt = select(Customer).where(Customer.phone == phone)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_customer_by_email(session: AsyncSession, email: str) -> Optional[Customer]:
    """
    Get a customer by their email address.
    
    Args:
        session: Database session
        email: Email address
        
    Returns:
        Customer object or None if not found
    """
    stmt = select(Customer).where(Customer.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_customers(
    session: AsyncSession, 
    city: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None
) -> List[Customer]:
    """
    List all customers with optional filters.
    
    Args:
        session: Database session
        city: Filter by city
        min_age: Filter by minimum age
        max_age: Filter by maximum age
        
    Returns:
        List of Customer objects
    """
    stmt = select(Customer)
    
    if city:
        stmt = stmt.where(Customer.city == city)
    if min_age is not None:
        stmt = stmt.where(Customer.age >= min_age)
    if max_age is not None:
        stmt = stmt.where(Customer.age <= max_age)
    
    stmt = stmt.order_by(Customer.created_at.desc())
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_customer(
    session: AsyncSession,
    customer_id: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    age: Optional[int] = None,
    city: Optional[str] = None
) -> Optional[Customer]:
    """
    Update a customer's information.
    
    Args:
        session: Database session
        customer_id: UUID of the customer
        name: New name (optional)
        email: New email (optional)
        phone: New phone (optional)
        age: New age (optional)
        city: New city (optional)
        
    Returns:
        Updated Customer object or None if not found
    """
    customer = await get_customer(session, customer_id)
    if not customer:
        return None
    
    if name is not None:
        customer.name = name
    if email is not None:
        # Check if new email is already taken
        existing = await get_customer_by_email(session, email)
        if existing and existing.id != customer_id:
            raise ValueError("Email already taken by another customer")
        customer.email = email
    if phone is not None:
        # Check if new phone is already taken
        existing = await get_customer_by_phone(session, phone)
        if existing and existing.id != customer_id:
            raise ValueError("Phone already taken by another customer")
        customer.phone = phone
    if age is not None:
        customer.age = age
    if city is not None:
        customer.city = city
    
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    
    logger.info(f"Updated customer: {customer.name} ({customer.id})")
    return customer


async def delete_customer(session: AsyncSession, customer_id: str) -> bool:
    """
    Delete a customer from the database.
    
    Args:
        session: Database session
        customer_id: UUID of the customer to delete
        
    Returns:
        True if deleted, False if customer not found
    """
    customer = await get_customer(session, customer_id)
    if not customer:
        return False
    
    await session.delete(customer)
    await session.commit()
    
    logger.info(f"Deleted customer: {customer.name} ({customer.phone})")
    return True


async def search_customers(
    session: AsyncSession,
    query: str
) -> List[Customer]:
    """
    Search customers by name, email, or phone.
    
    Args:
        session: Database session
        query: Search query string
        
    Returns:
        List of matching Customer objects
    """
    search_pattern = f"%{query}%"
    stmt = select(Customer).where(
        (Customer.name.ilike(search_pattern)) |
        (Customer.email.ilike(search_pattern)) |
        (Customer.phone.ilike(search_pattern))
    )
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


# =============================================================================
# CUSTOMERS WITH EXPIRING POLICIES
# =============================================================================

async def get_customers_with_expiring_policies(
    session: AsyncSession,
    days: int = 30
) -> List[Customer]:
    """
    Get all customers who have at least one policy expiring within the specified days.
    
    Args:
        session: Database session
        days: Number of days to check for policy expiration
        
    Returns:
        List of unique Customer objects with expiring policies
    """
    today = date.today()
    expiry_date = today + timedelta(days=days)
    
    # Get distinct customers who have active policies expiring soon
    stmt = (
        select(Customer)
        .join(Policy, Policy.customer_id == Customer.id)
        .where(
            Policy.status == "active",
            Policy.end_date >= today,
            Policy.end_date <= expiry_date
        )
        .distinct()
        .order_by(Customer.name)
    )
    
    result = await session.execute(stmt)
    return list(result.scalars().all())
