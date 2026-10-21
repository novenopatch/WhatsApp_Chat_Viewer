"""Structured logging configuration for WhatsApp Chat Viewer.

Provides a centralized logging setup with support for different log levels,
formatted output, and optional file logging.
"""

from __future__ import annotations

import logging
import sys
from typing import Any


def setup_logging(
    level: int = logging.INFO,
    verbose: bool = False,
    log_file: str | None = None,
) -> logging.Logger:
    """Configure structured logging for the application.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        verbose: If True, sets level to DEBUG and shows detailed output.
        log_file: Optional path to log file for persistent logging.

    Returns:
        Configured root logger instance.

    Example:
        >>> logger = setup_logging(verbose=True)
        >>> logger.info("Application started")
    """
    if verbose:
        level = logging.DEBUG

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()  # Remove existing handlers
    root_logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__ of the module).

    Returns:
        Logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message")
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for temporary log level changes.

    Useful for temporarily increasing log verbosity for specific operations.

    Example:
        >>> with LogContext(logging.DEBUG):
        ...     # All logs here will be at DEBUG level
        ...     logger.debug("Detailed debug info")
    """

    def __init__(self, level: int, logger: logging.Logger | None = None) -> None:
        """Initialize log context.

        Args:
            level: Temporary log level to apply.
            logger: Logger to modify. If None, uses root logger.
        """
        self.level = level
        self.logger = logger or logging.getLogger()
        self.previous_level = self.logger.level

    def __enter__(self) -> None:
        """Apply temporary log level."""
        self.logger.setLevel(self.level)
        return self.logger

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Restore previous log level."""
        self.logger.setLevel(self.previous_level)
