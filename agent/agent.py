from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import AzureChatOpenAI
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
    "You are an agentic assistant. You have access to the full conversation history, including all user messages, your own replies, and all tool outputs. "
    "Whenever possible, use any relevant information from the conversation history (including previous tool outputs, lists, tables, or facts) to answer the user's questions. "
    "If you do not have enough information, you may use tools to retrieve or compute what you need. "
    "Always reason over the entire conversation history to provide the most helpful answer."
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
)

# Intercept tool use for terminal tool (updated for conversational agent)
def run_agent_with_tool_intercept(messages, session_id, log_func=None) -> Tuple[str, dict]:
    """
    Runs the agent, but intercepts if a terminal tool is about to be used.
    Returns (reply, tool_request_dict or None)
    """
    user_input = messages[-1]["content"] if messages else ""
    if log_func:
        log_func(session_id, "agent_start", {"input": user_input})
    # Capture stdout for intermediate steps
    old_stdout = sys.stdout
    sys.stdout = mystdout = io.StringIO()
    try:
        # Use invoke to get intermediate steps
        result = agent_executor.invoke({"input": user_input}, include_intermediate_steps=True)
    finally:
        sys.stdout = old_stdout
    # Check for intermediate steps (tool usage)
    steps = result.get('intermediate_steps', None)
    if steps:
        for step in steps:
            if isinstance(step[0], AgentAction) and step[0].tool == "terminal":
                command = step[0].tool_input
                if log_func:
                    log_func(session_id, "terminal_intercepted", {"command": command})
                return (None, {"tool": "terminal", "command": command})
    # Fallback: parse stdout for terminal tool usage (legacy)
    output = mystdout.getvalue()
    tool_match = re.search(r'"action"\s*:\s*"terminal".*?"action_input"\s*:\s*"([^"]+?)"', output, re.DOTALL)
    if tool_match:
        command = tool_match.group(1)
        if log_func:
            log_func(session_id, "terminal_intercepted", {"command": command})
        return (None, {"tool": "terminal", "command": command})
    # Otherwise, normal agent reply
    if log_func:
        log_func(session_id, "agent_end", {"output": result.get('output', result)})
    return (result.get('output', result), None)

# Standard run_agent (unchanged)
def run_agent(messages, session_id, log_func=None):
    user_input = messages[-1]["content"] if messages else ""
    if log_func:
        log_func(session_id, "agent_start", {"input": user_input})
    result = agent_executor.run(user_input)
    if log_func:
        log_func(session_id, "agent_end", {"output": result})
    return result
