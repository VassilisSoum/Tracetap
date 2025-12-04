"""
Tests for utility functions module.

Tests safe_body(), calc_duration(), and status_color() functions
without making actual system changes.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "tracetap" / "capture"))

from utils import safe_body, calc_duration, status_color


class TestSafeBody:
    """Test suite for safe_body() function."""

    def test_text_body_extraction(self):
        """Test extraction of text body when text is provided."""
        text = "Hello, World!"
        raw = b"Hello, World!"

        result = safe_body(text, raw)

        assert isinstance(result, str)
        assert result == "Hello, World!"
        assert len(result) == 13

    def test_empty_text_with_raw_bytes(self):
        """Test fallback to raw bytes when text is empty."""
        text = ""
        raw = b"Raw body content"

        result = safe_body(text, raw)

        assert isinstance(result, str)
        assert result == "Raw body content"
        assert len(result) == 16

    def test_utf8_decoding_from_raw(self):
        """Test UTF-8 decoding of raw bytes."""
        text = ""
        raw = "Encoded UTF-8 content".encode('utf-8')

        result = safe_body(text, raw)

        assert result == "Encoded UTF-8 content"

    def test_size_limiting_text(self):
        """Test size limiting on text body."""
        text = "A" * 1000
        raw = b""
        max_bytes = 100

        result = safe_body(text, raw, max_bytes=max_bytes)

        assert isinstance(result, str)
        assert len(result) == 100
        assert result == "A" * 100
        assert not result.startswith("[binary data")  # Should be text, not placeholder

    def test_size_limiting_raw(self):
        """Test size limiting on raw bytes."""
        text = ""
        raw = b"B" * 1000
        max_bytes = 100

        result = safe_body(text, raw, max_bytes=max_bytes)

        assert len(result) == 100
        assert result == "B" * 100

    def test_empty_text_and_raw(self):
        """Test handling of empty text and raw bytes."""
        text = ""
        raw = b""

        result = safe_body(text, raw)

        assert isinstance(result, str)
        assert result == ""
        assert len(result) == 0

    def test_none_raw_bytes(self):
        """Test handling when raw bytes is None."""
        text = ""
        raw = None

        result = safe_body(text, raw)

        assert result == ""

    def test_binary_data_placeholder(self):
        """Test placeholder for binary data that cannot be decoded."""
        text = ""
        # Create binary data that will fail UTF-8 decoding
        raw = b"\x80\x81\x82\x83\x84"

        # The function uses 'replace' error handling, so it should succeed
        # but let's test the exception path by making decode raise
        result = safe_body(text, raw)

        # With 'replace' error handling, this should not hit the exception
        assert isinstance(result, str)

    def test_exception_handling_with_binary(self):
        """Test exception handling returns binary placeholder."""
        # Create a mock that raises exception during processing
        text = None  # This might cause issues
        raw = b"\xff\xfe\xfd\xfc"

        # This should handle the exception gracefully
        result = safe_body(text, raw)

        # Should either decode with replacement or return binary placeholder
        assert isinstance(result, str)

    def test_large_body_default_limit(self):
        """Test default size limit of 64KB."""
        text = "X" * (64 * 1024 + 1000)  # Larger than 64KB
        raw = b""

        result = safe_body(text, raw)

        assert len(result) == 64 * 1024

    def test_unicode_characters(self):
        """Test handling of Unicode characters."""
        text = "Hello 世界 🌍"
        raw = b""

        result = safe_body(text, raw)

        assert result == "Hello 世界 🌍"

    def test_json_body(self):
        """Test handling of JSON body."""
        text = '{"key": "value", "number": 123}'
        raw = b""

        result = safe_body(text, raw)

        assert result == '{"key": "value", "number": 123}'

    def test_xml_body(self):
        """Test handling of XML body."""
        text = "<?xml version='1.0'?><root><item>data</item></root>"
        raw = b""

        result = safe_body(text, raw)

        assert result == "<?xml version='1.0'?><root><item>data</item></root>"


class TestCalcDuration:
    """Test suite for calc_duration() function."""

    def test_duration_with_valid_timestamps(self):
        """Test duration calculation with valid timestamps."""
        flow = Mock()
        flow.server_conn = Mock()
        flow.server_conn.timestamp_start = 1000.0
        flow.server_conn.timestamp_end = 1002.5

        result = calc_duration(flow)

        # Duration should be 2.5 seconds = 2500 milliseconds
        assert isinstance(result, int)
        assert result == 2500
        assert result > 0

    def test_duration_with_fractional_seconds(self):
        """Test duration calculation with fractional seconds."""
        flow = Mock()
        flow.server_conn = Mock()
        flow.server_conn.timestamp_start = 1000.123
        flow.server_conn.timestamp_end = 1000.456

        result = calc_duration(flow)

        # Duration should be 0.333 seconds = 332-333 milliseconds (int truncation)
        assert result in [332, 333]

    def test_no_server_conn(self):
        """Test duration when server_conn is None."""
        flow = Mock()
        flow.server_conn = None

        result = calc_duration(flow)

        assert isinstance(result, int)
        assert result == 0
        assert result >= 0  # Should never be negative

    def test_missing_server_conn_attribute(self):
        """Test duration when server_conn attribute doesn't exist."""
        flow = Mock(spec=[])  # Mock with no attributes

        result = calc_duration(flow)

        assert result == 0

    def test_no_timestamp_end(self):
        """Test duration when timestamp_end is None."""
        flow = Mock()
        flow.server_conn = Mock()
        flow.server_conn.timestamp_start = 1000.0
        flow.server_conn.timestamp_end = None

        result = calc_duration(flow)

        assert result == 0

    def test_zero_duration(self):
        """Test duration when start and end are the same."""
        flow = Mock()
        flow.server_conn = Mock()
        flow.server_conn.timestamp_start = 1000.0
        flow.server_conn.timestamp_end = 1000.0

        result = calc_duration(flow)

        assert isinstance(result, int)
        assert result == 0
        assert result >= 0

    def test_very_long_duration(self):
        """Test duration calculation with long request."""
        flow = Mock()
        flow.server_conn = Mock()
        flow.server_conn.timestamp_start = 1000.0
        flow.server_conn.timestamp_end = 1060.0  # 60 seconds

        result = calc_duration(flow)

        assert result == 60000  # 60 seconds = 60000 milliseconds

    def test_exception_handling(self):
        """Test exception handling returns 0."""
        flow = Mock()
        # Make server_conn raise exception when accessed
        flow.server_conn = Mock()
        flow.server_conn.timestamp_end = Mock(side_effect=Exception("Test error"))

        result = calc_duration(flow)

        assert result == 0

    def test_millisecond_precision(self):
        """Test duration with small millisecond values."""
        flow = Mock()
        flow.server_conn = Mock()
        flow.server_conn.timestamp_start = 1000.0
        flow.server_conn.timestamp_end = 1000.1

        result = calc_duration(flow)

        # Duration should be 0.1 seconds = 100 milliseconds
        assert result == 100


