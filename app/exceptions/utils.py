"""
Exception handling utilities.

This module provides utility functions for working with exceptions,
including formatting, capturing, and error boundary patterns.
"""

import functools
import sys
import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast
from contextvars import ContextVar
from fastapi import status
from pydantic import ValidationError

from app.logging.context import get_logger
from app.exceptions.base import AppException

# Configure logger
logger = get_logger("exceptions.utils", metadata={"component": "exception_utils"})

# Type variables for generics
T = TypeVar('T')
R = TypeVar('R')
F = TypeVar('F', bound=Callable[..., Any])

# Context variable for tracking error context
error_context_var: ContextVar[Dict[str, Any]] = ContextVar('error_context', default={})


def format_exception(exc: Exception) -> Dict[str, Any]:
    """
    Format an exception into a standardized dictionary.
    
    Args:
        exc: The exception to format
        
    Returns:
        A dictionary with standardized exception information
    """
    error_id = str(uuid.uuid4())
    
    # Get the traceback
    tb = traceback.extract_tb(sys.exc_info()[2] if sys.exc_info()[2] else None)
    
    # Format as structured data
    result = {
        "error_id": error_id,
        "exception_type": exc.__class__.__name__,
        "message": str(exc),
        "traceback": traceback.format_exception_only(type(exc), exc),
        "traceback_frames": [
            {
                "filename": frame.filename,
                "lineno": frame.lineno,
                "name": frame.name,
                "line": frame.line
            }
            for frame in tb
        ],
        "timestamp": None  # Will be filled by the logging system
    }
    
    # Add extra attributes if it's an AppException
    if isinstance(exc, AppException):
        result.update({
            "error_id": exc.error_id,
            "status_code": exc.status_code,
            "error_type": exc.error_type,
            "details": exc.details
        })
    
    # Add any context stored in the error context
    context = error_context_var.get()
    if context:
        result["context"] = context
    
    return result


