"""
New simplified main application using reorganized structure.
"""
import uvicorn
from agentic_assistant.api.endpoints import create_app
from agentic_assistant.core.config import config


def main():
    """Main application entry point."""
    app = create_app()
    app_config = config.get_app_config()
    
    # Configure logging
    from browser_use.utils.logging_utils import LoggingUtils
    LoggingUtils.setup_logging(log_type=app_config.log_level)
    
    # Run the application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=app_config.log_level,
        reload=app_config.debug
    )


if __name__ == "__main__":
    main()