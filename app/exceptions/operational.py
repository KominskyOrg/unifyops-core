"""
Operational exception classes.

This module provides exceptions for operational issues that can occur
during application execution, such as timeouts, connection issues,
external service failures, and infrastructure-related errors.
"""

from typing import Any, Dict, List, Optional
from fastapi import status

from app.exceptions.base import ServerError


class TimeoutError(ServerError):
    """
    Exception for timeout errors.
    
    Raised when an operation times out.
    """
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    error_type = "timeout_error"
    
    def __init__(
        self,
        message: str = "Operation timed out",
        operation: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        
        # Create more specific message if operation and timeout are provided
        if operation and timeout_seconds:
            message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        elif operation:
            message = f"Operation '{operation}' timed out"
        
        # Create details if not provided but we have operation info
        if not details and (operation or timeout_seconds):
            details = [{
                "type": "timeout",
                "msg": message
            }]
            
            if operation:
                details[0]["operation"] = operation
            if timeout_seconds:
                details[0]["timeout_seconds"] = timeout_seconds
        
        super().__init__(message=message, details=details, **kwargs)


class ConnectionError(ServerError):
    """
    Exception for connection errors.
    
    Raised when a connection to an external resource fails.
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_type = "connection_error"
    
    def __init__(
        self,
        message: str = "Connection failed",
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.service = service
        self.endpoint = endpoint
        self.retry_after = retry_after
        
        # Create more specific message if service and endpoint are provided
        if service and endpoint:
            message = f"Connection to {service} at {endpoint} failed"
        elif service:
            message = f"Connection to {service} failed"
        
        # Create details if not provided but we have connection info
        if not details and (service or endpoint):
            details = [{
                "type": "connection_failed",
                "msg": message
            }]
            
            if service:
                details[0]["service"] = service
            if endpoint:
                details[0]["endpoint"] = endpoint
            if retry_after:
                details[0]["retry_after"] = retry_after
        
        super().__init__(message=message, details=details, **kwargs)


class ThrottlingError(ServerError):
    """
    Exception for throttling errors.
    
    Raised when an operation is throttled due to rate limiting.
    """
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_type = "throttling_error"
    
    def __init__(
        self,
        message: str = "Operation throttled",
        service: Optional[str] = None,
        quota: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.service = service
        self.quota = quota
        self.retry_after = retry_after
        
        # Create more specific message if service and quota are provided
        if service and quota:
            message = f"Operation throttled by {service} due to quota limit: {quota}"
        elif service:
            message = f"Operation throttled by {service}"
        
        # Create details if not provided but we have throttling info
        if not details and (service or quota or retry_after):
            details = [{
                "type": "throttled",
                "msg": message
            }]
            
            if service:
                details[0]["service"] = service
            if quota:
                details[0]["quota"] = quota
            if retry_after:
                details[0]["retry_after"] = retry_after
        
        super().__init__(message=message, details=details, **kwargs)


class ExternalServiceError(ServerError):
    """
    Exception for external service errors.
    
    Raised when an external service returns an error.
    """
    status_code = status.HTTP_502_BAD_GATEWAY
    error_type = "external_service_error"
    
    def __init__(
        self,
        message: str = "External service error",
        service: Optional[str] = None,
        status_code: Optional[int] = None,
        error_response: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.service = service
        self.external_status_code = status_code
        self.error_response = error_response
        self.operation = operation
        
        # Create more specific message if service and operation are provided
        if service and operation and status_code:
            message = f"External service {service} returned error {status_code} during {operation}"
        elif service and operation:
            message = f"External service {service} failed during {operation}"
        elif service:
            message = f"External service {service} error"
        
        # Create details if not provided but we have external service info
        if not details and (service or status_code or operation):
            details = [{
                "type": "external_service_error",
                "msg": message
            }]
            
            if service:
                details[0]["service"] = service
            if status_code:
                details[0]["status_code"] = status_code
            if operation:
                details[0]["operation"] = operation
            
            # Include a safe subset of the error response if available
            if error_response and isinstance(error_response, dict):
                # Extract only safe keys to avoid including sensitive data
                safe_keys = ["error", "message", "code", "status", "reason"]
                safe_response = {k: error_response[k] for k in safe_keys if k in error_response}
                
                if safe_response:
                    details[0]["error_response"] = safe_response
        
        super().__init__(message=message, details=details, **kwargs)


class TerraformError(ServerError):
    """
    Exception for Terraform operation errors.
    
    Raised when a Terraform operation fails.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type = "terraform_error"
    
    def __init__(
        self,
        message: str = "Terraform operation failed",
        operation: Optional[str] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.operation = operation
        self.exit_code = exit_code
        self.stderr = stderr
        
        # Create more specific message if operation and exit_code are provided
        if operation and exit_code:
            message = f"Terraform {operation} failed with exit code {exit_code}"
        elif operation:
            message = f"Terraform {operation} failed"
        
        # Create details if not provided but we have terraform info
        if not details and (operation or exit_code or stderr):
            details = [{
                "type": "terraform_error",
                "msg": message
            }]
            
            if operation:
                details[0]["operation"] = operation
            if exit_code:
                details[0]["exit_code"] = exit_code
            
            # Include a truncated version of stderr if available
            if stderr:
                # Truncate stderr to avoid very large error messages
                max_stderr_length = 500
                truncated_stderr = stderr[:max_stderr_length]
                if len(stderr) > max_stderr_length:
                    truncated_stderr += "... (truncated)"
                
                details[0]["stderr"] = truncated_stderr
        
        super().__init__(message=message, details=details, **kwargs)


class AsyncTaskError(ServerError):
    """
    Exception for asynchronous task errors.
    
    Raised when an asynchronous task fails.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type = "async_task_error"
    
    def __init__(
        self,
        message: str = "Asynchronous task failed",
        task_id: Optional[str] = None,
        task_type: Optional[str] = None,
        task_status: Optional[str] = None,
        exception: Optional[Exception] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.task_status = task_status
        self.original_exception = exception
        
        # Create more specific message if task info is provided
        if task_type and task_id:
            message = f"Asynchronous task {task_type} (ID: {task_id}) failed"
        elif task_type:
            message = f"Asynchronous task {task_type} failed"
        
        if exception:
            message = f"{message}: {str(exception)}"
        
        # Create details if not provided but we have task info
        if not details and (task_id or task_type or task_status or exception):
            details = [{
                "type": "async_task_error",
                "msg": message
            }]
            
            if task_id:
                details[0]["task_id"] = task_id
            if task_type:
                details[0]["task_type"] = task_type
            if task_status:
                details[0]["task_status"] = task_status
            
            # Include information about the original exception if available
            if exception:
                details[0]["exception_type"] = exception.__class__.__name__
                details[0]["exception_message"] = str(exception)
        
        super().__init__(message=message, details=details, **kwargs)


class ConfigurationError(ServerError):
    """
    Exception for configuration errors.
    
    Raised when there is an error in the application configuration.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type = "configuration_error"
    
    def __init__(
        self,
        message: str = "Configuration error",
        parameter: Optional[str] = None,
        expected: Optional[str] = None,
        actual: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.parameter = parameter
        self.expected = expected
        self.actual = actual
        
        # Create more specific message if parameter info is provided
        if parameter and expected and actual:
            message = f"Configuration error: {parameter} is '{actual}' but should be '{expected}'"
        elif parameter and expected:
            message = f"Configuration error: {parameter} should be '{expected}'"
        elif parameter:
            message = f"Configuration error in parameter '{parameter}'"
        
        # Create details if not provided but we have configuration info
        if not details and (parameter or expected or actual):
            details = [{
                "type": "configuration_error",
                "msg": message
            }]
            
            if parameter:
                details[0]["parameter"] = parameter
            if expected:
                details[0]["expected"] = expected
            if actual:
                # Only include actual value if it's not potentially sensitive
                # This is a simplistic check - in practice, you would check against a list of sensitive parameters
                sensitive_params = ["password", "secret", "key", "token", "credential"]
                is_sensitive = any(term in parameter.lower() if parameter else False for term in sensitive_params)
                
                if not is_sensitive:
                    details[0]["actual"] = actual
        
        super().__init__(message=message, details=details, **kwargs) 