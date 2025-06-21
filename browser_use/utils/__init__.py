"""
Browser Use utilities package.
"""

# Import from the root utils module to avoid circular imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from browser_use.utils import time_execution_sync, time_execution_async, SignalHandler, singleton, check_env_variables
except ImportError:
    # Fallback: direct import from utils.py
    import importlib.util
    utils_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'utils.py')
    spec = importlib.util.spec_from_file_location("utils", utils_path)
    utils_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_module)
    
    time_execution_sync = utils_module.time_execution_sync
    time_execution_async = utils_module.time_execution_async
    SignalHandler = utils_module.SignalHandler
    singleton = utils_module.singleton
    check_env_variables = utils_module.check_env_variables

__all__ = [
    'time_execution_sync',
    'time_execution_async', 
    'SignalHandler',
    'singleton',
    'check_env_variables'
]