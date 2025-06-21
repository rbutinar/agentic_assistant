"""
Terminal tool for executing system commands.
"""
import subprocess
from typing import Any, Dict
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class TerminalInput(BaseModel):
    """Input for terminal tool."""
    command: str = Field(description="Command to execute")


class TerminalConfirmationRequired(Exception):
    """Exception raised when terminal command requires confirmation."""
    
    def __init__(self, command: str):
        self.command = command
        super().__init__(f"Terminal command requires confirmation: {command}")


class TerminalTool(BaseTool):
    """Tool for executing terminal commands."""
    
    name: str = "terminal"
    description: str = "Process system commands. Use this for system operations, file management, and running programs."
    args_schema: type[BaseModel] = TerminalInput
    safe_mode: bool = True
    
    def __init__(self, safe_mode: bool = True, **kwargs):
        super().__init__(safe_mode=safe_mode, **kwargs)
    
    def _run(self, command: str) -> str:
        """Execute the command."""
        if self.safe_mode:
            # In safe mode, raise exception for confirmation
            raise TerminalConfirmationRequired(command)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
            
            if result.returncode != 0:
                output += f"\nReturn code: {result.returncode}"
            
            return output or "Command executed successfully (no output)"
            
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30 seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    async def _arun(self, command: str) -> str:
        """Async version - not implemented."""
        return self._run(command)