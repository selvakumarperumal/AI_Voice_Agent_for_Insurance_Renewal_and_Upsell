"""LiveKit Voice Agent - Optimized Entry Point."""
import logging
import asyncio

from livekit.agents import AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, google, aws, silero
from dotenv import load_dotenv

from config import settings
from state import create_state, cleanup_state
from services import (
    get_customer_by_phone, get_customer_policies, get_expiring_policies,
    get_all_products, format_policies_for_agent, format_products_for_agent, update_call_status,
)
from agent import create_agent

load_dotenv("./.env")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pre-load models
_vad = silero.VAD.load()
logger.info("VAD ready")


async def entrypoint(ctx: JobContext):
    room_name = ctx.room.name
    state = create_state(room_name)
    
    await ctx.connect()
    caller = await ctx.wait_for_participant()
    state.customer_phone = caller.identity
    
    # Update DB: answered
    await update_call_status(room_name=room_name, status="answered")
    logger.info(f"Answered: {caller.identity}")

    # Load customer data in parallel
    customer, products = await asyncio.gather(
        get_customer_by_phone(caller.identity),
        get_all_products(active_only=True)
    )
    
    if customer:
        state.customer_id = customer.id
        state.customer_name = customer.name
        state.customer_verified = True
        policies, expiring = await asyncio.gather(
            get_customer_policies(customer.id),
            get_expiring_policies(customer.id, days=30)
        )
        state.active_policies = [
            {"policy_number": p.policy_number, "product_name": p.product_name,
             "product_type": p.product_type, "end_date": str(p.end_date), "days_to_expiry": p.days_to_expiry}
            for p in policies
        ]
    else:
        state.customer_name = "Customer"
        policies, expiring = [], []

    has_expiring = len(expiring) > 0
    
    # Update DB: in_progress
    await update_call_status(room_name=room_name, status="in_progress", notes=f"Customer: {state.customer_name}")

    # Create agent and session
    agent = create_agent(state.customer_name, format_policies_for_agent(policies), format_products_for_agent(products))
    session = AgentSession(
        vad=_vad,
        stt=deepgram.STT(model="nova-2-phonecall", api_key=settings.DEEPGRAM_API_KEY),
        llm=google.LLM(model="gemini-2.0-flash-exp", api_key=settings.GEMINI_API_KEY),
        tts=aws.TTS(voice="Joanna", api_key=settings.AWS_ACCESS_KEY_ID, 
                    api_secret=settings.AWS_SECRET_ACCESS_KEY, region=settings.AWS_DEFAULT_REGION),
    )

    @session.on("user_speech_committed")
    def on_user(msg):
        state.add_message("user", msg.content)

    @session.on("agent_speech_committed") 
    def on_agent(msg):
        state.add_message("assistant", msg.content)

    @ctx.room.on("disconnected")
    def on_end():
        asyncio.create_task(_save_and_cleanup())

    async def _save_and_cleanup():
        try:
            s = state.get_call_summary_dict()
            outcome = ("transferred" if state.escalation_requested else
                      "interested" if s['interested_in_renewal'] else
                      "upsell_accepted" if s['interested_in_upsell'] else
                      "callback" if s['callback_scheduled'] else
                      "not_interested" if s['interested_in_renewal'] is False else "completed")
            
            # Note: selected_products contains product codes not UUIDs, so skip interested_product_id
            await update_call_status(
                room_name=room_name, status="completed", outcome=outcome,
                notes=f"Duration: {s['call_duration']}s | Products: {', '.join(s['selected_products']) if s['selected_products'] else 'None'}",
                summary=state.generate_summary(), transcript=state.get_transcript()
            )
            logger.info(f"Completed: {outcome}, {s['call_duration']}s")
        except Exception as e:
            logger.error(f"Save error: {e}")
            # Still try to update just the status
            try:
                await update_call_status(room_name=room_name, status="completed", outcome="error")
            except:
                pass
        finally:
            cleanup_state(room_name)

    await session.start(agent=agent, room=ctx.room)
    
    # Greeting
    n = len(expiring)
    greeting = (f"Greet {state.customer_name} warmly. Introduce yourself from XYZ Insurance. "
                f"{'Mention their ' + str(n) + ' expiring policy(ies). ' if has_expiring else ''}"
                f"Ask if this is a good time.")
    await session.generate_reply(instructions=greeting)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))