"""
Function Tools for LiveKit Voice Agent.
Callable by LLM during conversations to interact with database and perform actions.
"""
import asyncio
import logging
from typing import Dict, Any

from livekit.agents import function_tool, RunContext, get_job_context
from livekit import api

from state import get_current_state
from services import (
    get_expiring_policies_by_phone,
    get_customer_policies,
    get_renewal_options,
    get_upsell_options,
    get_product_by_id,
    update_call_status,
)

logger = logging.getLogger(__name__)


@function_tool
async def get_customer_expiring_policies(context: RunContext) -> Dict[str, Any]:
    """Check which customer policies are expiring within 30 days."""
    state = get_current_state()
    if not state or not state.customer_phone:
        return {"error": "Customer not identified"}

    try:
        expiring = await get_expiring_policies_by_phone(state.customer_phone, days=30)
        policies_data = [{
            "policy_number": p.policy_number,
            "product_name": p.product_name,
            "product_type": p.product_type,
            "product_id": p.product_id,
            "end_date": str(p.end_date),
            "days_to_expiry": p.days_to_expiry,
            "current_premium": p.premium_amount,
            "sum_assured": p.sum_assured
        } for p in expiring]
        
        for p in expiring:
            state.policies_discussed.append(p.policy_number)
        state.expiring_policies = policies_data
        state.current_step = "explain_expiry"
        
        return {"count": len(policies_data), "policies": policies_data}
    except Exception as e:
        logger.error(f"Error getting expiring policies: {e}")
        return {"error": str(e)}


@function_tool
async def get_all_customer_policies(context: RunContext) -> Dict[str, Any]:
    """Retrieve all active policies for the customer."""
    state = get_current_state()
    if not state or not state.customer_phone:
        return {"error": "Customer not identified"}

    try:
        policies = await get_customer_policies(state.customer_phone)
        policies_data = [{
            "policy_number": p.policy_number,
            "product_name": p.product_name,
            "product_type": p.product_type,
            "product_id": p.product_id,
            "end_date": str(p.end_date),
            "current_premium": p.premium_amount,
            "sum_assured": p.sum_assured,
            "status": p.status
        } for p in policies]
        
        state.active_policies = policies_data
        return {"count": len(policies_data), "policies": policies_data}
    except Exception as e:
        logger.error(f"Error getting policies: {e}")
        return {"error": str(e)}


@function_tool
async def get_renewal_options_for_product(context: RunContext, product_type: str) -> Dict[str, Any]:
    """Get renewal options for a product type (Health, Life, Motor, Home)."""
    state = get_current_state()
    if not state:
        return {"error": "No active session"}

    try:
        options = await get_renewal_options(product_type)
        renewal_options = [{
            "product_id": p.id,
            "product_name": p.product_name,
            "product_code": p.product_code,
            "base_premium": p.base_premium,
            "sum_assured_options": p.sum_assured_options,
            "features": p.features
        } for p in options]
        
        state.current_step = "offer_renewal"
        return {"product_type": product_type, "options": renewal_options}
    except Exception as e:
        logger.error(f"Error getting renewal options: {e}")
        return {"error": str(e)}


@function_tool
async def get_upsell_recommendations(context: RunContext, current_product_id: str) -> Dict[str, Any]:
    """Get upgrade recommendations based on current product."""
    state = get_current_state()
    if not state:
        return {"error": "No active session"}

    try:
        current = await get_product_by_id(current_product_id)
        if not current:
            return {"error": "Product not found"}
        
        options = await get_upsell_options(current_product_id)
        upsell_options = [{
            "product_id": p.id,
            "product_name": p.product_name,
            "base_premium": p.base_premium,
            "additional_features": p.features,
            "premium_difference": p.base_premium - current.base_premium
        } for p in options]
        
        state.current_step = "upsell"
        return {"current_product": current.product_name, "upsell_options": upsell_options}
    except Exception as e:
        logger.error(f"Error getting upsell options: {e}")
        return {"error": str(e)}


@function_tool
async def record_customer_interest(context: RunContext, interest_type: str, product_id: str = "") -> str:
    """Record customer response: 'renewal', 'upsell', or 'declined'."""
    state = get_current_state()
    if not state:
        return "Error: No active session"

    try:
        if interest_type == "renewal":
            state.interested_in_renewal = True
            state.current_step = "renewal_confirmed"
            if product_id:
                state.selected_products.append(product_id)
            await update_call_status(room_name=state.session_id, status="in_progress", 
                                     outcome="interested", interested_product_id=product_id or None)
            return "Great! I'll note your interest in renewing."

        elif interest_type == "upsell":
            state.interested_in_upsell = True
            state.current_step = "upsell_confirmed"
            if product_id:
                state.selected_products.append(product_id)
            await update_call_status(room_name=state.session_id, status="in_progress",
                                     outcome="upsell_accepted", interested_product_id=product_id or None)
            return "Excellent choice! I'll mark your interest in the upgraded plan."

        elif interest_type == "declined":
            state.interested_in_renewal = False
            state.current_step = "closing"
            await update_call_status(room_name=state.session_id, status="in_progress", outcome="not_interested")
            return "No problem at all. I understand."

        return "Interest recorded."
    except Exception as e:
        logger.error(f"Error recording interest: {e}")
        return f"Error: {e}"


