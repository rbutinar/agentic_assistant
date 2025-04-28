import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uuid
from typing import Dict, List

from models import StartSessionResponse, ChatMessage, ChatRequest, ChatResponse, SessionLogResponse, LogEntry
from agent.agent import execute_agent_turn
from agent.logging import log_step, get_session_log, clear_session_log
from agent.tools import run_terminal_command

# Load environment variables from .env file
load_dotenv()

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

# In-memory session storage (for chat history)
sessions: Dict[str, List[dict]] = {}
# In-memory pending tool actions (per session)
pending_tools: Dict[str, dict] = {}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/session", response_model=StartSessionResponse)
def start_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = []
    clear_session_log(session_id)
    return StartSessionResponse(session_id=session_id)

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session_history = sessions[request.session_id]
    user_message_content = request.message.strip()

    # --- Handle Pending Command Confirmation ---
    if request.session_id in pending_tools:
        pending_info = pending_tools[request.session_id]
        command_to_run = pending_info['command']
        del pending_tools[request.session_id] # Remove pending command regardless of outcome

        if user_message_content.lower().startswith("[terminal confirm]: yes"):
            try:
                log_step(request.session_id, "terminal_confirmed", {"command": command_to_run})
                # Execute the confirmed command
                output = run_terminal_command(command_to_run)
                log_step(request.session_id, "terminal_executed", {"command": command_to_run, "output": output})
                # Add execution result to history
                session_history.append({"role": "assistant", "content": f"[Terminal Output]:\n{output}"})

                # Optional: Follow-up agent call to process the output (can be added later if needed)
                # For now, just return the output directly.

            except Exception as e:
                log_step(request.session_id, "terminal_error", {"command": command_to_run, "error": str(e)})
                session_history.append({"role": "assistant", "content": f"Error executing terminal command: {str(e)}"})

        elif user_message_content.lower().startswith("[terminal confirm]: no"):
            log_step(request.session_id, "terminal_rejected", {"command": command_to_run})
            session_history.append({"role": "assistant", "content": f"Terminal command '{command_to_run}' was not executed."})
        else:
            # If it wasn't a confirmation reply, treat it as a normal message while a command was pending.
            # Log this potentially confusing state.
            log_step(request.session_id, "unexpected_message_while_pending", {"pending_command": command_to_run, "user_message": user_message_content})
            session_history.append({"role": "user", "content": user_message_content}) # Add the user message anyway
            # Re-invoke agent since the user sent a new message instead of confirming/denying
            agent_reply, pending_command_info = execute_agent_turn(
                user_input=user_message_content,
                chat_history_messages=session_history[:-1], # Pass history *before* this user message
                safe_mode=request.safe_mode,
                session_id=request.session_id,
                log_func=log_step
            )
            # Process the agent's response from this unexpected turn
            if pending_command_info:
                 pending_tools[request.session_id] = pending_command_info
                 # Return immediately with pending command signal
                 messages = [ChatMessage(**m) for m in session_history]
                 return ChatResponse(
                     session_id=request.session_id,
                     messages=messages,
                     pending_command=pending_command_info.get("command")
                 )
            elif agent_reply:
                 session_history.append({"role": "assistant", "content": agent_reply})

        # Return message list after handling confirmation (yes/no) or unexpected message
        messages = [ChatMessage(**m) for m in session_history]
        return ChatResponse(session_id=request.session_id, messages=messages)

    # --- Normal Message Handling (No pending command) ---
    session_history.append({"role": "user", "content": user_message_content})
    log_step(request.session_id, "user_message", {"content": user_message_content})

    # Call the new agent execution function
    agent_reply, pending_command_info = execute_agent_turn(
        user_input=user_message_content,
        chat_history_messages=session_history[:-1], # Pass history *before* this user message
        safe_mode=request.safe_mode,
        session_id=request.session_id,
        log_func=log_step
    )

    # --- Process Agent Response ---
    pending_command_output = None
    if pending_command_info:
        # Agent wants to run a command AND safe mode was on
        log_step(request.session_id, "terminal_confirmation_required", {"command": pending_command_info.get("command")})
        pending_tools[request.session_id] = pending_command_info
        pending_command_output = pending_command_info.get("command")
        # No agent text reply in this case, frontend shows confirmation prompt
    elif agent_reply:
        # Normal agent text reply
        session_history.append({"role": "assistant", "content": agent_reply})
        log_step(request.session_id, "assistant_reply", {"content": agent_reply})
    else:
        # Agent finished but produced no output and no pending command (should be rare)
        log_step(request.session_id, "agent_empty_response", {})
        session_history.append({"role": "assistant", "content": "[Agent produced no response]"})

    # --- Return Response to Frontend ---
    messages = [ChatMessage(**m) for m in sessions[request.session_id]]
    return ChatResponse(
        session_id=request.session_id,
        messages=messages,
        pending_command=pending_command_output # Will be None if no command is pending
    )

@app.get("/session/{session_id}/log", response_model=SessionLogResponse)
def get_log(session_id: str):
    log = get_session_log(session_id)
    log_entries = [LogEntry(**entry) for entry in log]
    return SessionLogResponse(session_id=session_id, log=log_entries)
