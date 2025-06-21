"""
Browser integration tool using the browser_use library.
"""
import asyncio
from typing import Any, Dict, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from browser_use import Agent as BrowserUseAgent, Browser, BrowserConfig
    from browser_use.browser.context import BrowserContextConfig
    BROWSER_USE_AVAILABLE = True
    IMPORT_ERROR = None
except ImportError as e:
    BrowserUseAgent = None
    Browser = None
    BrowserConfig = None
    BrowserContextConfig = None
    BROWSER_USE_AVAILABLE = False
    IMPORT_ERROR = str(e)


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
        
    def _ensure_browser_initialized(self) -> tuple[bool, str]:
        """Ensure browser and agent are initialized."""
        if not BROWSER_USE_AVAILABLE:
            return False, f"browser_use library not available. Import error: {IMPORT_ERROR}. Please install required dependencies: pip install python-dotenv playwright && playwright install"
            
        try:
            if self.browser is None:
                # Create BrowserConfig with context configuration
                browser_config = BrowserConfig(
                    headless=True,
                    disable_security=True
                )
                # Set the context configuration
                context_config = BrowserContextConfig(
                    headless=True,
                    disable_security=True
                )
                browser_config.new_context_config = context_config
                
                self.browser = Browser(config=browser_config)
                
        except Exception as e:
            return False, f"Failed to initialize browser: {str(e)}. Try running: playwright install"
            
        try:
            if self.agent is None and self.llm is not None:
                self.agent = BrowserUseAgent(
                    task="",  # Will be set per action
                    llm=self.llm,
                    browser=self.browser
                )
        except Exception as e:
            return False, f"Failed to initialize browser agent: {str(e)}"
            
        return True, "Browser initialized successfully"
    
    def _run(self, action: str, target: str, value: str = "") -> str:
        """Execute browser action using browser_use."""
        initialized, message = self._ensure_browser_initialized()
        if not initialized:
            return f"Error: {message}"
            
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
            
            # Execute the browser task - run async method in sync context
            try:
                # Try to get the current event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, we need to run in a thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.agent.run(max_steps=3))
                        result = future.result()
                else:
                    result = loop.run_until_complete(self.agent.run(max_steps=3))
            except RuntimeError:
                # No event loop exists, create one
                result = asyncio.run(self.agent.run(max_steps=3))
            
            return f"Browser action completed: {task}\nResult: {result}"
            
        except Exception as e:
            return f"Error in browser action: {str(e)}"
    
    async def _arun(self, action: str, target: str, value: str = "") -> str:
        """Async version - not implemented."""
        return self._run(action, target, value)