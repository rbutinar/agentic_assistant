"""
Unified state management for the agentic assistant.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class SessionState:
    """State for a user session."""
    session_id: str
    messages: list[dict] = field(default_factory=list)
    pending_action: Optional[dict] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class AgentState:
    """State for the conversational agent."""
    conversation_history: list[dict] = field(default_factory=list)
    current_task: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrowserState:
    """State for browser automation."""
    current_url: Optional[str] = None
    page_state: Dict[str, Any] = field(default_factory=dict)
    automation_history: list[dict] = field(default_factory=list)


class StateManager:
    """Unified state management across the application."""
    
    def __init__(self):
        self.session_states: Dict[str, SessionState] = {}
        self.agent_states: Dict[str, AgentState] = {}
        self.browser_states: Dict[str, BrowserState] = {}
    
    def get_session_state(self, session_id: str) -> SessionState:
        """Get or create session state."""
        if session_id not in self.session_states:
            self.session_states[session_id] = SessionState(session_id=session_id)
        return self.session_states[session_id]
    
    def get_agent_state(self, session_id: str) -> AgentState:
        """Get or create agent state."""
        if session_id not in self.agent_states:
            self.agent_states[session_id] = AgentState()
        return self.agent_states[session_id]
    
    def get_browser_state(self, session_id: str) -> BrowserState:
        """Get or create browser state."""
        if session_id not in self.browser_states:
            self.browser_states[session_id] = BrowserState()
        return self.browser_states[session_id]
    
    def clear_session(self, session_id: str) -> None:
        """Clear all state for a session."""
        self.session_states.pop(session_id, None)
        self.agent_states.pop(session_id, None) 
        self.browser_states.pop(session_id, None)