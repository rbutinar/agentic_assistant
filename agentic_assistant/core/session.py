"""
Session management for the agentic assistant.
"""
import uuid
from typing import Dict, List, Optional


class SessionManager:
    """Centralized session management."""
    
    def __init__(self):
        self.sessions: Dict[str, List[dict]] = {}
        self.pending_tools: Dict[str, dict] = {}
    
    def create_session(self) -> str:
        """Create a new session and return session ID."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = []
        self.pending_tools.pop(session_id, None)
        
        # Clear any existing logs for this session ID (unlikely but safe)
        from agentic_assistant.core.logging import clear_session_log
        clear_session_log(session_id)
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[List[dict]]:
        """Get session history by ID."""
        return self.sessions.get(session_id)
    
    def add_message(self, session_id: str, message: dict) -> None:
        """Add message to session history."""
        if session_id in self.sessions:
            self.sessions[session_id].append(message)
    
    def set_pending_tool(self, session_id: str, tool_info: dict) -> None:
        """Set pending tool for session."""
        self.pending_tools[session_id] = tool_info
    
    def clear_pending_tool(self, session_id: str) -> None:
        """Clear pending tool for session."""
        self.pending_tools.pop(session_id, None)
    
    def get_pending_tool(self, session_id: str) -> Optional[dict]:
        """Get pending tool for session."""
        return self.pending_tools.get(session_id)
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return session_id in self.sessions