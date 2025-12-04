"""
Tests for export functionality module.

Tests PostmanExporter and RawLogExporter classes for proper
JSON generation, file I/O, and data transformation.
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, mock_open, patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "tracetap" / "capture"))

from exporters import PostmanExporter, RawLogExporter


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

SAMPLE_RECORD_WITH_PORT = {
    "method": "GET",
    "url": "http://localhost:8080/api/test",
    "req_headers": {},
    "req_body": "",
    "status": 200,
    "duration": 50
}


class TestPostmanExporterBasicFunctionality:
    """Test suite for PostmanExporter basic export functionality."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_export_empty_records(self, mock_mkdir, mock_file):
        """Test exporting empty records list."""
        records = []

        PostmanExporter.export(records, "test-session", "/tmp/output.json")

        # Verify directory was created with correct parameters
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Verify file was opened for writing
        mock_file.assert_called_once()
        call_args = mock_file.call_args
        assert str(call_args[0][0]).endswith("output.json")
        assert call_args[0][1] == 'w'
        assert call_args[1].get('encoding') == 'utf-8'

        # Verify write was called
        assert mock_file().write.called

        # Get the written data
        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        # Verify structure and types
        assert isinstance(collection, dict)
        assert isinstance(collection["item"], list)
        assert collection["item"] == []
        assert "test-session" in collection["info"]["name"]

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_export_single_get_request(self, mock_mkdir, mock_file):
        """Test exporting single GET request."""
        records = [SAMPLE_RECORD_GET]

        PostmanExporter.export(records, "test-session", "/tmp/output.json")

        # Verify file operations
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called_once()
        assert mock_file().write.called

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        # Verify structure and types
        assert isinstance(collection, dict)
        assert isinstance(collection["item"], list)
        assert len(collection["item"]) == 1

        item = collection["item"][0]
        assert isinstance(item, dict)
        assert isinstance(item["request"], dict)
        assert item["request"]["method"] == "GET"
        assert "users" in item["name"]

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_export_multiple_requests(self, mock_mkdir, mock_file):
        """Test exporting multiple requests."""
        records = [SAMPLE_RECORD_GET, SAMPLE_RECORD_POST]

        PostmanExporter.export(records, "test-session", "/tmp/output.json")

        # Verify file operations
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        assert mock_file().write.called

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        # Verify structure and types
        assert isinstance(collection, dict)
        assert isinstance(collection["item"], list)
        assert len(collection["item"]) == 2

        # Verify each item is properly formatted
        for item in collection["item"]:
            assert isinstance(item, dict)
            assert "request" in item
            assert "method" in item["request"]


