# UnifyOps Logging System

A structured, context-aware logging system for FastAPI applications with built-in support for correlation IDs, metadata enrichment, and environment-adaptive formatting.

## Features

- **Context-Aware Logging**: Track request context across async boundaries
- **Correlation ID Tracking**: Automatically associate logs with request flows
- **Environment-Adaptive Formatting**:
  - Development: Colorized console output with readable formatting
  - Production: Structured JSON with DataDog compatibility
- **Metadata Enrichment**: Add contextual data to logs at module, request, or call level
- **Stack Frame Resolution**: Smart caller identification for accurate source file tracking
- **Robust Error Handling**: Graceful fallbacks for serialization errors

## Installation

The logging system is part of the UnifyOps core package. No additional installation is needed.

## Quick Start

### Basic Logger Acquisition

```python
from app.logging import get_logger

# Create a module-level logger
logger = get_logger(__name__)

# Basic logging
logger.info("System started")
logger.warning("Resource usage high")

# With metadata
logger.info("User authenticated", metadata={"user_id": "12345"})
```

### FastAPI Integration

```python
from fastapi import FastAPI
from app.logging.middleware import setup_logging_middleware

app = FastAPI()

# Add the logging middleware
setup_logging_middleware(app, exclude_paths=["/health", "/metrics"])
```

## Core Components

The logging system consists of these key files:

- `context_vars.py`: Central context variable definitions
- `context.py`: Logger adapters for context awareness
- `formatter.py`: Output formatters (Console and JSON)
- `logger_config.py`: Configuration for Python's logging system
- `logger_utils.py`: Utility functions and JSON formatting
- `middleware.py`: FastAPI middleware for request tracking

## Advanced Usage

### Module-Level Metadata

```python
# Set module-wide metadata that will be included in all logs from this logger
logger = get_logger(__name__, metadata={
    "component": "authentication_service",
    "version": "2.1.0"
})
```

### Request Context Metadata

```python
from app.logging import add_metadata

# Later in a request handler
add_metadata(
    user_id=user.id,
    tenant_id=tenant.id,
    feature_flags=enabled_features
)

# This metadata persists across all logs in the current request context
```

### Correlation ID Management

```python
from app.logging import set_correlation_id, get_correlation_id

# Set correlation ID manually
set_correlation_id("txn-12345-abcde")

# Retrieve current correlation ID
current_id = get_correlation_id()
```

## Configuration

The logging system behavior can be controlled through environment variables:

- `ENVIRONMENT`: Controls default formatting (local/dev/prod)
- `LOG_LEVEL`: Sets minimum log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `LOG_STYLE`: Forces specific formatting style (auto/console/json)
- `NO_COLOR`: Disables ANSI colors in console output when set
- `APP_ROOT`: Base directory for source file resolution

## Best Practices

1. **Use Module Loggers**: Create loggers at module level with `__name__`
2. **Add Contextual Metadata**: Include relevant business entities in logs
3. **Leverage Correlation IDs**: Use them to track request flows across services
4. **Structure Log Messages**: Make messages searchable and parseable
5. **Handle Exceptions**: Always include exception info with error logs

## Troubleshooting

### Common Issues

- **Missing Context Data**: Ensure middleware is properly configured
- **Incorrect Source File**: Check APP_ROOT environment variable
- **JSON Serialization Errors**: Check for non-serializable objects in metadata

### Diagnostic Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging._handlerList = []  # Clear existing handlers
```

## References

- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [DataDog Logging Best Practices](https://docs.datadoghq.com/logs/log_collection/python/)
