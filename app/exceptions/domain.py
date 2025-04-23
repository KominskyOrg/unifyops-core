"""
Domain-specific exception classes.

This module provides exceptions that are specific to the application's
domain logic, representing various error conditions that can occur in
business operations within the application.
"""

from typing import Any, Dict, List, Optional
from fastapi import status

from app.exceptions.base import ClientError, ServerError
from app.exceptions.http import ConflictError, NotFoundError


class ResourceAlreadyExistsError(ConflictError):
    """
    Exception for resource already exists errors.
    
    Raised when attempting to create a resource that already exists.
    """
    error_type = "resource_already_exists"
    
    def __init__(
        self,
        message: str = "Resource already exists",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        
        # Create more specific message if type and ID are provided
        if resource_type and resource_id:
            message = f"{resource_type} with ID '{resource_id}' already exists"
        elif resource_type:
            message = f"{resource_type} already exists"
        
        # Create details if not provided but we have resource info
        if not details and (resource_type or resource_id):
            details = [{
                "type": "resource_conflict",
                "msg": message
            }]
            
            if resource_type:
                details[0]["resource_type"] = resource_type
            if resource_id:
                details[0]["resource_id"] = resource_id
        
        super().__init__(message=message, details=details, **kwargs)


class ResourceNotFoundError(NotFoundError):
    """
    Exception for resource not found errors.
    
    Raised when a requested resource cannot be found.
    """
    error_type = "resource_not_found"
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        
        # Create more specific message if type and ID are provided
        if resource_type and resource_id:
            message = f"{resource_type} with ID '{resource_id}' not found"
        elif resource_type:
            message = f"{resource_type} not found"
        
        # Create details if not provided but we have resource info
        if not details and (resource_type or resource_id):
            details = [{
                "type": "resource_not_found",
                "msg": message
            }]
            
            if resource_type:
                details[0]["resource_type"] = resource_type
            if resource_id:
                details[0]["resource_id"] = resource_id
        
        super().__init__(message=message, details=details, **kwargs)


class ResourceStateError(ClientError):
    """
    Exception for resource state errors.
    
    Raised when a resource is in an invalid state for the requested operation.
    """
    status_code = status.HTTP_409_CONFLICT
    error_type = "resource_state_error"
    
    def __init__(
        self,
        message: str = "Resource is in an invalid state for this operation",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        current_state: Optional[str] = None,
        required_state: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.current_state = current_state
        self.required_state = required_state
        
        # Create more specific message if states are provided
        if current_state and required_state:
            if resource_type and resource_id:
                message = f"{resource_type} '{resource_id}' is in state '{current_state}' but '{required_state}' is required"
            elif resource_type:
                message = f"{resource_type} is in state '{current_state}' but '{required_state}' is required"
            else:
                message = f"Resource is in state '{current_state}' but '{required_state}' is required"
        
        # Create details if not provided but we have resource info
        if not details:
            details = [{
                "type": "invalid_state",
                "msg": message
            }]
            
            if resource_type:
                details[0]["resource_type"] = resource_type
            if resource_id:
                details[0]["resource_id"] = resource_id
            if current_state:
                details[0]["current_state"] = current_state
            if required_state:
                details[0]["required_state"] = required_state
        
        super().__init__(message=message, details=details, **kwargs)


class DependencyError(ClientError):
    """
    Exception for dependency errors.
    
    Raised when an operation fails due to a dependency issue.
    """
    status_code = status.HTTP_409_CONFLICT
    error_type = "dependency_error"
    
    def __init__(
        self,
        message: str = "Operation failed due to a dependency issue",
        dependency_type: Optional[str] = None,
        dependency_id: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.dependency_type = dependency_type
        self.dependency_id = dependency_id
        self.operation = operation
        
        # Create more specific message if dependency info is provided
        if dependency_type and dependency_id and operation:
            message = f"Cannot {operation} because of dependency on {dependency_type} '{dependency_id}'"
        elif dependency_type and operation:
            message = f"Cannot {operation} because of dependency on {dependency_type}"
        
        # Create details if not provided but we have dependency info
        if not details and (dependency_type or dependency_id or operation):
            details = [{
                "type": "dependency_error",
                "msg": message
            }]
            
            if dependency_type:
                details[0]["dependency_type"] = dependency_type
            if dependency_id:
                details[0]["dependency_id"] = dependency_id
            if operation:
                details[0]["operation"] = operation
        
        super().__init__(message=message, details=details, **kwargs)


class BusinessRuleViolationError(ClientError):
    """
    Exception for business rule violation errors.
    
    Raised when an operation would violate a business rule.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_type = "business_rule_violation"
    
    def __init__(
        self,
        message: str = "Operation would violate a business rule",
        rule_name: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.rule_name = rule_name
        
        # Create more specific message if rule name is provided
        if rule_name:
            message = f"Operation would violate business rule: {rule_name}"
        
        # Create details if not provided but we have rule info
        if not details and rule_name:
            details = [{
                "type": "business_rule_violation",
                "msg": message,
                "rule": rule_name
            }]
        
        super().__init__(message=message, details=details, **kwargs)


class TerraformResourceError(ClientError):
    """
    Exception for Terraform resource errors.
    
    Raised when an operation on a Terraform resource fails.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_type = "terraform_resource_error"
    
    def __init__(
        self,
        message: str = "Terraform resource operation failed",
        resource_type: Optional[str] = None,
        resource_name: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.operation = operation
        
        # Create more specific message if resource info is provided
        if resource_type and resource_name and operation:
            message = f"Terraform {operation} operation failed for {resource_type} '{resource_name}'"
        elif resource_type and operation:
            message = f"Terraform {operation} operation failed for {resource_type}"
        
        # Create details if not provided but we have resource info
        if not details and (resource_type or resource_name or operation):
            details = [{
                "type": "terraform_resource_error",
                "msg": message
            }]
            
            if resource_type:
                details[0]["resource_type"] = resource_type
            if resource_name:
                details[0]["resource_name"] = resource_name
            if operation:
                details[0]["operation"] = operation
        
        super().__init__(message=message, details=details, **kwargs) 