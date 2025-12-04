"""
LiveKit SIP Calling Module

This module handles the low-level integration with LiveKit for making
outbound phone calls via SIP/Twilio.

How it works:
    1. Creates/reuses a SIP trunk (connection to Twilio)
    2. Creates a LiveKit room for the call
    3. Connects the phone call to the room via SIP
    4. The AI agent joins the same room to handle the call

Configuration (from .env):
    - LIVEKIT_API_KEY: LiveKit API key
    - LIVEKIT_API_SECRET: LiveKit API secret
    - LIVEKIT_URL: LiveKit server URL
    - TWILIO_SIP_DOMAIN: Twilio SIP domain
    - TWILIO_PHONE_NUMBER: Caller ID phone number
    - TWILIO_SIP_USERNAME: SIP authentication username
    - TWILIO_SIP_PASSWORD: SIP authentication password
"""
import logging
from typing import Optional

from livekit import api
from livekit.protocol import sip as sip_protocol

from ..core.config import settings


logger = logging.getLogger(__name__)


async def _get_or_create_sip_trunk() -> str:
    """Get existing or create new SIP trunk."""
    
    livekit_api = api.LiveKitAPI(
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
        url=settings.LIVEKIT_URL,
    )

    try:
        # Check for existing trunk
        list_request = sip_protocol.ListSIPOutboundTrunkRequest()
        existing = await livekit_api.sip.list_sip_outbound_trunk(list=list_request)
        
        for trunk in existing.items:
            if trunk.name == "InsuranceAgentTrunk":
                logger.info(f"Using existing SIP trunk: {trunk.sip_trunk_id}")
                return trunk.sip_trunk_id
        
        # Create new trunk
        logger.info("Creating new SIP trunk...")
        trunk_info = sip_protocol.SIPOutboundTrunkInfo(
            name="InsuranceAgentTrunk",
            address=settings.TWILIO_SIP_DOMAIN,
            numbers=[settings.TWILIO_PHONE_NUMBER],
            auth_username=settings.TWILIO_SIP_USERNAME,
            auth_password=settings.TWILIO_SIP_PASSWORD,
        )
        
        create_req = sip_protocol.CreateSIPOutboundTrunkRequest(trunk=trunk_info)
        trunk = await livekit_api.sip.create_sip_outbound_trunk(create_req)
        
        logger.info(f"Created SIP trunk: {trunk.sip_trunk_id}")
        return trunk.sip_trunk_id
        
    finally:
        await livekit_api.aclose()


async def make_call(phone: str, customer_name: str) -> dict:
    """
    Make outbound call to customer.
    
    Args:
        phone: Phone number (E.164 format)
        customer_name: Customer name for display
    
    Returns:
        dict with success status and room_name
    """
    if not all([settings.TWILIO_SIP_DOMAIN, settings.TWILIO_PHONE_NUMBER]):
        return {"success": False, "error": "Twilio SIP not configured"}
    
    livekit_api = api.LiveKitAPI(
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
        url=settings.LIVEKIT_URL
    )

    try:
        trunk_id = await _get_or_create_sip_trunk()
        room_name = f"insurance_call:{phone}"
        
        create_req = sip_protocol.CreateSIPParticipantRequest(
            sip_trunk_id=trunk_id,
            sip_call_to=phone,
            room_name=room_name,
            participant_identity=phone,
            participant_name=customer_name,
            krisp_enabled=True,
            wait_until_answered=True,
        )

        logger.info(f"Calling {customer_name} at {phone}...")
        await livekit_api.sip.create_sip_participant(create=create_req)
        logger.info(f"Call initiated: {room_name}")
        
        return {"success": True, "room_name": room_name}

    except Exception as e:
        logger.error(f"Call failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        await livekit_api.aclose()


async def get_active_rooms() -> list:
    """Get list of active call rooms."""
    livekit_api = api.LiveKitAPI(
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
        url=settings.LIVEKIT_URL
    )
    
    try:
        rooms = await livekit_api.room.list_rooms()
        return [
            {
                "name": room.name,
                "sid": room.sid,
                "participants": room.num_participants,
            }
            for room in rooms
        ]
    finally:
        await livekit_api.aclose()
