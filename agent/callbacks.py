from typing import Any, Dict, List, Union
from uuid import UUID

from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

from .logging import log_step # Use relative import

class FileLoggingCallbackHandler(BaseCallbackHandler):
    """Callback Handler that logs agent actions and tool usage to a file via log_step."""

    def __init__(self, session_id: str, **kwargs: Any) -> None:
        """Initialize callback handler."""
        super().__init__(**kwargs)
        self.session_id = session_id

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Log when LLM starts."""
        # Optional: Log prompts if needed, might be verbose
        # log_step(self.session_id, "llm_start", {"prompts": prompts})
        pass

    def on_chat_model_start(
        self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], **kwargs: Any
    ) -> Any:
        """Log when Chat Model starts."""
        # Optional: Log messages if needed
        # log_step(self.session_id, "chat_model_start", {"messages": messages})
        pass

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Log when LLM ends."""
        # Optional: Log response if needed
        # log_step(self.session_id, "llm_end", {"response": response.dict()})
        pass

    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Log LLM error."""
        log_step(self.session_id, "llm_error", {"error": str(error)})

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """Log agent action."""
        # Action log often contains the 'thought' process
        log_step(self.session_id, "agent_action", {"tool": action.tool, "tool_input": action.tool_input, "log": action.log})

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        """Log tool start."""
        # Tool name is in serialized['name']
        log_step(self.session_id, "tool_start", {"tool": serialized.get('name'), "input": input_str})

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Log tool end."""
        # Tool name might need to be inferred or stored from on_tool_start if not present
        log_step(self.session_id, "tool_end", {"output": output})

    def on_tool_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> Any:
        """Log tool error."""
        log_step(self.session_id, "tool_error", {"error": str(error)})

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> Any:
        """Log agent finish."""
        log_step(self.session_id, "agent_finish", {"output": finish.return_values.get('output')})
