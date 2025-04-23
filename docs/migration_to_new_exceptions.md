# Migrating to the New Exceptions Package

This guide will help you migrate from the old `app.core.exceptions` module to the new comprehensive `app.exceptions` package.

## Overview

The new exceptions package provides:

- A more organized hierarchical structure of exceptions
- More specialized exception types for different scenarios
- Better integration with logging
- Utility functions for error handling
- Improved error response format
- Context tracking for exceptions

## Migration Progress

### Already Migrated Files

The following files have already been migrated to use the new exceptions package:

1. `app/main.py` - Using the new exception registration and error handling during startup
2. `app/routers/terraform.py` - Using domain-specific exceptions and error context
3. `app/routers/auth.py` - Using security-specific exceptions
4. `app/routers/environments.py` - Using resource and operational exceptions
5. `app/routers/terraform_templates.py` - Using resource and terraform exceptions
6. `app/db/init_db.py` - Using database-specific exceptions
7. `app/core/security.py` - Using security-specific exceptions (authentication, tokens, permissions)

### Files Still Needing Migration

Files that still need to be migrated include:

1. Any other service files containing exception handling
2. Any additional routers added to the application
3. Background task handlers
4. External service integrations

## Basic Migration Steps

### 1. Updating Imports

Replace:

```python
from app.core.exceptions import AppException, BadRequestError, NotFoundError
```

With:

```python
from app.exceptions import AppException, BadRequestError, NotFoundError
```

### 2. Replacing HTTPException with Domain-Specific Exceptions

Replace:

```python
from fastapi import HTTPException, status

# ...

if not item:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Item with ID {item_id} not found"
    )
```

With:

```python
from app.exceptions import ResourceNotFoundError

# ...

if not item:
    raise ResourceNotFoundError(
        resource_type="Item",
        resource_id=item_id
    )
```

### 3. Using Error Context

Add context to your error handling:

```python
from app.exceptions.utils import error_context

with error_context(user_id=user.id, operation="update_profile"):
    # Code that might raise exceptions
    update_user_profile(user, data)
```

### 4. Using Error Boundaries

Add error recovery mechanisms:

```python
from app.exceptions.utils import error_boundary

@error_boundary(fallback_value=[])
def get_items():
    # This function will return an empty list instead of raising an exception
    return fetch_items_from_database()
```

### 5. Converting Between Exception Types

```python
from app.exceptions.utils import convert_exception
from app.exceptions import BadRequestError

@convert_exception(ValueError, BadRequestError, "Invalid format")
def parse_config(config_str):
    return json.loads(config_str)
```

### 6. Registering Exception Handlers

Replace:

```python
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    internal_exception_handler,
)

# ...

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, internal_exception_handler)
```

With:

```python
from app.exceptions import register_exception_handlers

# ...

register_exception_handlers(app)
```

## Exception Type Mapping

Here's a mapping of old exception types to new ones:

| Old Exception        | New Exception                | Module                       |
| -------------------- | ---------------------------- | ---------------------------- |
| `AppException`       | `AppException`               | `app.exceptions.base`        |
| `BadRequestError`    | `BadRequestError`            | `app.exceptions.http`        |
| `UnauthorizedError`  | `UnauthorizedError`          | `app.exceptions.http`        |
| `ForbiddenError`     | `ForbiddenError`             | `app.exceptions.http`        |
| `NotFoundError`      | `NotFoundError`              | `app.exceptions.http`        |
| `ConflictError`      | `ConflictError`              | `app.exceptions.http`        |
| `TerraformError`     | `TerraformError`             | `app.exceptions.operational` |
| `AsyncTaskError`     | `AsyncTaskError`             | `app.exceptions.operational` |
| `HTTPException(404)` | `ResourceNotFoundError`      | `app.exceptions.domain`      |
| `HTTPException(401)` | `AuthenticationError`        | `app.exceptions.security`    |
| `HTTPException(403)` | `PermissionDeniedError`      | `app.exceptions.security`    |
| `HTTPException(409)` | `ResourceAlreadyExistsError` | `app.exceptions.domain`      |
| `HTTPException(500)` | `InternalServerError`        | `app.exceptions.http`        |

## New Domain-Specific Exceptions

The new package includes many domain-specific exceptions that you should use instead of generic ones:

### Database Exceptions

- `DatabaseError` - Base exception for database errors
- `ConnectionError` - Database connection failures
- `QueryError` - Database query errors
- `TransactionError` - Transaction-related errors
- `MigrationError` - Migration failures
- `IntegrityError` - Constraint violations
- `NoResultFoundError` - No results found

### Validation Exceptions

- `DataValidationError` - Data validation errors
- `SchemaValidationError` - Schema validation errors
- `ConstraintViolationError` - Business rule violations
- `InputValidationError` - User input validation errors
- `TypeConversionError` - Type conversion errors

### Security Exceptions

- `AuthenticationError` - Authentication failures
- `AuthorizationError` - Authorization failures
- `PermissionDeniedError` - Permission issues
- `TokenExpiredError` - Expired tokens
- `TokenInvalidError` - Invalid tokens
- `RateLimitExceededError` - Rate limit exceeded
- `CSRFError` - CSRF validation failures
- `IPBlockedError` - Blocked IP addresses

### Domain Exceptions

