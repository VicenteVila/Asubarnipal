"""Tests for core/logging_config.py."""

import json
import logging
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class TestJSONFormatter(unittest.TestCase):
    """Test JSON log formatter."""

    def test_format_produces_valid_json(self):
        from core.logging_config import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["message"], "Test message")
        self.assertIn("timestamp", data)

    def test_format_includes_exception(self):
        from core.logging_config import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=(Exception, Exception("test error"), None),
        )

        result = formatter.format(record)
        data = json.loads(result)

        self.assertIn("exception", data)

    def test_format_includes_custom_attributes(self):
        from core.logging_config import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Command executed",
            args=(),
            exc_info=None,
        )
        record.user_id = 123
        record.command = "/start"
        record.duration_ms = 45.2

        result = formatter.format(record)
        data = json.loads(result)

        self.assertEqual(data["user_id"], 123)
        self.assertEqual(data["command"], "/start")
        self.assertEqual(data["duration_ms"], 45.2)


class TestLogContext(unittest.TestCase):
    """Test LogContext context manager."""

    @patch("core.logging_config.datetime")
    def test_context_logs_start_and_ok(self, mock_datetime):
        from core.logging_config import LogContext

        mock_logger = Mock()
        mock_datetime.now.return_value.timestamp.return_value = 1000.0

        with LogContext(mock_logger, "test operation", user_id=1, command="/test"):
            mock_datetime.now.return_value.timestamp.return_value = 1000.05

        self.assertEqual(mock_logger.info.call_count, 2)
        start_call = mock_logger.info.call_args_list[0]
        end_call = mock_logger.info.call_args_list[1]

        self.assertIn("START", start_call[0][0])
        self.assertIn("OK", end_call[0][0])

    @patch("core.logging_config.datetime")
    def test_context_logs_error_on_exception(self, mock_datetime):
        from core.logging_config import LogContext

        mock_logger = Mock()
        mock_datetime.now.return_value.timestamp.return_value = 1000.0

        with self.assertRaises(ValueError):
            with LogContext(mock_logger, "failing operation"):
                mock_datetime.now.return_value.timestamp.return_value = 1000.05
                raise ValueError("test error")

        error_call = mock_logger.error.call_args
        self.assertIn("ERROR", error_call[0][0])


class TestLogCommand(unittest.TestCase):
    """Test log_command helper function."""

    def test_log_command_success(self):
        from core.logging_config import log_command

        mock_logger = Mock()
        log_command(mock_logger, "/start", user_id=123, status="ok", duration_ms=50.0)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        self.assertIn("/start", call_args[0][0])
        self.assertEqual(call_args[1]["extra"]["user_id"], 123)

    def test_log_command_error(self):
        from core.logging_config import log_command

        mock_logger = Mock()
        log_command(
            mock_logger, "/query", user_id=456,
            status="error", error="timeout"
        )

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        self.assertIn("failed", call_args[0][0])


if __name__ == "__main__":
    unittest.main()
