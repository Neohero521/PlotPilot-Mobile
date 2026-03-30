"""Web middleware components."""

from aitext.web.middleware.error_handler import add_error_handlers
from aitext.web.middleware.logging_config import get_logger, setup_logging

__all__ = ["add_error_handlers", "setup_logging", "get_logger"]