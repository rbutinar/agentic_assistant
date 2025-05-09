from langchain.tools import BaseTool
from typing import Optional, Any
import asyncio
import os
from playwright.async_api import async_playwright
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class BrowserUseTool(BaseTool):
    name: str = "browser_use_agent"
    description: str = "Use a browser automation agent to perform goal-oriented tasks online. Pass a clear task description."

    def _run(self, task: str, **kwargs: Any) -> dict:
        # Generic browser automation using Playwright
        async def run_agent():
            url = task if isinstance(task, str) and task.startswith("http") else "https://example.com"
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                await page.goto(url)
                # Detect login form (very basic heuristic)
                if await page.query_selector('input[type="password"]'):
                    # Placeholder: Here you would pause and hand over to the user
                    await browser.close()
                    return {
                        "action": "await_user_credentials",
                        "message": "Manual credential entry required. Please use the automation browser window to log in, then click Continue.",
                        "url": url
                    }
                # Placeholder for further automation logic
                await browser.close()
                return {"action": "automation_complete", "message": f"Successfully visited {url} and no login form detected."}
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
