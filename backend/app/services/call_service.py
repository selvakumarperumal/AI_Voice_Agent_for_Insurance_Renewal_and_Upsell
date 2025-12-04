"""Call Service - Database operations and call orchestration."""
import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models import Call
from . import customer_service, policy_service
from .caller import make_call as livekit_make_call, get_active_rooms as livekit_get_rooms

logger = logging.getLogger(__name__)


def _parse_sip_outcome(error: str) -> str:
    """Parse SIP error to outcome (busy, no_answer, rejected, failed)."""
    e = error.lower()
    if "busy" in e or "486" in error:
        return "busy"
    elif "no answer" in e or "408" in error or "timeout" in e:
        return "no_answer"
    elif "decline" in e or "rejected" in e or "603" in error:
        return "rejected"
    elif "unavailable" in e or "480" in error:
        return "unavailable"
    elif "trial account" in e or "verified caller" in e:
        return "config_error"
    return "failed"


async def initiate_call(session: AsyncSession, customer_id: str) -> Call:
    """Initiate a call to a customer via LiveKit SIP."""
    customer = await customer_service.get_customer(session, customer_id)
    if not customer:
        raise ValueError("Customer not found")

    result = await livekit_make_call(customer.phone, customer.name)

    if not result["success"]:
        error = result.get("error", "Call failed")
        call = Call(
            customer_id=customer_id, customer_phone=customer.phone,
            customer_name=customer.name, room_name="",
            status="failed", outcome=_parse_sip_outcome(error), notes=error
        )
        session.add(call)
        await session.commit()
        await session.refresh(call)
        raise ValueError(error)

    call = Call(
        customer_id=customer_id, customer_phone=customer.phone,
        customer_name=customer.name, room_name=result["room_name"], status="initiated"
    )
    session.add(call)
    await session.commit()
    await session.refresh(call)
    logger.info(f"Call initiated: {customer.name} - Room: {call.room_name}")
    return call


async def call_customers_with_expiring_policies(session: AsyncSession, days: int = 30, limit: int = 10) -> dict:
    """Batch call customers with expiring policies."""
    policies = await policy_service.get_expiring_policies(session, days=days)
    if not policies:
        return {"total_found": 0, "calls_made": 0, "results": []}

    customer_ids = list(set(p.customer_id for p in policies))[:limit]
    results, success = [], 0

    for cid in customer_ids:
        customer = await customer_service.get_customer(session, cid)
        if not customer:
            continue

        result = await livekit_make_call(customer.phone, customer.name)
        if result["success"]:
            call = Call(customer_id=cid, customer_phone=customer.phone,
                       customer_name=customer.name, room_name=result["room_name"], status="initiated")
            session.add(call)
            success += 1
            results.append({"customer_id": cid, "status": "initiated", "room": result["room_name"]})
        else:
            call = Call(customer_id=cid, customer_phone=customer.phone,
                       customer_name=customer.name, room_name="", status="failed", notes=result.get("error"))
            session.add(call)
            results.append({"customer_id": cid, "status": "failed", "error": result.get("error")})

    await session.commit()
    return {"total_found": len(customer_ids), "calls_made": success, "results": results}


async def get_call(session: AsyncSession, call_id: str) -> Optional[Call]:
    """Get call by ID."""
    result = await session.execute(select(Call).where(Call.id == call_id))
    return result.scalar_one_or_none()


async def get_call_by_room(session: AsyncSession, room_name: str) -> Optional[Call]:
    """Get call by room name."""
    result = await session.execute(select(Call).where(Call.room_name == room_name))
    return result.scalar_one_or_none()


async def get_customer_calls(session: AsyncSession, customer_id: str) -> List[Call]:
    """Get all calls for a customer."""
    result = await session.execute(
        select(Call).where(Call.customer_id == customer_id).order_by(Call.started_at.desc())
    )
    return list(result.scalars().all())


async def list_calls(session: AsyncSession, customer_id: Optional[str] = None,
                     status: Optional[str] = None, limit: int = 50) -> List[Call]:
    """List calls with optional filters."""
    stmt = select(Call)
    if customer_id:
        stmt = stmt.where(Call.customer_id == customer_id)
    if status:
        stmt = stmt.where(Call.status == status)
    result = await session.execute(stmt.order_by(Call.started_at.desc()).limit(limit))
    return list(result.scalars().all())


async def update_call_status(session: AsyncSession, call_id: str, status: str,
                             outcome: Optional[str] = None, notes: Optional[str] = None) -> Optional[Call]:
    """Update call status."""
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


async def update_call_summary(session: AsyncSession, call_id: str, outcome: Optional[str] = None,
                              notes: Optional[str] = None, interested_product_id: Optional[str] = None) -> Optional[Call]:
    """Update call with summary after completion."""
    call = await get_call(session, call_id)
    if not call:
        return None
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
    return call


async def get_active_calls() -> List[dict]:
    """Get active calls from LiveKit."""
    return await livekit_get_rooms()
