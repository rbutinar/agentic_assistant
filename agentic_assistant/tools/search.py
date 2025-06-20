"""
Search tool for web searches using DuckDuckGo.
"""
from typing import Any, List, Dict
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


class SearchInput(BaseModel):
    """Input for search tool."""
    query: str = Field(description="Search query")


class SearchTool(BaseTool):
    """Tool for performing web searches."""
    
    name: str = "search"
    description: str = "Search the web for information on any topic."
    args_schema: type[BaseModel] = SearchInput
    
    def _run(self, query: str) -> str:
        """Perform the search using DuckDuckGo."""
        if DDGS is None:
            return "Error: duckduckgo-search package not installed. Please install it with: pip install duckduckgo-search"
        
        try:
            # Perform the search using DuckDuckGo
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            
            if not results:
                return f"No search results found for: {query}"
            
            # Format results
            formatted_results = [f"Search results for: {query}\n"]
            for i, result in enumerate(results, 1):
                title = result.get('title', 'No title')
                body = result.get('body', 'No description')
                href = result.get('href', 'No URL')
                
                formatted_results.append(f"{i}. **{title}**")
                formatted_results.append(f"   {body}")
                formatted_results.append(f"   URL: {href}\n")
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            return f"Error performing search: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Async version - not implemented."""
        return self._run(query)