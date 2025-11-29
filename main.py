"""
═══════════════════════════════════════════════════════════════════════════════
AI Voice Agent for Insurance Renewal and Upsell
═══════════════════════════════════════════════════════════════════════════════

A production-ready AI voice agent built with LiveKit Agents 1.x for handling
insurance policy renewal and upsell conversations over phone calls.

ARCHITECTURE:
    - LiveKit: Real-time communication platform
    - Deepgram: Speech-to-Text (STT) for transcribing customer speech
    - Google Gemini: Language Model (LLM) for intelligent conversation
    - AWS Polly: Text-to-Speech (TTS) for natural voice synthesis
    - Silero VAD: Voice Activity Detection for turn-taking

KEY FEATURES:
    - Real-time voice conversations with customers
    - State management for tracking call progress
    - Function tools for accessing customer data and performing actions
    - Policy expiry detection and renewal recommendations
    - Intelligent upsell suggestions based on customer profile
    - Automated callback scheduling and payment link delivery

WORKFLOW:
    1. Customer calls in → System identifies caller by phone number
    2. Agent greets and confirms policy expiry
    3. Agent explains benefits of timely renewal
    4. Agent presents renewal options
    5. Agent suggests relevant upsells (if appropriate)
    6. Agent records customer interest
    7. Agent sends payment link or schedules callback
    8. Call ends → System saves call summary

═══════════════════════════════════════════════════════════════════════════════
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, google, aws, silero
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Import your mock database
from mock_database import (
    MOCK_DATABASE,
    ENDING_POLICY_CUSTOMERS,
    get_customer_active_policies,
    get_product_details,
)

# ============================================================================
# INITIALIZATION
# ============================================================================

# Load environment variables from .env file
load_dotenv("./.env")

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# SETTINGS
# ============================================================================

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Required environment variables:
        - DEEPGRAM_API_KEY: For speech-to-text transcription
        - GEMINI_API_KEY: For LLM-powered conversation
        - AWS_ACCESS_KEY_ID: For text-to-speech synthesis
        - AWS_SECRET_ACCESS_KEY: For AWS authentication
        - AWS_DEFAULT_REGION: AWS region for Polly service
        - LIVEKIT_API_KEY: For LiveKit server authentication
        - LIVEKIT_API_SECRET: For LiveKit server authentication
        - LIVEKIT_URL: LiveKit server URL
    """
    DEEPGRAM_API_KEY: str
    GEMINI_API_KEY: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_DEFAULT_REGION: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_URL: str

# Initialize settings singleton
settings = Settings()

# ============================================================================
# PRE-LOAD AI MODELS
# ============================================================================
# Pre-load heavy models at startup to avoid timeout during job assignment
# This runs once when the worker starts, not on every call
# ============================================================================

logger.info("Pre-loading Silero VAD model...")
_vad_model = silero.VAD.load()
logger.info("VAD model loaded successfully")


# ============================================================================
# STATE MANAGEMENT
# ============================================================================
# This section defines the state management system for tracking call progress,
# customer information, and conversation history throughout the call lifecycle.
# Similar to LangGraph's AgentState pattern for maintaining conversation context.
# ============================================================================

