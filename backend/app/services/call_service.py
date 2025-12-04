"""
Call Service Module

Handles all call-related database operations and orchestrates the calling flow.
This service coordinates between:
- Customer Service (get customer data)
- Policy Service (get expiring policies)
- LiveKit Caller (make actual calls)
- Database (store call records)

Flow:
    1. Route requests a call
    2. Call Service fetches customer
    3. Call Service invokes LiveKit to make call
    4. Call Service records the call in DB
    5. Returns result to route
"""
import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models import Customer, Call
from ..schemas import CallResponse
from . import customer_service, policy_service
from .caller import make_call as livekit_make_call, get_active_rooms as livekit_get_rooms


logger = logging.getLogger(__name__)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _parse_sip_outcome(error_message: str) -> str:
    """
    Parse SIP error message and return appropriate outcome.
    
    Common SIP status codes:
        - 486: Busy here
        - 480: Temporarily unavailable
        - 487: Request terminated (caller hung up)
        - 408: Request timeout (no answer)
        - 603: Decline (rejected)
        - 404: Not found
        - 400: Bad request
    """
    error_lower = error_message.lower()
    
    if "busy" in error_lower or "486" in error_message:
        return "busy"
    elif "no answer" in error_lower or "408" in error_message or "timeout" in error_lower:
        return "no_answer"
    elif "decline" in error_lower or "rejected" in error_lower or "603" in error_message:
        return "rejected"
    elif "unavailable" in error_lower or "480" in error_message:
        return "unavailable"
    elif "terminated" in error_lower or "487" in error_message:
        return "terminated"
    elif "trial account" in error_lower or "verified caller" in error_lower:
        return "config_error"
    else:
        return "failed"


# =============================================================================
# CALL OPERATIONS
# =============================================================================

async def initiate_call(session: AsyncSession, customer_id: str) -> Call:
    """
    Initiate a call to a customer.
    
    This is the main entry point for making calls. It:
    1. Fetches the customer from DB
    2. Calls them via LiveKit SIP
    3. Creates a call record
    
    Args:
        session: Database session
        customer_id: UUID of the customer to call
        
    Returns:
        Call object
        
    Raises:
        ValueError: If customer not found or call failed
    """
    # Step 1: Get the customer
    customer = await customer_service.get_customer(session, customer_id)
    if not customer:
        raise ValueError("Customer not found")
    
    # Step 2: Make the call via LiveKit
    call_result = await livekit_make_call(customer.phone, customer.name)
    
    if not call_result["success"]:
        error_msg = call_result.get("error", "Call failed")
        outcome = _parse_sip_outcome(error_msg)
        
        # Create a failed call record with proper outcome
        call = Call(
            customer_id=customer_id,
            customer_phone=customer.phone,
            customer_name=customer.name,
            room_name="",
            status="failed",
            outcome=outcome,
            notes=error_msg
        )
        session.add(call)
        await session.commit()
        await session.refresh(call)
        raise ValueError(error_msg)
    
    # Step 3: Create call record in database
    call = Call(
        customer_id=customer_id,
        customer_phone=customer.phone,
        customer_name=customer.name,
        room_name=call_result["room_name"],
        status="initiated"
    )
    session.add(call)
    
    # Commit all changes
    await session.commit()
    await session.refresh(call)
    
    logger.info(f"Call initiated to {customer.name} ({customer.phone}) - Room: {call.room_name}")
    
    return call


async def call_customers_with_expiring_policies(
    session: AsyncSession,
    days: int = 30,
    limit: int = 10
) -> dict:
    """
    Find and call all customers with expiring policies.
    
    This is the batch calling function that:
    1. Queries policies expiring within N days
    2. Gets unique customers from those policies
    3. Makes calls to each customer
    
    Args:
        session: Database session
        days: Call customers whose policy expires within this many days
        limit: Maximum number of calls to make in this batch
        
    Returns:
        dict with:
            - total_found: Number of eligible customers
            - calls_made: Number of successful calls
            - results: List of individual call results
    """
    # Get expiring policies
    expiring_policies = await policy_service.get_expiring_policies(session, days=days)
    
    if not expiring_policies:
        return {
            "total_found": 0,
            "calls_made": 0,
            "results": []
        }
    
    # Get unique customer IDs from expiring policies
    customer_ids = list(set(p.customer_id for p in expiring_policies))[:limit]
    
    logger.info(f"Found {len(customer_ids)} customers with expiring policies")
    
    results = []
    success_count = 0
    
    for customer_id in customer_ids:
        # Get customer
        customer = await customer_service.get_customer(session, customer_id)
        if not customer:
            continue
        
        # Try to call each customer
        call_result = await livekit_make_call(customer.phone, customer.name)
        
        if call_result["success"]:
            # Create call record
            call = Call(
                customer_id=customer_id,
                customer_phone=customer.phone,
                customer_name=customer.name,
                room_name=call_result["room_name"],
                status="initiated"
            )
            session.add(call)
            
            success_count += 1
            results.append({
                "customer_id": customer_id,
                "customer": customer.name,
                "phone": customer.phone,
                "status": "call_initiated",
                "room": call_result["room_name"]
            })
            
            logger.info(f"Called {customer.name} at {customer.phone}")
        else:
            # Create failed call record
            call = Call(
                customer_id=customer_id,
                customer_phone=customer.phone,
                customer_name=customer.name,
                room_name="",
                status="failed",
                notes=call_result.get("error")
            )
            session.add(call)
            
            results.append({
                "customer_id": customer_id,
                "customer": customer.name,
                "phone": customer.phone,
                "status": "failed",
                "error": call_result.get("error")
            })
            
            logger.warning(f"Failed to call {customer.name}: {call_result.get('error')}")
    
    # Commit all changes
    await session.commit()
    
    logger.info(f"Batch call completed: {success_count}/{len(customer_ids)} successful")
    
    return {
        "total_found": len(customer_ids),
        "calls_made": success_count,
        "results": results
    }