- `ResourceAlreadyExistsError` - Resource already exists
- `ResourceNotFoundError` - Resource not found
- `ResourceStateError` - Invalid resource state
- `DependencyError` - Dependency issues
- `BusinessRuleViolationError` - Business rule violations
- `TerraformResourceError` - Terraform resource operations

### Operational Exceptions

- `TimeoutError` - Operation timeouts
- `ConnectionError` - Connection failures
- `ThrottlingError` - Service throttling
- `ExternalServiceError` - External service failures
- `TerraformError` - Terraform operations
- `AsyncTaskError` - Async task failures
- `ConfigurationError` - Configuration issues

## Example: Complete Migration

Before:

```python
from fastapi import APIRouter, HTTPException, status
from app.core.exceptions import TerraformError

@router.get("/resource/{resource_id}")
async def get_resource(resource_id: str):
    try:
        # Fetch resource
        resource = fetch_resource(resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resource {resource_id} not found"
            )
        return resource
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching resource: {str(e)}"
        )
```

After:

```python
from fastapi import APIRouter
from app.exceptions import ResourceNotFoundError, TerraformError
from app.exceptions.utils import error_context

@router.get("/resource/{resource_id}")
async def get_resource(resource_id: str):
    with error_context(resource_id=resource_id, operation="get_resource"):
        # Fetch resource
        resource = fetch_resource(resource_id)
        if not resource:
            raise ResourceNotFoundError(
                resource_type="Resource",
                resource_id=resource_id
            )
        return resource
```

## Real-World Example from Our Codebase

Before (in the original `app/core/security.py`):

```python
def verify_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")

        if user_id is None or username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # ... rest of function

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

After (migrated to new exceptions):

```python
def verify_token(token: str) -> TokenData:
    try:
        with error_context(operation="verify_token", token_type="access"):
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            username: str = payload.get("username")

            if user_id is None or username is None:
                raise TokenInvalidError(
                    message="Invalid token data: missing required fields",
                    token_type="access",
                    reason="missing_fields"
                )

            # ... rest of function

    except JWTError as e:
        if "expired" in str(e).lower():
            raise TokenExpiredError(
                message="Token has expired",
                token_type="access"
            )
        else:
            raise AuthenticationError(
                message="Invalid authentication credentials",
                auth_type="bearer",
                reason="invalid_token",
                headers={"WWW-Authenticate": "Bearer"}
            )
```

## Best Practices

1. **Be Specific**: Use the most specific exception type available for the error situation
2. **Add Context**: Always provide enough information with your exceptions
3. **Secure Information**: Don't include sensitive information in error messages
4. **Use Domain Exceptions**: Prefer domain-specific exceptions over generic HTTP exceptions
5. **Leverage Utils**: Use the utility functions like `error_context` and `error_boundary`
6. **Handle Errors Early**: Handle expected errors as early as possible
7. **Consistent Patterns**: Follow consistent patterns for error handling throughout the codebase

## Testing and Verification

After migrating to the new exceptions package, it's important to verify that everything is working as expected. Here are some verification steps:

### 1. Exception Handler Registration

Verify that exception handlers are properly registered:

```python
# In your FastAPI app startup logs or via debugging
assert hasattr(app, "exception_handlers")
assert app.exception_handlers.get(AppException) is not None
```

### 2. End-to-End API Testing

Test your API endpoints to ensure they return the expected error responses:

1. **404 Not Found Test**:

   - Access a non-existent resource endpoint
   - Verify the response contains `resource_type`, `resource_id`, and proper error message
   - Check HTTP status code is 404

2. **Validation Error Test**:

   - Submit invalid data to an endpoint
   - Verify the response contains validation details with proper field locations
   - Check HTTP status code is 422

3. **Authentication Error Test**:
   - Access a protected endpoint without a token
   - Verify the response indicates authentication failure
   - Check HTTP status code is 401

### 3. Error Logging Verification

Check your logs to ensure exceptions are being properly logged:

1. Verify that exceptions include:

   - Unique error IDs
   - Context information (from error_context)
   - Stack traces for unexpected errors
   - Structured metadata

2. Check log format:
   ```
   [ERROR] AuthenticationError: Invalid authentication credentials | error_id=abc123 | auth_type=bearer | reason=invalid_token
   ```

### 4. Error Boundary Testing

Test error boundaries to ensure they're catching exceptions and providing fallback values:

```python
@error_boundary(fallback_value={"status": "error"})
def potentially_failing_function():
    # Deliberately cause an error
    raise ValueError("Test error")

result = potentially_failing_function()
assert result == {"status": "error"}
```

### 5. Monitoring and Alerting

Update your monitoring systems to recognize and alert on the new exception types:

1. Configure alerts for critical exceptions like:

   - `DatabaseError`
   - `AuthenticationError` (multiple occurrences)
   - `TerraformError`
   - `ConfigurationError`

2. Set up dashboard panels showing exception frequencies by type

### 6. Documentation

Update your API documentation to reflect the new error responses:

1. Ensure the API docs (Swagger/OpenAPI) show the correct error responses
2. Update any internal documentation about error handling patterns

By following these verification steps, you can ensure your migration to the new exceptions package is complete and working correctly.

For more detailed information about the new exceptions package, consult the package README at `app/exceptions/README.md`.
