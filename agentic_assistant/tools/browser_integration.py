"""
Browser integration tool using the browser_use library.
"""
from typing import Any, Dict, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from browser_use import Agent as BrowserUseAgent, Browser
    from browser_use.browser.context import BrowserContextConfig
except ImportError:
    BrowserUseAgent = None
    Browser = None
    BrowserContextConfig = None


class BrowserInput(BaseModel):
    """Input for browser tool."""
    action: str = Field(description="Browser action: navigate, click, type, etc.")
    target: str = Field(description="Target element or URL")
    value: str = Field(default="", description="Value for input actions")


class BrowserIntegrationTool(BaseTool):
    """Tool for browser automation using browser_use library."""
    
    name: str = "browser"
    description: str = "Interact with web browsers: navigate to URLs, click elements, fill forms, etc. Provide the action and target."
    args_schema: type[BaseModel] = BrowserInput
    llm: Optional[Any] = None
    browser: Optional[Any] = None
    agent: Optional[Any] = None
    
    def __init__(self, llm=None, **kwargs):
        super().__init__(llm=llm, browser=None, agent=None, **kwargs)
        
    def _ensure_browser_initialized(self) -> bool:
        """Ensure browser and agent are initialized."""
        if BrowserUseAgent is None:
            return False
            
        if self.browser is None:
            self.browser = Browser(
                config=BrowserContextConfig(
                    headless=True,
                    disable_security=True
                )
            )
            
        if self.agent is None and self.llm is not None:
            self.agent = BrowserUseAgent(
                task="",  # Will be set per action
                llm=self.llm,
                browser=self.browser
            )
            
        return True
    
    def _run(self, action: str, target: str, value: str = "") -> str:
        """Execute browser action using browser_use."""
        if not self._ensure_browser_initialized():
            return "Error: browser_use library not available. Please install it."
            
        try:
            if action.lower() == "navigate":
                task = f"Navigate to {target}"
            elif action.lower() == "click":
                task = f"Click on {target}"
            elif action.lower() == "type" and value:
                task = f"Type '{value}' into {target}"
            elif action.lower() == "search":
                task = f"Search for '{target}' {f'with value {value}' if value else ''}"
            else:
                task = f"Perform {action} on {target} {f'with value {value}' if value else ''}"
            
            if self.agent is None:
                return f"Error: LLM not provided for browser agent initialization"
                
            # Update the task for this specific action
            self.agent.task = task
            
            # Execute the browser task
            result = self.agent.run(max_steps=3)
            
            return f"Browser action completed: {task}\nResult: {result}"
            
        except Exception as e:
            return f"Error in browser action: {str(e)}"
    
    async def _arun(self, action: str, target: str, value: str = "") -> str:
        """Async version - not implemented."""
        return self._run(action, target, value)