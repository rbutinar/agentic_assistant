"""
Consolidated logging utilities to eliminate duplication.
"""
import logging
import os
import sys
from typing import Optional, Any

from dotenv import load_dotenv

load_dotenv()


class LoggingUtils:
    """Consolidated logging utilities."""
    
    @staticmethod
    def add_logging_level(level_name: str, level_num: int, method_name: Optional[str] = None) -> None:
        """
        Comprehensively adds a new logging level to the `logging` module.
        
        Args:
            level_name: Name of the new level
            level_num: Numeric value for the level
            method_name: Method name (defaults to level_name.lower())
        """
        if not method_name:
            method_name = level_name.lower()

        if hasattr(logging, level_name):
            raise AttributeError(f'{level_name} already defined in logging module')
        if hasattr(logging, method_name):
            raise AttributeError(f'{method_name} already defined in logging module')
        if hasattr(logging.getLoggerClass(), method_name):
            raise AttributeError(f'{method_name} already defined in logger class')

        def log_for_level(self, message, *args, **kwargs):
            if self.isEnabledFor(level_num):
                self._log(level_num, message, args, **kwargs)

        def log_to_root(message, *args, **kwargs):
            logging.log(level_num, message, *args, **kwargs)

        logging.addLevelName(level_num, level_name)
        setattr(logging, level_name, level_num)
        setattr(logging.getLoggerClass(), method_name, log_for_level)
        setattr(logging, method_name, log_to_root)
    
    @staticmethod
    def setup_logging(
        log_type: Optional[str] = None,
        custom_handler: Optional[logging.Handler] = None,
        custom_formatter: Optional[logging.Formatter] = None,
        log_to_file: bool = True,
        log_directory: str = "logs"
    ) -> None:
        """
        Setup logging configuration.
        
        Args:
            log_type: Log level type ('result', 'debug', 'info')
            custom_handler: Custom logging handler
            custom_formatter: Custom formatter
        """
        # Try to add RESULT level, but ignore if it already exists
        try:
            LoggingUtils.add_logging_level('RESULT', 35)
        except AttributeError:
            pass  # Level already exists, which is fine

        log_type = log_type or os.getenv('BROWSER_USE_LOGGING_LEVEL', 'info').lower()

        # Check if handlers are already set up
        if logging.getLogger().hasHandlers():
            return

        # Clear existing handlers
        root = logging.getLogger()
        root.handlers = []

        # Use custom formatter or create default
        if custom_formatter is None:
            class BrowserUseFormatter(logging.Formatter):
                def format(self, record):
                    if isinstance(record.name, str) and record.name.startswith('browser_use.'):
                        record.name = record.name.split('.')[-2]
                    return super().format(record)
            custom_formatter = BrowserUseFormatter()

        # Create handlers
        handlers = []
        
        # Console handler
        if custom_handler is None:
            console_handler = logging.StreamHandler(sys.stdout)
            handlers.append(console_handler)
        else:
            handlers.append(custom_handler)
        
        # File handler if requested
        if log_to_file:
            from datetime import datetime
            
            # Create logs directory if it doesn't exist
            os.makedirs(log_directory, exist_ok=True)
            
            # Create log filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = os.path.join(log_directory, f"agentic_assistant_{timestamp}.log")
            
            # Create file handler
            file_handler = logging.FileHandler(log_filename)
            handlers.append(file_handler)

        # Configure all handlers
        for handler in handlers:
            if log_type == 'result':
                handler.setLevel('RESULT')
                if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                    # Console gets simple format for result
                    handler.setFormatter(logging.Formatter('%(message)s'))
                else:
                    # File gets detailed format even for result
                    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            else:
                if isinstance(handler, logging.FileHandler):
                    # File gets detailed format
                    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
                else:
                    # Console gets custom format
                    handler.setFormatter(custom_formatter)
        
        # Configure root logger with all handlers
        for handler in handlers:
            root.addHandler(handler)

        # Set log level based on environment variable
        if log_type == 'result':
            root.setLevel('RESULT')
        elif log_type == 'debug':
            root.setLevel(logging.DEBUG)
        else:
            root.setLevel(logging.INFO)

        # Configure browser_use logger
        browser_use_logger = logging.getLogger('browser_use')
        browser_use_logger.propagate = False  # Don't propagate to root logger
        for handler in handlers:
            browser_use_logger.addHandler(handler)
        browser_use_logger.setLevel(root.level)
        
        # Configure agentic_assistant logger
        app_logger = logging.getLogger('agentic_assistant')
        app_logger.propagate = False
        for handler in handlers:
            app_logger.addHandler(handler)
        app_logger.setLevel(root.level)
    
    @staticmethod
    def silence_third_party_loggers() -> None:
        """Silence noisy third-party loggers."""
        third_party_loggers = [
            'WDM', 'httpx', 'selenium', 'playwright', 'urllib3', 'asyncio',
            'langchain', 'openai', 'httpcore', 'charset_normalizer',
            'anthropic._base_client', 'PIL.PngImagePlugin',
            'trafilatura.htmlprocessing', 'trafilatura',
        ]
        
        for logger_name in third_party_loggers:
            third_party = logging.getLogger(logger_name)
            third_party.setLevel(logging.ERROR)
            third_party.propagate = False 