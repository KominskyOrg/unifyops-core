import json
import logging
import sys
import os
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


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle exceptions and other special types"""
    def default(self, obj):
        # Handle exceptions by converting them to strings
        if isinstance(obj, Exception):
            return str(obj)
        # Let the base class handle other types or raise TypeError
        return super().default(obj)


class StructuredLogger:
    """
    Structured JSON logger for consistent, machine-parseable logs
    """

    def __init__(self, name: str, level: str = None, log_to_file: bool = False, file_path: Optional[str] = None):
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

        # Add JSON handler for console output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(console_handler)
        
        # Add file handler if requested
        if log_to_file:
            self._setup_file_handler(file_path)

    def _setup_file_handler(self, file_path: Optional[str] = None):
        """Set up a file handler for logging to a file"""
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Use provided file path or create a default one based on the logger name
        if not file_path:
            file_path = os.path.join(logs_dir, f"{self.name.replace('.', '_')}.log")
            
        # Create a file handler that appends to the log file
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)
        
        self.info(f"File logging enabled, writing to: {file_path}")

    def log(self, level: str, message: str, **kwargs) -> None:
        """Base logging method"""
        log_level = getattr(logging, level.upper())

        # Create structured log message
        log_data = {"level": level, "message": message, **kwargs}

        # Convert any exceptions to strings before JSON serialization
        if "exception" in kwargs and isinstance(kwargs["exception"], Exception):
            log_data["exception"] = str(kwargs["exception"])

        # Pass to the logger using custom encoder
        self.logger.log(log_level, json.dumps(log_data, cls=CustomJSONEncoder))

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

        # Return JSON string with custom encoder
        return json.dumps(log_data, cls=CustomJSONEncoder)


# Create default logger instance
get_logger = lambda name=None, log_to_file=False, file_path=None: StructuredLogger(name or __name__, log_to_file=log_to_file, file_path=file_path)
logger = get_logger("unifyops")

# Create a file logger for background tasks
def get_background_task_logger(task_type: str, task_id: str) -> StructuredLogger:
    """
    Get a logger specifically for background tasks with file output enabled.
    
    Args:
        task_type: Type of background task (e.g., 'terraform', 'resource', 'environment')
        task_id: Unique identifier for the task (e.g., resource_id, environment_id)
        
    Returns:
        StructuredLogger: Logger instance with file output enabled
    """
    logs_dir = os.path.join(os.getcwd(), "logs", "background_tasks")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create a file name that includes both task type and ID for easy identification
    file_path = os.path.join(logs_dir, f"{task_type}_{task_id}.log")
    
    return get_logger(f"background.{task_type}.{task_id}", log_to_file=True, file_path=file_path)
