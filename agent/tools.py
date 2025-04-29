import subprocess
import logging
from langchain.tools import Tool, tool # Import tool decorator
from langchain_community.tools import DuckDuckGoSearchRun
from typing import List

# Custom Exceptions for Terminal Tool
class TerminalConfirmationRequired(Exception):
    """Signal that a terminal command requires user confirmation."""
    def __init__(self, command: str):
        self.command = command
        super().__init__(f"Confirmation required for command: {command}")

class TerminalToolError(Exception):
    """Signal an error during direct terminal command execution."""
    pass


# --- Tool Functions ---

def run_terminal_command(command: str) -> str:
    """Executes a terminal command directly and returns its output or raises TerminalToolError."""
    logging.info(f"Executing terminal command (direct): {command}")
    if not command: # Basic validation
        return "Error: No command provided."
    try:
        # Using shell=True for simplicity, but be aware of security implications.
        # Consider more robust execution methods for production.
        # Timeout added for safety.
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            check=False, # Don't raise CalledProcessError automatically
            timeout=30 # Add a timeout (e.g., 30 seconds)
        )
        if result.returncode == 0:
            output = result.stdout.strip() or "(No output)"
            logging.info(f"Command successful: {command}\nOutput:\n{output}")
            return output
        else:
            error_output = result.stderr.strip() or f"Command failed with exit code {result.returncode}"
            logging.error(f"Command failed: {command}\nError:\n{error_output}")
            # Raise specific error for the graph to potentially handle
            raise TerminalToolError(f"Command '{command}' failed: {error_output}")
            
    except subprocess.TimeoutExpired:
        logging.error(f"Command timed out: {command}")
        raise TerminalToolError(f"Command '{command}' timed out after 30 seconds.")
    except Exception as e:
        logging.error(f"Error executing command '{command}': {e}")
        # Raise specific error
        raise TerminalToolError(f"Error executing command '{command}': {e}")

def request_terminal_confirmation(command: str):
    """Raises TerminalConfirmationRequired to signal the graph to interrupt."""
    logging.info(f"Requesting confirmation for terminal command: {command}")
    raise TerminalConfirmationRequired(command)

# Use the @tool decorator for the search tool for better integration
@tool("search")
def search_tool(query: str) -> str:
    """Runs a web search using DuckDuckGo and returns results."""
    logging.info(f"Executing search: {query}")
    search = DuckDuckGoSearchRun()
    try:
        results = search.run(query)
        logging.info(f"Search successful for '{query}'. Results obtained.") # Avoid logging potentially large results
        return results
    except Exception as e:
        logging.error(f"Error during search for '{query}': {e}")
        return f"Error performing search: {e}"

# --- Tool List Generation ---

def get_tools(safe_mode: bool) -> List[Tool]:
    """Returns the list of tools appropriate for the given safe_mode."""
    import logging
    tools = [search_tool] # Search tool is always available
    
    logging.info(f"[get_tools] safe_mode={safe_mode}")
    if safe_mode:
        logging.info("[get_tools] Selecting request_terminal_confirmation for terminal tool (confirmation required)")
        terminal_tool = Tool(
            name="terminal",
            func=request_terminal_confirmation,
            description="Proposes a terminal command for execution. Raises an exception to signal that user confirmation is required before running.",
        )
    else:
        logging.info("[get_tools] Selecting run_terminal_command for terminal tool (direct execution)")
        terminal_tool = Tool(
            name="terminal",
            func=run_terminal_command,
            description="Executes a terminal command directly and returns the output. Use with caution.",
        )
    
    tools.append(terminal_tool)
    return tools

# Keep the old list for compatibility if anything still imports it directly?
# Maybe remove it later. For now, keep it but note it's deprecated.
# DEPRECATED: Use get_tools(safe_mode) instead.
tool_list_legacy = get_tools(safe_mode=True) # Default to safe mode for legacy access
