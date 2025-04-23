"""
HTTP exception classes corresponding to standard HTTP status codes.

This module provides exception classes for common HTTP error status codes,
which can be used throughout the application to provide consistent error
handling and responses for different HTTP error scenarios.
"""

from typing import Dict, List, Optional, Any
from fastapi import status

from app.exceptions.base import ClientError, ServerError


# 4xx Client Errors
class BadRequestError(ClientError):
    """
    400 Bad Request error.
    
    Raised when the server cannot process the request due to a client error,
    such as malformed request syntax, invalid request framing, or deceptive
    request routing.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_type = "bad_request"

    def __init__(
        self, 
        message: str = "Bad request", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class UnauthorizedError(ClientError):
    """
    401 Unauthorized error.
    
    Raised when authentication is required but has failed or not been provided.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    error_type = "unauthorized"

    def __init__(
        self, 
        message: str = "Authentication required", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class ForbiddenError(ClientError):
    """
    403 Forbidden error.
    
    Raised when the server understood the request but refuses to authorize it
    due to insufficient permissions.
    """
    status_code = status.HTTP_403_FORBIDDEN
    error_type = "forbidden"

    def __init__(
        self, 
        message: str = "Permission denied", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class NotFoundError(ClientError):
    """
    404 Not Found error.
    
    Raised when the requested resource could not be found on the server.
    """
    status_code = status.HTTP_404_NOT_FOUND
    error_type = "not_found"

    def __init__(
        self, 
        message: str = "Resource not found", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class MethodNotAllowedError(ClientError):
    """
    405 Method Not Allowed error.
    
    Raised when the request method is known but not supported by the target resource.
    """
    status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    error_type = "method_not_allowed"

    def __init__(
        self, 
        message: str = "Method not allowed", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class NotAcceptableError(ClientError):
    """
    406 Not Acceptable error.
    
    Raised when the server cannot produce a response matching the list of
    acceptable values defined in the request's proactive content negotiation headers.
    """
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    error_type = "not_acceptable"

    def __init__(
        self, 
        message: str = "Not acceptable", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class ConflictError(ClientError):
    """
    409 Conflict error.
    
    Raised when the request conflicts with the current state of the server,
    such as when trying to create a resource that already exists.
    """
    status_code = status.HTTP_409_CONFLICT
    error_type = "conflict"

    def __init__(
        self, 
        message: str = "Resource conflict", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class GoneError(ClientError):
    """
    410 Gone error.
    
    Raised when the requested resource is no longer available at the server
    and no forwarding address is known.
    """
    status_code = status.HTTP_410_GONE
    error_type = "gone"

    def __init__(
        self, 
        message: str = "Resource is no longer available", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class UnprocessableEntityError(ClientError):
    """
    422 Unprocessable Entity error.
    
    Raised when the server understands the content type but the request
    entity cannot be processed due to semantic errors.
    """
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_type = "unprocessable_entity"

    def __init__(
        self, 
        message: str = "Unable to process entity", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class TooManyRequestsError(ClientError):
    """
    429 Too Many Requests error.
    
    Raised when the user has sent too many requests in a given amount of time
    (rate limiting).
    """
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_type = "too_many_requests"

    def __init__(
        self, 
        message: str = "Too many requests", 
        retry_after: Optional[int] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.retry_after = retry_after
        if retry_after:
            details = details or []
            details.append({
                "loc": ["header", "Retry-After"],
                "msg": f"Retry after {retry_after} seconds",
                "type": "rate_limit"
            })
        super().__init__(message=message, details=details, **kwargs)


# 5xx Server Errors
class InternalServerError(ServerError):
    """
    500 Internal Server Error.
    
    Raised when the server encountered an unexpected condition that
    prevented it from fulfilling the request.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type = "internal_server_error"

    def __init__(
        self, 
        message: str = "Internal server error", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class NotImplementedError(ServerError):
    """
    501 Not Implemented error.
    
    Raised when the server does not support the functionality required
    to fulfill the request.
    """
    status_code = status.HTTP_501_NOT_IMPLEMENTED
    error_type = "not_implemented"

    def __init__(
        self, 
        message: str = "Not implemented", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class BadGatewayError(ServerError):
    """
    502 Bad Gateway error.
    
    Raised when the server, while acting as a gateway or proxy, received an
    invalid response from the upstream server.
    """
    status_code = status.HTTP_502_BAD_GATEWAY
    error_type = "bad_gateway"

    def __init__(
        self, 
        message: str = "Bad gateway", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)


class ServiceUnavailableError(ServerError):
    """
    503 Service Unavailable error.
    
    Raised when the server is currently unable to handle the request due to
    temporary overloading or maintenance of the server.
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_type = "service_unavailable"

    def __init__(
        self, 
        message: str = "Service unavailable", 
        retry_after: Optional[int] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.retry_after = retry_after
        if retry_after:
            details = details or []
            details.append({
                "loc": ["header", "Retry-After"],
                "msg": f"Retry after {retry_after} seconds",
                "type": "service_unavailable"
            })
        super().__init__(message=message, details=details, **kwargs)


class GatewayTimeoutError(ServerError):
    """
    504 Gateway Timeout error.
    
    Raised when the server, while acting as a gateway or proxy, did not
    receive a timely response from the upstream server.
    """
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    error_type = "gateway_timeout"

    def __init__(
        self, 
        message: str = "Gateway timeout", 
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs) 