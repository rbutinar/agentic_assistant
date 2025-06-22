"""
Browser integration tool using the browser_use library.
"""
import asyncio
import logging
import os
import sys
from typing import Any, Dict, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    # Set encoding environment variables
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    
    # Create a custom log handler that replaces emojis
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                # Replace problematic emoji characters
                if hasattr(record, 'msg'):
                    record.msg = str(record.msg).replace('🚀', '[START]').replace('❌', '[ERROR]').replace('📍', '[STEP]').replace('⚠️', '[WARNING]')
                super().emit(record)
            except UnicodeEncodeError:
                # Fallback: strip all non-ASCII characters
                if hasattr(record, 'msg'):
                    record.msg = ''.join(char for char in str(record.msg) if ord(char) < 128)
                super().emit(record)
    
    # Patch logging to use safe handler
    def patch_browser_use_logging():
        import logging
        browser_use_logger = logging.getLogger('browser_use')
        if browser_use_logger.handlers:
            for handler in browser_use_logger.handlers[:]:
                if isinstance(handler, logging.StreamHandler):
                    browser_use_logger.removeHandler(handler)
                    safe_handler = SafeStreamHandler()
                    safe_handler.setLevel(handler.level)
                    safe_handler.setFormatter(handler.formatter)
                    browser_use_logger.addHandler(safe_handler)
else:
    def patch_browser_use_logging():
        pass

try:
    from browser_use import Agent as BrowserUseAgent, Browser, BrowserConfig
    from browser_use.browser.context import BrowserContextConfig
    BROWSER_USE_AVAILABLE = True
    IMPORT_ERROR = None
    # Apply logging patch after import
    patch_browser_use_logging()
except ImportError as e:
    BrowserUseAgent = None
    Browser = None
    BrowserConfig = None
    BrowserContextConfig = None
    BROWSER_USE_AVAILABLE = False
    IMPORT_ERROR = str(e)


class BrowserInput(BaseModel):
    """Input for browser tool."""
    action: str = Field(description="Browser action: navigate, click, type, pause, resume, show_browser, manual_mode, status, restart_visible, end_session, etc.")
    target: str = Field(description="Target element, URL, or task description")
    value: str = Field(default="", description="Value for input actions")
    instructions: str = Field(default="", description="Additional detailed instructions for the browser agent")


