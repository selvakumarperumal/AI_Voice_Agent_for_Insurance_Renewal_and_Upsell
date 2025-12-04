"""
Function Tools for LiveKit Voice Agent.

These tools are callable by the LLM during conversations to:
- Query customer data from the database
- Check policy expiry
- Get renewal/upsell options
- Record customer preferences
- Schedule callbacks
- Send payment links
- Hang up call when conversation ends
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
    """
    Check which of the customer's policies are expiring within 30 days.

    This tool queries the database to find:
    - All active policies for the customer
    - Policies expiring in the next 30 days
    - Policy details (number, premium, sum assured, expiry date)

    Returns:
        Dict with count and list of expiring policies, or error message
    """
    state = get_current_state()
    if not state or not state.customer_phone:
        return {"error": "Customer not identified"}

    try:
        # Query database for expiring policies
        expiring_policies = await get_expiring_policies_by_phone(state.customer_phone, days=30)
        
        # Convert to dict format for agent
        policies_data = []
        for p in expiring_policies:
            policies_data.append({
                "policy_number": p.policy_number,
                "product_name": p.product_name,
                "product_type": p.product_type,
                "product_id": p.product_id,
                "end_date": str(p.end_date),
                "days_to_expiry": p.days_to_expiry,
                "current_premium": p.premium_amount,
                "sum_assured": p.sum_assured
            })
            # Track discussed policies
            state.policies_discussed.append(p.policy_number)
        
        # Update state
        state.expiring_policies = policies_data
        state.current_step = "explain_expiry"
        
        logger.info(f"Found {len(policies_data)} expiring policies for {state.customer_name}")
        
        return {
            "count": len(policies_data),
            "policies": policies_data
        }
        
    except Exception as e:
        logger.error(f"Error getting expiring policies: {e}")
        return {"error": f"Failed to fetch policies: {str(e)}"}


@function_tool
async def get_all_customer_policies(context: RunContext) -> Dict[str, Any]:
    """
    Retrieve all active policies for the customer.

    Returns:
        Dict with count and list of all active policies, or error message
    """
    state = get_current_state()
    if not state or not state.customer_phone:
        return {"error": "Customer not identified"}

    try:
        # Query database for all active policies
        all_policies = await get_customer_policies(state.customer_phone)
        
        policies_data = []
        for p in all_policies:
            policies_data.append({
                "policy_number": p.policy_number,
                "product_name": p.product_name,
                "product_type": p.product_type,
                "product_id": p.product_id,
                "end_date": str(p.end_date),
                "current_premium": p.premium_amount,
                "sum_assured": p.sum_assured,
                "status": p.status
            })
        
        # Update state
        state.active_policies = policies_data
        
        logger.info(f"Retrieved {len(policies_data)} active policies for {state.customer_name}")
        
        return {
            "count": len(policies_data),
            "policies": policies_data
        }
        
    except Exception as e:
        logger.error(f"Error getting all customer policies: {e}")
        return {"error": f"Failed to fetch policies: {str(e)}"}


@function_tool
async def get_renewal_options_for_product(context: RunContext, product_type: str) -> Dict[str, Any]:
    """
    Fetch available renewal options for a specific insurance product type.

    Args:
        product_type: Type of insurance (e.g., "Health", "Life", "Motor", "Home")

    Returns:
        Dict with product type and list of available renewal options
    """
    state = get_current_state()
    if not state:
        return {"error": "No active session found"}

    try:
        options = await get_renewal_options(product_type)
        
        renewal_options = []
        for p in options:
            renewal_options.append({
                "product_id": p.id,
                "product_name": p.product_name,
                "product_code": p.product_code,
                "base_premium": p.base_premium,
                "sum_assured_options": p.sum_assured_options,
                "features": p.features,
                "eligibility": p.eligibility
            })
        
        state.current_step = "offer_renewal"
        
        logger.info(f"Found {len(renewal_options)} renewal options for {product_type}")
        
        return {
            "product_type": product_type,
            "options": renewal_options
        }
        
    except Exception as e:
        logger.error(f"Error getting renewal options: {e}")
        return {"error": f"Failed to fetch options: {str(e)}"}


@function_tool
async def get_upsell_recommendations(context: RunContext, current_product_id: str) -> Dict[str, Any]:
    """
    Recommend premium/upgraded products based on customer's current policy.

    Args:
        current_product_id: ID of the customer's current product

    Returns:
        Dict with current product and list of upgrade options
    """
    state = get_current_state()
    if not state:
        return {"error": "No active session found"}

    try:
        # Get current product
        current_product = await get_product_by_id(current_product_id)
        if not current_product:
            return {"error": "Product not found"}
        
        # Get upsell options
        options = await get_upsell_options(current_product_id)
        
        upsell_options = []
        for p in options:
            upsell_options.append({
                "product_id": p.id,
                "product_name": p.product_name,
                "base_premium": p.base_premium,
                "additional_features": p.features,
                "premium_difference": p.base_premium - current_product.base_premium
            })
        
        state.current_step = "upsell"
        
        logger.info(f"Found {len(upsell_options)} upsell options for {current_product_id}")
        
        return {
            "current_product": current_product.product_name,
            "upsell_options": upsell_options
        }
        
    except Exception as e:
        logger.error(f"Error getting upsell recommendations: {e}")
        return {"error": f"Failed to fetch recommendations: {str(e)}"}


@function_tool
async def record_customer_interest(context: RunContext, interest_type: str, product_id: str = "") -> str:
    """
    Record the customer's response to renewal/upsell offers.

    Args:
        interest_type: "renewal", "upsell", or "declined"
        product_id: Optional product ID if customer selected specific product

    Returns:
        Confirmation message to be spoken to customer
    """
    state = get_current_state()
    if not state:
        return "Error: No active session found"

    try:
        if interest_type == "renewal":
            state.interested_in_renewal = True
            state.current_step = "renewal_confirmed"
            if product_id:
                state.selected_products.append(product_id)
            
            # Update call record in database
            await update_call_status(
                room_name=state.session_id,
                status="in_progress",
                outcome="interested",
                interested_product_id=product_id if product_id else None
            )
            
            logger.info(f"Customer {state.customer_name} interested in renewal")
            return "Great! I'll note your interest in renewing the policy."

        elif interest_type == "upsell":
            state.interested_in_upsell = True
            state.current_step = "upsell_confirmed"
            if product_id:
                state.selected_products.append(product_id)
            
            await update_call_status(
                room_name=state.session_id,
                status="in_progress",
                outcome="upsell_accepted",
                interested_product_id=product_id if product_id else None
            )
            
            logger.info(f"Customer {state.customer_name} interested in upsell: {product_id}")
            return "Excellent choice! I'll mark you as interested in the upgraded plan."

        elif interest_type == "declined":
            state.interested_in_renewal = False
            state.current_step = "closing"
            
            await update_call_status(
                room_name=state.session_id,
                status="in_progress",
                outcome="not_interested"
            )
            
            logger.info(f"Customer {state.customer_name} declined")
            return "No problem at all. I understand."

        return "Interest recorded."
        
    except Exception as e:
        logger.error(f"Error recording interest: {e}")
        return f"Error recording interest: {str(e)}"


@function_tool
async def schedule_callback(context: RunContext, preferred_time: str = "") -> str:
    """
    Schedule a follow-up callback for customers who need more time.

    Args:
        preferred_time: Optional time preference (e.g., "tomorrow", "next week")

    Returns:
        Confirmation message to be spoken to customer
    """
    state = get_current_state()
    if not state:
        return "Error: No active session found"

    try:
        state.update_context("callback_scheduled", True)
        state.update_context("callback_time", preferred_time or "later")
        state.current_step = "callback_scheduled"
        
        # Update call record
        await update_call_status(
            room_name=state.session_id,
            status="in_progress",
            outcome="callback",
            notes=f"Callback requested for: {preferred_time or 'later'}"
        )
        
        logger.info(f"Callback scheduled for {state.customer_name} at {preferred_time or 'later'}")
        
        return f"Perfect! I've scheduled a callback for you{' at ' + preferred_time if preferred_time else ' later'}."
        
    except Exception as e:
        logger.error(f"Error scheduling callback: {e}")
        return f"Error scheduling callback: {str(e)}"


@function_tool
async def send_renewal_link(context: RunContext, contact_method: str = "sms") -> str:
    """
    Send payment/renewal link to customer via SMS or email.

    Args:
        contact_method: How to send the link - "sms" or "email"

    Returns:
        Confirmation message to be spoken to customer
    """
    state = get_current_state()
    if not state:
        return "Error: No active session found"

    try:
        state.update_context("link_sent", True)
        state.update_context("link_method", contact_method)
        
        # Update call record
        await update_call_status(
            room_name=state.session_id,
            status="in_progress",
            notes=f"Renewal link sent via {contact_method}"
        )
        
        logger.info(f"Renewal link sent to {state.customer_name} via {contact_method}")
        
        return f"I've sent the renewal link to your registered {contact_method}. Please check in a moment."
        
    except Exception as e:
        logger.error(f"Error sending renewal link: {e}")
        return f"Error sending link: {str(e)}"


@function_tool
async def end_call(context: RunContext) -> str:
    """
    End the current call after the conversation is complete.
    
    Use this tool when:
    - The customer says goodbye or indicates they want to end the call
    - All business has been concluded (renewal discussed, upsell offered, callback scheduled)
    - The customer explicitly asks to hang up
    - The conversation has naturally concluded
    
    This will gracefully terminate the call after a brief delay.

    Returns:
        Confirmation that the call will end
    """
    state = get_current_state()
    if state:
        state.current_step = "call_ended"
        logger.info(f"Agent initiating call end for customer {state.customer_name}")
    
    # Schedule the hangup in the background
    async def _hangup():
        ctx = get_job_context()
        if ctx is None:
            logger.warning("Cannot hang up: not running in a job context")
            return
        
        # Wait a few seconds for the goodbye message to be spoken
        await asyncio.sleep(4)
        
        try:
            # Delete the room to end the call
            await ctx.api.room.delete_room(
                api.DeleteRoomRequest(room=ctx.room.name)
            )
            logger.info(f"Call ended - room {ctx.room.name} deleted")
        except Exception as e:
            error_msg = str(e).lower()
            # These errors are expected when the call/room is already disconnecting
            if "disconnected" in error_msg or "closed" in error_msg or "not found" in error_msg:
                logger.info(f"Call already ended or disconnecting (room: {ctx.room.name})")
            else:
                logger.error(f"Error ending call: {e}")
    
    # Start the hangup task
    asyncio.create_task(_hangup())
    
    return "Call will end shortly. Goodbye!"


# Export all tools for use in agent
ALL_TOOLS = [
    get_customer_expiring_policies,
    get_all_customer_policies,
    get_renewal_options_for_product,
    get_upsell_recommendations,
    record_customer_interest,
    schedule_callback,
    send_renewal_link,
    end_call,
]
