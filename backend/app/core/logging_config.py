"""Structured JSON logging configuration."""

import logging
import os
import sys
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

# Context variables populated by middleware
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")
workspace_id_ctx: ContextVar[str] = ContextVar("workspace_id", default="")


class _AppJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that injects request context fields."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = self.formatTime(record)
        log_record["level"] = record.levelname
        log_record["request_id"] = request_id_ctx.get("")
        log_record["user_id"] = user_id_ctx.get("")
        log_record["workspace_id"] = workspace_id_ctx.get("")
        # method, path, status_code, duration_ms are added by the caller
        for key in ("method", "path", "status_code", "duration_ms"):
            if key not in log_record:
                log_record[key] = getattr(record, key, None)


def _setup_root_logger() -> None:
    """Configure the root logger once."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    formatter = _AppJsonFormatter(
        fmt="%(timestamp)s %(level)s %(name)s %(message)s"
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level, logging.INFO))
    # Avoid duplicate handlers when module is re-imported
    if not any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, _AppJsonFormatter) for h in root.handlers):
        root.addHandler(handler)


_setup_root_logger()


def get_logger(name: str) -> logging.Logger:
    """Return a named logger that inherits the JSON configuration."""
    return logging.getLogger(name)
