import uuid
from typing import Any

def parse_uuids(obj: Any) -> Any:
    """
    Recursively converts UUID objects to strings in dictionaries, lists, or other data structures.
    
    This ensures proper JSON serialization of data containing UUID objects,
    which is common in database records and API responses.
    
    Args:
        obj: The object to process (dict, list, UUID, or other value)
        
    Returns:
        The same data structure with UUIDs converted to strings
        
    Examples:
        >>> data = {"id": uuid.UUID("12345678-1234-5678-1234-567812345678"), "nested": {"uuid": uuid.UUID("87654321-4321-8765-4321-876543210987")}}
        >>> parse_uuids(data)
        {"id": "12345678-1234-5678-1234-567812345678", "nested": {"uuid": "87654321-4321-8765-4321-876543210987"}}
    """
    # Handle UUID objects
    if isinstance(obj, uuid.UUID):
        return str(obj)
    
    # Handle dictionaries recursively
    elif isinstance(obj, dict):
        return {k: parse_uuids(v) for k, v in obj.items()}
    
    # Handle lists, tuples and sets recursively
    elif isinstance(obj, (list, tuple, set)):
        return type(obj)(parse_uuids(item) for item in obj)
    
    # Return other types unchanged
    return obj 