@function_tool
async def schedule_callback(context: RunContext, preferred_time: str = "") -> str:
    """Schedule a follow-up callback."""
    state = get_current_state()
    if not state:
        return "Error: No active session"

    try:
        state.update_context("callback_scheduled", True)
        state.update_context("callback_time", preferred_time or "later")
        state.current_step = "callback_scheduled"
        await update_call_status(room_name=state.session_id, status="in_progress",
                                 outcome="callback", notes=f"Callback: {preferred_time or 'later'}")
        return f"I've scheduled a callback{' for ' + preferred_time if preferred_time else ''}."
    except Exception as e:
        logger.error(f"Error scheduling callback: {e}")
        return f"Error: {e}"


@function_tool
async def send_renewal_link(context: RunContext, contact_method: str = "sms") -> str:
    """Send renewal link via SMS or email."""
    state = get_current_state()
    if not state:
        return "Error: No active session"

    try:
        state.update_context("link_sent", True)
        state.update_context("link_method", contact_method)
        await update_call_status(room_name=state.session_id, status="in_progress",
                                 notes=f"Renewal link sent via {contact_method}")
        return f"I've sent the renewal link to your registered {contact_method}."
    except Exception as e:
        logger.error(f"Error sending link: {e}")
        return f"Error: {e}"


@function_tool
async def get_policy_details(context: RunContext, policy_number: str) -> Dict[str, Any]:
    """Get details of a specific policy."""
    state = get_current_state()
    if not state:
        return {"error": "No active session"}

    for policy in state.active_policies:
        if policy.get("policy_number") == policy_number:
            state.last_topic = f"policy_{policy_number}"
            return {
                "found": True,
                "policy_number": policy_number,
                "product_name": policy.get("product_name"),
                "product_type": policy.get("product_type"),
                "premium": policy.get("current_premium", policy.get("premium_amount")),
                "sum_assured": policy.get("sum_assured"),
                "end_date": policy.get("end_date"),
                "days_to_expiry": policy.get("days_to_expiry"),
            }
    return {"found": False, "error": f"Policy {policy_number} not found"}


@function_tool
async def transfer_to_human(context: RunContext, reason: str = "") -> str:
    """Transfer call to human agent."""
    state = get_current_state()
    if state:
        state.escalation_requested = True
        state.current_step = "human_transfer"
        await update_call_status(room_name=state.session_id, status="in_progress",
                                 outcome="transferred", notes=f"Transfer: {reason}")
        logger.info(f"Human transfer for {state.customer_name}: {reason}")
    
    return ("I understand you'd like to speak with a human agent. "
            "I'm connecting you now. Please hold.")


@function_tool
async def send_email_confirmation(context: RunContext, email_type: str = "summary") -> str:
    """Send email confirmation: 'summary', 'renewal_reminder', or 'quote'."""
    state = get_current_state()
    if not state:
        return "Error: No active session"

    try:
        state.update_context("email_sent", True)
        state.update_context("email_type", email_type)
        await update_call_status(room_name=state.session_id, status="in_progress",
                                 notes=f"Email ({email_type}) queued")
        
        descriptions = {
            "summary": "a summary of our conversation",
            "renewal_reminder": "renewal details and payment info",
            "quote": "a detailed quote"
        }
        return f"I'll send {descriptions.get(email_type, 'the information')} to your email."
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return "Sorry, couldn't queue the email."


@function_tool
async def update_customer_sentiment(context: RunContext, sentiment: str) -> str:
    """Track customer sentiment: positive, neutral, negative, frustrated."""
    state = get_current_state()
    if not state:
        return "Error: No active session"

    if sentiment not in ["positive", "neutral", "negative", "frustrated"]:
        sentiment = "neutral"
    
    state.sentiment = sentiment
    if sentiment == "frustrated":
        state.interruption_count += 1
        if state.interruption_count >= 2:
            return "SUGGEST_HUMAN_TRANSFER"
    return f"Sentiment: {sentiment}"


@function_tool
async def end_call(context: RunContext) -> str:
    """End the call gracefully."""
    state = get_current_state()
    if state:
        state.current_step = "call_ended"
        logger.info(f"Ending call for {state.customer_name}")

    async def _hangup():
        ctx = get_job_context()
        if not ctx:
            return
        await asyncio.sleep(4)
        try:
            await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
        except Exception as e:
            if not any(x in str(e).lower() for x in ["disconnected", "closed", "not found"]):
                logger.error(f"Error ending call: {e}")

    asyncio.create_task(_hangup())
    return "Goodbye!"


# All tools
ALL_TOOLS = [
    get_customer_expiring_policies,
    get_all_customer_policies,
    get_renewal_options_for_product,
    get_upsell_recommendations,
    record_customer_interest,
    schedule_callback,
    send_renewal_link,
    get_policy_details,
    transfer_to_human,
    send_email_confirmation,
    update_customer_sentiment,
    end_call,
]
