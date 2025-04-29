from langchain.agents import initialize_agent, AgentType
from langchain_openai import AzureChatOpenAI
from langchain.memory import ConversationBufferMemory
from .tools import get_tools, TerminalToolError, TerminalConfirmationRequired
from .callbacks import FileLoggingCallbackHandler # Keep for logging
import os
import re
import io
import sys
import traceback # Added for better error logging
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

import os
import operator
from typing import TypedDict, Annotated, Sequence, Optional, List, Dict, Tuple, Any
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain.agents import AgentExecutor, create_tool_calling_agent # Changed from react
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver # In-memory checkpointer for simplicity

from .tools import get_tools, TerminalToolError, TerminalConfirmationRequired
from .callbacks import FileLoggingCallbackHandler # Keep for logging

# --- Environment Setup ---
load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")

# --- LLM Setup ---
llm = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    openai_api_key=AZURE_OPENAI_KEY,
    openai_api_version=AZURE_OPENAI_API_VERSION,
    deployment_name=AZURE_OPENAI_DEPLOYMENT,
)

# --- Graph State Definition ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # Store pending command info if confirmation is needed
    pending_command: Optional[Dict[str, str]] = None
    # Track safe mode for the current run
    safe_mode: bool
    # Session ID for logging/callbacks
    session_id: str
    # Optional logger function
    log_func: Optional[callable] = None

# --- Agent and Tools Setup ---

# Define the prompt
# Using Tool Calling agent type now
AGENT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the provided tools to answer questions and fulfill requests. "
    "Check your conversation history before deciding on an action. "
    "If you need to run a terminal command and are asked to confirm first (safe_mode=True), use the 'terminal' tool with the command. The system will handle the confirmation request. "
    "If you are allowed to run commands directly (safe_mode=False), use the 'terminal' tool, and it will execute immediately."
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", AGENT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"), # <<< ADDED MISSING PLACEHOLDER
    ]
)

# Get tools (now passing safe_mode dynamically)
tools = get_tools(safe_mode=True) # Start with safe mode tools

# Create the Tool Calling Agent
# Note: We need a way to update the tools based on safe_mode for each run
agent = create_tool_calling_agent(llm, tools, prompt)

# --- Graph Nodes ---

def should_continue(state: AgentState) -> str:
    """Determines whether to continue execution or end."""
    last_message = state["messages"][-1]
    # If there are no tool calls, then we finish
    if not getattr(last_message, "tool_calls", None):
        return END
    # Otherwise if there is a pending command, we need confirmation
    if state.get("pending_command"):
         # Interrupt the graph before executing tools if confirmation needed
        return "human_confirm"
    # Otherwise ask the agent to execute tools
    return "execute_tools"

