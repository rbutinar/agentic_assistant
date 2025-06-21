"""
FastAPI endpoints for the agentic assistant.
"""
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agentic_assistant.api.models import (
    ChatRequest, ChatResponse, StartSessionResponse, 
    SessionLogResponse, ChatMessage, LogEntry
)
from agentic_assistant.core.session import SessionManager
from agentic_assistant.core.logging import log_step, get_session_log, clear_session_log
from agentic_assistant.agents.conversational import ConversationalAgent
from agentic_assistant.tools.terminal import TerminalConfirmationRequired


class ChatProcessor:
    """Handles chat processing logic."""
    
    def __init__(self, session_manager: SessionManager, agent: ConversationalAgent):
        self.session_manager = session_manager
        self.agent = agent
    
    def process_user_input(self, user_message: str, session_id: str, safe_mode: bool):
        """Process user input and determine agent parameters."""
        pending_info = self.session_manager.get_pending_tool(session_id)
        
        if pending_info:
            return self._handle_pending_confirmation(user_message, pending_info, session_id)
        else:
            return user_message, None, safe_mode
    
    def _handle_pending_confirmation(self, user_message: str, pending_info: dict, session_id: str):
        """Handle confirmation for pending commands."""
        command_to_run = pending_info['command']
        user_reply_lower = user_message.lower().strip()
        
        if user_reply_lower == "[terminal confirm]: yes":
            self.session_manager.clear_pending_tool(session_id)
            return None, command_to_run, False
        elif user_reply_lower == "[terminal confirm]: no":
            self.session_manager.clear_pending_tool(session_id)
            return None, None, True
        else:
            return user_message, None, True


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Agentic Assistant API")
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize components
    session_manager = SessionManager()
    agent = ConversationalAgent()
    chat_processor = ChatProcessor(session_manager, agent)
    
    @app.get("/health")
    def health_check():
        """Health check endpoint."""
        return {"status": "ok"}
    
    @app.post("/session", response_model=StartSessionResponse)
    def start_session():
        """Start a new chat session."""
        session_id = session_manager.create_session()
        log_step(session_id, "session_created", {"session_id": session_id})
        return StartSessionResponse(session_id=session_id)
    
    @app.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest):
        """Process a chat message."""
        if not session_manager.session_exists(request.session_id):
            log_step(request.session_id, "chat_error", {"error": "Session not found"})
            raise HTTPException(status_code=404, detail="Session not found")
        
        log_step(request.session_id, "chat_request_received", {
            "message": request.message[:100],  # Truncate long messages
            "safe_mode": request.safe_mode
        })
        
        # Add user message to session (unless it's a confirmation message)
        if not request.message.lower().startswith("[terminal confirm]:"):
            user_message = {"role": "user", "content": request.message}
            session_manager.add_message(request.session_id, user_message)
        
        # Process user input
        graph_input, confirmed_command, graph_safe_mode = chat_processor.process_user_input(
            request.message, request.session_id, request.safe_mode
        )
        
        # Handle command cancellation
        if confirmed_command is None and graph_input is None:
            log_step(request.session_id, "command_cancelled", {"reason": "User declined command"})
            cancellation_message = {"role": "assistant", "content": "Okay, command was not executed."}
            session_manager.add_message(request.session_id, cancellation_message)
            return ChatResponse(
                session_id=request.session_id,
                messages=[ChatMessage(**msg) for msg in session_manager.get_session(request.session_id)],
                pending_command=None
            )
        
        # Call the agent
        try:
            log_step(request.session_id, "agent_processing_start", {
                "user_input": graph_input,
                "safe_mode": graph_safe_mode,
                "confirmed_command": confirmed_command
            })
            
            new_messages, pending_info = agent.run_turn(
                user_input=graph_input,
                session_id=request.session_id,
                safe_mode=graph_safe_mode,
                confirmed_command=confirmed_command
            )
            
            log_step(request.session_id, "agent_processing_complete", {
                "messages_count": len(new_messages) if new_messages else 0,
                "pending_info": bool(pending_info)
            })
            
            # Process agent response
            for msg in new_messages:
                message_dict = {"role": "assistant", "content": str(msg.content)}
                session_manager.add_message(request.session_id, message_dict)
            
            if pending_info:
                session_manager.set_pending_tool(request.session_id, pending_info)
                
        except TerminalConfirmationRequired as tce:
            log_step(request.session_id, "terminal_confirmation_required", {"command": tce.command})
            session_manager.set_pending_tool(request.session_id, {"command": tce.command})
            pending_info = {"command": tce.command}
        except Exception as e:
            log_step(request.session_id, "agent_error", {"error": str(e)}, level="ERROR")
            
            # Handle Azure OpenAI content filter errors more carefully
            error_str = str(e)
            if "content_filter" in error_str or "ResponsibleAIPolicyViolation" in error_str:
                # Check if this was likely a false positive for common safe commands
                user_input_lower = str(graph_input).lower() if graph_input else ""
                safe_commands = ["whoami", "pwd", "ls", "dir", "date", "time", "echo", "cat", "type", "which", "where"]
                
                if any(cmd in user_input_lower for cmd in safe_commands):
                    error_message = {"role": "assistant", "content": "The content filter blocked this request, but it appears to be a safe system command. You can try executing it directly or contact support if this persists."}
                else:
                    error_message = {"role": "assistant", "content": "Sorry, I cannot process this request due to content policy restrictions. Please try rephrasing your request."}
            else:
                error_message = {"role": "assistant", "content": f"An error occurred while processing your request. Please try again."}
                
            session_manager.add_message(request.session_id, error_message)
            session_manager.clear_pending_tool(request.session_id)
            pending_info = None
        
        # Return response
        session_messages = session_manager.get_session(request.session_id) or []
        pending_command = session_manager.get_pending_tool(request.session_id)
        
        return ChatResponse(
            session_id=request.session_id,
            messages=[ChatMessage(**msg) for msg in session_messages],
            pending_command=pending_command.get("command") if pending_command else None
        )
    
    @app.get("/session/{session_id}/log", response_model=SessionLogResponse)
    def get_session_log_endpoint(session_id: str):
        """Get session logs."""
        if not session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        log_entries = get_session_log(session_id)
        log_entry_objects = [LogEntry(**entry) for entry in log_entries]
        
        return SessionLogResponse(session_id=session_id, log_entries=log_entry_objects)
    
    # Serve static files for frontend
    try:
        app.mount("/", StaticFiles(directory="frontend/build", html=True), name="static")
    except Exception:
        pass  # Frontend directory might not exist
    
    return app