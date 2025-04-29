from langchain.agents import initialize_agent, AgentType
from langchain_openai import AzureChatOpenAI
from langchain.memory import ConversationBufferMemory
from .tools import get_tools, TerminalToolError, TerminalConfirmationRequired
from .callbacks import FileLoggingCallbackHandler # Keep for logging
import os
import re
from typing import Tuple, Optional, Dict, List, Any
from dotenv import load_dotenv

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

AGENT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the provided tools to answer questions and fulfill requests. "
    "Check your conversation history before deciding on an action. "
    "If you need to run a terminal command and are asked to confirm first (safe_mode=True), use the 'terminal' tool with the command. The system will handle the confirmation request. "
    "If you are allowed to run commands directly (safe_mode=False), use the 'terminal' tool, and it will execute immediately."
)

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from operator import add

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add]
    pending_command: Optional[Dict[str, str]] = None
    safe_mode: bool
    session_id: str
    log_func: Optional[callable] = None

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", AGENT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

tools = get_tools(safe_mode=True) # Start with safe mode tools

agent = create_tool_calling_agent(llm, tools, prompt)

def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if not getattr(last_message, "tool_calls", None):
        return END
    if state.get("pending_command"):
        return "human_confirm"
    return "execute_tools"

def call_agent_node(state: AgentState, config: dict) -> Dict[str, Any]:
    print(f"--- DEBUG: Config received in call_agent_node: {config} ---") 

    configurable_config = config.get("configurable", {})
    log_func = configurable_config.get("log_func")
    session_id = configurable_config.get("session_id")

    if not session_id:
        print("--- ERROR: session_id not found in config['configurable'] ---")
        session_id = "unknown_session" 

    messages = state["messages"]
    safe_mode = state.get("safe_mode", False) 

    if log_func:
        log_func(session_id, "call_agent_node_start", {"safe_mode_in_state": safe_mode})
    else:
        print(f"--- ERROR: log_func is None in call_agent_node for session {session_id} --- ({config=})")

    current_tools = get_tools(safe_mode=safe_mode)
    log_func(session_id, "call_agent_node_tools_fetched", {"tool_count": len(current_tools)})

    agent = create_tool_calling_agent(llm, current_tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=current_tools, verbose=True)

    agent_input = {"input": state['messages'][-1].content if state['messages'] else "",
                   "chat_history": state['messages'][:-1]}
    agent_input["agent_scratchpad"] = []
    
    log_func(session_id, "call_agent_node_before_invoke", {"agent_input_keys": list(agent_input.keys()), "history_len": len(agent_input['chat_history'])})

    agent_outcome_message = None
    try:
        for chunk in agent_executor.stream(agent_input):
            if "messages" in chunk:
                agent_outcome_message = chunk["messages"][-1]

    except TerminalConfirmationRequired as e:
         log_func(session_id, "agent_confirmation_required", {"command": e.command})
         return {"pending_command": {"command": e.command}}

    except Exception as e:
         import traceback 
         log_func(session_id, "agent_error", {"error": str(e), "traceback": traceback.format_exc()})
         error_message = HumanMessage(content=f"Agent execution error: {e}")
         return {"messages": [error_message]}

    if not agent_outcome_message:
        agent_outcome_message = AIMessage(content="Agent did not produce a valid response.")

    log_func(session_id, "agent_call_end", {"outcome_message": agent_outcome_message.to_json()})

    return {"messages": [agent_outcome_message]}

def execute_tools_node(state: AgentState) -> Dict[str, Any]:
    session_id = state["session_id"]
    log_func = state.get("log_func")
    if log_func:
        log_func(session_id, "tool_execution_start", {"last_message": state['messages'][-1].to_json()})

    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        log_func(session_id, "tool_execution_skip", {"reason": "Last message is not an AIMessage with tool calls"})
        return {}

    tool_messages = []
    pending_command_info = None

    current_tools = get_tools(safe_mode=state['safe_mode'])
    tool_map = {tool.name: tool for tool in current_tools}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        if tool_name not in tool_map:
            error_msg = f"Error: Tool '{tool_name}' not found."
            tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
            log_func(session_id, "tool_not_found", {"tool_name": tool_name})
            continue

        selected_tool = tool_map[tool_name]
        log_func(session_id, "tool_attempt", {"tool_name": tool_name, "tool_args": tool_args, "tool_call_id": tool_id})

        try:
            if tool_name == "terminal" and isinstance(tool_args, dict):
                 tool_input = tool_args.get('command', '')
            elif tool_name == "search" and isinstance(tool_args, dict):
                 tool_input = tool_args.get('query', '')
            else:
                 tool_input = str(tool_args)

            output = selected_tool.invoke(tool_input) 
            tool_messages.append(ToolMessage(content=str(output), tool_call_id=tool_id))
            log_func(session_id, "tool_success", {"tool_name": tool_name, "output": str(output)})

        except TerminalConfirmationRequired as e:
            pending_command_info = {"tool": "terminal", "command": e.command}
            output = f"Confirmation required for command: {e.command}"
            tool_messages.append(ToolMessage(content=output, tool_call_id=tool_id))
            log_func(session_id, "tool_confirmation_required", {"command": e.command})
            break
        except TerminalToolError as e:
            error_msg = f"Error executing terminal command: {e}"
            tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
            log_func(session_id, "tool_terminal_error", {"error": str(e)})
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {e}"
            tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
            log_func(session_id, "tool_error", {"tool_name": tool_name, "error": str(e)})

    result = {"messages": tool_messages}
    if pending_command_info:
        result["pending_command"] = pending_command_info

    return result


