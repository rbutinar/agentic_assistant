"""
Session-based logging functionality for the agentic assistant.
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger('agentic_assistant.logging')


@dataclass
class LogEntry:
    """A single log entry for a session."""
    timestamp: str
    level: str
    step: str
    data: Dict[str, Any]
    session_id: str


class SessionLogger:
    """Manages session-specific logging."""
    
    def __init__(self):
        self.session_logs: Dict[str, List[LogEntry]] = {}
    
    def log_step(self, session_id: str, step: str, data: Dict[str, Any], level: str = "INFO") -> None:
        """Log a step for a specific session."""
        timestamp = datetime.now().isoformat()
        
        log_entry = LogEntry(
            timestamp=timestamp,
            level=level,
            step=step,
            data=data,
            session_id=session_id
        )
        
        # Add to session logs
        if session_id not in self.session_logs:
            self.session_logs[session_id] = []
        
        self.session_logs[session_id].append(log_entry)
        
        # Also log to the main logger
        log_message = f"Session {session_id} - {step}: {json.dumps(data)}"
        logger.info(log_message)
    
    def get_session_log(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all log entries for a session."""
        if session_id not in self.session_logs:
            return []
        
        return [asdict(entry) for entry in self.session_logs[session_id]]
    
    def clear_session_log(self, session_id: str) -> None:
        """Clear log entries for a session."""
        if session_id in self.session_logs:
            del self.session_logs[session_id]
        
        logger.info(f"Cleared logs for session {session_id}")
    
    def get_all_sessions(self) -> List[str]:
        """Get all session IDs that have logs."""
        return list(self.session_logs.keys())


# Global session logger instance
session_logger = SessionLogger()

# Convenience functions
def log_step(session_id: str, step: str, data: Dict[str, Any], level: str = "INFO") -> None:
    """Log a step for a session."""
    session_logger.log_step(session_id, step, data, level)

def get_session_log(session_id: str) -> List[Dict[str, Any]]:
    """Get session logs."""
    return session_logger.get_session_log(session_id)

def clear_session_log(session_id: str) -> None:
    """Clear session logs."""
    session_logger.clear_session_log(session_id)