def call_agent_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Calls the agent model to determine the next action."""
    print(f"--- DEBUG: Config received in call_agent_node: {config} ---") # Keep for debugging

    # Retrieve log_func and session_id from the 'configurable' part of the config
    configurable_config = config.get("configurable", {})
    log_func = configurable_config.get("log_func")
    session_id = configurable_config.get("session_id")

    if not session_id:
        print("--- ERROR: session_id not found in config['configurable'] ---")
        # Handle error appropriately, maybe raise or return an error state
        session_id = "unknown_session" # Fallback?

    # Extract state variables
    messages = state["messages"]
    safe_mode = state.get("safe_mode", False) # Default to False if not present

    if log_func:
        log_func(session_id, "call_agent_node_start", {"safe_mode_in_state": safe_mode})
    else:
        # Add an error print just in case it's still None
        print(f"--- ERROR: log_func is None in call_agent_node for session {session_id} --- ({config=})")

    # Get appropriate tools based on safe_mode
    current_tools = get_tools(safe_mode=safe_mode)
    log_func(session_id, "call_agent_node_tools_fetched", {"tool_count": len(current_tools)})

    # --- Create the agent dynamically within the node ---
    # This ensures the agent uses the correct tools (safe/unsafe terminal) for this turn
    agent = create_tool_calling_agent(llm, current_tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=current_tools, verbose=True)
    # -----------------------------------------------------

    # Prepare input, including potential confirmation override
    agent_input = {"input": state['messages'][-1].content if state['messages'] else "",
                   "chat_history": state['messages'][:-1]}
    # Optionally add agent_scratchpad if needed by the prompt
    agent_input["agent_scratchpad"] = []
    
    log_func(session_id, "call_agent_node_before_invoke", {"agent_input_keys": list(agent_input.keys()), "history_len": len(agent_input['chat_history'])})

    # Invoke the agent with the correct input keys
    agent_outcome_message = None
    try:
        for chunk in agent_executor.stream(agent_input):
            # Keep the last message containing the full response or tool calls
            if "messages" in chunk:
                agent_outcome_message = chunk["messages"][-1]

    except TerminalConfirmationRequired as e:
         if log_func:
             log_func(session_id, "agent_confirmation_required", {"command": e.command})
         # Update state to indicate pending confirmation
         return {"pending_command": {"command": e.command}}

    except Exception as e:
         if log_func:
             import traceback # Moved import here
             log_func(session_id, "agent_error", {"error": str(e), "traceback": traceback.format_exc()})
         # Add error message to state for general errors
         error_message = HumanMessage(content=f"Agent execution error: {e}")
         return {"messages": [error_message]}

    if not agent_outcome_message:
        # Handle cases where streaming might not yield the expected final message
        agent_outcome_message = AIMessage(content="Agent did not produce a valid response.")

    if log_func:
        log_func(session_id, "agent_call_end", {"outcome_message": agent_outcome_message.to_json()})

    # We only want to add the AIMessage to the list of messages
    return {"messages": [agent_outcome_message]}

def execute_tools_node(state: AgentState) -> Dict[str, Any]:
    """Executes the tools called by the agent."""
    session_id = state["session_id"]
    log_func = state.get("log_func")
    if log_func:
        log_func(session_id, "tool_execution_start", {"last_message": state['messages'][-1].to_json()})

    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        if log_func:
            log_func(session_id, "tool_execution_skip", {"reason": "Last message is not an AIMessage with tool calls"})
        return {}

    tool_messages = []
    pending_command_info = None

    # Dynamically get tools based on current safe_mode
    current_tools = get_tools(safe_mode=state['safe_mode'])
    # Create a mapping of tool names to functions for easy lookup
    tool_map = {tool.name: tool for tool in current_tools}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        if tool_name not in tool_map:
            error_msg = f"Error: Tool '{tool_name}' not found."
            tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
            if log_func:
                log_func(session_id, "tool_not_found", {"tool_name": tool_name})
            continue

        selected_tool = tool_map[tool_name]
        if log_func:
            log_func(session_id, "tool_attempt", {"tool_name": tool_name, "tool_args": tool_args, "tool_call_id": tool_id})

        try:
            # Execute the tool
            # Need to pass args correctly, often they are a dict
            # Langchain tools expect string input usually, but ToolCallingAgent passes dict
            # Adapt based on tool definition
            if tool_name == "terminal" and isinstance(tool_args, dict):
                 # Assuming terminal tool expects 'command' in args
                 tool_input = tool_args.get('command', '')
            elif tool_name == "search" and isinstance(tool_args, dict):
                 # Assuming search tool expects 'query' in args
                 tool_input = tool_args.get('query', '')
            else:
                 # Default or handle other tools
                 tool_input = str(tool_args)

            output = selected_tool.invoke(tool_input) # Pass adapted input
            tool_messages.append(ToolMessage(content=str(output), tool_call_id=tool_id))
            if log_func:
                log_func(session_id, "tool_success", {"tool_name": tool_name, "output": str(output)})

        except TerminalConfirmationRequired as e:
            # Specific exception from the safe terminal tool
            pending_command_info = {"tool": "terminal", "command": e.command}
            # Add a message indicating confirmation is needed, but the graph state handles the interrupt
            output = f"Confirmation required for command: {e.command}"
            tool_messages.append(ToolMessage(content=output, tool_call_id=tool_id))
            if log_func:
                log_func(session_id, "tool_confirmation_required", {"command": e.command})
            # Don't process further tools if confirmation is needed for one
            break
        except TerminalToolError as e:
            # Handle errors from direct terminal execution (non-safe mode)
            error_msg = f"Error executing terminal command: {e}"
            tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
            if log_func:
                log_func(session_id, "tool_terminal_error", {"error": str(e)})
        except Exception as e:
            # General tool execution error
            error_msg = f"Error executing tool {tool_name}: {e}"
            tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
            if log_func:
                log_func(session_id, "tool_error", {"tool_name": tool_name, "error": str(e)})

    result = {"messages": tool_messages}
    if pending_command_info:
        result["pending_command"] = pending_command_info

    return result


# --- Graph Definition ---
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("agent", call_agent_node)
workflow.add_node("execute_tools", execute_tools_node)
workflow.add_node("human_confirm", lambda state: state) # Placeholder node for interrupt

# Define edges
workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "execute_tools": "execute_tools",
        "human_confirm": "human_confirm", # Route to confirmation node if needed
        END: END,
    },
)

# After executing tools, always go back to the agent to process the results
workflow.add_edge("execute_tools", "agent")

# The 'human_confirm' node acts as an interrupt point. The graph stops here.
# The calling code needs to handle resuming the graph after confirmation.

# Compile the graph with memory
# Using MemorySaver for simplicity; replace with persistent storage if needed
memory = MemorySaver()
app = workflow.compile(checkpointer=memory, interrupt_before=["human_confirm"])

# --- Main Execution Function (Replaces execute_agent_turn) ---
def run_graph_turn(
    user_input: str,
    chat_history_messages: List[Dict[str, str]],
    safe_mode: bool,
    session_id: str,
    log_func: Optional[callable] = None,
    confirmed_command: Optional[str] = None # For resuming after confirmation
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Runs a turn of the agent graph, handling new input or resuming after confirmation.

    Args:
        user_input: The user's message (if it's a new turn).
        chat_history_messages: The conversation history.
        safe_mode: Whether terminal confirmation is needed.
        session_id: Unique ID for the session/graph run.
        log_func: Optional logging function.
        confirmed_command: The command confirmed by the user (if resuming).

    Returns:
        A tuple containing:
        - List of new message dictionaries added in this turn.
        - Pending command info dictionary if confirmation is now required, otherwise None.
    """
    # Pass log_func through the config dictionary so nodes can access it
    config = {
        "configurable": {"thread_id": session_id, "log_func": log_func},
    }
    current_state = app.get_state(config)

    input_messages = []
    if confirmed_command:
        # Resuming after confirmation: Add a ToolMessage with the command output
        # We assume the 'tools.py' handles actual execution on confirmation
        # Here, we just add the confirmation result back into the flow.
        # Note: Need to find the correct tool_call_id from the pending state.
        pending_state = app.get_state(config)
        if pending_state and pending_state.values.get('pending_command'):
            last_ai_message = next((m for m in reversed(pending_state.values['messages']) if isinstance(m, AIMessage) and m.tool_calls), None)
            if last_ai_message and last_ai_message.tool_calls:
                 tool_call_id = last_ai_message.tool_calls[0].get('id') # Assuming first tool call was terminal
                 # Use the actual execution function from tools (non-safe version)
                 try:
                     real_terminal_tool = get_tools(safe_mode=False)[0] # Assuming terminal is first
                     output = real_terminal_tool.invoke(confirmed_command)
                     tool_msg = ToolMessage(content=str(output), tool_call_id=tool_call_id)
                     input_messages.append(tool_msg)
                     if log_func:
                         log_func(session_id, "resuming_with_confirmed_command", {"command": confirmed_command, "output": str(output)})
                 except Exception as e:
                     error_output = f"Error running confirmed command: {e}"
                     tool_msg = ToolMessage(content=error_output, tool_call_id=tool_call_id)
                     input_messages.append(tool_msg)
                     if log_func:
                          log_func(session_id, "resuming_command_error", {"command": confirmed_command, "error": str(e)})
            else:
                 # Log error if state is inconsistent
                 if log_func:
                      log_func(session_id, "resuming_state_error", {"message": "Could not find prior tool call ID for confirmation."})
                 input_messages.append(HumanMessage(content="Error: Could not process confirmation properly."))
        else:
             if log_func:
                 log_func(session_id, "resuming_state_error", {"message": "No pending command found in state when resuming."})
             input_messages.append(HumanMessage(content="Error: No pending command to confirm."))

        # Clear pending command after processing
        graph_input = {"messages": input_messages, "pending_command": None}
    else:
        # New user input
        input_messages.append(HumanMessage(content=user_input))
        graph_input = {"messages": input_messages}

    # Update dynamic state elements
    graph_input["safe_mode"] = safe_mode
    graph_input["session_id"] = session_id

    # Stream the graph execution
    final_state = None
    try:
        # Use stream for better intermediate state visibility if needed
        # for event in app.stream(graph_input, config=config, stream_mode="values"):
        #     final_state = event
        # Using invoke for simplicity now, assuming final state is sufficient
        final_state = app.invoke(graph_input, config=config)

    except TerminalConfirmationRequired as e:
        if log_func:
            log_func(session_id, "terminal_confirmation_required", {"command": e.command})
        # Return current messages (as no new ones were added) and the pending command
        initial_messages = current_state.values.get("messages", []) if current_state else []
        # Format existing messages for return consistency
        output_messages = []
        for msg in initial_messages:
            if isinstance(msg, AIMessage):
                content_to_show = msg.content
                output_messages.append({"role": "assistant", "content": content_to_show})
            elif isinstance(msg, HumanMessage):
                output_messages.append({"role": "user", "content": msg.content})
            # We don't typically return ToolMessages or SystemMessages here
        pending_command_info = {"command": e.command}
        return output_messages, pending_command_info # Return existing messages and pending command

    except Exception as e:
        if log_func:
            import traceback
            log_func(session_id, "graph_execution_error", {"error": str(e), "traceback": traceback.format_exc()})
        # Return an error message if the graph fails
        error_msg = {"role": "assistant", "content": f"An error occurred during processing: {e}"}
        return ([error_msg], None)

    # Extract new messages added in this turn/invocation
    # Compare final messages with the initial messages from get_state
    initial_messages = current_state.values.get("messages", []) if current_state else []
    final_messages = final_state.get("messages", [])
    new_messages = final_messages[len(initial_messages):]

    # Format messages for output
    output_messages = []
    for msg in new_messages:
        if isinstance(msg, AIMessage):
            # Exclude tool calls from the assistant message content shown to user
            content_to_show = msg.content
            output_messages.append({"role": "assistant", "content": content_to_show})
            # Log tool calls separately if needed
            if msg.tool_calls and log_func:
                log_func(session_id, "agent_tool_calls", {"tool_calls": msg.tool_calls})
        elif isinstance(msg, HumanMessage):
            output_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, ToolMessage):
            # Optionally include tool messages if needed for frontend debugging?
            # Typically hidden unless explicitly requested or an error occurred.
            if log_func:
                 log_func(session_id, "tool_result_processed", {"tool_call_id": msg.tool_call_id, "content": msg.content})
            # Don't usually return raw tool messages to the frontend
            pass
        else:
             output_messages.append({"role": "system", "content": str(msg)})

    # Check if the graph ended with a pending command
    pending_command = final_state.get("pending_command")

    if pending_command and log_func:
        log_func(session_id, "graph_turn_end_pending", {"pending_command": pending_command})
    elif log_func:
        log_func(session_id, "graph_turn_end_final", {"output_messages": output_messages})

    return output_messages, pending_command

# --- Placeholder for potential main execution or testing ---
if __name__ == '__main__':
    # Example usage (requires running services or mocks)
    print("Agent module loaded. Run main.py to interact.")
    # Add basic test calls here if needed, mocking tools/LLM
    pass
