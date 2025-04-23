# app/logging/logger_config.py

import logging.config
from typing import Dict, Any
import logging

from app.config import settings
from app.logging.formatter import LevelColorFormatter, JSONFormatter

"""
Centralized logging configuration for the UnifyOps application.

This module configures the Python logging system based on environment settings:
- In local/test environments: Colorized console output
- In staging/production: JSON structured logging for DataDog

Environment variables that control behavior:
- ENVIRONMENT: The deployment environment (local, test, staging, prod)
- LOG_LEVEL: The minimum log level to record (DEBUG, INFO, WARNING, etc.)
- LOG_STYLE: Force a specific logging style (auto, console, json)
"""

# Centralized settings
ENVIRONMENT: str = settings.ENVIRONMENT.lower()
IS_LOCAL: bool = ENVIRONMENT in ("local", "test")
LOG_LEVEL: str = settings.LOG_LEVEL.upper() if hasattr(settings.LOG_LEVEL, 'upper') else settings.LOG_LEVEL
LOG_STYLE: str = settings.LOG_STYLE
SERVICE_NAME = getattr(settings, 'SERVICE_NAME', 'unifyops-api')
SERVICE_VERSION = getattr(settings, 'VERSION', '1.0.0')
LOG_RETENTION_DAYS = getattr(settings, 'LOG_RETENTION_DAYS', 30)

# Decide console vs JSON
if LOG_STYLE == "auto":
    use_console = IS_LOCAL
elif LOG_STYLE == "console":
    use_console = True
else:
    use_console = False

# Base handler (app logs)
handlers: Dict[str, Dict[str, Any]] = {
    "stdout": {
        "class":     "logging.StreamHandler",
        "formatter": "console" if use_console else "json",
        "level":     LOG_LEVEL,
        "stream":    "ext://sys.stdout",
    }
}

handlers["null"] = {
    "class": "logging.NullHandler",
}

uvicorn_loggers = {
    # both uvicorn and uvicorn.access go to NullHandler
    "uvicorn":        {"level": "WARNING", "handlers": ["null"], "propagate": False},
    "uvicorn.access": {"level": "WARNING", "handlers": ["null"], "propagate": False},
}

# Full logging configuration dictionary
LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "console": {
            "()": LevelColorFormatter,
            "format": "%(asctime)s [%(colored_levelname)s] %(message)s (%(shortpath)s:%(lineno)d)",
            "datefmt": "%H:%M:%S",
        },
        "json": {
            "()": JSONFormatter,
            "format": "%(message)s",
        },
    },

    "handlers": handlers,

    "root": {
        "handlers": ["stdout"],
        "level":    LOG_LEVEL,
    },

    "loggers": {
        **uvicorn_loggers,
    },
}

# Apply configuration
def configure_logging() -> None:
    """
    Configure the Python logging system with our settings.
    
    This function applies the LOGGING_CONFIG to Python's logging system.
    It should be called once during application startup.
    
    Raises:
        ValueError: If an invalid log level is specified
    """
    try:
        logging.config.dictConfig(LOGGING_CONFIG)
    except ValueError as e:
        # Provide a more helpful error message for log level issues
        if "Unknown level" in str(e):
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            print(f"ERROR: Invalid log level '{settings.LOG_LEVEL}'. Valid levels are: {', '.join(valid_levels)}")
        raise

# Apply configuration when this module is imported
configure_logging()
