from typing import Dict, List, Any
import threading
import logging
import os
import json

# Simple in-memory session log (thread-safe)
_session_logs: Dict[str, List[Dict[str, Any]]] = {}
_lock = threading.Lock()

# --- File logging setup ---
LOG_FILENAME = "agent_session.log"
LOG_DIRECTORY = os.path.dirname(__file__) # Log in the same directory as logging.py
LOG_FILEPATH = os.path.join(LOG_DIRECTORY, LOG_FILENAME)

print(f"--- DEBUG: Attempting to log to: {LOG_FILEPATH} ---") # Print the path

# Configure the logger
agent_logger = logging.getLogger("agent_session")
agent_logger.setLevel(logging.INFO) # Set the minimum level to log

# Prevent adding multiple handlers if this module is reloaded
# Temporarily removed for debugging:
# if not agent_logger.hasHandlers():

# Ensure handlers are cleared first if re-running in same process (e.g. notebook)
for handler in agent_logger.handlers[:]:
    agent_logger.removeHandler(handler)

# Create file handler
try:
    file_handler = logging.FileHandler(LOG_FILEPATH)
    file_handler.setLevel(logging.INFO)

    # Create formatter and add it to the handler
    # Example format: 2023-10-27 10:30:00,123 - INFO - Session [session_id] - Type [step_type] - Data: {data}
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the handler to the logger
    agent_logger.addHandler(file_handler)
    print("--- DEBUG: File handler added successfully. ---")
except Exception as e:
    print(f"--- DEBUG: FAILED to add file handler: {e} ---")
# --- End File logging setup ---

def log_step(session_id: str, step_type: str, data: Any):
    # 1. Log to file
    try:
        # Attempt to serialize data as JSON for cleaner logging
        data_str = json.dumps(data)
    except TypeError:
        data_str = str(data) # Fallback to string representation
    log_message = f"Session [{session_id}] - Type [{step_type}] - Data: {data_str}"
    try:
        agent_logger.info(log_message)
        # Explicitly flush the handler
        for handler in agent_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
    except Exception as e:
        print(f"--- DEBUG: FAILED to log message: {e} ---")

    # 2. Log to in-memory (existing behavior)
    with _lock:
        if session_id not in _session_logs:
            _session_logs[session_id] = []
        _session_logs[session_id].append({"type": step_type, "data": data})

def get_session_log(session_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return list(_session_logs.get(session_id, []))

def clear_session_log(session_id: str):
    with _lock:
        _session_logs.pop(session_id, None)
