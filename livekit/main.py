"""
═══════════════════════════════════════════════════════════════════════════════
AI Voice Agent for Insurance Renewal and Upsell
═══════════════════════════════════════════════════════════════════════════════

A production-ready AI voice agent built with LiveKit Agents 1.x for handling
insurance policy renewal and upsell conversations over phone calls.

This version queries the real PostgreSQL database for customer and policy data.

ARCHITECTURE:
    - LiveKit: Real-time communication platform
    - Deepgram: Speech-to-Text (STT) for transcribing customer speech
    - Google Gemini: Language Model (LLM) for intelligent conversation
    - AWS Polly: Text-to-Speech (TTS) for natural voice synthesis
    - Silero VAD: Voice Activity Detection for turn-taking
    - PostgreSQL: Real customer and policy data

WORKFLOW:
    1. Call comes in → System identifies caller by phone number from database
    2. Agent queries database for customer's policies
    3. Agent greets customer by name and explains expiring policies
    4. Agent presents renewal options from product catalog
    5. Agent suggests relevant upsells (if appropriate)
    6. Agent records customer interest in database
    7. Agent sends payment link or schedules callback
    8. Call ends → System saves call summary to database

═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import asyncio
from datetime import datetime

from livekit.agents import (
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import deepgram, google, aws, silero
from dotenv import load_dotenv

# Local imports
from config import settings
from state import create_state, cleanup_state, get_current_state
from services import (
    get_customer_by_phone,
    get_customer_policies,
    get_expiring_policies,
    get_all_products,
    format_policies_for_agent,
    format_products_for_agent,
    update_call_status,
)
from agent import create_agent

# ============================================================================
# INITIALIZATION
# ============================================================================

load_dotenv("./.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ============================================================================
# PRE-LOAD AI MODELS
# ============================================================================

logger.info("Pre-loading Silero VAD model...")
_vad_model = silero.VAD.load()
logger.info("VAD model loaded successfully")


# ============================================================================
# MAIN ENTRYPOINT
# ============================================================================

async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for insurance renewal calls.

    This function is called by LiveKit whenever a new call comes in.
    It orchestrates the entire call lifecycle:
    1. Initialize session state
    2. Connect to LiveKit room
    3. Identify caller from database
    4. Load customer policies and products
    5. Configure AI providers
    6. Start the conversation

    Args:
        ctx: JobContext from LiveKit containing room and participant info
    """

    # --- 1. Initialize Session State ---
    session_id = ctx.room.name
    state = create_state(session_id)
    
    logger.info(f"═══════════════════════════════════════════════════════════════")
    logger.info(f"Insurance call session started: {session_id}")
    logger.info(f"═══════════════════════════════════════════════════════════════")

    # --- 2. Connect to LiveKit Room ---
    await ctx.connect()

    # --- 3. Wait for Caller to Join ---
    caller = await ctx.wait_for_participant()
    caller_phone = caller.identity
    state.customer_phone = caller_phone
    
    logger.info(f"Caller joined: {caller_phone}")

    # --- 4. Identify Customer from Database ---
    customer = await get_customer_by_phone(caller_phone)
    
    if customer:
        state.customer_id = customer.id
        state.customer_name = customer.name
        state.customer_verified = True
        logger.info(f"Customer identified: {customer.name} (ID: {customer.id})")
    else:
        # Unknown caller - use phone number as identifier
        state.customer_name = "Customer"
        logger.warning(f"Unknown caller: {caller_phone}")

    # --- 5. Load Customer Policies from Database ---
    policies = []
    expiring_policies = []
    
    if state.customer_id:
        policies = await get_customer_policies(state.customer_id)
        expiring_policies = await get_expiring_policies(state.customer_id, days=30)
        
        # Store in state
        state.active_policies = [
            {
                "policy_number": p.policy_number,
                "product_name": p.product_name,
                "product_type": p.product_type,
                "end_date": str(p.end_date),
                "days_to_expiry": p.days_to_expiry
            }
            for p in policies
        ]
        
        logger.info(f"Found {len(policies)} active policies, {len(expiring_policies)} expiring soon")

    # Check if customer has expiring policies (proactive call scenario)
    has_expiring = len(expiring_policies) > 0
    state.update_context("has_expiring_policies", has_expiring)

    # --- 6. Load Available Products ---
    all_products = await get_all_products(active_only=True)
    
    # Format data for agent context
    customer_policies_str = format_policies_for_agent(policies)
    available_products_str = format_products_for_agent(all_products)

    # --- 7. Create the AI Agent ---
    agent = create_agent(
        customer_name=state.customer_name,
        customer_policies=customer_policies_str,
        available_products=available_products_str
    )

    # --- 8. Configure AI Provider Stack ---
    session = AgentSession(
        # Voice Activity Detection
        vad=_vad_model,

        # Speech-to-Text: Deepgram nova-2-phonecall for phone quality audio
        stt=deepgram.STT(
            model="nova-2-phonecall",
            api_key=settings.DEEPGRAM_API_KEY
        ),

        # Language Model: Google Gemini 2.0 Flash
        llm=google.LLM(
            model="gemini-2.0-flash-exp",
            api_key=settings.GEMINI_API_KEY
        ),

        # Text-to-Speech: AWS Polly
        tts=aws.TTS(
            voice="Joanna",
            api_key=settings.AWS_ACCESS_KEY_ID,
            api_secret=settings.AWS_SECRET_ACCESS_KEY,
            region=settings.AWS_DEFAULT_REGION
        ),
    )

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    @session.on("user_speech_committed")
    def on_user_speech(msg):
        """Called when customer finishes speaking."""
        state.add_message("user", msg.content)
        logger.info(f"Customer: {msg.content[:100]}...")

    @session.on("agent_speech_committed")
    def on_agent_speech(msg):
        """Called when agent finishes speaking."""
        state.add_message("assistant", msg.content)
        logger.info(f"Agent: {msg.content[:100]}...")

    @session.on("function_calls_collected")
    def on_function_calls(calls):
        """Called when agent invokes function tools."""
        for call in calls:
            function_name = call.function_info.name
            state.update_context("last_function_call", function_name)
            logger.info(f"Tool called: {function_name}")

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        """Called when a participant leaves."""
        logger.info(f"Participant disconnected: {participant.identity}")

    @ctx.room.on("disconnected")
    def on_call_ended():
        """Called when the call ends."""
        asyncio.create_task(handle_call_ended())

    async def handle_call_ended():
        """
        Async handler for call cleanup.
        Saves call summary and transcript to database and cleans up state.
        """
        try:
            summary_dict = state.get_call_summary_dict()
            
            # Generate conversation notes
            notes = f"Duration: {summary_dict['call_duration']}s, Messages: {summary_dict['messages_exchanged']}, "
            notes += f"Renewal Interest: {summary_dict['interested_in_renewal']}, "
            notes += f"Upsell Interest: {summary_dict['interested_in_upsell']}"
            
            # Determine final outcome
            outcome = "completed"
            if summary_dict['interested_in_renewal']:
                outcome = "interested"
            elif summary_dict['interested_in_upsell']:
                outcome = "upsell_accepted"
            elif summary_dict['callback_scheduled']:
                outcome = "callback"
            elif summary_dict['interested_in_renewal'] is False:
                outcome = "not_interested"
            
            # Generate transcript and human-readable summary
            transcript = state.get_transcript()
            call_summary = state.generate_summary()
            
            # Update call record in database with summary and transcript
            await update_call_status(
                room_name=session_id,
                status="completed",
                outcome=outcome,
                notes=notes,
                interested_product_id=summary_dict['selected_products'][0] if summary_dict['selected_products'] else None,
                summary=call_summary,
                transcript=transcript
            )
            
            logger.info("═══════════════════════════════════════════════════════════════")
            logger.info(f"Call ended - Summary:")
            logger.info(f"  Customer: {summary_dict['customer_name']}")
            logger.info(f"  Duration: {summary_dict['call_duration']}s")
            logger.info(f"  Outcome: {outcome}")
            logger.info(f"  Messages: {summary_dict['messages_exchanged']}")
            logger.info("───────────────────────────────────────────────────────────────")
            logger.info(f"Generated Summary:\n{call_summary}")
            logger.info("═══════════════════════════════════════════════════════════════")
            
        except Exception as e:
            logger.error(f"Error saving call summary: {e}")
        finally:
            # Clean up state
            cleanup_state(session_id)
            logger.info(f"Session cleaned up: {session_id}")

    # ========================================================================
    # START THE SESSION
    # ========================================================================

    await session.start(agent=agent, room=ctx.room)
    logger.info("Agent session started successfully")

    # --- 9. Generate Initial Greeting ---
    if has_expiring:
        # Proactive call - customer has expiring policies
        expiring_count = len(expiring_policies)
        greeting_instructions = (
            f"Start with a warm greeting. Address the customer as {state.customer_name}. "
            f"Introduce yourself as an insurance assistant from XYZ Insurance. "
            f"Mention you're calling about their upcoming policy renewal - "
            f"they have {expiring_count} {'policy' if expiring_count == 1 else 'policies'} expiring soon. "
            f"Ask if this is a good time to talk. Keep it natural and friendly."
        )
    else:
        # General inquiry or new customer
        greeting_instructions = (
            f"Greet the customer warmly as {state.customer_name}. "
            f"Introduce yourself as an insurance assistant from XYZ Insurance. "
            f"Ask how you can help them today."
        )

    # Generate and speak the greeting
    await session.generate_reply(instructions=greeting_instructions)


# ============================================================================
# RUN THE APPLICATION
# ============================================================================

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        ),
    )