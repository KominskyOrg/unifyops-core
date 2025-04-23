"""
Database exception classes.

This module provides exceptions for various database-related errors
that can occur during database operations, such as connection failures,
query errors, transaction errors, and migration issues.
"""

from typing import Any, Dict, List, Optional
from fastapi import status

from app.exceptions.base import ServerError


class DatabaseError(ServerError):
    """
    Base exception for database errors.
    
    A general exception for any database-related error.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type = "database_error"
    
    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        table: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.operation = operation
        self.table = table
        
        # Create more specific message if operation and table are provided
        if operation and table:
            message = f"Database {operation} operation on table '{table}' failed"
        elif operation:
            message = f"Database {operation} operation failed"
        
        # Create details if not provided but we have database info
        if not details and (operation or table):
            details = [{
                "type": "database_error",
                "msg": message
            }]
            
            if operation:
                details[0]["operation"] = operation
            if table:
                details[0]["table"] = table
        
        super().__init__(message=message, details=details, **kwargs)


class ConnectionError(DatabaseError):
    """
    Exception for database connection errors.
    
    Raised when a connection to the database fails.
    """
    error_type = "database_connection_error"
    
    def __init__(
        self,
        message: str = "Database connection failed",
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.host = host
        self.port = port
        self.database = database
        self.retry_after = retry_after
        
        # Create more specific message if connection details are provided
        if host and database:
            message = f"Connection to database '{database}' at {host}"
            if port:
                message += f":{port}"
            message += " failed"
        elif database:
            message = f"Connection to database '{database}' failed"
        
        # Create details if not provided but we have connection info
        if not details and (host or port or database):
            details = [{
                "type": "connection_error",
                "msg": message
            }]
            
            # Be careful with connection details - don't include credentials
            if host:
                details[0]["host"] = host
            if port:
                details[0]["port"] = port
            if database:
                details[0]["database"] = database
            if retry_after:
                details[0]["retry_after"] = retry_after
        
        super().__init__(message=message, details=details, operation="connect", **kwargs)


class QueryError(DatabaseError):
    """
    Exception for database query errors.
    
    Raised when a database query fails.
    """
    error_type = "query_error"
    
    def __init__(
        self,
        message: str = "Database query failed",
        query_type: Optional[str] = None,
        table: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.query_type = query_type
        self.error_code = error_code
        
        # Create more specific message if query details are provided
        if query_type and table:
            message = f"{query_type.upper()} query on table '{table}' failed"
            if error_code:
                message += f" with error code {error_code}"
        elif query_type:
            message = f"{query_type.upper()} query failed"
            if error_code:
                message += f" with error code {error_code}"
        
        # Create details if not provided but we have query info
        if not details and (query_type or table or error_code):
            details = [{
                "type": "query_error",
                "msg": message
            }]
            
            if query_type:
                details[0]["query_type"] = query_type
            if table:
                details[0]["table"] = table
            if error_code:
                details[0]["error_code"] = error_code
        
        super().__init__(message=message, details=details, operation=query_type, table=table, **kwargs)


class TransactionError(DatabaseError):
    """
    Exception for database transaction errors.
    
    Raised when a database transaction fails.
    """
    error_type = "transaction_error"
    
    def __init__(
        self,
        message: str = "Database transaction failed",
        transaction_operation: Optional[str] = None,
        isolation_level: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.transaction_operation = transaction_operation
        self.isolation_level = isolation_level
        
        # Create more specific message if transaction details are provided
        if transaction_operation:
            message = f"Database transaction {transaction_operation} failed"
            if isolation_level:
                message += f" (isolation level: {isolation_level})"
        
        # Create details if not provided but we have transaction info
        if not details and (transaction_operation or isolation_level):
            details = [{
                "type": "transaction_error",
                "msg": message
            }]
            
            if transaction_operation:
                details[0]["transaction_operation"] = transaction_operation
            if isolation_level:
                details[0]["isolation_level"] = isolation_level
        
        super().__init__(message=message, details=details, operation="transaction", **kwargs)


class MigrationError(DatabaseError):
    """
    Exception for database migration errors.
    
    Raised when a database migration fails.
    """
    error_type = "migration_error"
    
    def __init__(
        self,
        message: str = "Database migration failed",
        migration_version: Optional[str] = None,
        migration_name: Optional[str] = None,
        migration_direction: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.migration_version = migration_version
        self.migration_name = migration_name
        self.migration_direction = migration_direction
        
        # Create more specific message if migration details are provided
        if migration_version and migration_name and migration_direction:
            message = f"Database migration {migration_direction} to version {migration_version} ({migration_name}) failed"
        elif migration_version and migration_direction:
            message = f"Database migration {migration_direction} to version {migration_version} failed"
        elif migration_direction:
            message = f"Database {migration_direction} migration failed"
        
        # Create details if not provided but we have migration info
        if not details and (migration_version or migration_name or migration_direction):
            details = [{
                "type": "migration_error",
                "msg": message
            }]
            
            if migration_version:
                details[0]["migration_version"] = migration_version
            if migration_name:
                details[0]["migration_name"] = migration_name
            if migration_direction:
                details[0]["migration_direction"] = migration_direction
        
        super().__init__(message=message, details=details, operation="migration", **kwargs)


class IntegrityError(DatabaseError):
    """
    Exception for database integrity errors.
    
    Raised when a database constraint is violated.
    """
    error_type = "integrity_error"
    
    def __init__(
        self,
        message: str = "Database integrity constraint violated",
        constraint_name: Optional[str] = None,
        constraint_type: Optional[str] = None,
        table: Optional[str] = None,
        column: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.constraint_name = constraint_name
        self.constraint_type = constraint_type
        self.column = column
        
        # Create more specific message if constraint details are provided
        if constraint_type and table and column:
            message = f"{constraint_type.capitalize()} constraint violated on {table}.{column}"
            if constraint_name:
                message += f" (constraint: {constraint_name})"
        elif constraint_type and table:
            message = f"{constraint_type.capitalize()} constraint violated on table {table}"
            if constraint_name:
                message += f" (constraint: {constraint_name})"
        elif constraint_type:
            message = f"{constraint_type.capitalize()} constraint violated"
            if constraint_name:
                message += f" (constraint: {constraint_name})"
        
        # Create details if not provided but we have constraint info
        if not details and (constraint_name or constraint_type or table or column):
            details = [{
                "type": "integrity_error",
                "msg": message
            }]
            
            if constraint_name:
                details[0]["constraint_name"] = constraint_name
            if constraint_type:
                details[0]["constraint_type"] = constraint_type
            if table:
                details[0]["table"] = table
            if column:
                details[0]["column"] = column
        
        super().__init__(message=message, details=details, table=table, **kwargs)


class NoResultFoundError(DatabaseError):
    """
    Exception for when a query returns no results but a result was expected.
    
    Typically used in single-result queries where at least one result is required.
    """
    status_code = status.HTTP_404_NOT_FOUND
    error_type = "no_result_found"
    
    def __init__(
        self,
        message: str = "No result found for query",
        query_type: Optional[str] = None,
        table: Optional[str] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.query_type = query_type
        self.filter_criteria = filter_criteria
        
        # Create more specific message if query details are provided
        if query_type and table and filter_criteria:
            criteria_str = ", ".join(f"{k}={v}" for k, v in filter_criteria.items())
            message = f"No result found for {query_type} query on table '{table}' with criteria: {criteria_str}"
        elif query_type and table:
            message = f"No result found for {query_type} query on table '{table}'"
        
        # Create details if not provided but we have query info
        if not details and (query_type or table or filter_criteria):
            details = [{
                "type": "no_result_found",
                "msg": message
            }]
            
            if query_type:
                details[0]["query_type"] = query_type
            if table:
                details[0]["table"] = table
            
            # Include safe filter criteria in details, avoiding potential sensitive info
            if filter_criteria:
                # This is a simplistic filter - in production, you would have a more sophisticated approach
                safe_criteria = {}
                for k, v in filter_criteria.items():
                    if not any(term in k.lower() for term in ["password", "secret", "token", "key"]):
                        safe_criteria[k] = v
                
                if safe_criteria:
                    details[0]["filter_criteria"] = safe_criteria
        
        super().__init__(message=message, details=details, operation=query_type, table=table, **kwargs) 