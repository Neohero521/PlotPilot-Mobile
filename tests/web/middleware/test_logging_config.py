"""Tests for unified logging configuration."""

import logging
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from aitext.web.middleware.logging_config import get_logger, setup_logging


@pytest.fixture
def reset_logging():
    """Reset logging configuration before and after each test."""
    # Clear all handlers before test
    root_logger = logging.getLogger()
    handlers = root_logger.handlers[:]
    for handler in handlers:
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)

    yield

    # Clear all handlers after test
    root_logger = logging.getLogger()
    handlers = root_logger.handlers[:]
    for handler in handlers:
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)


class TestSetupLogging:
    """Test suite for setup_logging function."""

    def test_setup_logging_console_only(self, reset_logging):
        """Test logging setup with console output only."""
        setup_logging(level=logging.DEBUG)

        root_logger = logging.getLogger()

        # Verify root logger level
        assert root_logger.level == logging.DEBUG

        # Verify we have a console handler
        assert len(root_logger.handlers) == 1
        handler = root_logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.level == logging.DEBUG

        # Verify formatter
        formatter = handler.formatter
        assert formatter is not None
        assert "%(levelname)s" in formatter._fmt
        assert formatter.datefmt == "%H:%M:%S"

    def test_setup_logging_with_file(self, reset_logging):
        """Test logging setup with both console and file output."""
        temp_dir = tempfile.mkdtemp()
        try:
            log_file_path = os.path.join(temp_dir, 'test.log')

            setup_logging(level=logging.INFO, log_file=log_file_path)

            root_logger = logging.getLogger()

            # Verify root logger level
            assert root_logger.level == logging.INFO

            # Verify we have two handlers (console and file)
            assert len(root_logger.handlers) == 2

            # Verify console handler
            console_handler = root_logger.handlers[0]
            assert isinstance(console_handler, logging.StreamHandler)
            assert console_handler.level == logging.INFO

            # Verify file handler
            file_handler = root_logger.handlers[1]
            assert isinstance(file_handler, logging.FileHandler)
            assert file_handler.level == logging.INFO

            # Verify file handler has different date format
            file_formatter = file_handler.formatter
            assert file_formatter.datefmt == "%Y-%m-%d %H:%M:%S"

            # Test actual file writing
            test_logger = get_logger("test")
            test_logger.info("Test message")

            assert os.path.exists(log_file_path)
            with open(log_file_path, 'r') as f:
                content = f.read()
                assert "Test message" in content
                assert "[INFO]" in content

            # Close the file handler before cleanup to avoid Windows file lock issues
            file_handler.close()
            root_logger.removeHandler(file_handler)

        finally:
            # Clean up temp directory and file
            import shutil
            import time
            # Give the file system time to release the file handle
            time.sleep(0.1)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def test_setup_logging_clears_existing_handlers(self, reset_logging):
        """Test that setup_logging clears existing handlers."""
        # Add a dummy handler first
        root_logger = logging.getLogger()
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)

        # Count existing handlers (including our dummy one)
        existing_handler_count = len(root_logger.handlers)
        assert existing_handler_count >= 1
        assert dummy_handler in root_logger.handlers

        # Now setup logging - it should clear the dummy handler
        setup_logging()

        # Should only have 1 handler (the console handler from setup_logging)
        assert len(root_logger.handlers) == 1
        assert root_logger.handlers[0] is not dummy_handler

    def test_setup_logging_sets_third_party_levels(self, reset_logging):
        """Test that third-party library levels are set to WARNING."""
        setup_logging(level=logging.DEBUG)

        uvicorn_logger = logging.getLogger("uvicorn")
        fastapi_logger = logging.getLogger("fastapi")

        assert uvicorn_logger.level == logging.WARNING
        assert fastapi_logger.level == logging.WARNING

    def test_setup_logging_custom_format(self, reset_logging):
        """Test logging setup with custom format string."""
        custom_format = "%(name)s - %(message)s"
        setup_logging(level=logging.INFO, format_string=custom_format)

        root_logger = logging.getLogger()
        handler = root_logger.handlers[0]

        assert handler.formatter._fmt == custom_format


class TestGetLogger:
    """Test suite for get_logger function."""

    def test_get_logger_returns_logger(self, reset_logging):
        """Test that get_logger returns a Logger instance."""
        setup_logging()
        logger = get_logger("test_logger")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_get_logger_with_different_names(self, reset_logging):
        """Test get_logger with different name patterns."""
        setup_logging()

        logger1 = get_logger("module.submodule")
        logger2 = get_logger("another_module")

        assert logger1.name == "module.submodule"
        assert logger2.name == "another_module"
        assert logger1 is not logger2

    def test_get_logger_respects_root_level(self, reset_logging):
        """Test that loggers respect root logger level."""
        setup_logging(level=logging.ERROR)

        logger = get_logger("test")

        # Logger inherits root level
        assert logger.getEffectiveLevel() == logging.ERROR

    def test_get_logger_can_log(self, reset_logging):
        """Test that logger can actually log messages."""
        setup_logging(level=logging.INFO)

        logger = get_logger("test_logger")

        # Add a custom handler to capture log records
        import io
        log_capture = io.StringIO()
        test_handler = logging.StreamHandler(log_capture)
        test_handler.setLevel(logging.INFO)
        test_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        logger.addHandler(test_handler)

        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

        # Check that messages were logged
        log_content = log_capture.getvalue()
        assert "Test info message" in log_content
        assert "Test warning message" in log_content
        assert "Test error message" in log_content

        # Clean up
        logger.removeHandler(test_handler)