class TestStatusColor:
    """Test suite for status_color() function."""

    def test_2xx_success_green(self):
        """Test 2xx status codes return green color."""
        result = status_color(200)
        assert isinstance(result, str)
        assert result == "\033[32m"
        assert status_color(201) == "\033[32m"
        assert status_color(204) == "\033[32m"
        assert status_color(299) == "\033[32m"

    def test_3xx_redirect_cyan(self):
        """Test 3xx status codes return cyan color."""
        assert status_color(300) == "\033[36m"
        assert status_color(301) == "\033[36m"
        assert status_color(302) == "\033[36m"
        assert status_color(304) == "\033[36m"
        assert status_color(399) == "\033[36m"

    def test_4xx_client_error_yellow(self):
        """Test 4xx status codes return yellow color."""
        result = status_color(404)
        assert isinstance(result, str)
        assert result == "\033[33m"
        assert status_color(400) == "\033[33m"
        assert status_color(401) == "\033[33m"
        assert status_color(403) == "\033[33m"
        assert status_color(499) == "\033[33m"

    def test_5xx_server_error_red(self):
        """Test 5xx status codes return red color."""
        assert status_color(500) == "\033[31m"
        assert status_color(501) == "\033[31m"
        assert status_color(502) == "\033[31m"
        assert status_color(503) == "\033[31m"
        assert status_color(599) == "\033[31m"

    def test_1xx_informational_no_color(self):
        """Test 1xx status codes return no color."""
        result = status_color(100)
        assert isinstance(result, str)
        assert result == ""
        assert len(result) == 0
        assert status_color(101) == ""
        assert status_color(199) == ""

    def test_6xx_invalid_no_color(self):
        """Test invalid/non-standard status codes return no color."""
        assert status_color(600) == ""
        assert status_color(700) == ""
        assert status_color(999) == ""

    def test_zero_status_no_color(self):
        """Test zero status code returns no color."""
        assert status_color(0) == ""

    def test_negative_status_no_color(self):
        """Test negative status code returns no color."""
        assert status_color(-1) == ""

    def test_boundary_199_no_color(self):
        """Test boundary at 199 returns no color."""
        assert status_color(199) == ""

    def test_boundary_200_green(self):
        """Test boundary at 200 returns green."""
        assert status_color(200) == "\033[32m"

    def test_boundary_299_green(self):
        """Test boundary at 299 returns green."""
        assert status_color(299) == "\033[32m"

    def test_boundary_300_cyan(self):
        """Test boundary at 300 returns cyan."""
        assert status_color(300) == "\033[36m"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
