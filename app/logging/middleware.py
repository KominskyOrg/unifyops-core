"""
FastAPI middleware for request logging and correlation ID tracking.

This module provides middleware for FastAPI applications to:
1. Track correlation IDs across requests
2. Log request details including timing
3. Set up context for structured logging
4. Extract W3C Trace Context headers for distributed tracing

Use this middleware in your FastAPI application to enable
consistent logging and correlation ID tracking.
"""

import time
import uuid
import re
from typing import Callable, Optional, Tuple

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging import get_logger, set_correlation_id, add_metadata, set_trace_context

# Module logger
logger = get_logger(__name__)

# W3C Trace Context traceparent header pattern
# Format: version-trace_id-parent_id-flags
# Example: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
TRACEPARENT_PATTERN = re.compile(r'^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$')

def parse_traceparent(header_value: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse the W3C Trace Context traceparent header.
    
    Args:
        header_value: The traceparent header value
        
    Returns:
        Tuple of (trace_id, span_id) or (None, None) if invalid
    """
    if not header_value:
        return None, None
        
    match = TRACEPARENT_PATTERN.match(header_value)
    if not match:
        return None, None
        
    version, trace_id, parent_id, flags = match.groups()
    return trace_id, parent_id

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive logging middleware that combines:
    - Correlation ID tracking
    - Request/response logging with timing
    - Context metadata population
    - W3C Trace Context extraction
    
    This is the preferred middleware to use for FastAPI applications.
    """
    
    def __init__(self, app: FastAPI, *, exclude_paths: Optional[list[str]] = None, 
                 sample_rate: float = 1.0):
        """
        Initialize with sampling support.
        
        Args:
            app: The FastAPI application
            exclude_paths: Optional list of paths to exclude from logging (e.g. health checks)
            sample_rate: Fraction of requests to log (0.0-1.0)
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self.sample_rate = max(0.0, min(1.0, sample_rate))  # Clamp between 0 and 1
        
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        # Extract and set W3C Trace Context if present
        traceparent = request.headers.get("traceparent")
        if traceparent:
            trace_id, span_id = parse_traceparent(traceparent)
            if trace_id and span_id:
                set_trace_context(trace_id, span_id)
                # If no correlation ID was explicitly provided, use trace_id as correlation_id
                if not request.headers.get("X-Correlation-ID"):
                    correlation_id = trace_id
                    set_correlation_id(correlation_id)
        
        # Store in request state for handlers
        request.state.correlation_id = correlation_id
        
        # Add request metadata to logging context
        add_metadata(
            path=request.url.path,
            method=request.method,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        logger.info(f"Request started: {request.method} {request.url.path}")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Add response metadata
            add_metadata(
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2)
            )
            
            # Log successful response
            logger.info(
                f"Request completed: {response.status_code} in {duration_ms:.2f}ms"
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            # Propagate trace context in response if it was in the request
            if traceparent:
                response.headers["traceparent"] = traceparent
                if "tracestate" in request.headers:
                    response.headers["tracestate"] = request.headers["tracestate"]
            
            return response
            
        except Exception as exc:
            # Calculate duration for error case
            duration_ms = (time.time() - start_time) * 1000
            
            # Log exception with details
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exc_info=exc,
                metadata={
                    "duration_ms": round(duration_ms, 2),
                    "error": str(exc)
                }
            )
            
            # Re-raise to let exception handlers process it
            raise


def setup_logging_middleware(app: FastAPI, exclude_paths: Optional[list[str]] = None) -> None:
    """
    Set up the logging middleware for a FastAPI application.
    
    Args:
        app: The FastAPI application
        exclude_paths: Optional list of paths to exclude from logging
    
    Example:
        ```python
        from fastapi import FastAPI
        from app.logging.middleware import setup_logging_middleware
        
        app = FastAPI()
        setup_logging_middleware(app, exclude_paths=["/health", "/metrics"])
        ```
    """
    app.add_middleware(
        LoggingMiddleware,
        exclude_paths=exclude_paths
    ) 