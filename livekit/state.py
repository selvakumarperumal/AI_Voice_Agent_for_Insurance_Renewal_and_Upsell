"""
Call State Management for LiveKit Voice Agent.

Manages the state of each active call including:
- Customer identification
- Conversation history
- Policy information
- Call progress tracking
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


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
    call_start: datetime = field(default_factory=datetime.now)

    # --- Customer Identification ---
    customer_phone: str = ""
    customer_name: str = ""
    customer_id: str = ""
    customer_verified: bool = False

    # --- Conversation Tracking ---
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    # --- Policy Information ---
    active_policies: List[Dict] = field(default_factory=list)
    expiring_policies: List[Dict] = field(default_factory=list)
    policies_discussed: List[str] = field(default_factory=list)

    # --- Workflow State ---
    current_step: str = "greeting"  # greeting, explain_expiry, offer_renewal, upsell, closing

    # --- Customer Responses & Intent ---
    interested_in_renewal: Optional[bool] = None
    interested_in_upsell: Optional[bool] = None
    selected_products: List[str] = field(default_factory=list)

    # --- Additional Context ---
    context: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation history with timestamp."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def update_context(self, key: str, value: Any):
        """Store arbitrary context data for this call."""
        self.context[key] = value

    def get_summary(self) -> str:
        """Generate a quick summary of call progress."""
        duration = (datetime.now() - self.call_start).seconds
        return f"Call duration: {duration}s, Step: {self.current_step}, Messages: {len(self.conversation_history)}"
    
    def get_call_summary_dict(self) -> Dict[str, Any]:
        """Generate comprehensive call summary for database storage."""
        call_duration = (datetime.now() - self.call_start).seconds
        
        return {
            "session_id": self.session_id,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "customer_id": self.customer_id,
            "customer_verified": self.customer_verified,
            "call_duration": call_duration,
            "messages_exchanged": len(self.conversation_history),
            "final_step": self.current_step,
            "interested_in_renewal": self.interested_in_renewal,
            "interested_in_upsell": self.interested_in_upsell,
            "selected_products": self.selected_products,
            "policies_discussed": self.policies_discussed,
            "callback_scheduled": self.context.get("callback_scheduled", False),
            "link_sent": self.context.get("link_sent", False),
        }
    
    def get_transcript(self) -> str:
        """
        Generate full conversation transcript from conversation history.
        
        Returns:
            Formatted transcript string with timestamps
        """
        if not self.conversation_history:
            return "No conversation recorded."
        
        lines = []
        for msg in self.conversation_history:
            role = "Customer" if msg["role"] == "user" else "Agent"
            timestamp = msg.get("timestamp", "")
            content = msg["content"]
            lines.append(f"[{timestamp}] {role}: {content}")
        
        return "\n".join(lines)
    
    def generate_summary(self) -> str:
        """
        Generate a human-readable summary of the call.
        
        Returns:
            Summary string with key call details
        """
        duration = (datetime.now() - self.call_start).seconds
        minutes = duration // 60
        seconds = duration % 60
        
        # Build summary
        summary_parts = []
        
        # Header
        summary_parts.append(f"Call Summary for {self.customer_name}")
        summary_parts.append(f"Phone: {self.customer_phone}")
        summary_parts.append(f"Duration: {minutes}m {seconds}s")
        summary_parts.append(f"Date: {self.call_start.strftime('%Y-%m-%d %H:%M')}")
        summary_parts.append("")
        
        # Outcome
        if self.interested_in_renewal:
            summary_parts.append("✅ OUTCOME: Customer interested in RENEWAL")
        elif self.interested_in_upsell:
            summary_parts.append("✅ OUTCOME: Customer interested in UPSELL/UPGRADE")
        elif self.interested_in_renewal is False:
            summary_parts.append("❌ OUTCOME: Customer NOT INTERESTED")
        elif self.context.get("callback_scheduled"):
            summary_parts.append("📞 OUTCOME: Callback scheduled")
        else:
            summary_parts.append("⏳ OUTCOME: No decision made")
        
        # Selected products
        if self.selected_products:
            summary_parts.append(f"Selected Products: {', '.join(self.selected_products)}")
        
        # Policies discussed
        if self.policies_discussed:
            summary_parts.append(f"Policies Discussed: {', '.join(self.policies_discussed)}")
        
        # Actions taken
        summary_parts.append("")
        summary_parts.append("Actions:")
        if self.context.get("link_sent"):
            method = self.context.get("link_method", "sms")
            summary_parts.append(f"  • Renewal link sent via {method}")
        if self.context.get("callback_scheduled"):
            callback_time = self.context.get("callback_time", "later")
            summary_parts.append(f"  • Callback scheduled for: {callback_time}")
        
        # Conversation stats
        summary_parts.append("")
        summary_parts.append(f"Messages exchanged: {len(self.conversation_history)}")
        summary_parts.append(f"Final workflow step: {self.current_step}")
        
        return "\n".join(summary_parts)


# Global state store: Maps session_id -> InsuranceCallState
state_store: Dict[str, InsuranceCallState] = {}


def get_current_state() -> Optional[InsuranceCallState]:
    """Get the current active call state (one call per worker)."""
    if not state_store:
        return None
    session_id = list(state_store.keys())[0]
    return state_store.get(session_id)


def create_state(session_id: str) -> InsuranceCallState:
    """Create a new call state."""
    state = InsuranceCallState(session_id=session_id)
    state_store[session_id] = state
    return state


def cleanup_state(session_id: str):
    """Remove call state from store."""
    if session_id in state_store:
        del state_store[session_id]
