from langchain.tools import Tool
from typing import Any, Dict
import subprocess

# Example: Terminal tool
def run_terminal_command(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout or result.stderr
    except Exception as e:
        return f"[Terminal error: {e}]"

terminal_tool = Tool(
    name="terminal",
    func=run_terminal_command,
    description="Executes a terminal command and returns the output."
)

# Example: Search tool (placeholder)
def search_tool_func(query: str) -> str:
    # In production, integrate with a real search API
    return f"[Search results for: {query}]"

search_tool = Tool(
    name="search",
    func=search_tool_func,
    description="Searches the web for information."
)

tool_list = [terminal_tool, search_tool]