# =============================================================================
# CALL RECORD OPERATIONS
# =============================================================================

async def get_call(session: AsyncSession, call_id: str) -> Optional[Call]:
    """
    Get a call record by its ID.
    
    Args:
        session: Database session
        call_id: UUID of the call
        
    Returns:
        Call object or None if not found
    """
    stmt = select(Call).where(Call.id == call_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_call_by_room(session: AsyncSession, room_name: str) -> Optional[Call]:
    """
    Get a call record by its LiveKit room name.
    
    Args:
        session: Database session
        room_name: LiveKit room name (e.g., "insurance_call:+919123456789")
        
    Returns:
        Call object or None if not found
    """
    stmt = select(Call).where(Call.room_name == room_name)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_customer_calls(session: AsyncSession, customer_id: str) -> List[Call]:
    """
    Get all calls for a specific customer.
    
    Args:
        session: Database session
        customer_id: UUID of the customer
        
    Returns:
        List of Call objects
    """
    stmt = select(Call).where(Call.customer_id == customer_id).order_by(Call.started_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_calls(
    session: AsyncSession, 
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Call]:
    """
    List recent calls, ordered by most recent first.
    
    Args:
        session: Database session
        customer_id: Filter by customer ID (optional)
        status: Filter by call status (optional)
        limit: Maximum number of calls to return
        
    Returns:
        List of Call objects
    """
    stmt = select(Call)
    
    if customer_id:
        stmt = stmt.where(Call.customer_id == customer_id)
    if status:
        stmt = stmt.where(Call.status == status)
    
    stmt = stmt.order_by(Call.started_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_call_status(
    session: AsyncSession,
    call_id: str,
    status: str,
    outcome: Optional[str] = None,
    notes: Optional[str] = None
) -> Optional[Call]:
    """
    Update a call's status.
    
    Args:
        session: Database session
        call_id: UUID of the call
        status: New status
        outcome: Call outcome (optional)
        notes: Additional notes (optional)
        
    Returns:
        Updated Call object or None if not found
    """
    call = await get_call(session, call_id)
    if not call:
        return None
    
    call.status = status
    if outcome:
        call.outcome = outcome
    if notes:
        call.notes = notes
    if status == "completed":
        call.ended_at = datetime.now()
    
    session.add(call)
    await session.commit()
    await session.refresh(call)
    
    return call


async def update_call_summary(
    session: AsyncSession,
    call_id: str,
    outcome: Optional[str] = None,
    notes: Optional[str] = None,
    interested_product_id: Optional[str] = None
) -> Optional[Call]:
    """
    Update a call record with summary data from the AI agent.
    
    Called when the LiveKit agent sends call results via HTTP.
    
    Args:
        session: Database session
        call_id: UUID of the call to update
        outcome: Call outcome (e.g., "interested", "not_interested", "callback")
        notes: Notes from the conversation
        interested_product_id: Product the customer is interested in
        
    Returns:
        Updated Call object or None if not found
    """
    # Find the call
    call = await get_call(session, call_id)
    if not call:
        return None
    
    # Update call record
    call.status = "completed"
    call.ended_at = datetime.now()
    
    if outcome:
        call.outcome = outcome
    if notes:
        call.notes = notes
    if interested_product_id:
        call.interested_product_id = interested_product_id
    
    session.add(call)
    await session.commit()
    await session.refresh(call)
    
    logger.info(f"Call summary saved for {call_id}: outcome={outcome}")
    
    return call


async def get_active_calls() -> List[dict]:
    """
    Get list of currently active calls from LiveKit.
    
    Returns:
        List of active room info dicts
    """
    return await livekit_get_rooms()
