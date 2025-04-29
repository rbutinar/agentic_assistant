from pydantic import BaseModel
from typing import List, Optional

class StartSessionResponse(BaseModel):
    session_id: str

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    session_id: str
    message: str
    safe_mode: bool = False

class ChatResponse(BaseModel):
    session_id: str
    messages: List[ChatMessage]
    pending_command: Optional[str] = None
    proposed_command: Optional[str] = None

class LogEntry(BaseModel):
    type: str
    data: dict

class SessionLogResponse(BaseModel):
    session_id: str
    log: List[LogEntry]
