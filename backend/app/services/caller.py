"""LiveKit SIP Calling - Optimized with connection reuse."""
import logging
from livekit import api
from livekit.protocol import sip as sip_protocol
from ..core.config import settings

logger = logging.getLogger(__name__)

# Singleton API client and trunk ID
_api_client: api.LiveKitAPI = None
_trunk_id: str = None


def _get_api() -> api.LiveKitAPI:
    """Get or create singleton API client."""
    global _api_client
    if _api_client is None:
        _api_client = api.LiveKitAPI(
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
            url=settings.LIVEKIT_URL,
        )
    return _api_client


async def _ensure_trunk() -> str:
    """Get or create SIP trunk (cached)."""
    global _trunk_id
    if _trunk_id:
        return _trunk_id
    
    lk = _get_api()
    existing = await lk.sip.list_sip_outbound_trunk(list=sip_protocol.ListSIPOutboundTrunkRequest())
    
    for trunk in existing.items:
        if trunk.name == "InsuranceAgentTrunk":
            _trunk_id = trunk.sip_trunk_id
            logger.info(f"Using trunk: {_trunk_id}")
            return _trunk_id
    
    trunk = await lk.sip.create_sip_outbound_trunk(
        sip_protocol.CreateSIPOutboundTrunkRequest(
            trunk=sip_protocol.SIPOutboundTrunkInfo(
                name="InsuranceAgentTrunk",
                address=settings.TWILIO_SIP_DOMAIN,
                numbers=[settings.TWILIO_PHONE_NUMBER],
                auth_username=settings.TWILIO_SIP_USERNAME,
                auth_password=settings.TWILIO_SIP_PASSWORD,
            )
        )
    )
    _trunk_id = trunk.sip_trunk_id
    logger.info(f"Created trunk: {_trunk_id}")
    return _trunk_id


async def make_call(phone: str, name: str) -> dict:
    """Fire and forget call - returns immediately."""
    if not settings.TWILIO_SIP_DOMAIN:
        return {"success": False, "error": "SIP not configured"}
    
    try:
        room = f"insurance_call:{phone}"
        await _get_api().sip.create_sip_participant(
            create=sip_protocol.CreateSIPParticipantRequest(
                sip_trunk_id=await _ensure_trunk(),
                sip_call_to=phone,
                room_name=room,
                participant_identity=phone,
                participant_name=name,
                krisp_enabled=True,
            )
        )
        logger.info(f"Call fired: {name} -> {room}")
        return {"success": True, "room_name": room}
    except Exception as e:
        logger.error(f"Call failed: {e}")
        return {"success": False, "error": str(e)}


async def get_active_rooms() -> list:
    """Get active rooms."""
    rooms = await _get_api().room.list_rooms()
    return [{"name": r.name, "sid": r.sid, "participants": r.num_participants} for r in rooms]
