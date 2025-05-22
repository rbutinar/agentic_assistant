from langchain.tools import BaseTool
from typing import Optional, Any
import asyncio
import os
from langchain.tools import BaseTool
from browser_use import Agent as BrowserAgent
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv

# Load environment variables from project root or specified location
load_dotenv()

class BrowserUseTool(BaseTool):
    name: str = "browser_use_agent"
    description: str = "Use a browser automation agent to perform goal-oriented tasks online. Pass a clear task description."

    def _run(self, task: str, **kwargs: Any) -> str:
        # Run the browser_use agent synchronously (wrap async)
        async def run_agent():
            llm = AzureChatOpenAI(
                deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                openai_api_key=os.getenv("AZURE_OPENAI_KEY"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                temperature=0.0
            )
            agent = BrowserAgent(
                task=task,
                llm=llm,
            )
            result = await agent.run()
            return result
        return asyncio.run(run_agent())

    def _arun(self, task: str, **kwargs: Any) -> Any:
        # For async LangChain support
        async def run_agent():
            llm = AzureChatOpenAI(
                deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                openai_api_key=os.getenv("AZURE_OPENAI_KEY"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                temperature=0.0
            )
            agent = BrowserAgent(
                task=task,
                llm=llm,
            )
            result = await agent.run()
            return result
        return run_agent()
