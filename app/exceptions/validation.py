"""
Validation exception classes for data validation errors.

This module provides exceptions for various types of validation errors
that can occur during data processing, schema validation, and constraint
checking throughout the application.
"""

from typing import Any, Dict, List, Optional, Sequence, Union
from fastapi import status
from pydantic import ValidationError as PydanticValidationError

from app.exceptions.base import ClientError
from app.exceptions.http import UnprocessableEntityError


class DataValidationError(UnprocessableEntityError):
    """
    Exception for data validation errors.
    
    Raised when incoming data fails validation but is syntactically correct.
    This is typically used for application-level business validation rules.
    """
    error_type = "data_validation_error"
    
    def __init__(
        self,
        message: str = "Data validation failed",
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message=message, details=details, **kwargs)
    
    @classmethod
    def from_validation_error(cls, error: PydanticValidationError, message: Optional[str] = None) -> 'DataValidationError':
        """
        Create a DataValidationError from a Pydantic ValidationError.
        
        Args:
            error: The Pydantic ValidationError
            message: Optional custom message to use
            
        Returns:
            A new DataValidationError instance with details from the ValidationError
        """
        # Extract details from the validation error
        details = []
        for err in error.errors():
            details.append({
                "loc": [str(loc) for loc in err["loc"]],
                "msg": err["msg"],
                "type": err["type"]
            })
        
        # Use provided message or generate one
        error_message = message or "Data validation failed"
        if not message and len(details) == 1:
            # If a single error and no custom message, use the error message
            error_message = f"Validation error: {details[0]['msg']}"
        
        return cls(message=error_message, details=details)


class SchemaValidationError(DataValidationError):
    """
    Exception for schema validation errors.
    
    Raised when data does not conform to an expected schema or data model.
    """
    error_type = "schema_validation_error"
    
    def __init__(
        self,
        message: str = "Schema validation failed",
        schema_name: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.schema_name = schema_name
        
        # Add schema information to details if provided
        if schema_name and details:
            for detail in details:
                if "schema" not in detail:
                    detail["schema"] = schema_name
        
        super().__init__(message=message, details=details, **kwargs)


class ConstraintViolationError(DataValidationError):
    """
    Exception for constraint violation errors.
    
    Raised when a business rule or data constraint is violated. This is
    typically used for application-level constraints that aren't enforced
    by the data model or schema.
    """
    error_type = "constraint_violation_error"
    
    def __init__(
        self,
        message: str = "Constraint violation",
        constraint_name: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.constraint_name = constraint_name
        
        # Add constraint information to details if provided
        if constraint_name:
            details = details or []
            
            # Check if we already have a detail with this constraint
            constraint_detail_exists = any(
                detail.get("constraint") == constraint_name for detail in details
            )
            
            # If not, add a generic constraint detail
            if not constraint_detail_exists:
                details.append({
                    "loc": None,
                    "msg": f"Violated constraint: {constraint_name}",
                    "type": "constraint_violation",
                    "constraint": constraint_name
                })
        
        super().__init__(message=message, details=details, **kwargs)


class InputValidationError(DataValidationError):
    """
    Exception for input validation errors.
    
    Raised when user input fails validation. This is typically used for
    form input validation or API request parameter validation.
    """
    error_type = "input_validation_error"
    
    def __init__(
        self,
        message: str = "Invalid input",
        field_errors: Optional[Dict[str, str]] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        # Convert field_errors to details format if provided
        if field_errors and not details:
            details = []
            for field, error in field_errors.items():
                details.append({
                    "loc": ["body", field],
                    "msg": error,
                    "type": "invalid_input",
                    "field": field
                })
        
        super().__init__(message=message, details=details, **kwargs)


class TypeConversionError(DataValidationError):
    """
    Exception for type conversion errors.
    
    Raised when a value cannot be converted to the expected type.
    """
    error_type = "type_conversion_error"
    
    def __init__(
        self,
        message: str = "Type conversion error",
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.source_type = source_type
        self.target_type = target_type
        
        # Don't include the actual value in details for security reasons
        # unless it's a basic type and reasonably short
        safe_value = None
        if value is not None:
            if isinstance(value, (str, int, float, bool)):
                # Convert to string and truncate if needed
                value_str = str(value)
                safe_value = value_str[:100] if len(value_str) > 100 else value_str
        
        # Build details if not provided
        if not details and (source_type or target_type):
            details = [{
                "loc": None,
                "msg": f"Cannot convert {source_type or 'value'} to {target_type or 'target type'}",
                "type": "type_conversion_error"
            }]
            if safe_value is not None:
                details[0]["value"] = safe_value
        
        super().__init__(message=message, details=details, **kwargs) 