"""
Security exception classes.

This module provides exceptions for security-related errors that can 
occur during authentication, authorization, and other security operations.
"""

from typing import Any, Dict, List, Optional
from fastapi import status

from app.exceptions.base import ClientError
from app.exceptions.http import UnauthorizedError, ForbiddenError


class AuthenticationError(UnauthorizedError):
    """
    Exception for authentication errors.
    
    Raised when user authentication fails.
    """
    error_type = "authentication_error"
    
    def __init__(
        self,
        message: str = "Authentication failed",
        auth_type: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.auth_type = auth_type
        self.reason = reason
        
        # Create more specific message if auth details are provided
        if auth_type and reason:
            message = f"{auth_type} authentication failed: {reason}"
        elif auth_type:
            message = f"{auth_type} authentication failed"
        
        # Create details if not provided but we have auth info
        if not details and (auth_type or reason):
            details = [{
                "type": "authentication_error",
                "msg": message
            }]
            
            if auth_type:
                details[0]["auth_type"] = auth_type
            if reason:
                details[0]["reason"] = reason
        
        super().__init__(message=message, details=details, **kwargs)


class AuthorizationError(ForbiddenError):
    """
    Exception for authorization errors.
    
    Raised when a user is authenticated but not authorized to perform an action.
    """
    error_type = "authorization_error"
    
    def __init__(
        self,
        message: str = "Not authorized to perform this action",
        action: Optional[str] = None,
        resource: Optional[str] = None,
        required_role: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.action = action
        self.resource = resource
        self.required_role = required_role
        
        # Create more specific message if auth details are provided
        if action and resource and required_role:
            message = f"Not authorized to {action} {resource}. Requires role: {required_role}"
        elif action and resource:
            message = f"Not authorized to {action} {resource}"
        elif action:
            message = f"Not authorized to {action}"
        
        # Create details if not provided but we have auth info
        if not details and (action or resource or required_role):
            details = [{
                "type": "authorization_error",
                "msg": message
            }]
            
            if action:
                details[0]["action"] = action
            if resource:
                details[0]["resource"] = resource
            if required_role:
                details[0]["required_role"] = required_role
        
        super().__init__(message=message, details=details, **kwargs)


class PermissionDeniedError(ForbiddenError):
    """
    Exception for permission denied errors.
    
    Raised when a user does not have the required permissions.
    """
    error_type = "permission_denied"
    
    def __init__(
        self,
        message: str = "Permission denied",
        permission: Optional[str] = None,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.permission = permission
        self.resource = resource
        self.resource_id = resource_id
        
        # Create more specific message if permission details are provided
        if permission and resource and resource_id:
            message = f"Permission denied: {permission} on {resource} (ID: {resource_id})"
        elif permission and resource:
            message = f"Permission denied: {permission} on {resource}"
        elif permission:
            message = f"Permission denied: {permission}"
        
        # Create details if not provided but we have permission info
        if not details and (permission or resource or resource_id):
            details = [{
                "type": "permission_denied",
                "msg": message
            }]
            
            if permission:
                details[0]["permission"] = permission
            if resource:
                details[0]["resource"] = resource
            if resource_id:
                details[0]["resource_id"] = resource_id
        
        super().__init__(message=message, details=details, **kwargs)


class TokenExpiredError(UnauthorizedError):
    """
    Exception for token expired errors.
    
    Raised when an authentication token has expired.
    """
    error_type = "token_expired"
    
    def __init__(
        self,
        message: str = "Authentication token has expired",
        token_type: Optional[str] = None,
        expiry_time: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.token_type = token_type
        self.expiry_time = expiry_time
        
        # Create more specific message if token details are provided
        if token_type and expiry_time:
            message = f"{token_type} token expired at {expiry_time}"
        elif token_type:
            message = f"{token_type} token has expired"
        
        # Create details if not provided but we have token info
        if not details and (token_type or expiry_time):
            details = [{
                "type": "token_expired",
                "msg": message
            }]
            
            if token_type:
                details[0]["token_type"] = token_type
            if expiry_time:
                details[0]["expiry_time"] = expiry_time
        
        super().__init__(message=message, details=details, **kwargs)


class TokenInvalidError(UnauthorizedError):
    """
    Exception for invalid token errors.
    
    Raised when an authentication token is invalid.
    """
    error_type = "token_invalid"
    
    def __init__(
        self,
        message: str = "Authentication token is invalid",
        token_type: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.token_type = token_type
        self.reason = reason
        
        # Create more specific message if token details are provided
        if token_type and reason:
            message = f"{token_type} token is invalid: {reason}"
        elif token_type:
            message = f"{token_type} token is invalid"
        
        # Create details if not provided but we have token info
        if not details and (token_type or reason):
            details = [{
                "type": "token_invalid",
                "msg": message
            }]
            
            if token_type:
                details[0]["token_type"] = token_type
            if reason:
                details[0]["reason"] = reason
        
        super().__init__(message=message, details=details, **kwargs)


class RateLimitExceededError(ClientError):
    """
    Exception for rate limit exceeded errors.
    
    Raised when a user has exceeded the rate limit for a particular operation.
    """
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_type = "rate_limit_exceeded"
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        period: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.limit = limit
        self.period = period
        self.retry_after = retry_after
        
        # Create more specific message if rate limit details are provided
        if limit and period:
            message = f"Rate limit of {limit} requests per {period} exceeded"
            if retry_after:
                message += f". Try again in {retry_after} seconds"
        
        # Create details if not provided but we have rate limit info
        if not details and (limit or period or retry_after):
            details = [{
                "type": "rate_limit_exceeded",
                "msg": message
            }]
            
            if limit:
                details[0]["limit"] = limit
            if period:
                details[0]["period"] = period
            if retry_after:
                details[0]["retry_after"] = retry_after
        
        super().__init__(message=message, details=details, **kwargs)


class CSRFError(ClientError):
    """
    Exception for CSRF token validation errors.
    
    Raised when CSRF token validation fails.
    """
    status_code = status.HTTP_403_FORBIDDEN
    error_type = "csrf_error"
    
    def __init__(
        self,
        message: str = "CSRF token validation failed",
        reason: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.reason = reason
        
        # Create more specific message if reason is provided
        if reason:
            message = f"CSRF token validation failed: {reason}"
        
        # Create details if not provided but we have reason info
        if not details and reason:
            details = [{
                "type": "csrf_error",
                "msg": message,
                "reason": reason
            }]
        
        super().__init__(message=message, details=details, **kwargs)


class IPBlockedError(ClientError):
    """
    Exception for IP blocked errors.
    
    Raised when a request comes from a blocked IP address.
    """
    status_code = status.HTTP_403_FORBIDDEN
    error_type = "ip_blocked"
    
    def __init__(
        self,
        message: str = "Your IP address has been blocked",
        reason: Optional[str] = None,
        until: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.reason = reason
        self.until = until
        
        # Create more specific message if block details are provided
        if reason and until:
            message = f"Your IP address has been blocked: {reason}. Block expires: {until}"
        elif reason:
            message = f"Your IP address has been blocked: {reason}"
        elif until:
            message = f"Your IP address has been blocked until {until}"
        
        # Create details if not provided but we have block info
        if not details and (reason or until):
            details = [{
                "type": "ip_blocked",
                "msg": message
            }]
            
            if reason:
                details[0]["reason"] = reason
            if until:
                details[0]["until"] = until
        
        super().__init__(message=message, details=details, **kwargs) 