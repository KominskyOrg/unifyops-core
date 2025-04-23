"""
UnifyOps Logging System
=======================

A structured logging system for FastAPI applications that provides:
- Context-aware logging across async boundaries
- Correlation ID tracking
- Environment-appropriate formatting (colorized console vs. JSON)
- DataDog-compatible structured logs
- Metadata enrichment
- OpenTelemetry-compatible distributed tracing

Usage Examples
-------------

Basic logger acquisition:
```python
from app.logging import get_logger

# Create a module-level logger
logger = get_logger(__name__)

# Use the logger
logger.info("Processing started")
logger.error("Failed to process", metadata={"item_id": "123"})
```

With correlation ID tracking in FastAPI:
```python
from fastapi import Depends, FastAPI, Request
from app.logging import set_correlation_id, add_metadata, get_logger
from app.logging.middleware import setup_logging_middleware

app = FastAPI()
logger = get_logger(__name__)

# Add comprehensive logging middleware
setup_logging_middleware(app, exclude_paths=["/health", "/metrics"])
```

With structured logging:
```python
logger = get_logger(__name__)
logger.structured("info", "user_login", user_id="123", success=True, auth_method="oauth")
```

Monitoring log metrics:
```python
from app.logging.logger_utils import get_logging_metrics

metrics = get_logging_metrics()
print(f"Log counts: {metrics['log_counts_by_level']}")
print(f"Serialization errors: {metrics['serialization_errors']}")
```
"""

# Import key components for easier access
from app.logging.context import get_logger, ContextLoggerAdapter
from app.logging.context_vars import (
    set_correlation_id,
    get_correlation_id,
    add_metadata,
    get_metadata,
    set_trace_context,
)
from app.logging.logger_config import LOG_LEVEL, ENVIRONMENT, IS_LOCAL, SERVICE_NAME, SERVICE_VERSION
from app.logging.logger_utils import get_logging_metrics

# Re-export these for convenient access
__all__ = [
    # Core logging components
    "get_logger",
    "ContextLoggerAdapter",
    
    # Context management
    "set_correlation_id",
    "get_correlation_id", 
    "add_metadata",
    "get_metadata",
    "set_trace_context",
    
    # Configuration
    "LOG_LEVEL",
    "ENVIRONMENT",
    "IS_LOCAL",
    "SERVICE_NAME",
    "SERVICE_VERSION",
    
    # Metrics
    "get_logging_metrics",
] 