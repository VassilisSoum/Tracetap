"""
Tests for export functionality module.

Tests RawLogExporter class for proper JSON generation, file I/O, and data transformation.
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, mock_open, patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "tracetap" / "capture"))

from exporters import RawLogExporter


# Sample test data
SAMPLE_RECORD_GET = {
    "method": "GET",
    "url": "https://api.example.com/users?page=1&limit=10",
    "req_headers": {"Authorization": "Bearer token123", "Accept": "application/json"},
    "req_body": "",
    "status": 200,
    "duration": 150
}

SAMPLE_RECORD_POST = {
    "method": "POST",
    "url": "https://api.example.com/users",
    "req_headers": {"Content-Type": "application/json"},
    "req_body": '{"name": "John", "email": "john@example.com"}',
    "status": 201,
    "duration": 200
}


class TestRawLogExporterBasicFunctionality:
    """Test suite for RawLogExporter basic export functionality."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.stat')
    def test_export_empty_records(self, mock_stat, mock_mkdir, mock_file):
        """Test exporting empty records list."""
        mock_stat.return_value.st_size = 512
        records = []

        RawLogExporter.export(records, "test-session", "/tmp/log.json", [], None)

        # Verify file operations
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called_once()
        assert mock_file().write.called

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        log_data = json.loads(written_data)

        # Verify structure and types
        assert isinstance(log_data, dict)
        assert isinstance(log_data["requests"], list)
        assert log_data["total_requests"] == 0
        assert log_data["requests"] == []

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.stat')
    def test_export_with_records(self, mock_stat, mock_mkdir, mock_file):
        """Test exporting records."""
        mock_stat.return_value.st_size = 2048
        records = [SAMPLE_RECORD_GET, SAMPLE_RECORD_POST]

        RawLogExporter.export(records, "test", "/tmp/log.json", [], None)

        # Verify file operations
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        assert mock_file().write.called

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        log_data = json.loads(written_data)

        # Verify structure and types
        assert isinstance(log_data, dict)
        assert isinstance(log_data["requests"], list)
        assert log_data["total_requests"] == 2
        assert len(log_data["requests"]) == 2
        assert log_data["requests"] == records


class TestRawLogExporterMetadata:
    """Test suite for metadata generation."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.stat')
    def test_includes_session_name(self, mock_stat, mock_mkdir, mock_file):
        """Test includes session name in metadata."""
        mock_stat.return_value.st_size = 512
        records = []

        RawLogExporter.export(records, "my-session", "/tmp/log.json", [], None)

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        log_data = json.loads(written_data)

        assert log_data["session"] == "my-session"

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.stat')
    def test_includes_timestamp(self, mock_stat, mock_mkdir, mock_file):
        """Test includes timestamp in metadata."""
        mock_stat.return_value.st_size = 512
        records = []

        RawLogExporter.export(records, "test", "/tmp/log.json", [], None)

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        log_data = json.loads(written_data)

        assert "captured_at" in log_data
        # Should be ISO format timestamp
        assert "T" in log_data["captured_at"]

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.stat')
    def test_includes_host_filters(self, mock_stat, mock_mkdir, mock_file):
        """Test includes host filters in metadata."""
        mock_stat.return_value.st_size = 512
        records = []
        host_filters = ["api.example.com", "*.test.com"]

        RawLogExporter.export(records, "test", "/tmp/log.json", host_filters, None)

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        log_data = json.loads(written_data)

        assert log_data["filters"]["hosts"] == host_filters

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.stat')
    def test_includes_regex_filter(self, mock_stat, mock_mkdir, mock_file):
        """Test includes regex filter in metadata."""
        mock_stat.return_value.st_size = 512
        records = []
        regex = ".*\\.example\\.com"

        RawLogExporter.export(records, "test", "/tmp/log.json", [], regex)

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        log_data = json.loads(written_data)

        assert log_data["filters"]["regex"] == regex

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.stat')
    def test_regex_none_when_not_provided(self, mock_stat, mock_mkdir, mock_file):
        """Test regex is None when not provided."""
        mock_stat.return_value.st_size = 512
        records = []

        RawLogExporter.export(records, "test", "/tmp/log.json", [], None)

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        log_data = json.loads(written_data)

        assert log_data["filters"]["regex"] is None


class TestRawLogExporterFileIO:
    """Test suite for file I/O operations."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.stat')
    def test_creates_parent_directory(self, mock_stat, mock_mkdir, mock_file):
        """Test that parent directories are created."""
        mock_stat.return_value.st_size = 512
        records = []

        RawLogExporter.export(records, "test", "/tmp/nested/log.json", [], None)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.stat')
    def test_writes_utf8_encoding(self, mock_stat, mock_mkdir, mock_file):
        """Test file is written with UTF-8 encoding."""
        mock_stat.return_value.st_size = 512
        records = []

        RawLogExporter.export(records, "test", "/tmp/log.json", [], None)

        args, kwargs = mock_file.call_args
        assert kwargs.get("encoding") == "utf-8"

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.stat')
    def test_prints_file_size(self, mock_stat, mock_mkdir, mock_file, capsys):
        """Test prints file size in summary."""
        mock_stat.return_value.st_size = 2048  # 2 KB
        records = []

        RawLogExporter.export(records, "test", "/tmp/log.json", [], None)

        captured = capsys.readouterr()
        assert "✓ Exported raw log" in captured.out
        assert "2.0 KB" in captured.out
        assert "/tmp/log.json" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