class BrowserIntegrationTool(BaseTool):
    """Tool for browser automation using browser_use library."""
    
    name: str = "browser"
    description: str = """Interact with web browsers to navigate, extract content, fill forms, and perform actions.
    
    Parameters:
    - action: Basic action type (navigate, click, type, extract, etc.)
    - target: URL, element selector, or target description
    - value: Text to input (for type actions)
    - instructions: Detailed task instructions for complex operations
    
    Example usage:
    - Navigate: action='navigate', target='https://example.com', instructions='Go to the homepage and wait for it to load'
    - Extract: action='extract', target='https://news.com', instructions='Extract the main headlines'
    - Login: action='navigate', target='https://site.com', instructions='Navigate to login page'
    
    Actions: navigate, click, type, extract, search, pause, resume, show_browser, manual_mode, status, restart_visible, end_session."""
    args_schema: type[BaseModel] = BrowserInput
    llm: Optional[Any] = None
    browser: Optional[Any] = None
    agent: Optional[Any] = None
    _is_browser_visible: bool = False
    _is_interactive_session: bool = False
    _last_action: str = ""
    
    def __init__(self, llm=None, **kwargs):
        super().__init__(llm=llm, browser=None, agent=None, **kwargs)
        self._is_browser_visible = False
        self._is_interactive_session = False
        self._last_action = ""
        
    def _ensure_browser_initialized(self) -> tuple[bool, str]:
        """Ensure browser and agent are initialized."""
        if not BROWSER_USE_AVAILABLE:
            return False, f"browser_use library not available. Import error: {IMPORT_ERROR}. Please install required dependencies: pip install python-dotenv playwright && playwright install"
            
        try:
            if self.browser is None:
                # Check if user wants to show browser or keep it hidden
                # Force visible mode for debugging navigation issues
                show_browser = True  # Temporary: always show browser for debugging
                
                # Base browser arguments for performance
                browser_args = [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--allow-running-insecure-content',
                    # Performance optimizations
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-background-networking',
                    '--disable-ipc-flooding-protection',
                    '--aggressive-cache-discard',
                    '--memory-pressure-off',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-javascript-harmony-shipping'
                ]
                
                # Keep images enabled for better compatibility
                
                # Create BrowserConfig with performance optimizations
                browser_config = BrowserConfig(
                    headless=not show_browser,
                    disable_security=True,
                    extra_browser_args=browser_args
                )
                # Set the context configuration with conditional image blocking
                context_config = BrowserContextConfig(
                    headless=not show_browser,
                    disable_security=True
                )
                
                browser_config.new_context_config = context_config
                
                self.browser = Browser(config=browser_config)
                
        except Exception as e:
            error_msg = str(e)
            if "playwright" in error_msg.lower():
                return False, f"Playwright not properly installed: {error_msg}. Run: pip install playwright && playwright install chromium"
            return False, f"Failed to initialize browser: {error_msg}. Try running: playwright install chromium"
            
        try:
            if self.agent is None and self.llm is not None:
                # Create agent without initial task - it will be set dynamically
                self.agent = BrowserUseAgent(
                    task="",  # Will be set per action
                    llm=self.llm,
                    browser=self.browser,
                    # Disable memory to prevent interference with new tasks
                    enable_memory=False
                )
        except Exception as e:
            return False, f"Failed to initialize browser agent: {str(e)}"
            
        return True, "Browser initialized successfully"
    
    def _setup_fast_mode_blocking(self):
        """Setup image blocking for fast mode that can be dynamically controlled."""
        try:
            # This will be applied to new contexts created by the browser_use agent
            # The agent can still override this if it detects issues
            if hasattr(self.browser, '_config') and hasattr(self.browser._config, 'new_context_config'):
                # Note: Actual implementation would require access to browser_use internals
                # For now, we'll rely on the browser args approach but make it more flexible
                pass
        except Exception as e:
            print(f"⚠️ Warning: Could not setup fast mode blocking: {e}")
            # Fallback to browser args approach (already implemented)
    
    def _should_preserve_browser_session(self, action: str, target: str, instructions: str) -> bool:
        """Determine if the browser session should be preserved for interactive tasks."""
        # Preserve session for interactive scenarios
        interactive_keywords = [
            'login', 'signin', 'sign in', 'authenticate', 'credentials',
            'password', 'username', 'email', 'user', 'account',
            'manual', 'pause', 'wait', 'input', 'form', 'captcha',
            'booking', 'reservation', 'checkout', 'payment',
            'interactive', 'session', 'continue', 'step by step'
        ]
        
        # Check if this is an interactive site (common login/booking sites)
        interactive_domains = [
            'booking.com', 'expedia.com', 'airbnb.com', 'hotels.com',
            'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
            'github.com', 'google.com', 'microsoft.com', 'amazon.com',
            'paypal.com', 'stripe.com', 'auth0.com'
        ]
        
        # Check if we're already in an interactive session
        if self._is_interactive_session:
            return True
        
        # Check action types that suggest interactivity
        if action.lower() in ['pause', 'manual_mode', 'type', 'input']:
            return True
        
        # Check for interactive keywords in instructions or target
        combined_text = f"{target} {instructions}".lower()
        if any(keyword in combined_text for keyword in interactive_keywords):
            return True
        
        # Check if navigating to interactive domains
        if action.lower() == 'navigate':
            target_lower = target.lower()
            if any(domain in target_lower for domain in interactive_domains):
                return True
        
        # Check if previous action was interactive
        if self._last_action in ['navigate', 'type', 'click'] and self._is_interactive_session:
            return True
        
        return False
    
    
    def _run(self, action: str, target: str, value: str = "", instructions: str = "") -> str:
        """Execute browser action using browser_use."""
        initialized, message = self._ensure_browser_initialized()
        if not initialized:
            return f"Error: {message}"
            
        try:
            # Handle user intervention actions first
            if action.lower() == "pause":
                return self._pause_agent(target)
            elif action.lower() == "resume":
                return self._resume_agent()
            elif action.lower() == "show_browser":
                return self._show_browser()
            elif action.lower() == "manual_mode":
                return self._enter_manual_mode(target, value)
            elif action.lower() == "status":
                return self._get_agent_status()
            elif action.lower() == "restart_visible":
                return self._restart_browser_visible()
            elif action.lower() == "end_session":
                return self._end_interactive_session()
            
            # Build comprehensive task from all parameters
            else:
                # Construct a comprehensive task description
                task_parts = []
                
                # Add action-specific context with clear, direct instructions
                if action.lower() == "navigate":
                    # Use very explicit and imperative language for navigation
                    task_parts.append(f"IMPORTANT: Navigate DIRECTLY to {target}")
                    task_parts.append(f"NEVER go to Google, search engines, or any other website first")
                    task_parts.append(f"The ONLY URL you should visit is: {target}")
                    task_parts.append(f"Use the go_to_url action immediately with: {target}")
                elif action.lower() == "click":
                    task_parts.append(f"Click on {target}")
                elif action.lower() == "type" and value:
                    task_parts.append(f"Type '{value}' into {target}")
                elif action.lower() == "search":
                    task_parts.append(f"Search for '{target}'" + (f" with value '{value}'" if value else ""))
                elif action.lower() == "extract":
                    task_parts.append(f"Navigate to {target} and extract content")
                else:
                    task_parts.append(f"{action} on {target}" + (f" with value '{value}'" if value else ""))
                
                # Add detailed instructions if provided
                if instructions.strip():
                    task_parts.append(f"Additional instructions: {instructions}")
                
                # Create a very direct task that forces the exact behavior
                task = ". ".join(task_parts)
                
                # For navigate actions, override with extremely direct task
                if action.lower() == "navigate":
                    task = f"Navigate to {target} immediately. Do not visit any other website. Your first and only action should be go_to_url with {target}."
            
            if self.agent is None:
                return f"Error: Browser agent not initialized"
                
            # Debug: Print the final task that will be executed
            print(f"🔍 BROWSER DEBUG - Final task: {task}")
            
            # Remove fast_mode complexity
            
            # Smart browser session management - preserve for interactive tasks
            should_preserve_session = self._should_preserve_browser_session(action, target, instructions)
            
            try:
                if should_preserve_session and self.browser is not None and self.agent is not None:
                    # Preserve existing browser session for interactive tasks
                    print(f"🔄 BROWSER DEBUG - Preserving session for interactive task")
                    # Update agent task for continued operation
                    self.agent.task = task
                else:
                    # Close existing browser if it exists (for non-interactive or first time)
                    if self.browser is not None:
                        try:
                            # Try to close properly (might fail if already closed)
                            pass  # browser_use handles cleanup automatically
                        except:
                            pass  # Ignore cleanup errors
                        self.browser = None
                        self.agent = None
                    
                    # Reinitialize browser
                    initialized, message = self._ensure_browser_initialized()
                    if not initialized:
                        return f"Error reinitializing browser: {message}"
                    
                    # Create fresh agent with the task
                    self.agent = BrowserUseAgent(
                        task=task,
                        llm=self.llm,
                        browser=self.browser,
                        enable_memory=False  # Disable memory to prevent interference
                    )
                    print(f"🆕 BROWSER DEBUG - Created fresh browser session")
                
                # Track session state
                self._is_interactive_session = should_preserve_session
                self._last_action = action
                
            except Exception as e:
                return f"Error managing browser session: {str(e)}"
            
            # Execute the browser task - run in separate thread to avoid blocking
            try:
                # Set up event loop policy for Windows
                if sys.platform == "win32":
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                
                # Run the agent with timeout to prevent infinite hanging
                import concurrent.futures
                import threading
                
                def run_with_timeout():
                    try:
                        # Set event loop policy for this thread
                        if sys.platform == "win32":
                            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                        
                        # Run with more steps for complex content extraction
                        result = asyncio.run(self.agent.run(max_steps=15))
                        return result
                    except Exception as e:
                        return f"Error in browser execution: {str(e)}"
                
                # Use ThreadPoolExecutor with timeout
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_with_timeout)
                    try:
                        result = future.result(timeout=90)  # 1.5 minute timeout for content extraction
                    except concurrent.futures.TimeoutError:
                        return f"Browser action '{action}' timed out after 1.5 minutes. The website may be slow or have anti-bot protection."
                    except Exception as e:
                        return f"Error executing browser action: {str(e)}"
                        
            except Exception as e:
                return f"Error in browser execution: {str(e)}"
            
            return f"Browser action completed: {task}\nResult: {result}"
            
        except Exception as e:
            return f"Error executing browser action '{action}' on {target}: {str(e)}"
    
    
    async def _arun(self, action: str, target: str, value: str = "", instructions: str = "") -> str:
        """Async version of browser tool execution."""
        initialized, message = self._ensure_browser_initialized()
        if not initialized:
            return f"Error: {message}"
            
        try:
            # Handle user intervention actions first
            if action.lower() == "pause":
                return self._pause_agent(target)
            elif action.lower() == "resume":
                return self._resume_agent()
            elif action.lower() == "show_browser":
                return self._show_browser()
            elif action.lower() == "manual_mode":
                return self._enter_manual_mode(target, value)
            elif action.lower() == "status":
                return self._get_agent_status()
            elif action.lower() == "restart_visible":
                return self._restart_browser_visible()
            elif action.lower() == "end_session":
                return self._end_interactive_session()
            
            # Build comprehensive task from all parameters
            else:
                # Construct a comprehensive task description
                task_parts = []
                
                # Add action-specific context with clear, direct instructions
                if action.lower() == "navigate":
                    # Use very explicit and imperative language for navigation
                    task_parts.append(f"IMPORTANT: Navigate DIRECTLY to {target}")
                    task_parts.append(f"NEVER go to Google, search engines, or any other website first")
                    task_parts.append(f"The ONLY URL you should visit is: {target}")
                    task_parts.append(f"Use the go_to_url action immediately with: {target}")
                elif action.lower() == "click":
                    task_parts.append(f"Click on {target}")
                elif action.lower() == "type" and value:
                    task_parts.append(f"Type '{value}' into {target}")
                elif action.lower() == "search":
                    task_parts.append(f"Search for '{target}'" + (f" with value '{value}'" if value else ""))
                elif action.lower() == "extract":
                    task_parts.append(f"Navigate to {target} and extract content")
                else:
                    task_parts.append(f"{action} on {target}" + (f" with value '{value}'" if value else ""))
                
                # Add detailed instructions if provided
                if instructions.strip():
                    task_parts.append(f"Additional instructions: {instructions}")
                
                # Create a very direct task that forces the exact behavior
                task = ". ".join(task_parts)
                
                # For navigate actions, override with extremely direct task
                if action.lower() == "navigate":
                    task = f"Navigate to {target} immediately. Do not visit any other website. Your first and only action should be go_to_url with {target}."
            
            if self.agent is None:
                return f"Error: Browser agent not initialized"
                
            # Debug: Print the final task that will be executed
            print(f"🔍 BROWSER DEBUG - Final task: {task}")
            
            # Remove fast_mode complexity
            
            # Smart browser session management - preserve for interactive tasks
            should_preserve_session = self._should_preserve_browser_session(action, target, instructions)
            
            try:
                if should_preserve_session and self.browser is not None and self.agent is not None:
                    # Preserve existing browser session for interactive tasks
                    print(f"🔄 BROWSER DEBUG - Preserving session for interactive task")
                    # Update agent task for continued operation
                    self.agent.task = task
                else:
                    # Close existing browser if it exists (for non-interactive or first time)
                    if self.browser is not None:
                        try:
                            # Try to close properly (might fail if already closed)
                            pass  # browser_use handles cleanup automatically
                        except:
                            pass  # Ignore cleanup errors
                        self.browser = None
                        self.agent = None
                    
                    # Reinitialize browser
                    initialized, message = self._ensure_browser_initialized()
                    if not initialized:
                        return f"Error reinitializing browser: {message}"
                    
                    # Create fresh agent with the task
                    self.agent = BrowserUseAgent(
                        task=task,
                        llm=self.llm,
                        browser=self.browser,
                        enable_memory=False  # Disable memory to prevent interference
                    )
                    print(f"🆕 BROWSER DEBUG - Created fresh browser session")
                
                # Track session state
                self._is_interactive_session = should_preserve_session
                self._last_action = action
                
            except Exception as e:
                return f"Error managing browser session: {str(e)}"
            
            # Execute the browser task asynchronously
            try:
                # Run the agent directly since we're in async context
                result = await self.agent.run(max_steps=15)
                return f"Browser action completed: {task}\nResult: {result}"
            except Exception as e:
                return f"Error in browser execution: {str(e)}"
            
        except Exception as e:
            return f"Error executing browser action '{action}' on {target}: {str(e)}"
    
    def _pause_agent(self, reason: str = "") -> str:
        """Pause the browser agent for user intervention."""
        if self.agent is None:
            return "Error: Browser agent not initialized"
        
        try:
            # Set interactive session flag to preserve browser
            self._is_interactive_session = True
            
            # Make browser visible if not already
            if not self._is_browser_visible:
                self._is_browser_visible = True
                # Note: For browser_use, visibility is set during initialization
                # Current session remains as-is, but future sessions will be visible
            
            pause_reason = f" Reason: {reason}" if reason else ""
            return f"✋ Browser agent paused for user intervention.{pause_reason}\n" \
                   f"📱 Browser session is preserved and ready for manual control.\n" \
                   f"🔄 Use 'resume' action to continue automation when ready.\n" \
                   f"💡 The browser session will remain open for your interactions."
        except Exception as e:
            return f"Error pausing agent: {str(e)}"
    
    def _resume_agent(self) -> str:
        """Resume the browser agent after user intervention."""
        if self.agent is None:
            return "Error: Browser agent not initialized"
        
        try:
            # Keep interactive session flag to continue preserving browser
            # The session is already active and preserved
            return f"▶️ Browser agent ready to resume. Session has been preserved.\n" \
                   f"🤖 Agent is ready to continue with next tasks.\n" \
                   f"💡 Browser session remains active for continued operations."
        except Exception as e:
            return f"Error resuming agent: {str(e)}"
    
    def _show_browser(self) -> str:
        """Make the browser window visible."""
        try:
            # Set flag to show browser in future initializations
            self._is_browser_visible = True
            
            # If browser is already running, we need to restart it with visible mode
            if self.browser is not None:
                return f"👁️ Browser visibility flag set. Note: To see the browser window, " \
                       f"the browser session needs to be restarted. Current session remains headless.\n" \
                       f"💡 Tip: Use 'pause' action to make browser visible and allow manual intervention."
            else:
                return f"👁️ Browser will be visible when next initialized."
        except Exception as e:
            return f"Error setting browser visibility: {str(e)}"
    
    def _enter_manual_mode(self, instructions: str = "", duration: str = "") -> str:
        """Enter manual mode with instructions for the user."""
        if self.agent is None:
            return "Error: Browser agent not initialized"
        
        try:
            # Pause the agent first
            self.agent.pause()
            
            # Make browser visible
            if not self._is_browser_visible:
                self._show_browser()
            
            instructions_text = f"\n📋 Instructions: {instructions}" if instructions else ""
            duration_text = f"\n⏱️ Expected duration: {duration}" if duration else ""
            
            return f"🛠️ Manual mode activated. Browser agent is paused.{instructions_text}{duration_text}\n" \
                   f"👤 You now have full control of the browser window.\n" \
                   f"🔧 Complete your manual tasks (login, CAPTCHA, etc.)\n" \
                   f"▶️ Use 'resume' action when ready to return control to the agent."
        except Exception as e:
            return f"Error entering manual mode: {str(e)}"
    
    def _get_agent_status(self) -> str:
        """Get the current status of the browser agent."""
        if self.agent is None:
            return "❌ Browser agent not initialized"
        
        try:
            status_info = []
            
            # Check agent state
            if hasattr(self.agent, 'state'):
                if self.agent.state.paused:
                    status_info.append("⏸️ Agent: PAUSED")
                elif self.agent.state.stopped:
                    status_info.append("⏹️ Agent: STOPPED") 
                else:
                    status_info.append("▶️ Agent: RUNNING")
                
                if hasattr(self.agent.state, 'n_steps'):
                    status_info.append(f"📊 Steps completed: {self.agent.state.n_steps}")
            
            # Check browser visibility
            visibility = "VISIBLE" if self._is_browser_visible else "HEADLESS"
            status_info.append(f"👁️ Browser: {visibility}")
            
            # Check current task
            if hasattr(self.agent, 'task') and self.agent.task:
                status_info.append(f"🎯 Current task: {self.agent.task}")
            
            return "📊 Browser Agent Status:\n" + "\n".join(status_info)
        except Exception as e:
            return f"Error getting agent status: {str(e)}"
    
    def _restart_browser_visible(self) -> str:
        """Restart the browser in visible mode for user intervention."""
        try:
            # Close existing browser if it exists
            if self.browser is not None:
                # Note: browser_use handles cleanup automatically
                self.browser = None
                self.agent = None
            
            # Set visibility flag
            self._is_browser_visible = True
            
            # Reinitialize browser and agent
            initialized, message = self._ensure_browser_initialized()
            if not initialized:
                return f"Error restarting browser: {message}"
            
            return f"🔄 Browser restarted in visible mode.\n" \
                   f"👁️ Browser window is now visible for user interaction.\n" \
                   f"🤖 Agent is ready to continue automation when needed."
        except Exception as e:
            return f"Error restarting browser: {str(e)}"
    
    def _end_interactive_session(self) -> str:
        """End the interactive session and reset to normal mode."""
        try:
            # Reset interactive session flag
            self._is_interactive_session = False
            self._last_action = ""
            
            # Close existing browser to start fresh next time
            if self.browser is not None:
                try:
                    # browser_use handles cleanup automatically
                    pass
                except:
                    pass  # Ignore cleanup errors
                self.browser = None
                self.agent = None
            
            return f"🏁 Interactive session ended successfully.\n" \
                   f"🆕 Next browser actions will start with a fresh session.\n" \
                   f"💡 Use 'navigate' to start a new browsing session."
        except Exception as e:
            return f"Error ending interactive session: {str(e)}"
    
