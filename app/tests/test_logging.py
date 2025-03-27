import json
import logging
from unittest.mock import patch, MagicMock
import pytest

from app.core.logging import StructuredLogger, get_logger, JSONFormatter, LogMessage


def test_structured_logger_creation():
    """Test that a structured logger can be created successfully."""
    logger = get_logger("test_logger")
    assert isinstance(logger, StructuredLogger)
    assert logger.name == "test_logger"


def test_json_formatter():
    """Test that the JSON formatter formats logs correctly."""
    formatter = JSONFormatter()

    # Create a log record
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=json.dumps({"message": "Test message", "level": "INFO", "context": {"key": "value"}}),
        args=(),
        exc_info=None,
    )

    # Format the record
    formatted = formatter.format(record)

    # Check it's valid JSON
    log_data = json.loads(formatted)

    # Verify keys
    assert "timestamp" in log_data
    assert "message" in log_data
    assert log_data["message"] == "Test message"
    assert log_data["level"] == "INFO"
    assert log_data["context"] == {"key": "value"}
    assert log_data["service"] == "unifyops-api"
    assert "environment" in log_data


@patch("sys.stdout")
def test_logger_info(mock_stdout):
    """Test that the logger.info method works correctly."""
    logger = get_logger("test_logger")

    # Call the logger
    logger.info("Test info message", test_field="test_value")

    # Get the output that would have been sent to stdout
    mock_stdout.write.assert_called()


@patch("sys.stdout")
def test_logger_error_with_exception(mock_stdout):
    """Test that the logger.error method correctly logs exceptions."""
    logger = get_logger("test_logger")

    # Create a test exception
    test_exception = ValueError("Test error")

    # Call the logger with the exception
    logger.error("Error occurred", exception=test_exception)

    # Get the output that would have been sent to stdout
    mock_stdout.write.assert_called()


def test_log_message_model():
    """Test that the LogMessage model works correctly."""
    # Create a log message
    log_message = LogMessage(
        level="INFO",
        message="Test message",
        correlation_id="test-correlation-id",
        path="/api/test",
        method="GET",
    )

    # Convert to dict
    log_dict = log_message.model_dump()

    # Verify fields
    assert log_dict["level"] == "INFO"
    assert log_dict["message"] == "Test message"
    assert log_dict["correlation_id"] == "test-correlation-id"
    assert log_dict["path"] == "/api/test"
    assert log_dict["method"] == "GET"
    assert "timestamp" in log_dict
    assert "service" in log_dict
    assert "environment" in log_dict
