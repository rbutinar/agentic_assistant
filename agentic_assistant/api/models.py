"""
Pydantic models for API requests and responses.
"""
from typing import List, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """A chat message."""
    role: str
    content: str
    tool_call_id: Optional[str] = None


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    session_id: str
    message: str
    safe_mode: bool = True


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    session_id: str
    messages: List[ChatMessage]
    pending_command: Optional[str] = None


class StartSessionResponse(BaseModel):
    """Response from starting a new session."""
    session_id: str


class LogEntry(BaseModel):
    """A log entry."""
    timestamp: str
    level: str
    message: str
    data: dict


class SessionLogResponse(BaseModel):
    """Response from session log endpoint."""
    session_id: str
    log_entries: List[LogEntry]