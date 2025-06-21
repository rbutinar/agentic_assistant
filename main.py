"""
New simplified main application using reorganized structure.
"""
import uvicorn
from agentic_assistant.api.endpoints import create_app
from agentic_assistant.core.config import config

# Create app instance for uvicorn
app = create_app()

def main():
    """Main application entry point."""
    app_config = config.get_app_config()
    
    # Configure logging
    from browser_use.utils.logging_utils import LoggingUtils
    LoggingUtils.setup_logging(log_type=app_config.log_level)
    
    # Run the application - reload disabled to prevent infinite loop in Windows/WSL
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=app_config.log_level,
        reload=False  # Disabled due to WSL/Windows compatibility issues
    )


if __name__ == "__main__":
    main()