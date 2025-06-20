"""
Unified configuration management for the agentic assistant.
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    provider: str = "azure_openai"
    azure_openai_endpoint: Optional[str] = None
    azure_openai_key: Optional[str] = None
    azure_openai_deployment: Optional[str] = None
    azure_openai_api_version: str = "2023-03-15-preview"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


@dataclass 
class AppConfig:
    """Main application configuration."""
    debug: bool = False
    safe_mode: bool = True
    log_level: str = "info"
    browser_headless: bool = False


class ConfigManager:
    """Centralized configuration management."""
    
    def __init__(self):
        load_dotenv()
        self._llm_config = None
        self._app_config = None
    
    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration."""
        if self._llm_config is None:
            self._llm_config = LLMConfig(
                azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                azure_openai_key=os.getenv("AZURE_OPENAI_KEY"),
                azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview"),
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        return self._llm_config
    
    def get_app_config(self) -> AppConfig:
        """Get application configuration."""
        if self._app_config is None:
            self._app_config = AppConfig(
                debug=os.getenv("DEBUG", "false").lower() == "true",
                safe_mode=os.getenv("SAFE_MODE", "true").lower() == "true",
                log_level=os.getenv("LOG_LEVEL", "info").lower(),
                browser_headless=os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
            )
        return self._app_config
    
    def get_env_var(self, key: str, default: str = "") -> str:
        """Get environment variable with default."""
        return os.getenv(key, default)


# Global configuration instance
config = ConfigManager()