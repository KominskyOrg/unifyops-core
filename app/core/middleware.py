import time
import uuid
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from fastapi.responses import JSONResponse

from app.core.logging import logger, get_logger
from app.core.exceptions import TerraformError, NotFoundError, BadRequestError


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
                correlation_id=correlation_id,
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
                correlation_id=correlation_id,
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
    """Initialize middleware for the FastAPI application"""

    # Add Terraform-specific error handlers
    @app.exception_handler(TerraformError)
    async def terraform_error_handler(request: Request, exc: TerraformError):
        """Handle Terraform errors"""
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.error(f"Terraform error: {str(exc)}", exception=exc, correlation_id=correlation_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)}
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        """Handle not found errors"""
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.warning(f"Not found error: {str(exc)}", exception=exc, correlation_id=correlation_id)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(BadRequestError)
    async def bad_request_error_handler(request: Request, exc: BadRequestError):
        """Handle bad request errors"""
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.warning(
            f"Bad request error: {str(exc)}", exception=exc, correlation_id=correlation_id
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


def setup_middleware(app: FastAPI) -> None:
    """Set up middleware for the application"""

    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next: Callable):
        """Add correlation ID to the request state for tracing"""
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        # Add correlation ID to response headers
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable):
        """Log request and response details"""
        start_time = time.time()

        # Get correlation ID from state
        correlation_id = getattr(request.state, "correlation_id", None)

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            correlation_id=correlation_id,
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"Response: {response.status_code}",
                status_code=response.status_code,
                process_time_ms=process_time,
                correlation_id=correlation_id,
            )

            # Add processing time header
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            return response

        except Exception as e:
            # Log exception
            logger.error(f"Request failed: {str(e)}", exception=e, correlation_id=correlation_id)
            raise

    @app.exception_handler(TerraformError)
    async def terraform_error_handler(request: Request, exc: TerraformError):
        """Handle Terraform errors"""
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.error(f"Terraform error: {str(exc)}", exception=exc, correlation_id=correlation_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)}
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        """Handle not found errors"""
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.warning(f"Not found error: {str(exc)}", exception=exc, correlation_id=correlation_id)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(BadRequestError)
    async def bad_request_error_handler(request: Request, exc: BadRequestError):
        """Handle bad request errors"""
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.warning(
            f"Bad request error: {str(exc)}", exception=exc, correlation_id=correlation_id
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})
