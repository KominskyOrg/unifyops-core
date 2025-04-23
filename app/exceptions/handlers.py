"""
Exception handlers for FastAPI.

This module provides the necessary exception handlers to integrate the 
custom exceptions with FastAPI applications, ensuring consistent error
responses and logging across the application.
"""

from typing import Any, Dict, List, Optional, Type, Union
import traceback
import sys
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler as fastapi_http_exception_handler
from pydantic import ValidationError as PydanticValidationError
import logging

from app.exceptions.base import AppException, ErrorResponse, ErrorDetail
from app.logging.context import get_logger

# Configure logger
logger = get_logger("exceptions", metadata={"component": "exception_handlers"})


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handler for application-specific exceptions.
    
    Args:
        request: The FastAPI request
        exc: The AppException that was raised
        
    Returns:
        JSONResponse with standardized error format
    """
    # Extract correlation ID from request state if available
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Log the exception with context
    logger.error(
        f"{exc.error_type}: {exc.message}",
        metadata={
            "exception": exc.__class__.__name__,
            "error_id": exc.error_id,
            "path": request.url.path,
            "method": request.method,
            "correlation_id": correlation_id,
            "status_code": exc.status_code,
            "error_type": exc.error_type,
        }
    )
    
    # Return the response using the exception's to_response method
    response_data = exc.to_response().model_dump()
    
    # Add correlation ID to response if available
    if correlation_id and "details" in response_data:
        response_data["correlation_id"] = correlation_id
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def http_exception_handler(request: Request, exc) -> JSONResponse:
    """
    Handler for FastAPI's HTTPException.
    
    Args:
        request: The FastAPI request
        exc: The HTTPException that was raised
        
    Returns:
        JSONResponse with standardized error format
    """
    from fastapi import HTTPException
    
    # Extract correlation ID from request state if available
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Create an error ID for tracking
    from app.exceptions.base import AppException
    error_instance = AppException(
        message=str(exc.detail),
        status_code=exc.status_code
    )
    
    # Log the exception with context
    logger.error(
        f"HTTP {exc.status_code}: {exc.detail}",
        metadata={
            "exception": "HTTPException",
            "error_id": error_instance.error_id,
            "path": request.url.path,
            "method": request.method,
            "correlation_id": correlation_id,
            "status_code": exc.status_code,
        }
    )
    
    # Convert to standardized response format
    response = error_instance.to_response().model_dump()
    
    # Add correlation ID to response if available
    if correlation_id:
        response["correlation_id"] = correlation_id
    
    # Return the response with any headers from the original exception
    return JSONResponse(
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
        content=response
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handler for FastAPI's RequestValidationError.
    
    Args:
        request: The FastAPI request
        exc: The RequestValidationError that was raised
        
    Returns:
        JSONResponse with standardized error format
    """
    # Extract correlation ID from request state if available
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Create an error ID for tracking
    from app.exceptions.base import AppException
    error_instance = AppException(
        message="Validation error",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    
    # Create a readable error message for logging
    error_details = []
    details = []
    
    for error in exc.errors():
        loc = [str(loc_item) for loc_item in error.get("loc", [])]
        msg = error.get("msg", "")
        err_type = error.get("type", "validation_error")
        
        error_details.append(f"{'.'.join(loc)}: {msg}")
        
        # Create structured error details
        details.append(
            ErrorDetail(
                loc=loc,
                msg=msg,
                type=err_type
            ).model_dump()
        )
    
    readable_errors = ", ".join(error_details)
    
    # Log the validation error with detailed context
    logger.warning(
        f"Validation error: {readable_errors}",
        metadata={
            "exception": "RequestValidationError",
            "error_id": error_instance.error_id,
            "path": request.url.path,
            "method": request.method,
            "correlation_id": correlation_id,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "errors": error_details,
        }
    )
    
    # Create standardized response
    response = ErrorResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_id=error_instance.error_id,
        message=f"Validation error: {readable_errors}",
        details=[ErrorDetail.model_validate(detail) for detail in details],
        error_type="validation_error"
    ).model_dump()
    
    # Add correlation ID to response if available
    if correlation_id:
        response["correlation_id"] = correlation_id
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response
    )


async def pydantic_validation_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """
    Handler for Pydantic's ValidationError.
    
    Args:
        request: The FastAPI request
        exc: The PydanticValidationError that was raised
        
    Returns:
        JSONResponse with standardized error format
    """
    # Convert to FastAPI's RequestValidationError and use its handler
    from fastapi.exceptions import RequestValidationError
    return await validation_exception_handler(request, RequestValidationError(exc.errors()))


async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for unexpected exceptions.
    
    Args:
        request: The FastAPI request
        exc: The unexpected Exception that was raised
        
    Returns:
        JSONResponse with standardized error format that does not expose internal details
    """
    # Extract correlation ID from request state if available
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Create an error ID for tracking
    from app.exceptions.base import AppException
    error_instance = AppException(
        message="An unexpected error occurred",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    
    # Get full traceback for logging
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_str = "".join(tb)
    
    # Log the exception with full context
    logger.critical(
        "Unhandled exception",
        metadata={
            "exception": exc.__class__.__name__,
            "exception_message": str(exc),
            "error_id": error_instance.error_id,
            "path": request.url.path,
            "method": request.method,
            "correlation_id": correlation_id,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "traceback": tb_str,
        }
    )
    
    # Create standardized response (without exposing internal details)
    response = ErrorResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_id=error_instance.error_id,
        message="An unexpected error occurred",
        error_type="server_error"
    ).model_dump()
    
    # Add correlation ID to response if available
    if correlation_id:
        response["correlation_id"] = correlation_id
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with a FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """
    from fastapi import HTTPException
    
    # Register handlers for custom exceptions
    app.add_exception_handler(AppException, app_exception_handler)
    
    # Register handlers for FastAPI exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Register handler for Pydantic validation errors (if they occur outside of request validation)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_handler)
    
    # Register catch-all handler for unexpected exceptions
    app.add_exception_handler(Exception, internal_exception_handler)
    
    logger.info("Registered all exception handlers") 