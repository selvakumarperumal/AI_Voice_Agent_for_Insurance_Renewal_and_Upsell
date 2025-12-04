"""
Call State Management for LiveKit Voice Agent.
Tracks customer info, conversation history, and call progress.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class InsuranceCallState:
    """State for a single insurance call session."""
    
    # Session
    session_id: str
    call_start: datetime = field(default_factory=datetime.now)
    
    # Customer
    customer_phone: str = ""
    customer_name: str = ""
    customer_id: str = ""
    customer_verified: bool = False
    
    # Conversation
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Policies
    active_policies: List[Dict] = field(default_factory=list)
    expiring_policies: List[Dict] = field(default_factory=list)
    policies_discussed: List[str] = field(default_factory=list)
    
    # Workflow
    current_step: str = "greeting"
    
    # Customer intent
    interested_in_renewal: Optional[bool] = None
    interested_in_upsell: Optional[bool] = None
    selected_products: List[str] = field(default_factory=list)
    
    # Sentiment tracking
    sentiment: str = "neutral"
    escalation_requested: bool = False
    interruption_count: int = 0
    last_topic: str = ""
    
    # Extra context
    context: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def update_context(self, key: str, value: Any):
        self.context[key] = value

    def get_call_summary_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "customer_id": self.customer_id,
            "call_duration": (datetime.now() - self.call_start).seconds,
            "messages_exchanged": len(self.conversation_history),
            "interested_in_renewal": self.interested_in_renewal,
            "interested_in_upsell": self.interested_in_upsell,
            "selected_products": self.selected_products,
            "callback_scheduled": self.context.get("callback_scheduled", False),
        }
    
    def get_transcript(self) -> str:
        if not self.conversation_history:
            return "No conversation recorded."
        lines = []
        for msg in self.conversation_history:
            role = "Customer" if msg["role"] == "user" else "Agent"
            lines.append(f"[{msg.get('timestamp', '')}] {role}: {msg['content']}")
        return "\n".join(lines)
    
    def generate_summary(self) -> str:
        duration = (datetime.now() - self.call_start).seconds
        mins, secs = duration // 60, duration % 60
        
        # Outcome
        if self.interested_in_renewal:
            outcome = "✅ INTERESTED IN RENEWAL"
        elif self.interested_in_upsell:
            outcome = "✅ INTERESTED IN UPSELL"
        elif self.interested_in_renewal is False:
            outcome = "❌ NOT INTERESTED"
        elif self.context.get("callback_scheduled"):
            outcome = "📞 CALLBACK SCHEDULED"
        else:
            outcome = "⏳ NO DECISION"
        
        summary = [
            f"Call Summary for {self.customer_name}",
            f"Phone: {self.customer_phone}",
            f"Duration: {mins}m {secs}s",
            f"Date: {self.call_start.strftime('%Y-%m-%d %H:%M')}",
            "",
            f"OUTCOME: {outcome}",
        ]
        
        if self.selected_products:
            summary.append(f"Products: {', '.join(self.selected_products)}")
        if self.policies_discussed:
            summary.append(f"Policies Discussed: {', '.join(self.policies_discussed)}")
        
        summary.append(f"\nMessages: {len(self.conversation_history)}")
        return "\n".join(summary)


# Global state store
state_store: Dict[str, InsuranceCallState] = {}


def get_current_state() -> Optional[InsuranceCallState]:
    """Get current active call state."""
    if not state_store:
        return None
    return state_store.get(list(state_store.keys())[0])


def create_state(session_id: str) -> InsuranceCallState:
    """Create new call state."""
    state = InsuranceCallState(session_id=session_id)
    state_store[session_id] = state
    return state


def cleanup_state(session_id: str):
    """Remove call state."""
    state_store.pop(session_id, None)