@dataclass
class InsuranceCallState:
    """
    Stateful data structure for tracking insurance renewal call progress.

    This class maintains all information about a single call session including:
    - Customer identification and verification
    - Conversation history
    - Policy information
    - Customer preferences and responses
    - Current workflow step

    Each call session has its own instance stored in the global state_store.
    """
    # --- Session Metadata ---
    session_id: str  # Unique identifier for this call (room name)
    call_start: datetime = field(default_factory=datetime.now)  # Timestamp when call started

    # --- Customer Identification ---
    customer_phone: str = ""  # Caller's phone number (from LiveKit identity)
    customer_name: str = ""  # Customer's full name
    customer_id: str = ""  # Unique customer ID from database
    customer_verified: bool = False  # Whether identity has been confirmed

    # --- Conversation Tracking ---
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)  # Full transcript with timestamps

    # --- Policy Information ---
    active_policies: List[Dict] = field(default_factory=list)  # All active policies for customer
    expiring_policies: List[Dict] = field(default_factory=list)  # Policies expiring within 30 days
    policies_discussed: List[str] = field(default_factory=list)  # Policy IDs mentioned in call

    # --- Workflow State ---
    # Tracks where we are in the conversation flow
    current_step: str = "greeting"  # Options: greeting, explain_expiry, offer_renewal, upsell, closing

    # --- Customer Responses & Intent ---
    interested_in_renewal: Optional[bool] = None  # True/False/None (not asked yet)
    interested_in_upsell: Optional[bool] = None  # True/False/None (not asked yet)
    selected_products: List[str] = field(default_factory=list)  # Product IDs customer selected

    # --- Additional Context ---
    context: Dict[str, Any] = field(default_factory=dict)  # Flexible storage for extra data
    
    def add_message(self, role: str, content: str):
        """
        Add a message to the conversation history with timestamp.

        Args:
            role: Either "user" (customer) or "assistant" (agent)
            content: The message text
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def update_context(self, key: str, value: Any):
        """
        Store arbitrary context data for this call.

        Args:
            key: Context key (e.g., "callback_scheduled", "link_sent")
            value: Value to store
        """
        self.context[key] = value

    def get_summary(self) -> str:
        """
        Generate a quick summary of call progress.

        Returns:
            String summary with duration, step, and message count
        """
        duration = (datetime.now() - self.call_start).seconds
        return f"Call duration: {duration}s, Step: {self.current_step}, Messages: {len(self.conversation_history)}"


# ============================================================================
# Global state store: Maps session_id -> InsuranceCallState
# Each active call has one entry. Cleaned up when call ends.
# ============================================================================
state_store: Dict[str, InsuranceCallState] = {}


# ============================================================================
# FUNCTION TOOLS - Insurance-specific operations
# ============================================================================
# These @function_tool decorated functions are callable by the LLM during
# conversations. They provide the agent with capabilities to:
#   - Query customer data
#   - Check policy expiry
#   - Get renewal/upsell options
#   - Record customer preferences
#   - Schedule callbacks
#   - Send payment links
#
# IMPORTANT: LiveKit's RunContext doesn't have a 'room' attribute, so we
# access the session via the global state_store (one call per worker).
# ============================================================================

@function_tool
async def get_customer_expiring_policies(context: RunContext) -> Dict[str, Any]:
    """
    Check which of the customer's policies are expiring within 30 days.

    This tool queries the database to find:
    - All active policies for the customer
    - Policies expiring in the next 30 days
    - Policy details (number, premium, sum assured, expiry date)

    Args:
        context: RunContext from LiveKit (not directly used, session accessed via state_store)

    Returns:
        Dict with count and list of expiring policies, or error message
    """
    # Access the current call session from global store
    if not state_store:
        return {"error": "No active session found"}
    session_id = list(state_store.keys())[0]  # One call per worker
    state = state_store.get(session_id)

    # Ensure customer has been identified
    if not state or not state.customer_phone:
        return {"error": "Customer not identified"}

    expiring_policies = []
    today = datetime.today()

    # Search for customer in database by phone number
    for customer in MOCK_DATABASE["customers"].values():
        if customer["phone"] == state.customer_phone:
            # Check each of the customer's active policies
            for policy_id in customer["active_policies"]:
                policy = MOCK_DATABASE["policies"].get(policy_id)
                if policy:
                    # Calculate days until expiry
                    end_date = datetime.strptime(policy["end_date"], "%Y-%m-%d")
                    days_to_expiry = (end_date - today).days

                    # Filter for policies expiring in next 30 days
                    if 0 <= days_to_expiry <= 30:
                        product = MOCK_DATABASE["products"].get(policy["product_id"])
                        expiring_policies.append({
                            "policy_number": policy["policy_number"],
                            "product_name": product["product_name"],
                            "product_type": product["product_type"],
                            "end_date": policy["end_date"],
                            "days_to_expiry": days_to_expiry,
                            "current_premium": policy["premium_paid"],
                            "sum_assured": policy["sum_assured"]
                        })

    # Update state with findings
    state.expiring_policies = expiring_policies
    state.current_step = "explain_expiry"  # Move workflow forward

    logger.info(f"Found {len(expiring_policies)} expiring policies for {state.customer_name}")

    return {
        "count": len(expiring_policies),
        "policies": expiring_policies
    }


@function_tool
async def get_renewal_options(context: RunContext, product_type: str) -> Dict[str, Any]:
    """
    Fetch available renewal options for a specific insurance product type.

    When a customer's policy is expiring, this tool finds all available
    products of the same type they can renew into.

    Args:
        context: RunContext from LiveKit
        product_type: Type of insurance (e.g., "health", "term_life", "car")

    Returns:
        Dict with product type and list of available renewal options
    """
    # Access the current call session
    if not state_store:
        return {"error": "No active session found"}
    session_id = list(state_store.keys())[0]
    state = state_store.get(session_id)

    if not state:
        return {"error": "Session not found"}

    renewal_options = []

    # Find all products matching the requested type
    for product in MOCK_DATABASE["products"].values():
        if product["product_type"] == product_type:
            renewal_options.append({
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "base_premium": product["base_premium"],
                "sum_assured_options": product["sum_assured_options"],
                "features": product["features"],
                "eligibility": product["eligibility"]
            })

    # Update workflow state
    state.current_step = "offer_renewal"

    logger.info(f"Found {len(renewal_options)} renewal options for {product_type}")

    return {
        "product_type": product_type,
        "options": renewal_options
    }


@function_tool
async def get_upsell_recommendations(context: RunContext, current_product_id: str) -> Dict[str, Any]:
    """
    Recommend premium/upgraded products based on customer's current policy.

    This tool finds higher-tier products of the same type, allowing the
    agent to suggest upgrades with better coverage or additional features.

    Args:
        context: RunContext from LiveKit
        current_product_id: ID of the customer's current product

    Returns:
        Dict with current product and list of upgrade options
    """
    # Access the current call session
    if not state_store:
        return {"error": "No active session found"}
    session_id = list(state_store.keys())[0]
    state = state_store.get(session_id)

    if not state:
        return {"error": "Session not found"}

    # Get current product details
    current_product = MOCK_DATABASE["products"].get(current_product_id)
    if not current_product:
        return {"error": "Product not found"}

    upsell_options = []
    current_premium = current_product["base_premium"]
    product_type = current_product["product_type"]

    # Find higher-tier products of the same type
    # (same type + higher premium = upgrade)
    for product in MOCK_DATABASE["products"].values():
        if (product["product_type"] == product_type and
            product["base_premium"] > current_premium and
            product["product_id"] != current_product_id):

            upsell_options.append({
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "base_premium": product["base_premium"],
                "additional_features": product["features"],
                "premium_difference": product["base_premium"] - current_premium  # Extra cost
            })

    # Update workflow state
    state.current_step = "upsell"

    logger.info(f"Found {len(upsell_options)} upsell options for {current_product_id}")

    return {
        "current_product": current_product["product_name"],
        "upsell_options": upsell_options
    }


@function_tool
async def record_customer_interest(context: RunContext, interest_type: str, product_id: str = "") -> str:
    """
    Record the customer's response to renewal/upsell offers.

    This tool captures customer intent for analytics and follow-up.
    It tracks whether they're interested in renewal, upgrades, or not interested.

    Args:
        context: RunContext from LiveKit
        interest_type: "renewal", "upsell", or "declined"
        product_id: Optional product ID if customer selected specific product

    Returns:
        Confirmation message to be spoken to customer
    """
    # Access the current call session
    if not state_store:
        return "Error: No active session found"
    session_id = list(state_store.keys())[0]
    state = state_store.get(session_id)

    if not state:
        return "Error: Session not found"

    # Handle different interest types
    if interest_type == "renewal":
        state.interested_in_renewal = True
        state.current_step = "renewal_confirmed"
        logger.info(f"Customer {state.customer_name} interested in renewal")
        return "Great! I'll note your interest in renewing the policy."

    elif interest_type == "upsell":
        state.interested_in_upsell = True
        if product_id:
            state.selected_products.append(product_id)
        state.current_step = "upsell_confirmed"
        logger.info(f"Customer {state.customer_name} interested in upsell: {product_id}")
        return "Excellent choice! I'll mark you as interested in the upgraded plan."

    elif interest_type == "declined":
        state.interested_in_renewal = False
        state.current_step = "closing"
        logger.info(f"Customer {state.customer_name} declined")
        return "No problem at all. I understand."

    return "Interest recorded."


@function_tool
async def schedule_callback(context: RunContext, preferred_time: str = "") -> str:
    """
    Schedule a follow-up callback for customers who need more time.

    When customers want to think about the offer or aren't ready to decide,
    this tool records their callback preference for later follow-up.

    Args:
        context: RunContext from LiveKit
        preferred_time: Optional time preference (e.g., "tomorrow", "next week")

    Returns:
        Confirmation message to be spoken to customer
    """
    # Access the current call session
    if not state_store:
        return "Error: No active session found"
    session_id = list(state_store.keys())[0]
    state = state_store.get(session_id)

    if not state:
        return "Error: Session not found"

    # Record callback details in context
    state.update_context("callback_scheduled", True)
    state.update_context("callback_time", preferred_time or "later")
    state.current_step = "callback_scheduled"

    logger.info(f"Callback scheduled for {state.customer_name} at {preferred_time or 'later'}")

    return f"Perfect! I've scheduled a callback for you{' at ' + preferred_time if preferred_time else ' later'}."


@function_tool
async def send_renewal_link(context: RunContext, contact_method: str = "sms") -> str:
    """
    Send payment/renewal link to customer via SMS or email.

    When customer is ready to proceed, this tool sends them a secure link
    to complete the renewal or purchase online.

    Args:
        context: RunContext from LiveKit
        contact_method: How to send the link - "sms" or "email"

    Returns:
        Confirmation message to be spoken to customer
    """
    # Access the current call session
    if not state_store:
        return "Error: No active session found"
    session_id = list(state_store.keys())[0]
    state = state_store.get(session_id)

    if not state:
        return "Error: Session not found"

    # Record link delivery in context
    state.update_context("link_sent", True)
    state.update_context("link_method", contact_method)

    logger.info(f"Renewal link sent to {state.customer_name} via {contact_method}")

    return f"I've sent the renewal link to your registered {contact_method}. Please check in a moment."


# ============================================================================
# INSURANCE RENEWAL UPSELL AGENT
# ============================================================================
# This is the main AI agent class that handles conversations.
# It inherits from LiveKit's Agent class and is configured with:
#   - System instructions (personality, objectives, workflow)
#   - Function tools (capabilities)
#   - Context about the customer (policies, available products)
# ============================================================================

class InsuranceRenewalUpsellAgent(Agent):
    """
    AI Voice Agent specialized in insurance renewal and upsell conversations.

    This agent is configured with customer-specific context and follows a
    structured workflow to guide customers through renewal decisions.
    """

    def __init__(self, customer_policies: str, available_products: str):
        """
        Initialize the agent with customer context.

        Args:
            customer_policies: Formatted string of customer's active policies
            available_products: Formatted string of available insurance products
        """
        self.customer_policies = customer_policies
        self.available_products = available_products

        today = datetime.today().strftime('%Y-%m-%d')

        instructions = f"""You are an AI Voice Insurance Assistant speaking to a customer over a phone call.