def capture_exception(
    exc: Exception,
    reraise: bool = True,
    message: Optional[str] = None,
    log_level: str = "error",
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Capture an exception, log it, and optionally re-raise it.
    
    Args:
        exc: The exception to capture
        reraise: Whether to re-raise the exception after capturing
        message: Optional custom message to log
        log_level: The log level to use (debug, info, warning, error, critical)
        additional_data: Additional data to include in the log
        
    Returns:
        The formatted exception data
        
    Raises:
        The original exception if reraise is True
    """
    # Format the exception
    exc_data = format_exception(exc)
    
    # Add any additional data
    if additional_data:
        exc_data.update(additional_data)
    
    # Get the message to log
    log_message = message or f"Exception captured: {exc}"
    
    # Log with the appropriate level
    logger_method = getattr(logger, log_level)
    logger_method(
        log_message,
        metadata={
            "captured_exception": exc_data,
            "error_id": exc_data.get("error_id"),
        }
    )
    
    # Re-raise if requested
    if reraise:
        raise exc
    
    return exc_data


class error_context:
    """
    Context manager for adding context to exceptions.
    
    Example:
        ```python
        with error_context(user_id="123", operation="create_item"):
            # Any exception raised here will include the context
            item = create_item(data)
        ```
    """
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.token = None
    
    def __enter__(self):
        # Get the current context and update it with new values
        current = error_context_var.get()
        updated = {**current, **self.context}
        
        # Set the updated context
        self.token = error_context_var.set(updated)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore the previous context
        if self.token:
            error_context_var.reset(self.token)
        
        # If an exception occurred, add context to it
        if exc_val and isinstance(exc_val, Exception):
            # If it's our app exception, we can add context directly
            if isinstance(exc_val, AppException) and not hasattr(exc_val, "context"):
                exc_val.context = self.context
            
            # Log the exception with the context
            logger.error(
                f"Exception in error_context: {exc_val}",
                metadata={
                    "exception": exc_val.__class__.__name__,
                    "message": str(exc_val),
                    "error_context": self.context
                }
            )
        
        # Don't suppress the exception
        return False


def error_boundary(
    *,
    fallback_value: Optional[Any] = None,
    error_transformer: Optional[Callable[[Exception], Exception]] = None,
    on_error: Optional[Callable[[Exception], None]] = None
) -> Callable[[F], F]:
    """
    Decorator that creates a boundary around a function to handle exceptions.
    
    Args:
        fallback_value: Value to return if an exception occurs
        error_transformer: Function to transform the exception
        on_error: Function to call when an exception occurs
        
    Returns:
        Decorated function
        
    Example:
        ```python
        @error_boundary(fallback_value=[])
        def get_items():
            # If this raises an exception, the function will return []
            return fetch_items_from_database()
        ```
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                # Call the on_error callback if provided
                if on_error:
                    try:
                        on_error(exc)
                    except Exception as callback_exc:
                        logger.error(
                            f"Error in on_error callback: {callback_exc}",
                            metadata={"original_exception": str(exc)}
                        )
                
                # Transform the exception if a transformer is provided
                if error_transformer:
                    try:
                        transformed_exc = error_transformer(exc)
                        raise transformed_exc
                    except Exception as transform_exc:
                        if transform_exc is not exc:
                            logger.error(
                                f"Error in error_transformer: {transform_exc}",
                                metadata={"original_exception": str(exc)}
                            )
                            raise transform_exc
                
                # If we get here, return the fallback value
                return fallback_value
        
        return cast(F, wrapper)
    
    return decorator


def convert_exception(
    from_exc: Type[Exception],
    to_exc: Type[Exception],
    message: Optional[str] = None,
    status_code: Optional[int] = None
) -> Callable[[F], F]:
    """
    Decorator that converts specific exceptions to application exceptions.
    
    Args:
        from_exc: The exception type to convert from
        to_exc: The exception type to convert to
        message: Optional message for the new exception
        status_code: Optional status code for the new exception
        
    Returns:
        Decorated function
        
    Example:
        ```python
        @convert_exception(ValueError, BadRequestError, "Invalid value provided")
        def parse_config(config_str):
            # If this raises ValueError, it will be converted to BadRequestError
            return json.loads(config_str)
        ```
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except from_exc as exc:
                # Prepare arguments for the new exception
                exc_args = {}
                
                if message:
                    exc_args["message"] = message
                elif hasattr(to_exc, "__init__") and "message" in to_exc.__init__.__code__.co_varnames:
                    exc_args["message"] = str(exc)
                
                if status_code and hasattr(to_exc, "__init__") and "status_code" in to_exc.__init__.__code__.co_varnames:
                    exc_args["status_code"] = status_code
                
                # Create and raise the new exception
                if issubclass(to_exc, AppException):
                    raise to_exc(**exc_args)
                else:
                    raise to_exc(str(exc))
                
        return cast(F, wrapper)
    
    return decorator


def handle_validation_errors(func: F) -> F:
    """
    Decorator that handles Pydantic validation errors.
    
    Converts Pydantic ValidationError to app's DataValidationError.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function
        
    Example:
        ```python
        @handle_validation_errors
        def create_user(user_data: Dict[str, Any]) -> User:
            # If UserModel validation fails, it will raise DataValidationError
            return UserModel(**user_data)
        ```
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as exc:
            # Import here to avoid circular imports
            from app.exceptions.validation import DataValidationError
            
            # Convert to app's DataValidationError
            raise DataValidationError.from_validation_error(exc)
        
    return cast(F, wrapper)


def handle_database_errors(func: F) -> F:
    """
    Decorator that handles database-related errors.
    
    Converts various database exceptions to appropriate app exceptions.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function
        
    Example:
        ```python
        @handle_database_errors
        async def get_user(user_id: str) -> User:
            # Database errors will be converted to appropriate app exceptions
            return await db.users.find_one({"_id": user_id})
        ```
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            # Import here to avoid circular imports
            from app.exceptions.database import (
                ConnectionError as DBConnectionError,
                QueryError,
                TransactionError,
                IntegrityError,
                NoResultFoundError
            )
            
            # Check the exception type and convert appropriately
            if "connection" in str(exc).lower() or "timeout" in str(exc).lower():
                raise DBConnectionError(message=f"Database connection error: {exc}")
            elif "transaction" in str(exc).lower():
                raise TransactionError(message=f"Database transaction error: {exc}")
            elif "integrity" in str(exc).lower() or "constraint" in str(exc).lower():
                raise IntegrityError(message=f"Database integrity error: {exc}")
            elif "no row" in str(exc).lower() or "not found" in str(exc).lower():
                raise NoResultFoundError(message=f"Database record not found: {exc}")
            else:
                raise QueryError(message=f"Database query error: {exc}")
        
    return cast(F, wrapper)