"""Unified logging configuration module."""

import logging
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: str = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
) -> None:
    """Configure logging with console and optional file output.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path for file logging output
        format_string: Log message format string
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set the root logging level
    root_logger.setLevel(level)

    # Create formatters with different date formats for console and file
    console_formatter = logging.Formatter(
        format_string,
        datefmt="%H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_formatter = logging.Formatter(
            format_string,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Set third-party library log levels to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        Logger instance configured with the global settings
    """
    return logging.getLogger(name)