"""Call Service - Optimized database operations."""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models import Call, CustomerPolicy, Policy
from . import customer_service, policy_service
from .caller import make_call as livekit_call, get_active_rooms

logger = logging.getLogger(__name__)

SIP_OUTCOMES = {
    "busy": ["busy", "486"],
    "no_answer": ["no answer", "408", "timeout"],
    "rejected": ["decline", "rejected", "603"],
    "unavailable": ["unavailable", "480"],
    "config_error": ["trial account", "verified caller"],
}


def _parse_outcome(error: str) -> str:
    e = error.lower()
    for outcome, patterns in SIP_OUTCOMES.items():
        if any(p in e for p in patterns):
            return outcome
    return "failed"


async def initiate_call(session: AsyncSession, customer_id: str) -> Call:
    """Initiate call - fires immediately, doesn't wait."""
    customer = await customer_service.get_customer(session, customer_id)
    if not customer:
        raise ValueError("Customer not found")

    result = await livekit_call(customer.phone, customer.name)
    
    call = Call(
        customer_id=customer_id,
        customer_phone=customer.phone,
        customer_name=customer.name,
        room_name=result.get("room_name", ""),
        status="initiated" if result["success"] else "failed",
        outcome=None if result["success"] else _parse_outcome(result.get("error", "")),
        notes=None if result["success"] else result.get("error")
    )
    session.add(call)
    await session.commit()
    await session.refresh(call)
    
    if not result["success"]:
        raise ValueError(result.get("error", "Call failed"))
    return call


async def batch_call_expiring(session: AsyncSession, days: int = 30, limit: int = 10) -> dict:
    """Batch call customers with expiring policies."""
    policies = await policy_service.get_expiring_policies(session, days=days)
    if not policies:
        return {"total": 0, "initiated": 0, "results": []}

    customer_ids = list(set(p.customer_id for p in policies))[:limit]
    results, success = [], 0

    for cid in customer_ids:
        customer = await customer_service.get_customer(session, cid)
        if not customer:
            continue

        result = await livekit_call(customer.phone, customer.name)
        call = Call(
            customer_id=cid, customer_phone=customer.phone, customer_name=customer.name,
            room_name=result.get("room_name", ""),
            status="initiated" if result["success"] else "failed",
            notes=result.get("error") if not result["success"] else None
        )
        session.add(call)
        
        if result["success"]:
            success += 1
            results.append({"customer_id": cid, "status": "initiated", "room": result["room_name"]})
        else:
            results.append({"customer_id": cid, "status": "failed", "error": result.get("error")})

    await session.commit()
    return {"total": len(customer_ids), "initiated": success, "results": results}


