# Background Task Logging System

This directory contains logs for background tasks in the UnifyOps platform, particularly for Terraform operations that run asynchronously.

## Directory Structure

- `/logs` - Main logs directory
  - `/background_tasks` - Logs for background tasks (Terraform operations, etc.)
    - `resource_[id].log` - Logs for resource provisioning tasks
    - `environment_[id].log` - Logs for environment provisioning tasks

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
  "resource_id": "def456",
  "module_path": "modules/aws/s3",
  "execution_id": "ghi789",
  "duration_ms": 1234.56
}
```

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
- `LOG_DIR`: Directory for general logs
- `TASK_LOG_DIR`: Directory for background task logs
- `LOG_MAX_SIZE_MB`: Maximum log file size before rotation
- `LOG_BACKUP_COUNT`: Number of rotated log files to keep
- `TERRAFORM_LOG_LEVEL`: Specific log level for Terraform operations

## Benefits

Using this logging system provides several advantages:

1. **Debugging** - Detailed logs help troubleshoot issues with Terraform operations
2. **Audit Trail** - Complete history of infrastructure changes
3. **Non-blocking** - Background tasks can be monitored without interrupting their execution
4. **Structured Data** - JSON format enables easy parsing and analysis

## Best Practices

1. Use the log viewer script rather than directly opening log files
2. Set appropriate log levels in production to avoid excessive logging
3. Implement log rotation for production deployments
4. Consider integrating with a centralized logging system for production use
