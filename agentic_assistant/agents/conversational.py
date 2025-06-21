"""
Conversational agent using LangGraph for structured conversation management.
"""
from typing import TypedDict, Annotated, Sequence, Optional, List, Tuple
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from operator import add
import os

from agentic_assistant.core.config import config
from agentic_assistant.tools.registry import get_tools


class AgentState(TypedDict):
    """State for the conversational agent."""
    messages: Annotated[Sequence[BaseMessage], add]
    pending_tool_confirmation: Optional[dict]


class ConversationalAgent:
    """LangGraph-based conversational agent."""
    
    def __init__(self, safe_mode: bool = True):
        self.llm_config = config.get_llm_config()
        self.llm = self._create_llm()
        self.safe_mode = safe_mode
        self.tools = get_tools(llm=self.llm, safe_mode=safe_mode)
        
        # Load knowledge base guidelines
        kb_path = os.path.join(os.path.dirname(__file__), '../../knowledge_base/agent_guidelines.md')
        try:
            with open(kb_path, 'r') as f:
                self.kb_guidelines = f.read()
        except Exception:
            self.kb_guidelines = ''
        
        self.system_prompt = self._create_system_prompt()
        self.graph = self._create_graph()
    
    def _create_llm(self) -> AzureChatOpenAI:
        """Create the LLM instance."""
        return AzureChatOpenAI(
            azure_endpoint=self.llm_config.azure_openai_endpoint,
            openai_api_key=self.llm_config.azure_openai_key,
            openai_api_version=self.llm_config.azure_openai_api_version,
            deployment_name=self.llm_config.azure_openai_deployment,
            temperature=0.7,
            max_tokens=1000,
        )
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt with guidelines."""
        return (
            "You are a helpful assistant. Use the provided tools to answer questions and fulfill requests. "
            "Check your conversation history before deciding on an action. "
            "If you need to run a system command and are asked to confirm first (safe_mode=True), use the 'terminal' tool with the command. The system will handle the confirmation request. "
            "If you are allowed to run system operations directly (safe_mode=False), use the 'terminal' tool, and it will process immediately.\n\n"
            f"Knowledge Base:\n{self.kb_guidelines}"
        )
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph state graph."""
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the agent
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
        
        # Define the graph nodes
        def call_model(state: AgentState) -> AgentState:
            response = agent_executor.invoke(state)
            # Wrap the string output in an AIMessage
            ai_message = AIMessage(content=response["output"])
            return {"messages": [ai_message]}
        
        # Create the graph
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)
        
        # Add memory
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def run_turn(
        self,
        user_input: Optional[str],
        session_id: str,
        safe_mode: bool = True,
        confirmed_command: Optional[str] = None
    ) -> Tuple[List[BaseMessage], Optional[dict]]:
        """
        Run a single turn of the conversation.
        
        Args:
            user_input: The user's input message
            session_id: Session identifier
            safe_mode: Whether to require confirmation for terminal commands
            confirmed_command: Previously confirmed command to execute
            
        Returns:
            Tuple of (new_messages, pending_command_info)
        """
        # Update tools with current safe_mode setting
        if self.safe_mode != safe_mode:
            self.safe_mode = safe_mode
            self.tools = get_tools(llm=self.llm, safe_mode=safe_mode)
            # Recreate the graph with updated tools
            self.graph = self._create_graph()
        
        config_dict = {"configurable": {"thread_id": session_id}}
        
        # Handle confirmed command execution directly
        if confirmed_command:
            # Execute the confirmed command directly using the terminal tool
            from agentic_assistant.tools.terminal import TerminalTool
            terminal_tool = TerminalTool(safe_mode=False)  # Disable safe mode for confirmed commands
            
            try:
                result = terminal_tool._run(confirmed_command)
                # Clean up the result by removing leading/trailing whitespace
                cleaned_result = result.strip() if result else "No output"
                response_message = AIMessage(content=f"Command executed: `{confirmed_command}`\n\nOutput:\n```\n{cleaned_result}\n```")
                return [response_message], None
            except Exception as e:
                error_message = AIMessage(content=f"Error executing command `{confirmed_command}`: {str(e)}")
                return [error_message], None
        
        # Prepare the input for regular user input
        if user_input:
            input_messages = [HumanMessage(content=user_input)]
        else:
            return [], None
        
        # Run the graph
        result = self.graph.invoke(
            {"messages": input_messages},
            config=config_dict
        )
        
        # Extract new messages and any pending confirmations
        all_messages = result.get("messages", [])
        pending_confirmation = result.get("pending_tool_confirmation")
        
        # Filter to return only AI messages (not the user input we just sent)
        new_ai_messages = [msg for msg in all_messages if isinstance(msg, AIMessage)]
        
        return new_ai_messages, pending_confirmation