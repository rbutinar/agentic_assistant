from langchain.agents import initialize_agent, AgentType
from langchain_community.chat_models import AzureChatOpenAI
from langchain.memory import ConversationBufferMemory
from .tools import tool_list
import os
import re
import io
import sys
from typing import Tuple

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

# Setup general-purpose memory
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Use the recommended conversational agent type for memory
agent_executor = initialize_agent(
    tools=tool_list,
    llm=llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    verbose=True,
    memory=memory,
    system_message=SYSTEM_PROMPT,
    handle_parsing_errors=True
)

# Intercept tool use for terminal tool (updated for conversational agent)
def run_agent_with_tool_intercept(messages, session_id, log_func=None, disable_terminal_tool=False) -> Tuple[str, dict]:
    """
    Runs the agent, but intercepts if a terminal tool is about to be used.
    Returns (reply, tool_request_dict or None)
    If disable_terminal_tool is True, the terminal tool is not available for this turn.
    """
    user_input = messages[-1]["content"] if messages else ""
    if log_func:
        log_func(session_id, "agent_start", {"input": user_input})
    # Optionally disable terminal tool for this turn
    if disable_terminal_tool:
        tools = [t for t in tool_list if t.name != "terminal"]
        agent_executor_no_terminal = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
            verbose=True,
            memory=memory,
            system_message=SYSTEM_PROMPT,
        )
        result = agent_executor_no_terminal.invoke({"input": user_input}, include_intermediate_steps=True)
    else:
        old_stdout = sys.stdout
        sys.stdout = mystdout = io.StringIO()
        try:
            result = agent_executor.invoke({"input": user_input}, include_intermediate_steps=True)
        finally:
            sys.stdout = old_stdout
    # Check for special signal from safe terminal tool
    output_text = result.get('output', '')
    if isinstance(output_text, str) and output_text.startswith("__CONFIRM_TERMINAL__:"):
        command = output_text[len("__CONFIRM_TERMINAL__:"):].strip()
        if log_func:
            log_func(session_id, "terminal_intercepted", {"command": command})
        return (None, {"tool": "terminal", "command": command})
    # Otherwise, normal agent reply
    if log_func:
        log_func(session_id, "agent_end", {"output": output_text})
    return (output_text, None)

# Standard run_agent (unchanged)
def run_agent(messages, session_id, log_func=None):
    user_input = messages[-1]["content"] if messages else ""
    if log_func:
        log_func(session_id, "agent_start", {"input": user_input})
    result = agent_executor.run(user_input)
    if log_func:
        log_func(session_id, "agent_end", {"output": result})
    return result
