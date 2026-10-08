import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict

# Context variable for request ID tracking across async calls
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class StructuredFormatter(logging.Formatter):
    """Formats log records as structured JSON including timestamp, level, request_id, and metadata."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get() or getattr(record, "request_id", ""),
        }
        if hasattr(record, "event"):
            log_entry["event"] = record.event
        if hasattr(record, "metadata") and isinstance(record.metadata, dict):
            log_entry["metadata"] = record.metadata
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logger(name: str = "graphintel") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = setup_logger()


def log_event(event: str, message: str, level: int = logging.INFO, **metadata: Any) -> None:
    """Helper to log domain events with structured metadata."""
    extra = {
        "event": event,
        "metadata": metadata,
        "request_id": request_id_ctx.get(),
    }
    logger.log(level, message, extra=extra)