class TestPostmanExporterCollectionStructure:
    """Test suite for Postman collection structure generation."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_collection_info_structure(self, mock_mkdir, mock_file):
        """Test collection info section structure."""
        records = [SAMPLE_RECORD_GET]

        PostmanExporter.export(records, "my-session", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        assert "info" in collection
        assert "name" in collection["info"]
        assert "schema" in collection["info"]
        assert "my-session" in collection["info"]["name"]
        assert "v2.1.0" in collection["info"]["schema"]

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_collection_includes_timestamp(self, mock_mkdir, mock_file):
        """Test that collection name includes timestamp."""
        records = [SAMPLE_RECORD_GET]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        # Check for @ separator and timestamp
        assert " @ " in collection["info"]["name"]


class TestPostmanExporterURLParsing:
    """Test suite for URL parsing and transformation."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_url_with_query_parameters(self, mock_mkdir, mock_file):
        """Test parsing URL with query parameters."""
        records = [SAMPLE_RECORD_GET]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        url_obj = collection["item"][0]["request"]["url"]
        assert "query" in url_obj
        assert len(url_obj["query"]) == 2
        # Check query parameters
        query_keys = [q["key"] for q in url_obj["query"]]
        assert "page" in query_keys
        assert "limit" in query_keys

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_url_protocol_extraction(self, mock_mkdir, mock_file):
        """Test protocol extraction from URL."""
        records = [SAMPLE_RECORD_GET]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        url_obj = collection["item"][0]["request"]["url"]
        assert url_obj["protocol"] == "https"

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_url_host_parsing(self, mock_mkdir, mock_file):
        """Test host parsing into array format."""
        records = [SAMPLE_RECORD_GET]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        url_obj = collection["item"][0]["request"]["url"]
        assert url_obj["host"] == ["api", "example", "com"]

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_url_path_parsing(self, mock_mkdir, mock_file):
        """Test path parsing into array format."""
        records = [SAMPLE_RECORD_GET]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        url_obj = collection["item"][0]["request"]["url"]
        assert url_obj["path"] == ["users"]

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_url_with_port_number(self, mock_mkdir, mock_file):
        """Test URL with port number removes port from host."""
        records = [SAMPLE_RECORD_WITH_PORT]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        url_obj = collection["item"][0]["request"]["url"]
        assert url_obj["host"] == ["localhost"]
        # Port should not be in host array

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_url_with_multiple_path_segments(self, mock_mkdir, mock_file):
        """Test URL with multiple path segments."""
        record = {
            "method": "GET",
            "url": "https://api.example.com/v1/users/123/posts",
            "req_headers": {},
            "req_body": "",
            "status": 200,
            "duration": 100
        }

        PostmanExporter.export([record], "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        url_obj = collection["item"][0]["request"]["url"]
        assert url_obj["path"] == ["v1", "users", "123", "posts"]

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_url_without_query_parameters(self, mock_mkdir, mock_file):
        """Test URL without query parameters doesn't include query field."""
        records = [SAMPLE_RECORD_POST]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        url_obj = collection["item"][0]["request"]["url"]
        assert "query" not in url_obj


class TestPostmanExporterHeadersAndBody:
    """Test suite for headers and body handling."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_headers_conversion(self, mock_mkdir, mock_file):
        """Test headers converted to Postman format."""
        records = [SAMPLE_RECORD_GET]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        headers = collection["item"][0]["request"]["header"]
        assert len(headers) == 2
        assert all("key" in h and "value" in h for h in headers)
        header_keys = [h["key"] for h in headers]
        assert "Authorization" in header_keys
        assert "Accept" in header_keys

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_post_request_with_body(self, mock_mkdir, mock_file):
        """Test POST request includes body."""
        records = [SAMPLE_RECORD_POST]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        request = collection["item"][0]["request"]
        assert "body" in request
        assert request["body"]["mode"] == "raw"
        assert "John" in request["body"]["raw"]

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_get_request_without_body(self, mock_mkdir, mock_file):
        """Test GET request without body doesn't include body field."""
        records = [SAMPLE_RECORD_GET]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        request = collection["item"][0]["request"]
        assert "body" not in request

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_empty_headers(self, mock_mkdir, mock_file):
        """Test handling of empty headers."""
        records = [SAMPLE_RECORD_WITH_PORT]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        collection = json.loads(written_data)

        headers = collection["item"][0]["request"]["header"]
        assert headers == []


class TestPostmanExporterFileIO:
    """Test suite for file I/O operations."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_creates_parent_directory(self, mock_mkdir, mock_file):
        """Test that parent directories are created."""
        records = [SAMPLE_RECORD_GET]

        PostmanExporter.export(records, "test", "/tmp/nested/dir/output.json")

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_writes_utf8_encoding(self, mock_mkdir, mock_file):
        """Test file is written with UTF-8 encoding."""
        records = [SAMPLE_RECORD_GET]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        # Check that open was called with UTF-8 encoding
        args, kwargs = mock_file.call_args
        assert kwargs.get("encoding") == "utf-8"

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_prints_export_summary(self, mock_mkdir, mock_file, capsys):
        """Test prints summary message."""
        records = [SAMPLE_RECORD_GET, SAMPLE_RECORD_POST]

        PostmanExporter.export(records, "test", "/tmp/output.json")

        captured = capsys.readouterr()
        assert "✓ Exported" in captured.out
        assert "2 requests" in captured.out
        assert "/tmp/output.json" in captured.out


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
