import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uuid
from typing import Dict, List, Optional
from langchain_core.messages import BaseMessage, AIMessage
from models import StartSessionResponse, ChatMessage, ChatRequest, ChatResponse, SessionLogResponse, LogEntry
from agent.agent import run_graph_turn
from agent.logging import log_step, get_session_log, clear_session_log, agent_logger
from agent.tools import TerminalConfirmationRequired
from fastapi.staticfiles import StaticFiles

# Load environment variables from .env file
load_dotenv()

agent_logger.info("=== LOGGING TEST: main.py startup ===")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")

app = FastAPI(title="Agentic Assistant Backend")

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (for chat history shown to user)
# Note: LangGraph manages its own internal state via checkpointer
sessions: Dict[str, List[dict]] = {}
# In-memory pending tool actions (per session) - Still needed to track graph interrupts
pending_tools: Dict[str, dict] = {}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/session", response_model=StartSessionResponse)
def start_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = [] # Initialize user-facing history
    pending_tools.pop(session_id, None) # Clear any pending state
    clear_session_log(session_id)
    # Note: Consider clearing graph checkpointer state here too if needed
    log_step(session_id, "session_started", {})
    return StartSessionResponse(session_id=session_id)

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if request.session_id not in sessions:
        log_step(request.session_id, "chat_error", {"error": "Session not found"})
        raise HTTPException(status_code=404, detail="Session not found")

    session_history = sessions[request.session_id]
    user_message_content = request.message.strip()
    session_id = request.session_id
    safe_mode = request.safe_mode # Use safe_mode from request for the initial turn

    log_step(session_id, "chat_endpoint_entry", {"user_message": user_message_content, "safe_mode_request": safe_mode, "current_pending_keys": list(pending_tools.keys())})

    # --- Variables for graph call ---
    graph_input_message: Optional[str] = None
    graph_confirmed_command: Optional[str] = None
    graph_safe_mode = safe_mode # Default to request's safe mode
    skip_graph_call = False

    user_message = {"role": "user", "content": user_message_content}

    # --- Handle Pending Command Confirmation FIRST ---
    if session_id in pending_tools:
        pending_info = pending_tools[session_id]
        command_to_run = pending_info['command']
        log_step(session_id, "pending_check_hit", {"command_pending": True, "pending_command": command_to_run})

        user_reply_lower = user_message_content.lower().strip()
        # Updated check for specific confirmation format
        is_affirmative = user_reply_lower == "[terminal confirm]: yes"
        is_negative = user_reply_lower == "[terminal confirm]: no"
        log_step(session_id, "confirmation_input_check", {
            "user_reply_lower": user_reply_lower,
            "is_affirmative": is_affirmative,
        })

        if is_affirmative:
            log_step(session_id, "affirmative_branch_entered", {"command": command_to_run})
            # Clear pending state and prepare to resume graph with confirmed command
            del pending_tools[session_id]
            graph_confirmed_command = command_to_run
            graph_input_message = None # No new user text input for the graph
            graph_safe_mode = False # Confirmation received, allow direct execution in graph

        elif is_negative:
            log_step(session_id, "negative_branch_entered", {"command": command_to_run})
            # Clear pending state, inform user, and skip agent call
            del pending_tools[session_id]
            cancellation_message = f"Okay, command `{command_to_run}` was not executed."
            session_history.append({"role": "assistant", "content": cancellation_message})
            skip_graph_call = True # Don't call the graph
            log_step(session_id, "terminal_rejected", {"command": command_to_run})

        else:
            # User sent something other than yes/no while command was pending
            log_step(session_id, "unexpected_input_branch_entered", {"pending_command": command_to_run, "user_message": user_message_content})
            # Keep the command pending, pass the new user message to the graph
            graph_input_message = user_message_content
            graph_confirmed_command = None
            graph_safe_mode = True # Still need confirmation for the original command

    else:
        # --- Normal Message Handling (No pending command) ---
        log_step(session_id, "pending_check_miss", {"command_pending": False})
        graph_input_message = user_message_content
        graph_confirmed_command = None
        graph_safe_mode = safe_mode # Use safe_mode from original request

    # --- Call the Agent Graph (if not skipped) ---
    new_agent_messages = []
    new_pending_command_info = None

    if not skip_graph_call:
        log_step(session_id, "before_run_graph_turn", {
            "input_message": graph_input_message,
            "confirmed_command": graph_confirmed_command,
            "safe_mode": graph_safe_mode
        })

        try:
            # Note: run_graph_turn now manages internal history via checkpointer
            # We pass only the trigger (new message or confirmation)
            new_agent_messages, new_pending_command_info = run_graph_turn(
                user_input=graph_input_message, # Can be None if resuming
                chat_history_messages=[], # Pass empty, graph loads from checkpointer
                safe_mode=graph_safe_mode,
                session_id=session_id,
                log_func=log_step,
                confirmed_command=graph_confirmed_command
            )
            log_step(session_id, "after_run_graph_turn", {
                "new_messages_count": len(new_agent_messages),
                "pending_command_info_present": bool(new_pending_command_info)
            })

        except TerminalConfirmationRequired as tce:
            # Special handling for terminal confirmation: set pending_command
            log_step(session_id, "terminal_confirmation_required", {"command": tce.command})
            pending_tools[session_id] = {"command": tce.command}
            skip_graph_call = True
            new_agent_messages = []
            new_pending_command_info = {"command": tce.command}

        except Exception as e:
            # Catch errors during graph execution
            log_step(session_id, "run_graph_turn_exception", {"error": str(e)})
            error_message = {"role": "assistant", "content": f"An error occurred processing your request: {e}"}
            session_history.append(error_message)
            # Reset pending state just in case
            pending_tools.pop(session_id, None)
            skip_graph_call = True # Prevent further processing below

    # --- Process Graph Response ---    
    # Append new messages from the graph turn to the session history
    if new_agent_messages:
        # Make sure tool messages have the right structure
        processed_messages = []
        for msg in new_agent_messages:
            if isinstance(msg, BaseMessage):
                 # Convert LangChain messages if needed (example assumes AIMessage/ToolMessage)
                if isinstance(msg, AIMessage):
                    processed_messages.append({"role": "assistant", "content": msg.content})
                # Add other message type checks if necessary (e.g., ToolMessage)
                elif hasattr(msg, 'tool_call_id'): # Basic check for tool message structure
                     processed_messages.append({"role": "tool", "content": str(msg.content), "tool_call_id": msg.tool_call_id})
                else: # Fallback for other BaseMessage types
                    processed_messages.append({"role": "assistant", "content": str(msg.content)}) # Or handle appropriately
            elif isinstance(msg, dict) and "role" in msg and "content" in msg:
                 processed_messages.append(msg) # Assume it's already in the correct dict format
            else:
                log_step(session_id, "unknown_message_format", {"message_type": type(msg), "message_content": str(msg)})
                # Fallback for unknown format - might need adjustment
                processed_messages.append({"role": "assistant", "content": f"Received unexpected message format: {str(msg)}"})
        
        session_history.extend(processed_messages)
        log_step(session_id, "appended_agent_messages", {"count": len(processed_messages)})

    # Update pending tool state if the graph requires confirmation now
    if new_pending_command_info:
        pending_tools[session_id] = new_pending_command_info
        log_step(session_id, "updated_pending_tools", {"pending_info": new_pending_command_info})
    elif session_id in pending_tools and not graph_confirmed_command:
        # If graph finished *without* requiring confirmation again, but we had a pending command
        # (e.g. user sent unexpected input), assume the agent handled it and clear pending.
        log_step(session_id, "clearing_stale_pending_tool", {"pending_info": pending_tools[session_id]})
        del pending_tools[session_id]
    
    # Final pending command to send to frontend (if any)
    final_pending_command_output = pending_tools.get(session_id, {}).get("command")

    # --- Return Response to Frontend ---
    log_step(session_id, "returning_from_chat_endpoint", {"final_history_len": len(session_history), "final_pending_command": final_pending_command_output})
    messages_for_response = [ChatMessage(**m) for m in session_history]
    return ChatResponse(
        session_id=session_id,
        messages=messages_for_response,
        pending_command=final_pending_command_output
    )

@app.get("/session/{session_id}/log", response_model=SessionLogResponse)
def get_log(session_id: str):
    # Ensure session exists conceptually, though log might be empty
    # if session_id not in sessions: # Check might be less relevant now if logs persist
    #     raise HTTPException(status_code=404, detail="Session not found")
    log = get_session_log(session_id)
    if not log and session_id not in sessions:
         raise HTTPException(status_code=404, detail="Session log not found")
         
    log_entries = [LogEntry(**entry) for entry in log]
    return SessionLogResponse(session_id=session_id, log=log_entries)

frontend_build_path = os.path.join(os.path.dirname(__file__), "frontend_build")
if os.path.exists(frontend_build_path):
    app.mount("/", StaticFiles(directory=frontend_build_path, html=True), name="static")