async def get_call(session: AsyncSession, call_id: str) -> Optional[Call]:
    return (await session.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()


async def get_call_by_room(session: AsyncSession, room: str) -> Optional[Call]:
    return (await session.execute(select(Call).where(Call.room_name == room))).scalar_one_or_none()


async def list_calls(session: AsyncSession, customer_id: str = None, status: str = None, limit: int = 50) -> List[Call]:
    stmt = select(Call)
    if customer_id:
        stmt = stmt.where(Call.customer_id == customer_id)
    if status:
        stmt = stmt.where(Call.status == status)
    return list((await session.execute(stmt.order_by(Call.started_at.desc()).limit(limit))).scalars().all())


async def update_status(session: AsyncSession, call_id: str, status: str, 
                        outcome: str = None, notes: str = None) -> Optional[Call]:
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


async def update_summary(
    session: AsyncSession, 
    call_id: str, 
    outcome: str = None,
    notes: str = None, 
    product_id: str = None,
    customer_policy_id: str = None,
    renewal_agreed: bool = None,
    upgrade_agreed: bool = None,
    upgrade_to_policy_id: str = None
) -> Optional[Call]:
    """
    Update call summary with renewal/upgrade status.
    
    If renewal_agreed=True, automatically renews the customer's policy.
    If upgrade_agreed=True with upgrade_to_policy_id, creates new upgraded policy.
    """
    call = await get_call(session, call_id)
    if not call:
        return None
    
    call.status = "completed"
    call.ended_at = datetime.now()
    
    if outcome:
        call.outcome = outcome
    if notes:
        call.notes = notes
    if product_id:
        call.interested_product_id = product_id
    if customer_policy_id:
        call.customer_policy_id = customer_policy_id
    
    # Handle renewal agreement
    if renewal_agreed is not None:
        call.renewal_agreed = renewal_agreed
        if renewal_agreed and customer_policy_id:
            await _process_renewal(session, customer_policy_id)
            call.outcome = "renewal_agreed"
            logger.info(f"Customer policy {customer_policy_id} renewed via call {call_id}")
    
    # Handle upgrade agreement
    if upgrade_agreed is not None:
        call.upgrade_agreed = upgrade_agreed
        if upgrade_to_policy_id:
            call.upgrade_to_policy_id = upgrade_to_policy_id
        if upgrade_agreed and upgrade_to_policy_id and call.customer_id:
            await _process_upgrade(session, call.customer_id, customer_policy_id, upgrade_to_policy_id)
            call.outcome = "upgrade_agreed"
            logger.info(f"Customer upgraded to policy {upgrade_to_policy_id} via call {call_id}")
    
    session.add(call)
    await session.commit()
    await session.refresh(call)
    return call


async def _process_renewal(session: AsyncSession, customer_policy_id: str) -> bool:
    """
    Process policy renewal - extends the policy end date by the policy duration.
    """
    result = await session.execute(
        select(CustomerPolicy).where(CustomerPolicy.id == customer_policy_id)
    )
    customer_policy = result.scalar_one_or_none()
    
    if not customer_policy:
        logger.warning(f"CustomerPolicy {customer_policy_id} not found for renewal")
        return False
    
    # Get the policy to determine duration
    policy_result = await session.execute(
        select(Policy).where(Policy.id == customer_policy.policy_id)
    )
    policy = policy_result.scalar_one_or_none()
    
    if not policy:
        logger.warning(f"Policy {customer_policy.policy_id} not found")
        return False
    
    # Calculate new end date based on policy duration
    # duration_months is in the Policy model
    today = date.today()
    new_start_date = max(customer_policy.end_date, today)
    new_end_date = new_start_date + timedelta(days=policy.duration_months * 30)
    
    customer_policy.start_date = new_start_date
    customer_policy.end_date = new_end_date
    customer_policy.status = "active"
    customer_policy.renewal_reminder_sent = False  # Reset for next cycle
    
    session.add(customer_policy)
    await session.commit()
    
    logger.info(f"Renewed CustomerPolicy {customer_policy_id}: {new_start_date} to {new_end_date}")
    return True


async def _process_upgrade(
    session: AsyncSession, 
    customer_id: str, 
    old_customer_policy_id: str,
    new_policy_id: str
) -> bool:
    """
    Process policy upgrade - cancels old policy and creates new one.
    """
    # Cancel old policy if provided
    if old_customer_policy_id:
        old_result = await session.execute(
            select(CustomerPolicy).where(CustomerPolicy.id == old_customer_policy_id)
        )
        old_policy = old_result.scalar_one_or_none()
        if old_policy:
            old_policy.status = "upgraded"
            session.add(old_policy)
    
    # Get new policy details
    policy_result = await session.execute(
        select(Policy).where(Policy.id == new_policy_id)
    )
    new_policy = policy_result.scalar_one_or_none()
    
    if not new_policy:
        logger.warning(f"Policy {new_policy_id} not found for upgrade")
        return False
    
    # Create new customer policy
    today = date.today()
    new_customer_policy = CustomerPolicy(
        customer_id=customer_id,
        policy_id=new_policy_id,
        start_date=today,
        end_date=today + timedelta(days=new_policy.duration_months * 30),
        premium_amount=new_policy.base_premium,
        sum_assured=new_policy.base_sum_assured,
        status="active"
    )
    
    session.add(new_customer_policy)
    await session.commit()
    
    logger.info(f"Upgraded customer {customer_id} to policy {new_policy_id}")
    return True


async def get_active() -> List[dict]:
    return await get_active_rooms()

