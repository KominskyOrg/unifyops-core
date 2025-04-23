"""
Context variables for logging and request tracking.

This module centralizes all ContextVar definitions used for tracking
request context, correlation IDs, and metadata across async boundaries.
"""

from contextvars import ContextVar
from typing import Dict, Any, Optional

# Main context tracking variables
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
metadata_var: ContextVar[Dict[str, Any]] = ContextVar("metadata", default={})
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar("span_id", default=None)

def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current execution context."""
    correlation_id_var.set(correlation_id)
    
def get_correlation_id() -> Optional[str]:
    """Get the correlation ID for the current execution context."""
    return correlation_id_var.get()

def add_metadata(**kwargs: Any) -> None:
    """
    Merge key/value pairs into the current context's metadata.
    
    This metadata will be included in log entries for tracking
    and filtering purposes.
    
    Args:
        **kwargs: Key-value pairs to add to the metadata
    """
    meta = metadata_var.get().copy()
    meta.update(kwargs)
    metadata_var.set(meta)
    
def get_metadata() -> Dict[str, Any]:
    """Get the metadata for the current execution context."""
    return metadata_var.get().copy()

def set_trace_context(trace_id: str, span_id: str) -> None:
    """Set OpenTelemetry-compatible trace context."""
    trace_id_var.set(trace_id)
    span_id_var.set(span_id) 