from typing import Dict, List, Any
import threading

# Simple in-memory session log (thread-safe)
_session_logs: Dict[str, List[Dict[str, Any]]] = {}
_lock = threading.Lock()

def log_step(session_id: str, step_type: str, data: Any):
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
