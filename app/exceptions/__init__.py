"""
UnifyOps Exceptions System
=========================

A comprehensive exceptions system for FastAPI applications that provides:
- Standardized error responses
- Consistent error handling patterns
- Structured error logging integration
- Detailed error tracking with unique IDs
- Domain-specific exception hierarchies
- Exception handlers for FastAPI

Usage Examples
-------------

Basic exception raising:
```python
from app.exceptions import NotFoundError

# Raise a standard exception
raise NotFoundError(message="User not found", details=[{"loc": ["user_id"], "msg": "User with ID 123 not found"}])
```

Raising domain-specific exceptions:
```python
from app.exceptions import DataValidationError

# Raise a validation error with details
raise DataValidationError(
    message="Invalid data format",
    details=[
        {"loc": ["data", "email"], "msg": "Invalid email format"},
        {"loc": ["data", "age"], "msg": "Must be greater than 0"}
    ]
)
```

Extending with custom exceptions:
```python
from app.exceptions import AppException
from fastapi import status

class CustomServiceError(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_type = "service_unavailable"
    
    def __init__(self, service_name, *args, **kwargs):
        message = f"Service {service_name} is unavailable"
        super().__init__(message=message, *args, **kwargs)
"""

# Import base exception classes
from app.exceptions.base import (
    AppException,
    ErrorDetail,
    ErrorResponse,
)

# Import HTTP exceptions
from app.exceptions.http import (
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ConflictError,
    UnprocessableEntityError,
    TooManyRequestsError,
    InternalServerError,
    ServiceUnavailableError,
)

# Import validation exceptions
from app.exceptions.validation import (
    DataValidationError,
    SchemaValidationError,
    ConstraintViolationError,
)

# Import domain exceptions
from app.exceptions.domain import (
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    ResourceStateError,
    DependencyError,
)

# Import operational exceptions
from app.exceptions.operational import (
    TimeoutError,
    ConnectionError,
    ThrottlingError,
    ExternalServiceError,
    TerraformError,
    AsyncTaskError,
)

# Import database exceptions
from app.exceptions.database import (
    DatabaseError,
    QueryError,
    TransactionError,
    MigrationError,
    IntegrityError,
)

# Import security exceptions
from app.exceptions.security import (
    AuthenticationError,
    AuthorizationError,
    PermissionDeniedError,
    TokenExpiredError,
    TokenInvalidError,
)

# Import handlers for FastAPI integration
from app.exceptions.handlers import (
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    internal_exception_handler,
    register_exception_handlers,
)

# Import utility functions
from app.exceptions.utils import (
    format_exception,
    error_context,
    error_boundary,
    capture_exception,
)

# Re-export these for convenient access
__all__ = [
    # Base exceptions
    "AppException",
    "ErrorDetail",
    "ErrorResponse",
    
    # HTTP exceptions
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "UnprocessableEntityError",
    "TooManyRequestsError", 
    "InternalServerError",
    "ServiceUnavailableError",
    
    # Validation exceptions
    "DataValidationError",
    "SchemaValidationError",
    "ConstraintViolationError",
    
    # Domain exceptions
    "ResourceAlreadyExistsError", 
    "ResourceNotFoundError",
    "ResourceStateError",
    "DependencyError",
    
    # Operational exceptions
    "TimeoutError",
    "ConnectionError", 
    "ThrottlingError",
    "ExternalServiceError",
    "TerraformError",
    "AsyncTaskError",
    
    # Database exceptions
    "DatabaseError",
    "QueryError",
    "TransactionError", 
    "MigrationError",
    "IntegrityError",
    
    # Security exceptions
    "AuthenticationError",
    "AuthorizationError", 
    "PermissionDeniedError",
    "TokenExpiredError",
    "TokenInvalidError",
    
    # Exception handlers
    "app_exception_handler",
    "http_exception_handler",
    "validation_exception_handler",
    "internal_exception_handler",
    "register_exception_handlers",
    
    # Utilities
    "format_exception",
    "error_context",
    "error_boundary",
    "capture_exception",
] 