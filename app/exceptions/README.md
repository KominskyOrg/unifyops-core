# UnifyOps Exception System

A comprehensive, standards-compliant exception system for UnifyOps applications.

## Key Features

- **Standardized Error Responses**: Consistent JSON error response format across the application
- **Structured Logging Integration**: Automatic error logging with context and correlation IDs
- **Hierarchical Exception Types**: Domain-specific exceptions organized in a logical hierarchy
- **Detailed Error Tracking**: Unique error IDs for every exception for improved traceability
- **Utility Functions**: Helpful tools for exception handling, including decorators and context managers
- **FastAPI Integration**: Pre-configured exception handlers for FastAPI

## Exception Hierarchy

```
AppException (base)
├── ClientError
│   ├── BadRequestError
│   ├── UnauthorizedError
│   ├── ForbiddenError
│   ├── NotFoundError
│   ├── ConflictError
│   ├── UnprocessableEntityError
│   └── ...
├── ServerError
│   ├── InternalServerError
│   ├── ServiceUnavailableError
│   ├── TimeoutError
│   └── ...
└── Domain-specific exceptions
    ├── ValidationErrors
    ├── DatabaseErrors
    ├── SecurityErrors
    └── ...
```

## Standard Error Response Format

All exceptions result in a standardized JSON response with the following structure:

```json
{
  "status_code": 404,
  "error_id": "3f7e5d1c-8c2b-4d6a-9f1c-2e5a7c8b9d0e",
  "message": "User with ID '123' not found",
  "error_type": "resource_not_found",
  "details": [
    {
      "loc": ["path", "user_id"],
      "msg": "User with ID '123' not found",
      "type": "resource_not_found"
    }
  ],
  "timestamp": "2023-04-01T12:34:56.789Z"
}
```

## How to Use

### 1. Raising Exceptions

Raise exceptions with clear, actionable messages and appropriate status codes:

```python
from app.exceptions import NotFoundError, BadRequestError

# Simple error
raise BadRequestError(message="Invalid input format")

# With details
raise NotFoundError(
    message="User not found",
    details=[
        {
            "loc": ["path", "user_id"],
            "msg": "User with ID '123' not found",
            "type": "not_found"
        }
    ]
)

# Domain-specific errors (provide contextual information)
from app.exceptions import ResourceNotFoundError

raise ResourceNotFoundError(
    resource_type="User",
    resource_id="123"
)  # Auto-generates "User with ID '123' not found" message
```

### 2. Using Exception Handlers in FastAPI

Register all exception handlers in your FastAPI application:

```python
from fastapi import FastAPI
from app.exceptions.handlers import register_exception_handlers

app = FastAPI()

# Register all exception handlers
register_exception_handlers(app)
```

### 3. Using Error Context

Add contextual information to exceptions that occur within a block:

```python
from app.exceptions.utils import error_context

user_id = "123"
with error_context(user_id=user_id, operation="update_profile"):
    # Any exception raised here will have this context in logs
    user = get_user(user_id)
    update_user_profile(user, new_data)
```

### 4. Using Utility Decorators

Handle common error patterns with utility decorators:

```python
from app.exceptions.utils import handle_validation_errors, handle_database_errors

# Convert Pydantic validation errors to DataValidationError
@handle_validation_errors
def create_user(user_data: dict):
    return UserModel(**user_data)  # Validation errors converted automatically

# Convert database exceptions to appropriate app exceptions
@handle_database_errors
async def get_user(user_id: str):
    return await db.users.find_one({"_id": user_id})
```

### 5. Using Error Boundaries

Create error boundaries to recover from errors gracefully:

```python
from app.exceptions.utils import error_boundary

# Return empty list on error instead of crashing
@error_boundary(fallback_value=[])
def get_all_items():
    return fetch_items_from_database()
```

### 6. Converting Between Exception Types

Convert standard exceptions to application-specific exceptions:

```python
from app.exceptions.utils import convert_exception
from app.exceptions import BadRequestError

# Convert ValueError to BadRequestError
@convert_exception(ValueError, BadRequestError, "Invalid format")
def parse_config(config_str):
    return json.loads(config_str)
```

## Best Practices

1. **Be Specific**: Use the most specific exception type available for the error situation.

2. **Include Context**: Always provide enough context in error messages for developers to understand the issue.

3. **Secure Information**: Never include sensitive information in error messages that might be exposed to clients.

4. **Add Details**: Use the `details` parameter to provide structured error information when relevant.

5. **Log Extension**: Don't duplicate logging when raising exceptions - the exception handlers will log automatically.

6. **Use Domain Exceptions**: Prefer domain-specific exceptions (like `ResourceNotFoundError`) over generic ones (like `NotFoundError`) when applicable.

7. **Error Handling Strategy**: Define clear error handling strategies for different parts of your application.

## Exception Categories

### HTTP Exceptions (`app.exceptions.http`)

Standard exceptions corresponding to HTTP status codes.

### Validation Exceptions (`app.exceptions.validation`)

Exceptions related to data validation issues.

### Domain Exceptions (`app.exceptions.domain`)

Business-logic and domain-specific exceptions.

### Operational Exceptions (`app.exceptions.operational`)

Exceptions related to operational issues (timeouts, connections, etc.).

### Database Exceptions (`app.exceptions.database`)

Exceptions related to database operations.

### Security Exceptions (`app.exceptions.security`)

Exceptions related to authentication, authorization, and other security concerns.

## Extending the System

To add new exception types, simply extend the appropriate base class:

```python
from app.exceptions.base import ClientError
from fastapi import status

class PaymentFailedError(ClientError):
    """Exception raised when a payment operation fails."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    error_type = "payment_failed"

    def __init__(
        self,
        message: str = "Payment failed",
        payment_id: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.payment_id = payment_id
        self.reason = reason

        # Generate a more specific message if details are provided
        if payment_id and reason:
            message = f"Payment '{payment_id}' failed: {reason}"

        # Create details if not provided
        if not details and (payment_id or reason):
            details = [{
                "type": "payment_failed",
                "msg": message
            }]

            if payment_id:
                details[0]["payment_id"] = payment_id
            if reason:
                details[0]["reason"] = reason

        super().__init__(message=message, details=details, **kwargs)
```
