"""Structured logging configuration."""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "command"):
            log_data["command"] = record.command
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"{color}[{timestamp}] {record.levelname:8s}{self.RESET} {record.getMessage()}"


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    json_format: bool = False,
) -> None:
    """Configure application logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        json_format: Use JSON format for production
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = ColoredFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


class LogContext:
    """Context manager for timed operations with logging."""

    def __init__(
        self,
        logger: logging.Logger,
        message: str,
        user_id: Optional[int] = None,
        command: Optional[str] = None,
    ) -> None:
        self.logger = logger
        self.message = message
        self.user_id = user_id
        self.command = command
        self._start: Optional[float] = None

    def __enter__(self) -> "LogContext":
        self._start = datetime.now().timestamp()
        extra = {"user_id": self.user_id, "command": self.command}
        self.logger.info(f"START: {self.message}", extra=extra)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        duration = (datetime.now().timestamp() - self._start) * 1000
        extra = {
            "user_id": self.user_id,
            "command": self.command,
            "duration_ms": round(duration, 1),
        }
        if exc_type:
            self.logger.error(f"ERROR: {self.message} ({exc_val})", extra=extra)
        else:
            self.logger.info(f"OK: {self.message} ({duration:.0f}ms)", extra=extra)


def log_command(
    logger: logging.Logger,
    command: str,
    user_id: int,
    status: str = "ok",
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    """Log a command execution with structured data."""
    extra = {
        "user_id": user_id,
        "command": command,
        "status": status,
    }
    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 1)
    if error:
        extra["error"] = error

    if status == "error":
        logger.error(f"CMD {command} failed: {error}", extra=extra)
    else:
        logger.info(f"CMD {command} completed", extra=extra)
