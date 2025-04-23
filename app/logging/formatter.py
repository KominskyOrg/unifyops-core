import logging
import sys
import os
import inspect
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, Union

from app.logging.logger_utils import format_log_as_json

APP_ROOT = os.getenv("APP_ROOT", os.getcwd())

# ANSI color codes
_LEVEL_COLORS = {
    "DEBUG":    "\033[94m",
    "INFO":     "\033[92m",
    "WARNING":  "\033[93m",
    "ERROR":    "\033[91m",
    "CRITICAL": "\033[91m\033[1m",
}
_RESET = "\033[0m"
_DIM   = "\033[2m"


def _find_app_frame() -> Tuple[Optional[str], Optional[int]]:
    """
    Walk the stack and return (filename, lineno) for first .py under APP_ROOT.
    
    This helps identify the actual application code that triggered the log
    even when the log was generated through library code.
    
    Returns:
        Tuple of (filename, line_number) or (None, None) if no app frame found
    """
    for frame in inspect.stack():
        fn = frame.filename or ""
        if fn.startswith(APP_ROOT) and fn.endswith(".py"):
            return fn, frame.lineno
    return None, None


class LevelColorFormatter(logging.Formatter):
    """
    Console formatter that enhances log output with colors and metadata.
    
    Features:
    - Rewrites non-app paths to point to calling app code
    - Shortens paths to basename for readability
    - Colorizes log levels for better visual distinction
    - Adds metadata as bracketed key-value pairs
    
    This formatter is primarily for local development to improve log readability.
    """
    def __init__(
        self, 
        fmt: Optional[str] = None, 
        datefmt: Optional[str] = None, 
        style: str = '%',
        validate: bool = True
    ):
        super().__init__(fmt, datefmt, style, validate)
        self.use_colors = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
        if fmt and "%(levelname)" in fmt and self.use_colors:
            # swap to colored level slot
            self._style._fmt = fmt.replace("%(levelname)s", "%(colored_levelname)s")

    def format(self, record: logging.LogRecord) -> str:
        # rewrite pathname/lineno if outside APP_ROOT
        path = record.pathname or ""
        if not path.startswith(APP_ROOT):
            fn, ln = _find_app_frame()
            if fn:
                record.pathname = fn
                record.lineno   = ln

        # shorten to basename
        record.shortpath = os.path.basename(record.pathname or "<unknown>")

        # colorize level
        if self.use_colors:
            color = _LEVEL_COLORS.get(record.levelname, "")
            record.colored_levelname = f"{color}{record.levelname}{_RESET}"
        else:
            record.colored_levelname = record.levelname

        # build base line
        base = super().format(record)

        # append metadata
        meta = getattr(record, "custom_metadata", None)
        if meta:
            parts = [f"{k}={v}" for k, v in meta.items()]
            block = " ".join(parts)
            if self.use_colors:
                return f"{base} { _DIM }[{block}]{ _RESET }"
            else:
                return f"{base} [{block}]"

        return base

    def formatException(self, exc_info) -> str:
        text = super().formatException(exc_info)
        if self.use_colors:
            return f"{_LEVEL_COLORS['ERROR']}{text}{_RESET}"
        return text


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging in production environments.
    
    Features:
    - Remaps source file/line to application code when needed
    - Adds ISO8601Z timestamp for precise time tracking
    - Creates DataDog-compatible structured JSON
    - Preserves all metadata for searchability
    
    This formatter is intended for production use to enable log aggregation,
    indexing, and querying in logging systems like DataDog.
    """
    def format(self, record: logging.LogRecord) -> str:
        # 1) rewrite pathname/lineno if outside APP_ROOT
        path = record.pathname or ""
        if not path.startswith(APP_ROOT):
            fn, ln = _find_app_frame()
            if fn:
                # DataDog JSON builder uses record.pathname & record.lineno
                record.pathname = fn
                record.lineno   = ln

        # 2) let %-formatting run (if you have a message fmt)
        message = super().format(record)

        # 3) inject precise ISO timestamp for dd processing
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc)
        record.iso_timestamp = ts.isoformat(timespec="milliseconds")

        # 4) build the final JSON
        return format_log_as_json(record, message)