Your job is to clearly explain upcoming policy expiries, help them renew, and offer suitable upgrades.

TODAY'S DATE: {today}

CONTEXT YOU HAVE ACCESS TO:

Customer active policies and their expiry dates:
{self.customer_policies}

Available insurance products and add-ons:
{self.available_products}

YOUR OBJECTIVES:
1. Greet the customer politely.
2. Check and explain which policies are expiring soon (use get_customer_expiring_policies tool).
3. Help the customer understand benefits of renewing on time (no break-in, continuous coverage).
4. Present the best renewal option (use get_renewal_options tool).
5. Offer relevant upgrades or add-ons ONLY if they match (use get_upsell_recommendations tool):
   - The customer's current policy type
   - Their risk profile
   - Or the product list provided
6. If the customer shows interest:
   - Use record_customer_interest tool to track their preference
   - Confirm details
   - Walk them through the benefits
   - Use send_renewal_link tool to send payment link
7. If the customer declines:
   - Acknowledge politely
   - Use schedule_callback tool to offer callback
8. Keep responses short, natural, and conversational (not robotic).
9. Avoid giving any legal or regulatory advice.
10. If the customer asks anything outside your provided data, politely say you can escalate to a human agent.

COMMUNICATION STYLE:
- Speak slowly and clearly
- Use simple, friendly language
- Never overwhelm the customer with too much information at once
- Keep the call under 2 minutes
- Be empathetic and patient

