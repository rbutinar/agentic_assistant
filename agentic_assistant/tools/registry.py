"""
Tool registry for the agentic assistant.
"""
from typing import List
from langchain_core.tools import Tool
from agentic_assistant.tools.terminal import TerminalTool
from agentic_assistant.tools.search import SearchTool
from agentic_assistant.tools.browser_integration import BrowserIntegrationTool


def get_tools(llm=None, safe_mode: bool = True) -> List[Tool]:
    """Get all available tools for the agent."""
    return [
        TerminalTool(safe_mode=safe_mode),
        SearchTool(),
        BrowserIntegrationTool(llm=llm),
    ]