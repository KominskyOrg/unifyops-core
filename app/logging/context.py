import logging
from typing import Optional, Dict, Any, cast

from app.logging.context_vars import correlation_id_var, metadata_var

class ContextLoggerAdapter(logging.LoggerAdapter):
    """
    Enhanced logger adapter that injects contextual information into log records.
    
    This adapter enriches log entries with:
      1) module‑level metadata (from adapter construction)
      2) per‑request metadata (from ContextVar)
      3) inline metadata (supplied in individual log calls)
      4) correlation_id (from ContextVar)
    
    This allows for consistent logging across asynchronous request boundaries.
    """
    def __init__(
        self,
        logger: logging.Logger,
        module_metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(logger, {})
        self.module_metadata = module_metadata or {}

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        extra = kwargs.setdefault("extra", {})

        # 1) module‑level metadata
        if self.module_metadata:
            extra.setdefault("custom_metadata", {}).update(self.module_metadata)

        # 2) per‑request metadata
        req_meta = metadata_var.get()
        if req_meta:
            extra.setdefault("custom_metadata", {}).update(req_meta)

        # 3) inline metadata
        inline = kwargs.pop("metadata", None)
        if inline:
            extra.setdefault("custom_metadata", {}).update(inline)

        # 4) correlation ID
        cid = correlation_id_var.get()
        if cid:
            extra["correlation_id"] = cid

        # ensure correct caller file/line
        kwargs.setdefault("stacklevel", 2)
        return msg, kwargs

    def structured(self, level: str, event: str, **kwargs):
        """Log a structured event with key-value pairs."""
        level_method = getattr(self, level.lower(), self.info)
        level_method(f"{event}", metadata=kwargs)

def get_logger(
    name: str = __name__,
    metadata: Optional[Dict[str, Any]] = None
) -> ContextLoggerAdapter:
    """
    Get a context-aware logger with optional module-level metadata.
    
    This is the preferred way to obtain a logger throughout the application.
    The returned logger will automatically include correlation IDs and
    context metadata in all log entries.
    
    Args:
        name: Logger name (typically __name__)
        metadata: Module-level metadata to include in all log entries
        
    Returns:
        A context-aware logger adapter
        
    Example:
        ```python
        # In your module
        logger = get_logger(__name__, metadata={"component": "auth_service"})
        
        # Later in request handling
        logger.info("Processing request", metadata={"user_id": user.id})
        ```
    """
    base = logging.getLogger(name)
    return ContextLoggerAdapter(base, module_metadata=metadata)
