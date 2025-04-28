import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uuid
from typing import Dict, List

from models import StartSessionResponse, ChatMessage, ChatRequest, ChatResponse, SessionLogResponse, LogEntry
from agent.agent import run_agent_with_tool_intercept
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
    # If there is a pending terminal command, expect user confirmation
    if request.session_id in pending_tools:
        pending = pending_tools[request.session_id]
        user_msg = request.message.strip().lower()
        if user_msg.startswith("[terminal confirm]: yes"):
            try:
                # User accepted, run the command
                output = run_terminal_command(pending['command'])
                # Remove pending
                del pending_tools[request.session_id]
                # Add terminal output to chat and log
                sessions[request.session_id].append({"role": "assistant", "content": f"[Terminal Output]:\n{output}"})
                log_step(request.session_id, "terminal_executed", {"command": pending['command'], "output": output})
            except Exception as e:
                error_message = f"Error executing terminal command: {str(e)}"
                log_step(request.session_id, "terminal_error", {"command": pending['command'], "error": error_message})
                sessions[request.session_id].append({"role": "assistant", "content": error_message})
                del pending_tools[request.session_id] # Ensure pending is cleared
                messages = [ChatMessage(**m) for m in sessions[request.session_id]]
                return ChatResponse(session_id=request.session_id, messages=messages)

            try:
                # Re-invoke the agent with terminal tool disabled so it can reason over the output, but not chain terminal calls
                agent_reply, tool_request = run_agent_with_tool_intercept(sessions[request.session_id], request.session_id, log_func=log_step, disable_terminal_tool=True)
                sessions[request.session_id].append({"role": "assistant", "content": agent_reply})
                log_step(request.session_id, "assistant_reply", {"content": agent_reply})
            except Exception as e:
                error_message = f"Error during agent follow-up after terminal execution: {str(e)}"
                log_step(request.session_id, "agent_followup_error", {"error": error_message})
                sessions[request.session_id].append({"role": "assistant", "content": error_message})
            
            # Always return the session messages after attempting the follow-up
            messages = [ChatMessage(**m) for m in sessions[request.session_id]]
            return ChatResponse(session_id=request.session_id, messages=messages)
        else:
            # User rejected
            del pending_tools[request.session_id]
            sessions[request.session_id].append({"role": "assistant", "content": f"Terminal command was not executed."})
            log_step(request.session_id, "terminal_rejected", {"command": pending['command']})
        messages = [ChatMessage(**m) for m in sessions[request.session_id]]
        return ChatResponse(session_id=request.session_id, messages=messages)
    # Add user message to history
    sessions[request.session_id].append({"role": "user", "content": request.message})
    log_step(request.session_id, "user_message", {"content": request.message})
    # Run agent (LangChain orchestration) -- intercept tool use
    agent_reply, tool_request = run_agent_with_tool_intercept(sessions[request.session_id], request.session_id, log_func=log_step)
    if tool_request and tool_request['tool'] == 'terminal':
        # Pause and ask for confirmation
        pending_tools[request.session_id] = tool_request
        sessions[request.session_id].append({"role": "assistant", "content": f"[TERMINAL COMMAND]: {tool_request['command']}"})
        log_step(request.session_id, "terminal_requested", {"command": tool_request['command']})
        messages = [ChatMessage(**m) for m in sessions[request.session_id]]
        return ChatResponse(session_id=request.session_id, messages=messages)
    # Otherwise, normal agent reply
    sessions[request.session_id].append({"role": "assistant", "content": agent_reply})
    log_step(request.session_id, "assistant_reply", {"content": agent_reply})
    messages = [ChatMessage(**m) for m in sessions[request.session_id]]
    return ChatResponse(session_id=request.session_id, messages=messages)

@app.get("/session/{session_id}/log", response_model=SessionLogResponse)
def get_log(session_id: str):
    log = get_session_log(session_id)
    log_entries = [LogEntry(**entry) for entry in log]
    return SessionLogResponse(session_id=session_id, log=log_entries)
