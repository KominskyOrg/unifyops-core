"""
Base exception classes for the application.

This module defines the foundational exception classes that other 
exception types will inherit from, as well as the standard error
response structures used throughout the application.
"""

from typing import Any, Dict, List, Optional, Union
from fastapi import status
from pydantic import BaseModel, Field
import uuid
import traceback
import sys
from datetime import datetime

# Error schema definitions
class ErrorDetail(BaseModel):
    """
    Structure for detailed error information.
    
    Attributes:
        loc: Location of the error (e.g., ["body", "user", "email"])
        msg: Human-readable error message
        type: Error type identifier
        code: Optional error code for client interpretation
    """
    loc: Optional[List[str]] = None
    msg: str
    type: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """
    Standard error response format returned to clients.
    
    Attributes:
        status_code: HTTP status code
        error_id: Unique identifier for the error instance
        message: Human-readable error message
        details: Detailed error information
        timestamp: When the error occurred
        error_type: Type of error that occurred
    """
    status_code: int
    error_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_type: str = "error"


class AppException(Exception):
    """
    Base exception class for all application-specific exceptions.
    
    This class provides a standardized way to handle errors throughout
    the application with consistent error responses and logging.
    
    Attributes:
        message: Human-readable error message
        status_code: HTTP status code to return
        details: Detailed error information
        error_id: Unique identifier for the error instance
        error_type: Type of error for categorization
        timestamp: When the error occurred
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type = "server_error"
    
    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: Optional[int] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        error_id: Optional[str] = None,
    ):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.details = details
        self.error_id = error_id or str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.extract_tb(sys.exc_info()[2]) if sys.exc_info()[2] else None
        
        # Call the base class constructor
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the exception to a dictionary representation.
        
        Returns:
            Dict containing the exception details.
        """
        error_dict = {
            "error_id": self.error_id,
            "message": self.message,
            "status_code": self.status_code,
            "error_type": self.error_type,
            "timestamp": self.timestamp.isoformat(),
        }
        
        if self.details:
            error_dict["details"] = self.details
            
        return error_dict
    
    def to_response(self) -> ErrorResponse:
        """
        Convert the exception to an ErrorResponse object.
        
        Returns:
            ErrorResponse object representing this exception.
        """
        # Convert raw details dictionaries to ErrorDetail objects
        details = None
        if self.details:
            details = [
                ErrorDetail(
                    loc=detail.get("loc"),
                    msg=detail.get("msg", ""),
                    type=detail.get("type", self.error_type),
                    code=detail.get("code"),
                )
                for detail in self.details
            ]
            
        return ErrorResponse(
            status_code=self.status_code,
            error_id=self.error_id,
            message=self.message,
            details=details,
            timestamp=self.timestamp,
            error_type=self.error_type,
        )
    
    @classmethod
    def from_exception(cls, exc: Exception, message: Optional[str] = None) -> 'AppException':
        """
        Create an AppException from another exception.
        
        Args:
            exc: The source exception
            message: Optional custom message to use
            
        Returns:
            A new AppException instance
        """
        error_message = message or str(exc)
        return cls(message=error_message, details=[
            {"loc": None, "msg": str(exc), "type": exc.__class__.__name__}
        ])


class ClientError(AppException):
    """
    Base class for all client-side errors (4xx status codes).
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_type = "client_error"


class ServerError(AppException):
    """
    Base class for all server-side errors (5xx status codes).
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type = "server_error" 