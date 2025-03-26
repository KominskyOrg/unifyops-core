import time
import uuid
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.logging import logger


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all incoming requests and responses with performance metrics
    """
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID if not provided in headers
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        
        # Add correlation ID to request state for use in route handlers
        request.state.correlation_id = correlation_id
        
        # Start timer
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log successful request
            logger.request_log(
                request=request,
                status_code=response.status_code,
                duration_ms=duration_ms,
                correlation_id=correlation_id
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
        except Exception as e:
            # Calculate duration for failed requests
            duration_ms = (time.time() - start_time) * 1000
            
            # Log exception (the exception handler will log it as well, but here we track timing)
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exception=e,
                path=request.url.path,
                method=request.method,
                duration_ms=duration_ms,
                correlation_id=correlation_id
            )
            
            # Re-raise the exception for the exception handlers to process
            raise


class CorrelationIDMiddleware:
    """
    Middleware that ensures all requests have a correlation ID
    This is implemented as a pure ASGI middleware for better performance
    """
    def __init__(self, app: ASGIApp):
        self.app = app
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            # Pass through non-HTTP requests
            await self.app(scope, receive, send)
            return
        
        # Extract headers from scope
        headers = dict(scope.get("headers", []))
        
        # Generate correlation ID if not provided
        correlation_id = headers.get(b"x-correlation-id", b"").decode() or str(uuid.uuid4())
        
        # Add correlation ID to scope state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["correlation_id"] = correlation_id
        
        # Modify the send function to include the correlation ID header
        async def send_with_correlation_id(message):
            if message["type"] == "http.response.start":
                # Add correlation ID to response headers
                headers = message.get("headers", [])
                correlation_header = (b"x-correlation-id", correlation_id.encode())
                
                # Check if the header already exists
                header_exists = False
                for i, (key, _) in enumerate(headers):
                    if key.lower() == b"x-correlation-id":
                        headers[i] = correlation_header
                        header_exists = True
                        break
                
                # Add the header if it doesn't exist
                if not header_exists:
                    headers.append(correlation_header)
                
                message["headers"] = headers
            
            await send(message)
        
        # Process the request with modified send function
        await self.app(scope, receive, send_with_correlation_id)


def init_middleware(app: FastAPI) -> None:
    """Initialize all middleware for the application"""
    # Add correlation ID middleware
    app.add_middleware(CorrelationIDMiddleware)
    
    # Add request logger middleware
    app.add_middleware(RequestLoggerMiddleware)
    
    # You can add more middleware here as needed 