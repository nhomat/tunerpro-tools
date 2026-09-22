"""Shared logging setup.

Every tool logs to ``logs/<tool_name>.log`` via :func:`get_tool_logger`.
Log lines record date, tool, file used, operation and any error - never
unrelated personal information (see SAFETY.md / AGENTS instructions).
"""
from __future__ import annotations

import logging
from pathlib import Path

from .config import get_config

_CONFIGURED_LOGGERS: set[str] = set()


def get_tool_logger(tool_name: str) -> logging.Logger:
    """Return a logger that writes to ``logs/<tool_name>.log`` and stderr."""
    logger = logging.getLogger(f"tunerpro_tools.{tool_name}")
    if tool_name in _CONFIGURED_LOGGERS:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    config = get_config()
    log_path = config.logs_dir / f"{tool_name}.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    _CONFIGURED_LOGGERS.add(tool_name)
    return logger


def log_operation(
    logger: logging.Logger,
    operation: str,
    file_used: str | Path | None = None,
    error: str | None = None,
) -> None:
    """Log one operation in the standard "operation on file" shape."""
    parts = [f"operation={operation}"]
    if file_used is not None:
        parts.append(f"file={file_used}")
    if error:
        logger.error(" | ".join(parts + [f"error={error}"]))
    else:
        logger.info(" | ".join(parts))
