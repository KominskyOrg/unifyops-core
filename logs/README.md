# UnifyOps Logging System

This directory contains logs for the UnifyOps platform, with a focus on structured JSON logging for both the API service and background tasks.

## Directory Structure

- `/logs` - Main logs directory
  - `/background_tasks` - Logs for background tasks (Terraform operations, etc.)
    - `resource_[id].log` - Logs for resource provisioning tasks
    - `environment_[id].log` - Logs for environment provisioning tasks
    - `terraform_[execution_id].log` - Logs for specific Terraform executions

## Logging Architecture

The UnifyOps platform uses structured logging with JSON format throughout:

1. **API Service Logs**: Captured in the console and optionally in files
2. **Background Task Logs**: Always written to files in this directory
3. **Middleware Request Logging**: All HTTP requests are automatically logged with timing information

## Log Format

All logs are stored in JSON format with consistent fields:

```json
{
  "timestamp": "2023-06-21T12:34:56.789Z",
  "level": "INFO",
  "message": "The log message",
  "service": "unifyops-api",
  "environment": "development",
  "correlation_id": "abc123",
  "path": "/api/v1/resources/123",
  "method": "GET",
  "duration_ms": 42.5,
  "status_code": 200
}
```

### Common Fields

| Field            | Description                                               |
| ---------------- | --------------------------------------------------------- |
| `timestamp`      | ISO 8601 timestamp in UTC                                 |
| `level`          | Log level (INFO, DEBUG, WARNING, ERROR, CRITICAL)         |
| `message`        | Human-readable log message                                |
| `service`        | Service name (unifyops-api)                               |
| `environment`    | Deployment environment (development, staging, production) |
| `correlation_id` | Request correlation ID for tracking across services       |

### Context-Specific Fields

Background task logs may include additional fields:

- `resource_id`: ID of the resource being provisioned
- `environment_id`: ID of the environment being managed
- `execution_id`: Unique ID for Terraform execution
- `module_path`: Path to the Terraform module
- `duration_ms`: Duration of operation in milliseconds

## Viewing Logs

The system includes a log viewer script to help you read and monitor task logs. The script is located at the root of the project:

```bash
./read_task_logs.py
```

### Usage Examples

List all available log files:

```bash
./read_task_logs.py --list
```

View logs for a specific resource:

```bash
./read_task_logs.py --type resource --id <resource_id>
```

View logs for a specific environment:

```bash
./read_task_logs.py --type environment --id <environment_id>
```

Follow logs in real-time (similar to `tail -f`):

```bash
./read_task_logs.py --type resource --id <resource_id> --follow
```

## Configuration

Logging behavior can be configured through environment variables:

- `LOG_LEVEL`: Set the minimum log level (debug, info, warning, error, critical)
- `LOG_TO_FILE`: Enable/disable file logging (true/false)
- `LOG_DIR`: Directory for general logs (defaults to ./logs)
- `TERRAFORM_LOG_LEVEL`: Specific log level for Terraform operations

## Implementation Details

### Logger Initialization

```python
from app.core.logging import get_logger

# Standard logger (console output)
logger = get_logger("component_name")

# File logger with custom path
file_logger = get_logger("component_name", log_to_file=True, file_path="/path/to/log.log")

# Background task logger (automatically creates task-specific log file)
from app.core.logging import get_background_task_logger
task_logger = get_background_task_logger("resource", "resource_id")
```

### Usage in Code

```python
# Basic logging
logger.info("Operation completed successfully")

# Logging with additional context
logger.info(
    "Resource created",
    resource_id="123",
    resource_type="ec2",
    duration_ms=142.5
)

# Error logging with exception details
try:
    # Some operation
except Exception as e:
    logger.error("Failed to create resource", exception=e, resource_id="123")
```

## Best Practices

1. Use the log viewer script rather than directly opening log files
2. Set appropriate log levels in production to avoid excessive logging
3. Include correlation_id in logs when available to trace requests through the system
4. Add relevant context to logs (resource IDs, operation details) to aid troubleshooting
5. Consider integrating with a centralized logging system for production use
