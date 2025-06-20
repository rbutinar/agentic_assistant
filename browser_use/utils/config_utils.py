"""
Configuration utilities to centralize environment and config management.
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMConfig:
    """Configuration for Language Models."""
    openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_key: Optional[str] = None
    azure_openai_deployment: Optional[str] = None
    azure_openai_api_version: str = "2023-03-15-preview"
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    grok_api_key: Optional[str] = None


@dataclass
class BrowserConfig:
    """Configuration for Browser settings."""
    headless: bool = True
    window_width: Optional[int] = None
    window_height: Optional[int] = None
    keep_alive: bool = True
    ignore_https_errors: bool = False


class ConfigManager:
    """Centralized configuration management."""
    
    @staticmethod
    def get_llm_config() -> LLMConfig:
        """Get LLM configuration from environment variables."""
        return LLMConfig(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_openai_key=os.getenv("AZURE_OPENAI_KEY"),
            azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            grok_api_key=os.getenv("GROK_API_KEY"),
        )
    
    @staticmethod
    def get_browser_config() -> BrowserConfig:
        """Get browser configuration from environment variables."""
        return BrowserConfig(
            headless=os.getenv("BROWSER_HEADLESS", "true").lower() == "true",
            window_width=int(os.getenv("BROWSER_WIDTH", "0")) or None,
            window_height=int(os.getenv("BROWSER_HEIGHT", "0")) or None,
            keep_alive=os.getenv("BROWSER_KEEP_ALIVE", "true").lower() == "true",
            ignore_https_errors=os.getenv("BROWSER_IGNORE_HTTPS_ERRORS", "false").lower() == "true",
        )
    
    @staticmethod
    def validate_required_env_vars(required_vars: Dict[str, list[str]]) -> None:
        """
        Validate that required environment variables are set.
        
        Args:
            required_vars: Dictionary mapping service names to required env vars
        """
        missing_vars = []
        
        for service, vars_list in required_vars.items():
            for var in vars_list:
                if not os.getenv(var):
                    missing_vars.append(f"{service}: {var}")
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    @staticmethod
    def get_logging_config() -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            "level": os.getenv("BROWSER_USE_LOGGING_LEVEL", "info").lower(),
            "format": os.getenv("BROWSER_USE_LOG_FORMAT", "standard"),
        } 