from langchain.tools import BaseTool
from typing import Optional, Any
import asyncio
import os
import sys

# Add browser_use to sys.path if needed
BROWSER_USE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../browser_use'))
if BROWSER_USE_PATH not in sys.path:
    sys.path.insert(0, BROWSER_USE_PATH)

from browser_use import Agent as BrowserAgent
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(BROWSER_USE_PATH, '.env'))

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