SAFETY RULES:
- Do NOT make promises not included in product details
- Do NOT discuss benefits or coverage not listed in available products
- Provide only factual information from the provided data
- Always use the function tools to access customer data and perform actions

WORKFLOW:
1. Greeting → 2. Check Expiring Policies → 3. Explain Expiry → 4. Offer Renewal → 5. Suggest Upsell (if appropriate) → 6. Confirm Interest → 7. Send Link/Schedule Callback → 8. Close Call

Remember: You have powerful tools at your disposal. Use them to access real-time customer data and perform actions!"""

        # Initialize the Agent with instructions and tools
        super().__init__(
            instructions=instructions,
            tools=[
                # Tools for querying customer data
                get_customer_expiring_policies,
                get_renewal_options,
                get_upsell_recommendations,
                # Tools for recording customer actions
                record_customer_interest,
                schedule_callback,
                send_renewal_link,
            ]
        )


# ============================================================================
# MAIN ENTRYPOINT
# ============================================================================
# This async function is called by LiveKit for each new call.
# It sets up the entire conversation flow:
#   1. Initialize session state
#   2. Connect to LiveKit room
#   3. Identify the caller
#   4. Configure AI providers (STT, LLM, TTS, VAD)
#   5. Set up event handlers
#   6. Start the conversation
# ============================================================================

async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for insurance renewal calls.

    This function is called by LiveKit whenever a new call comes in.
    It orchestrates the entire call lifecycle from setup to cleanup.

    Args:
        ctx: JobContext from LiveKit containing room and participant info
    """

    # --- 1. Initialize Session State ---
    session_id = ctx.room.name  # Unique identifier for this call
    state_store[session_id] = InsuranceCallState(session_id=session_id)
    state = state_store[session_id]

    logger.info(f"Insurance call session started: {session_id}")

    # --- 2. Connect to LiveKit Room ---
    await ctx.connect()

    # --- 3. Wait for Caller to Join ---
    caller = await ctx.wait_for_participant()

    # Identify customer by phone number (from LiveKit identity)
    caller_phone = caller.identity
    state.customer_phone = caller_phone

    logger.info(f"Caller joined: {caller_phone}")

    # --- 4. Check Customer Status ---
    # Determine if this is a proactive outbound call (customer has expiring policies)
    is_expiring_customer = caller_phone in ENDING_POLICY_CUSTOMERS

    if is_expiring_customer:
        logger.info(f"Identified customer with expiring policies: {caller_phone}")
        state.update_context("expiring_customer", True)

    # --- 5. Load Customer Data ---
    # Fetch customer policies and available products for agent context
    customer_policies = get_customer_active_policies(caller_phone)
    available_products = get_product_details()

    # --- 6. Create the AI Agent ---
    # Initialize agent with customer-specific context
    agent = InsuranceRenewalUpsellAgent(
        customer_policies=customer_policies,
        available_products=available_products
    )

    # --- 7. Configure AI Provider Stack ---
    # Set up the voice AI pipeline: VAD → STT → LLM → TTS
    session = AgentSession(
        # Voice Activity Detection: Use pre-loaded model for fast startup
        vad=_vad_model,

        # Speech-to-Text: Transcribes customer speech to text
        # Using nova-2-phonecall model optimized for phone audio quality
        stt=deepgram.STT(
            model="nova-2-phonecall",
            api_key=settings.DEEPGRAM_API_KEY
        ),

        # Language Model: Powers intelligent conversation
        # Using Gemini 2.0 Flash for fast, cost-effective responses
        llm=google.LLM(
            model="gemini-2.0-flash-exp",
            api_key=settings.GEMINI_API_KEY
        ),

        # Text-to-Speech: Converts agent responses to natural voice
        # Using AWS Polly's Joanna voice (neutral American English)
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
    # These handlers track conversation progress and save data for analytics.
    # They're called automatically by LiveKit during the conversation.
    # ========================================================================

    @session.on("user_speech_committed")
    def on_user_speech(msg):
        """
        Called when customer finishes speaking and speech is finalized.
        Saves customer's message to conversation history.
        """
        state.add_message("user", msg.content)
        logger.info(f"User: {msg.content[:100]}...")

    @session.on("agent_speech_committed")
    def on_agent_speech(msg):
        """
        Called when agent finishes speaking and speech is finalized.
        Saves agent's message to conversation history.
        """
        state.add_message("assistant", msg.content)
        logger.info(f"Agent: {msg.content[:100]}...")

    @session.on("function_calls_collected")
    def on_function_calls(calls):
        """
        Called when agent invokes function tools.
        Tracks which tools were used for analytics.
        """
        for call in calls:
            function_name = call.function_info.name
            state.update_context(f"last_function_call", function_name)
            logger.info(f"Function called: {function_name}")

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        """
        Called when a participant leaves the call.
        Logs disconnection for monitoring.
        """
        logger.info(f"Participant disconnected: {participant.identity}")

    @ctx.room.on("disconnected")
    def on_call_ended():
        """
        Called when the call completely ends (room closes).
        Triggers async cleanup and reporting.
        """
        asyncio.create_task(handle_call_ended())

    async def handle_call_ended():
        """
        Async handler for call cleanup.

        This function:
        1. Calculates call duration
        2. Generates a summary of the call
        3. Logs key metrics
        4. Cleans up session state
        5. (In production) Saves to database for analytics
        """
        call_duration = (datetime.now() - state.call_start).seconds

        # Generate comprehensive call summary
        summary = {
            "session_id": state.session_id,
            "customer_name": state.customer_name,
            "customer_phone": state.customer_phone,
            "customer_verified": state.customer_verified,
            "call_duration": call_duration,
            "messages_exchanged": len(state.conversation_history),
            "final_step": state.current_step,
            "interested_in_renewal": state.interested_in_renewal,
            "interested_in_upsell": state.interested_in_upsell,
            "selected_products": state.selected_products,
            "policies_discussed": state.policies_discussed,
            "callback_scheduled": state.context.get("callback_scheduled", False),
            "link_sent": state.context.get("link_sent", False),
        }

        logger.info("----------------------------------------------------------------------------------------------------------")
        logger.info(f"Call ended summary: {summary}")
        logger.info("----------------------------------------------------------------------------------------------------------")

        # TODO: In production, save to database for analytics and CRM integration
        # await save_call_record_to_db(summary, state.conversation_history)

        # Clean up state from memory
        if session_id in state_store:
            del state_store[session_id]

        logger.info(f"Session cleaned up: {session_id}")
    
    # ========================================================================
    # START THE SESSION
    # ========================================================================
    # Everything is set up. Now start the conversation!
    # ========================================================================

    # Start the agent session (connects all AI components)
    await session.start(agent=agent, room=ctx.room)

    logger.info("Agent session started successfully")

    # --- 8. Generate Initial Greeting ---
    # Create personalized greeting based on whether this is a proactive
    # outbound call (expiring policies) or general inquiry
    if is_expiring_customer:
        greeting_instructions = (
            "Start with a warm greeting. "
            "Introduce yourself as an insurance assistant. "
            "Inform them you're calling about their upcoming policy renewal. "
            "Keep it natural and friendly."
        )
    else:
        greeting_instructions = (
            "Greet the customer warmly. "
            "Introduce yourself as an insurance assistant. "
            "Ask how you can help them today."
        )

    # Generate and speak the greeting
    await session.generate_reply(instructions=greeting_instructions)


# ============================================================================
# RUN THE APPLICATION
# ============================================================================
# This is the entry point when running the script directly.
# It starts a LiveKit agent worker that listens for incoming calls.
#
# Usage: python main.py start
# ============================================================================

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,  # Function to call for each new session
        ),
    )