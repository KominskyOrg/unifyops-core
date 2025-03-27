from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
import traceback
import uuid

from app.core.logging import logger


class ErrorDetail(BaseModel):
    """Structure for error details"""

    loc: Optional[List[str]] = None
    msg: str
    type: str


class ErrorResponse(BaseModel):
    """Standard error response format"""

    status_code: int
    error_id: str = ""
    message: str
    details: Optional[List[ErrorDetail]] = None


class AppException(Exception):
    """
    Base exception class for application-specific exceptions
    with standardized error responses
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type = "server_error"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: Optional[int] = None,
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.details = details
        self.error_id = str(uuid.uuid4())
        super().__init__(self.message)


class BadRequestError(AppException):
    """400 Bad Request error"""

    status_code = status.HTTP_400_BAD_REQUEST
    error_type = "bad_request"

    def __init__(
        self, message: str = "Bad request", details: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(message=message, details=details)


class UnauthorizedError(AppException):
    """401 Unauthorized error"""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_type = "unauthorized"

    def __init__(
        self, message: str = "Unauthorized", details: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(message=message, details=details)


class ForbiddenError(AppException):
    """403 Forbidden error"""

    status_code = status.HTTP_403_FORBIDDEN
    error_type = "forbidden"

    def __init__(self, message: str = "Forbidden", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, details=details)


class NotFoundError(AppException):
    """404 Not Found error"""

    status_code = status.HTTP_404_NOT_FOUND
    error_type = "not_found"

    def __init__(
        self, message: str = "Resource not found", details: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(message=message, details=details)


class ConflictError(AppException):
    """409 Conflict error"""

    status_code = status.HTTP_409_CONFLICT
    error_type = "conflict"

    def __init__(
        self, message: str = "Resource conflict", details: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(message=message, details=details)


class TerraformError(AppException):
    """Error during Terraform operations"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type = "terraform_error"

    def __init__(
        self,
        message: str = "Terraform operation failed",
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message=message, details=details)


class AsyncTaskError(AppException):
    """Error during asynchronous task execution"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type = "async_task_error"

    def __init__(
        self,
        message: str = "Async task execution failed",
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message=message, details=details)


# Exception handlers
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler for application-specific exceptions"""
    # Log the exception
    logger.error(
        f"{exc.error_type}: {exc.message}",
        exception=exc,
        path=request.url.path,
        method=request.method,
        error_id=exc.error_id,
        status_code=exc.status_code,
    )

    # Convert details to ErrorDetail objects if provided
    details = None
    if exc.details:
        details = [
            ErrorDetail(
                loc=detail.get("loc"),
                msg=detail.get("msg", ""),
                type=detail.get("type", exc.error_type),
            )
            for detail in exc.details
        ]

    # Return standardized error response
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            status_code=exc.status_code, error_id=exc.error_id, message=exc.message, details=details
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler for FastAPI HTTPException"""
    error_id = str(uuid.uuid4())

    # Log the exception
    logger.error(
        f"HTTP {exc.status_code}: {exc.detail}",
        path=request.url.path,
        method=request.method,
        error_id=error_id,
        status_code=exc.status_code,
    )

    # Return standardized error response
    return JSONResponse(
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
        content=ErrorResponse(
            status_code=exc.status_code, error_id=error_id, message=str(exc.detail)
        ).model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handler for validation errors.
    """
    error_id = str(uuid.uuid4())

    # Create a readable error message for logging
    error_details = []
    for error in exc.errors():
        error_details.append(f"{'.'.join(str(loc) for loc in error['loc'])}: {error['msg']}")

    readable_errors = ", ".join(error_details)

    # Log the validation error with complete details
    logger.error(
        f"Validation error: {readable_errors}",
        path=request.url.path,
        method=request.method,
        error_id=error_id,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        # Convert validation errors to a safe format for JSON
        errors=[
            {
                "loc": [str(loc) for loc in error["loc"]],
                "msg": str(error["msg"]),
                "type": str(error["type"]),
            }
            for error in exc.errors()
        ],
    )

    # Return a structured response
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": f"Validation error: {readable_errors}",
            "error_id": error_id,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "errors": [
                {
                    "loc": [str(loc) for loc in error["loc"]],
                    "msg": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors()
            ],
            "details": None,
        },
    )


async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unexpected exceptions"""
    error_id = str(uuid.uuid4())

    # Log the exception with traceback
    logger.critical(
        "Unhandled exception",
        exception=exc,
        traceback=traceback.format_exc(),
        path=request.url.path,
        method=request.method,
        error_id=error_id,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    # Return standardized error response
    # Note: We don't expose internal error details in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_id=error_id,
            message="An unexpected error occurred",
        ).model_dump(),
    )
