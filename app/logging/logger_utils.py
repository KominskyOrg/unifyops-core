import os
import json
import logging
from typing import Dict, Any
from collections import defaultdict
import time

from app.utils.utils import parse_uuids
from app.logging.context_vars import (
    correlation_id_var, 
    metadata_var, 
    trace_id_var, 
    span_id_var
)

# Metrics tracking
_log_counts = defaultdict(int)
_serialization_errors = 0
_rate_limit_counters = defaultdict(int)
_rate_limit_timestamps = defaultdict(float)

def get_logging_metrics():
    """
    Return metrics about the logging system performance.
    
    Returns:
        Dict containing log counts by level and error statistics
    """
    return {
        "log_counts_by_level": dict(_log_counts),
        "serialization_errors": _serialization_errors,
        "rate_limited_logs": dict(_rate_limit_counters)
    }

def is_rate_limited(key: str, max_count: int, time_window: float) -> bool:
    """
    Check if a log should be rate limited.
    
    Args:
        key: The rate limiting key (usually log message or category)
        max_count: Maximum allowed count in the time window
        time_window: Time window in seconds
        
    Returns:
        True if the log should be rate limited, False otherwise
    """
    now = time.time()
    
    # Reset counter if time window has passed
    if now - _rate_limit_timestamps.get(key, 0) > time_window:
        _rate_limit_counters[key] = 0
        _rate_limit_timestamps[key] = now
    
    # Increment counter
    _rate_limit_counters[key] += 1
    
    # Check if limit exceeded
    return _rate_limit_counters[key] > max_count

# ——— Metadata helpers ———
def add_metadata(**kwargs) -> None:
    """
    Merge these key/value pairs into the current request's metadata.
    They'll end up as flat fields in the JSON log.
    """
    meta = metadata_var.get() or {}
    meta.update(kwargs)
    metadata_var.set(meta)


# ——— JSON builder ———
def format_log_as_json(record: logging.LogRecord, message: str) -> str:
    """
    Assemble structured log data in the format expected by DataDog.
    
    This function transforms a log record into a properly structured JSON
    format with metadata flattening and correlation ID tracking.
    
    Args:
        record: The LogRecord object
        message: The formatted log message
        
    Returns:
        JSON string representation of the log data
        
    Raises:
        ValueError: If the record contains data that cannot be serialized to JSON
    """
    # Track metrics by log level
    global _serialization_errors
    _log_counts[record.levelname] += 1
    
    try:
        # Process metadata with UUID handling
        flat_meta = _flatten_metadata(metadata_var.get() or {})
        
        # Get trace context if available
        trace_id = trace_id_var.get()
        span_id = span_id_var.get()
        
        # Build the base payload with standard fields
        payload = {
            # core log data
            "message":    message,
            "levelname":  record.levelname,
            "timestamp":  int(record.created * 1000),
            "logger.name":record.name,
            "threadName": record.threadName,
            "correlation_id": correlation_id_var.get(),
    
            # source info
            "pathname": getattr(record, "source_file", record.pathname),
            "lineno":   getattr(record, "source_line", record.lineno),
            "funcName": record.funcName,
            "hostname": os.getenv("HOSTNAME", "unknown"),
            "ddsource": "python",
            "service": os.getenv("SERVICE_NAME", "unifyops-api"),
            "env": os.getenv("ENVIRONMENT", "development"),
            **flat_meta,
        }
        
        # Add OpenTelemetry trace context if available
        if trace_id:
            payload["trace_id"] = trace_id
        if span_id:
            payload["span_id"] = span_id
    
        # Add exception information if present
        if record.exc_info:
            err = logging.Formatter().formatException(record.exc_info)
            if err and "NoneType" not in err:
                payload["error.stack"] = err
    
        # Drop nulls and emit JSON
        clean = {k: v for k, v in payload.items() if v is not None}
        return json.dumps(clean)
    except TypeError as e:
        # Handle JSON serialization errors gracefully
        _serialization_errors += 1
        fallback = {
            "message": f"ERROR SERIALIZING LOG: {str(e)}",
            "original_message": message,
            "levelname": record.levelname,
            "timestamp": int(record.created * 1000),
            "logger.name": record.name,
            "correlation_id": correlation_id_var.get()
        }
        return json.dumps(fallback)
    except Exception as e:
        # Catch any other errors to prevent logging failures
        _serialization_errors += 1
        return json.dumps({
            "message": f"CRITICAL ERROR IN LOG FORMATTING: {str(e)}",
            "levelname": "ERROR",
            "timestamp": int(record.created * 1000)
        })


def _flatten_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flattens nested metadata dictionaries for consistent log field structure.
    
    Args:
        metadata: The metadata dictionary to flatten
        
    Returns:
        Flattened dictionary with nested keys joined by underscores
    """
    flat_meta = {}
    for k, v in parse_uuids(metadata).items():
        if isinstance(v, dict):
            for subk, subv in v.items():
                flat_meta[f"{k}_{subk}"] = subv
        else:
            flat_meta[k] = v
    return flat_meta
