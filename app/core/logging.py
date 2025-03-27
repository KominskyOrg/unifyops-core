import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union

from fastapi import Request
from pydantic import BaseModel, Field

from app.core.config import settings


class LogMessage(BaseModel):
    """Structured log message format"""

    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    level: str
    message: str
    service: str = "unifyops-api"
    environment: str = Field(default_factory=lambda: settings.ENVIRONMENT)
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None
    user_id: Optional[str] = None
    client_ip: Optional[str] = None
    duration_ms: Optional[float] = None
    status_code: Optional[int] = None
    exception: Optional[str] = None
    traceback: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class StructuredLogger:
    """
    Structured JSON logger for consistent, machine-parseable logs
    """

    def __init__(self, name: str, level: str = None):
        self.name = name
        self.logger = logging.getLogger(name)

        # Set log level from settings if not explicitly provided
        if level:
            self.logger.setLevel(getattr(logging, level.upper()))
        else:
            self.logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

        # Remove existing handlers to avoid duplicate logs
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Add JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)

    def log(self, level: str, message: str, **kwargs) -> None:
        """Base logging method"""
        log_level = getattr(logging, level.upper())

        # Create structured log message
        log_data = {"level": level, "message": message, **kwargs}

        # Pass to the logger
        self.logger.log(log_level, json.dumps(log_data))

    def info(self, message: str, **kwargs) -> None:
        """Log at INFO level"""
        self.log("INFO", message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """Log at DEBUG level"""
        self.log("DEBUG", message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log at WARNING level"""
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log at ERROR level with optional exception details"""
        if exception:
            kwargs["exception"] = str(exception)
            kwargs["traceback"] = "".join(
                traceback.format_exception(type(exception), exception, exception.__traceback__)
            )
        self.log("ERROR", message, **kwargs)

    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log at CRITICAL level with optional exception details"""
        if exception:
            kwargs["exception"] = str(exception)
            kwargs["traceback"] = "".join(
                traceback.format_exception(type(exception), exception, exception.__traceback__)
            )
        self.log("CRITICAL", message, **kwargs)

    def request_log(
        self,
        request: Request,
        status_code: int,
        duration_ms: float,
        correlation_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log API request details"""
        self.info(
            f"Request {request.method} {request.url.path}",
            path=request.url.path,
            method=request.method,
            status_code=status_code,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            client_ip=request.client.host if request.client else None,
            **kwargs,
        )


class JSONFormatter(logging.Formatter):
    """Formatter that outputs JSON strings"""

    def format(self, record):
        # Extract the log message
        if isinstance(record.msg, str):
            try:
                # Try to parse as JSON
                message_dict = json.loads(record.msg)
            except json.JSONDecodeError:
                # If not JSON, create a dict with the message
                message_dict = {"message": record.msg}
        else:
            message_dict = record.msg

        # Create the log entry
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "unifyops-api",
            "environment": settings.ENVIRONMENT,
            **message_dict,
        }

        # Return JSON string
        return json.dumps(log_data)


# Create default logger instance
get_logger = lambda name=None: StructuredLogger(name or __name__)
logger = get_logger("unifyops")
