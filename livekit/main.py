"""
LiveKit Voice Agent - Main Entry Point

AI voice agent for insurance renewal and upsell conversations.
Uses Deepgram STT, Google Gemini LLM, and AWS Polly TTS.
"""
import logging
import asyncio
from datetime import datetime

from livekit.agents import AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, google, aws, silero
from dotenv import load_dotenv

from config import settings
from state import create_state, cleanup_state
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

# Initialize
load_dotenv("./.env")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pre-load VAD model
logger.info("Loading Silero VAD model...")
_vad_model = silero.VAD.load()
logger.info("VAD model ready")


async def entrypoint(ctx: JobContext):
    """Main entrypoint for insurance renewal calls."""
    
    session_id = ctx.room.name
    state = create_state(session_id)
    logger.info(f"Call session started: {session_id}")

    await ctx.connect()

    # Wait for caller and identify
    caller = await ctx.wait_for_participant()
    state.customer_phone = caller.identity
    logger.info(f"Caller joined: {caller.identity}")

    # Lookup customer in database
    customer = await get_customer_by_phone(caller.identity)
    if customer:
        state.customer_id = customer.id
        state.customer_name = customer.name
        state.customer_verified = True
        logger.info(f"Customer identified: {customer.name}")
    else:
        state.customer_name = "Customer"
        logger.warning(f"Unknown caller: {caller.identity}")

    # Load policies
    policies = []
    expiring_policies = []
    if state.customer_id:
        policies = await get_customer_policies(state.customer_id)
        expiring_policies = await get_expiring_policies(state.customer_id, days=30)
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
        logger.info(f"Found {len(policies)} policies, {len(expiring_policies)} expiring")

    has_expiring = len(expiring_policies) > 0
    state.update_context("has_expiring_policies", has_expiring)

    # Load products and create agent
    all_products = await get_all_products(active_only=True)
    agent = create_agent(
        customer_name=state.customer_name,
        customer_policies=format_policies_for_agent(policies),
        available_products=format_products_for_agent(all_products)
    )

    # Configure AI providers
    session = AgentSession(
        vad=_vad_model,
        stt=deepgram.STT(model="nova-2-phonecall", api_key=settings.DEEPGRAM_API_KEY),
        llm=google.LLM(model="gemini-2.0-flash-exp", api_key=settings.GEMINI_API_KEY),
        tts=aws.TTS(
            voice="Joanna",
            api_key=settings.AWS_ACCESS_KEY_ID,
            api_secret=settings.AWS_SECRET_ACCESS_KEY,
            region=settings.AWS_DEFAULT_REGION
        ),
    )

    # Event handlers
    @session.on("user_speech_committed")
    def on_user_speech(msg):
        state.add_message("user", msg.content)
        logger.info(f"Customer: {msg.content[:80]}...")

    @session.on("agent_speech_committed")
    def on_agent_speech(msg):
        state.add_message("assistant", msg.content)
        logger.info(f"Agent: {msg.content[:80]}...")

    @session.on("function_calls_collected")
    def on_function_calls(calls):
        for call in calls:
            logger.info(f"Tool called: {call.function_info.name}")

    @ctx.room.on("disconnected")
    def on_call_ended():
        asyncio.create_task(_handle_call_ended())

    async def _handle_call_ended():
        """Save call summary and cleanup."""
        try:
            summary_dict = state.get_call_summary_dict()
            
            # Determine outcome
            if summary_dict['interested_in_renewal']:
                outcome = "interested"
            elif summary_dict['interested_in_upsell']:
                outcome = "upsell_accepted"
            elif summary_dict['callback_scheduled']:
                outcome = "callback"
            elif summary_dict['interested_in_renewal'] is False:
                outcome = "not_interested"
            else:
                outcome = "completed"
            
            await update_call_status(
                room_name=session_id,
                status="completed",
                outcome=outcome,
                notes=f"Duration: {summary_dict['call_duration']}s, Messages: {summary_dict['messages_exchanged']}",
                interested_product_id=summary_dict['selected_products'][0] if summary_dict['selected_products'] else None,
                summary=state.generate_summary(),
                transcript=state.get_transcript()
            )
            logger.info(f"Call ended - Outcome: {outcome}, Duration: {summary_dict['call_duration']}s")
        except Exception as e:
            logger.error(f"Error saving call summary: {e}")
        finally:
            cleanup_state(session_id)

    # Start session
    await session.start(agent=agent, room=ctx.room)
    logger.info("Agent session started")

    # Generate greeting
    if has_expiring:
        count = len(expiring_policies)
        greeting = (
            f"Start with a warm greeting. Address the customer as {state.customer_name}. "
            f"Introduce yourself as an insurance assistant from XYZ Insurance. "
            f"Mention you're calling about their upcoming policy renewal - "
            f"they have {count} {'policy' if count == 1 else 'policies'} expiring soon. "
            f"Ask if this is a good time to talk."
        )
    else:
        greeting = (
            f"Greet the customer warmly as {state.customer_name}. "
            f"Introduce yourself as an insurance assistant from XYZ Insurance. "
            f"Ask how you can help them today."
        )
    
    await session.generate_reply(instructions=greeting)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))