from langchain.agents import initialize_agent, AgentType
from langchain_community.chat_models import AzureChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from .tools import run_terminal_command, search_tool
from .callbacks import FileLoggingCallbackHandler
import os
import re
import io
import sys
from typing import Tuple, Optional, Dict, List, Any
from dotenv import load_dotenv

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")

# Custom system prompt for general-purpose memory
SYSTEM_PROMPT = (
    "You are an agentic assistant equipped with several tools to help the user. Your primary goal is to be helpful and follow instructions.\n"
    "1. **Consult History:** First, check the conversation history (including previous tool outputs) for relevant information.\n"
    "2. **Use Tools:** If the history doesn't contain the answer, or if the user explicitly asks you to perform an action (like running a command or searching), use the appropriate tool. You have the following tools:\n"
    "   - `terminal`: Executes commands on the user's system after getting confirmation. Use this tool when asked to run specific commands (e.g., `whoami`, `ls`, `pwd`) or to find system information requested by the user. Do not refuse to use this tool if the user asks for it; simply propose the command using the tool.\n"
    "   - `search`: Searches the web.\n"
    "3. **Reason & Respond:** Base your final answer on the information gathered from history and tools.\n"
    "4. **Explain Limitations:** If you truly cannot fulfill a request even with tools, explain the limitation clearly.\n"
    "Always prioritize direct user instructions regarding tool usage."
)

# Setup LangChain LLM
llm = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    openai_api_key=AZURE_OPENAI_KEY,
    openai_api_version=AZURE_OPENAI_API_VERSION,
    deployment_name=AZURE_OPENAI_DEPLOYMENT,
)

def execute_agent_turn(
    user_input: str,
    chat_history_messages: List[Dict[str, str]], 
    safe_mode: bool,
    session_id: str,
    log_func: Optional[callable] = None
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Executes a single turn of the agent interaction, handling safe mode for the terminal tool.

    Args:
        user_input: The latest message from the user.
        chat_history_messages: The history of the conversation.
        safe_mode: Boolean indicating if safe mode is enabled for this turn.
        session_id: The ID of the current session.
        log_func: Optional logging function.

    Returns:
        A tuple containing:
        - The agent's text response (str) or None if confirmation is needed.
        - A dictionary with pending command info (if confirmation needed) or None.
          Format: {"tool": "terminal", "command": "the_command"}
    """
    if log_func:
        log_func(session_id, "agent_turn_start", {"input": user_input, "safe_mode": safe_mode})

    # --- Create Tool List Dynamically Based on Safe Mode ---
    if safe_mode:
        # In safe mode, terminal tool returns a confirmation string instead of executing
        safe_terminal_func = lambda command: f"__CONFIRM_TERMINAL__:{command}"
        current_terminal_tool = Tool(
            name="terminal",
            func=safe_terminal_func,
            description="Proposes a terminal command for execution (requires confirmation). Use this to suggest commands like ls, pwd, etc." 
        )
    else:
        # In normal mode, terminal tool executes the command directly
        current_terminal_tool = Tool(
            name="terminal",
            func=run_terminal_command, 
            description="Executes a terminal command directly and returns the output." 
        )

    # Include other tools (assuming search_tool is defined in tools.py)
    current_tools = [current_terminal_tool, search_tool]

    # --- Setup Memory for this turn ---
    # Note: Langchain memory needs proper handling for conversational context loading.
    # This example assumes simple ConversationBufferMemory re-creation per turn,
    # which might lose context if not managed correctly by the caller loading `chat_history_messages`.
    # A better approach involves loading the history into the memory object.
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, input_key="input")
    for msg in chat_history_messages:
        if msg['role'] == 'user':
            memory.chat_memory.add_user_message(msg['content'])
        elif msg['role'] == 'assistant':
            memory.chat_memory.add_ai_message(msg['content'])

    # --- Initialize Agent Executor for this turn ---
    callback_handler = FileLoggingCallbackHandler(session_id=session_id) if log_func else None
    callbacks = [callback_handler] if callback_handler else None

    current_agent_executor = initialize_agent(
        tools=current_tools,
        llm=llm,
        agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
        verbose=True, 
        memory=memory,
        agent_kwargs={"system_message": SYSTEM_PROMPT}, 
        handle_parsing_errors=True,
    )

    # --- Invoke Agent ---
    try:
        # Redirect stdout only if needed for debugging agent internal thoughts
        # old_stdout = sys.stdout
        # sys.stdout = mystdout = io.StringIO()
        result = current_agent_executor.invoke({"input": user_input}, config={"callbacks": callbacks})
        agent_output = result.get('output', '')
        # sys.stdout = old_stdout # Restore stdout
        # captured_stdout = mystdout.getvalue() # Get captured output if needed

    except Exception as e:
        if log_func:
            log_func(session_id, "agent_error", {"error": str(e)})
        return (f"An error occurred: {e}", None)

    # --- Process Result ---
    pending_command_info = None
    final_output = agent_output

    if isinstance(agent_output, str) and agent_output.startswith("__CONFIRM_TERMINAL__:"):
        command = agent_output[len("__CONFIRM_TERMINAL__:"):].strip()
        pending_command_info = {"tool": "terminal", "command": command}
        final_output = None # No text response when asking for confirmation
        if log_func:
            log_func(session_id, "terminal_confirmation_pending", {"command": command})
    else:
        if log_func:
            log_func(session_id, "agent_turn_end", {"output": agent_output})

    return (final_output, pending_command_info)