workflow = StateGraph(AgentState)

workflow.add_node("agent", call_agent_node)
workflow.add_node("execute_tools", execute_tools_node)
workflow.add_node("human_confirm", lambda state: state) 

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "execute_tools": "execute_tools",
        "human_confirm": "human_confirm", 
        END: END,
    },
)

workflow.add_edge("execute_tools", "agent")

memory = MemorySaver()
app = workflow.compile(checkpointer=memory, interrupt_before=["human_confirm"])

def run_graph_turn(
    user_input: str,
    chat_history_messages: List[Dict[str, str]],
    safe_mode: bool,
    session_id: str,
    log_func: Optional[callable] = None,
    confirmed_command: Optional[str] = None 
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    config = {
        "configurable": {"thread_id": session_id, "log_func": log_func},
    }
    current_state = app.get_state(config)

    input_messages = []
    if confirmed_command:
        # Resuming after confirmation: Add a ToolMessage with the command output
        pending_state = app.get_state(config)
        tool_call_id = None
        last_ai_message = None
        error_message = None
        if pending_state and pending_state.values.get('pending_command'):
            # Search for the last AIMessage with a tool call
            for m in reversed(pending_state.values['messages']):
                if isinstance(m, AIMessage) and getattr(m, 'tool_calls', None):
                    last_ai_message = m
                    break
            if last_ai_message and last_ai_message.tool_calls:
                tool_call_id = last_ai_message.tool_calls[0].get('id')
                try:
                    real_terminal_tool = get_tools(safe_mode=False)[0]  # Assuming terminal is first
                    output = real_terminal_tool.invoke(confirmed_command)
                    tool_msg = ToolMessage(content=str(output), tool_call_id=tool_call_id)
                    input_messages.append(tool_msg)
                    log_func(session_id, "resuming_with_confirmed_command", {"command": confirmed_command, "output": str(output)})
                    error_message = None
                except Exception as e:
                    error_output = f"Error running confirmed command: {e}"
                    tool_msg = ToolMessage(content=error_output, tool_call_id=tool_call_id)
                    input_messages.append(tool_msg)
                    log_func(session_id, "resuming_command_error", {"command": confirmed_command, "error": str(e)})
                    error_message = None
            else:
                # Improved error logging for debugging
                debug_message = f"Could not find prior tool call ID for confirmation.\n"
                debug_message += f"Message history: {[str(m) for m in pending_state.values['messages']]}"
                log_func(session_id, "resuming_state_error", {"message": debug_message})
                error_message = "Error: Could not process confirmation properly. Please try again or start a new session."
        else:
            log_func(session_id, "resuming_state_error", {"message": "No pending command found in state when resuming."})
            error_message = "Error: No pending command to confirm. Please try again or start a new session."
        # Only append error message if NO ToolMessage or assistant message was added
        has_tool_or_assistant = any(
            isinstance(m, ToolMessage) or (hasattr(m, 'role') and getattr(m, 'role', None) == 'assistant')
            for m in input_messages
        )
        if not has_tool_or_assistant and error_message:
            input_messages.append(HumanMessage(content=error_message))
        graph_input = {"messages": input_messages, "pending_command": None}
    else:
        input_messages.append(HumanMessage(content=user_input))
        graph_input = {"messages": input_messages}

    graph_input["safe_mode"] = safe_mode
    graph_input["session_id"] = session_id

    final_state = None
    try:
        final_state = app.invoke(graph_input, config=config)

    except TerminalConfirmationRequired as e:
        log_func(session_id, "terminal_confirmation_required", {"command": e.command})
        initial_messages = current_state.values.get("messages", []) if current_state else []
        output_messages = []
        for msg in initial_messages:
            if isinstance(msg, AIMessage):
                content_to_show = msg.content
                output_messages.append({"role": "assistant", "content": content_to_show})
            elif isinstance(msg, HumanMessage):
                output_messages.append({"role": "user", "content": msg.content})
        pending_command_info = {"command": e.command}
        return output_messages, pending_command_info 

    except Exception as e:
         import traceback
         log_func(session_id, "graph_execution_error", {"error": str(e), "traceback": traceback.format_exc()})
         error_msg = {"role": "assistant", "content": f"An error occurred during processing: {e}"}
         return ([error_msg], None)

    initial_messages = current_state.values.get("messages", []) if current_state else []
    final_messages = final_state.get("messages", [])
    new_messages = final_messages[len(initial_messages):]

    output_messages = []
    for msg in new_messages:
        if isinstance(msg, AIMessage):
            content_to_show = msg.content
            output_messages.append({"role": "assistant", "content": content_to_show})
            if msg.tool_calls and log_func:
                log_func(session_id, "agent_tool_calls", {"tool_calls": msg.tool_calls})
        elif isinstance(msg, HumanMessage):
            output_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, ToolMessage):
            if log_func:
                 log_func(session_id, "tool_result_processed", {"tool_call_id": msg.tool_call_id, "content": msg.content})
            pass
        else:
             output_messages.append({"role": "system", "content": str(msg)})

    pending_command = final_state.get("pending_command")

    if pending_command and log_func:
        log_func(session_id, "graph_turn_end_pending", {"pending_command": pending_command})
    elif log_func:
        log_func(session_id, "graph_turn_end_final", {"output_messages": output_messages})

    return output_messages, pending_command

if __name__ == '__main__':
    print("Agent module loaded. Run main.py to interact.")
    pass
