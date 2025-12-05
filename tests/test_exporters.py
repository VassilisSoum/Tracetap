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

from exporters import PostmanExporter, RawLogExporter, OpenAPIExporter


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


class TestOpenAPIExporterBasicFunctionality:
    """Test suite for OpenAPIExporter basic export functionality."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_export_empty_records(self, mock_mkdir, mock_file):
        """Test exporting empty records list prints warning."""
        records = []

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        # Should print warning and return early (no file operations)
        mock_mkdir.assert_not_called()
        mock_file.assert_not_called()

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_export_single_get_request(self, mock_mkdir, mock_file):
        """Test exporting single GET request generates valid OpenAPI spec."""
        records = [{
            "method": "GET",
            "url": "https://api.example.com/users",
            "req_headers": {},
            "req_body": "",
            "status": 200,
            "response_body": '{"id": 1, "name": "John"}'
        }]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called_once()

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        # Verify OpenAPI 3.0 structure
        assert spec["openapi"] == "3.0.3"
        assert spec["info"]["title"] == "test-session"
        assert spec["info"]["version"] == "1.0.0"
        assert "paths" in spec
        assert "servers" in spec

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_export_with_custom_title_and_version(self, mock_mkdir, mock_file):
        """Test custom title and version in OpenAPI spec."""
        records = [{
            "method": "GET",
            "url": "https://api.example.com/users",
            "req_headers": {},
            "req_body": "",
            "status": 200,
            "response_body": ""
        }]

        OpenAPIExporter.export(
            records,
            "test-session",
            "/tmp/openapi.json",
            title="My API",
            version="2.0.0"
        )

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        assert spec["info"]["title"] == "My API"
        assert spec["info"]["version"] == "2.0.0"


class TestOpenAPIPathNormalization:
    """Test suite for path normalization and parameter detection."""

    def test_normalize_numeric_id(self):
        """Test numeric ID normalization."""
        assert OpenAPIExporter._normalize_path("https://api.example.com/users/123") == "/users/{id}"
        assert OpenAPIExporter._normalize_path("https://api.example.com/users/456/posts") == "/users/{id}/posts"
        assert OpenAPIExporter._normalize_path("https://api.example.com/posts/789/comments/999") == "/posts/{id}/comments/{id}"

    def test_normalize_uuid(self):
        """Test UUID normalization."""
        url = "https://api.example.com/users/550e8400-e29b-41d4-a716-446655440000"
        assert OpenAPIExporter._normalize_path(url) == "/users/{id}"

        url = "https://api.example.com/orders/123e4567-e89b-12d3-a456-426614174000/items"
        assert OpenAPIExporter._normalize_path(url) == "/orders/{id}/items"

    def test_normalize_alphanumeric_id(self):
        """Test alphanumeric ID normalization (8+ chars)."""
        assert OpenAPIExporter._normalize_path("https://api.example.com/posts/abc123def") == "/posts/{id}"
        assert OpenAPIExporter._normalize_path("https://api.example.com/users/user_12345") == "/users/{id}"

    def test_normalize_short_alphanumeric_not_replaced(self):
        """Test short alphanumeric segments (< 8 chars) are not replaced."""
        assert OpenAPIExporter._normalize_path("https://api.example.com/api/v1/users") == "/api/v1/users"
        assert OpenAPIExporter._normalize_path("https://api.example.com/en/users") == "/en/users"

    def test_normalize_preserves_trailing_slash(self):
        """Test trailing slash preservation."""
        assert OpenAPIExporter._normalize_path("https://api.example.com/users/123/") == "/users/{id}/"


class TestOpenAPISchemaInference:
    """Test suite for JSON schema inference."""

    def test_infer_primitive_types(self):
        """Test inference of primitive types."""
        assert OpenAPIExporter._infer_schema(None) == {"type": "null"}
        assert OpenAPIExporter._infer_schema(True) == {"type": "boolean"}
        assert OpenAPIExporter._infer_schema(False) == {"type": "boolean"}
        assert OpenAPIExporter._infer_schema(42) == {"type": "integer"}
        assert OpenAPIExporter._infer_schema(3.14) == {"type": "number"}
        assert OpenAPIExporter._infer_schema("hello") == {"type": "string"}

    def test_infer_empty_array(self):
        """Test inference of empty array."""
        schema = OpenAPIExporter._infer_schema([])
        assert schema == {"type": "array", "items": {}}

    def test_infer_array_of_primitives(self):
        """Test inference of array with primitive items."""
        schema = OpenAPIExporter._infer_schema([1, 2, 3])
        assert schema == {"type": "array", "items": {"type": "integer"}}

        schema = OpenAPIExporter._infer_schema(["a", "b", "c"])
        assert schema == {"type": "array", "items": {"type": "string"}}

    def test_infer_simple_object(self):
        """Test inference of simple object."""
        data = {"id": 1, "name": "John", "active": True}
        schema = OpenAPIExporter._infer_schema(data)

        assert schema["type"] == "object"
        assert "properties" in schema
        assert schema["properties"]["id"] == {"type": "integer"}
        assert schema["properties"]["name"] == {"type": "string"}
        assert schema["properties"]["active"] == {"type": "boolean"}
        assert set(schema["required"]) == {"id", "name", "active"}

    def test_infer_object_with_null_values(self):
        """Test inference with null values (not required)."""
        data = {"id": 1, "optional": None}
        schema = OpenAPIExporter._infer_schema(data)

        assert schema["type"] == "object"
        assert schema["properties"]["id"] == {"type": "integer"}
        assert schema["properties"]["optional"] == {"type": "null"}
        assert schema["required"] == ["id"]  # None values not required

    def test_infer_nested_object(self):
        """Test inference of nested objects."""
        data = {
            "user": {
                "id": 1,
                "name": "John"
            },
            "active": True
        }
        schema = OpenAPIExporter._infer_schema(data)

        assert schema["type"] == "object"
        assert schema["properties"]["user"]["type"] == "object"
        assert schema["properties"]["user"]["properties"]["id"] == {"type": "integer"}
        assert schema["properties"]["user"]["properties"]["name"] == {"type": "string"}
        assert schema["properties"]["active"] == {"type": "boolean"}

    def test_infer_array_of_objects(self):
        """Test inference of array containing objects."""
        data = [
            {"id": 1, "name": "John"},
            {"id": 2, "name": "Jane"}
        ]
        schema = OpenAPIExporter._infer_schema(data)

        assert schema["type"] == "array"
        assert schema["items"]["type"] == "object"
        assert schema["items"]["properties"]["id"] == {"type": "integer"}
        assert schema["items"]["properties"]["name"] == {"type": "string"}


class TestOpenAPIEndpointGrouping:
    """Test suite for endpoint grouping and operation building."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_groups_same_path_different_methods(self, mock_mkdir, mock_file):
        """Test same path with different methods grouped together."""
        records = [
            {
                "method": "GET",
                "url": "https://api.example.com/users",
                "req_headers": {},
                "req_body": "",
                "status": 200,
                "response_body": "[]"
            },
            {
                "method": "POST",
                "url": "https://api.example.com/users",
                "req_headers": {},
                "req_body": '{"name": "John"}',
                "status": 201,
                "response_body": '{"id": 1}'
            }
        ]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        # Should have one path with two operations
        assert len(spec["paths"]) == 1
        assert "/users" in spec["paths"]
        assert "get" in spec["paths"]["/users"]
        assert "post" in spec["paths"]["/users"]

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_extracts_query_parameters(self, mock_mkdir, mock_file):
        """Test query parameters are extracted."""
        records = [{
            "method": "GET",
            "url": "https://api.example.com/users?page=1&limit=10",
            "req_headers": {},
            "req_body": "",
            "status": 200,
            "response_body": "[]"
        }]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        # Check parameters were extracted
        params = spec["paths"]["/users"]["get"]["parameters"]
        param_names = [p["name"] for p in params]
        assert "page" in param_names
        assert "limit" in param_names

        # Verify parameter structure
        page_param = next(p for p in params if p["name"] == "page")
        assert page_param["in"] == "query"
        assert page_param["required"] is False
        assert page_param["schema"]["type"] == "string"
        assert page_param["example"] == "1"

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_extracts_path_parameters(self, mock_mkdir, mock_file):
        """Test path parameters are extracted from normalized paths."""
        records = [{
            "method": "GET",
            "url": "https://api.example.com/users/123",
            "req_headers": {},
            "req_body": "",
            "status": 200,
            "response_body": '{"id": 123}'
        }]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        # Path should be normalized with {id}
        assert "/users/{id}" in spec["paths"]

        # Should have path parameter
        params = spec["paths"]["/users/{id}"]["get"]["parameters"]
        id_param = next(p for p in params if p["name"] == "id")
        assert id_param["in"] == "path"
        assert id_param["required"] is True
        assert id_param["schema"]["type"] == "string"


class TestOpenAPIResponseHandling:
    """Test suite for response handling and schema generation."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_handles_json_response(self, mock_mkdir, mock_file):
        """Test JSON response schema generation."""
        records = [{
            "method": "GET",
            "url": "https://api.example.com/users",
            "req_headers": {},
            "req_body": "",
            "status": 200,
            "response_body": '{"id": 1, "name": "John", "active": true}'
        }]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        response = spec["paths"]["/users"]["get"]["responses"]["200"]
        assert "application/json" in response["content"]

        schema = response["content"]["application/json"]["schema"]
        assert schema["type"] == "object"
        assert schema["properties"]["id"]["type"] == "integer"
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["active"]["type"] == "boolean"

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_handles_multiple_status_codes(self, mock_mkdir, mock_file):
        """Test multiple status codes for same endpoint."""
        records = [
            {
                "method": "GET",
                "url": "https://api.example.com/users/123",
                "req_headers": {},
                "req_body": "",
                "status": 200,
                "response_body": '{"id": 123}'
            },
            {
                "method": "GET",
                "url": "https://api.example.com/users/999",
                "req_headers": {},
                "req_body": "",
                "status": 404,
                "response_body": '{"error": "Not found"}'
            }
        ]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        responses = spec["paths"]["/users/{id}"]["get"]["responses"]
        assert "200" in responses
        assert "404" in responses

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_handles_non_json_response(self, mock_mkdir, mock_file):
        """Test non-JSON response handling."""
        records = [{
            "method": "GET",
            "url": "https://api.example.com/health",
            "req_headers": {},
            "req_body": "",
            "status": 200,
            "response_body": "OK"
        }]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        response = spec["paths"]["/health"]["get"]["responses"]["200"]
        assert "text/plain" in response["content"]

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_handles_empty_response_body(self, mock_mkdir, mock_file):
        """Test empty response body handling."""
        records = [{
            "method": "DELETE",
            "url": "https://api.example.com/users/123",
            "req_headers": {},
            "req_body": "",
            "status": 204,
            "response_body": ""
        }]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        response = spec["paths"]["/users/{id}"]["delete"]["responses"]["204"]
        assert "description" in response
        # Empty response should not have content
        assert "content" not in response or response.get("content") == {}


class TestOpenAPIRequestBodyHandling:
    """Test suite for request body handling."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_handles_json_request_body(self, mock_mkdir, mock_file):
        """Test JSON request body schema generation."""
        records = [{
            "method": "POST",
            "url": "https://api.example.com/users",
            "req_headers": {},
            "req_body": '{"name": "John", "email": "john@example.com", "age": 30}',
            "status": 201,
            "response_body": '{"id": 1}'
        }]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        request_body = spec["paths"]["/users"]["post"]["requestBody"]
        assert request_body["required"] is True
        assert "application/json" in request_body["content"]

        schema = request_body["content"]["application/json"]["schema"]
        assert schema["type"] == "object"
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["email"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_handles_non_json_request_body(self, mock_mkdir, mock_file):
        """Test non-JSON request body."""
        records = [{
            "method": "POST",
            "url": "https://api.example.com/upload",
            "req_headers": {},
            "req_body": "plain text data",
            "status": 200,
            "response_body": ""
        }]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        request_body = spec["paths"]["/upload"]["post"]["requestBody"]
        assert "text/plain" in request_body["content"]

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_no_request_body_for_get(self, mock_mkdir, mock_file):
        """Test GET requests don't have requestBody."""
        records = [{
            "method": "GET",
            "url": "https://api.example.com/users",
            "req_headers": {},
            "req_body": "",
            "status": 200,
            "response_body": "[]"
        }]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        # GET should not have requestBody
        assert "requestBody" not in spec["paths"]["/users"]["get"]


class TestOpenAPIServerExtraction:
    """Test suite for server URL extraction."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_extracts_single_server(self, mock_mkdir, mock_file):
        """Test single server extraction."""
        records = [{
            "method": "GET",
            "url": "https://api.example.com/users",
            "req_headers": {},
            "req_body": "",
            "status": 200,
            "response_body": "[]"
        }]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        assert len(spec["servers"]) == 1
        assert spec["servers"][0]["url"] == "https://api.example.com"

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_extracts_multiple_servers(self, mock_mkdir, mock_file):
        """Test multiple unique servers."""
        records = [
            {
                "method": "GET",
                "url": "https://api.example.com/users",
                "req_headers": {},
                "req_body": "",
                "status": 200,
                "response_body": "[]"
            },
            {
                "method": "GET",
                "url": "https://api2.example.com/users",
                "req_headers": {},
                "req_body": "",
                "status": 200,
                "response_body": "[]"
            },
            {
                "method": "GET",
                "url": "http://localhost:8080/users",
                "req_headers": {},
                "req_body": "",
                "status": 200,
                "response_body": "[]"
            }
        ]

        OpenAPIExporter.export(records, "test-session", "/tmp/openapi.json")

        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        spec = json.loads(written_data)

        assert len(spec["servers"]) == 3
        server_urls = [s["url"] for s in spec["servers"]]
        assert "https://api.example.com" in server_urls
        assert "https://api2.example.com" in server_urls
        assert "http://localhost:8080" in server_urls


class TestOpenAPIFileIO:
    """Test suite for file I/O operations."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_creates_parent_directory(self, mock_mkdir, mock_file):
        """Test parent directories are created."""
        records = [{
            "method": "GET",
            "url": "https://api.example.com/users",
            "req_headers": {},
            "req_body": "",
            "status": 200,
            "response_body": ""
        }]

        OpenAPIExporter.export(records, "test", "/tmp/nested/dir/openapi.json")

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_writes_utf8_encoding(self, mock_mkdir, mock_file):
        """Test file written with UTF-8 encoding."""
        records = [{
            "method": "GET",
            "url": "https://api.example.com/users",
            "req_headers": {},
            "req_body": "",
            "status": 200,
            "response_body": ""
        }]

        OpenAPIExporter.export(records, "test", "/tmp/openapi.json")

        args, kwargs = mock_file.call_args
        assert kwargs.get("encoding") == "utf-8"

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_prints_summary(self, mock_mkdir, mock_file, capsys):
        """Test prints export summary."""
        records = [
            {
                "method": "GET",
                "url": "https://api.example.com/users",
                "req_headers": {},
                "req_body": "",
                "status": 200,
                "response_body": ""
            },
            {
                "method": "POST",
                "url": "https://api.example.com/posts",
                "req_headers": {},
                "req_body": '{"title": "Test"}',
                "status": 201,
                "response_body": ""
            }
        ]

        OpenAPIExporter.export(records, "test", "/tmp/openapi.json")

        captured = capsys.readouterr()
        assert "✓ Exported OpenAPI 3.0 spec" in captured.out
        assert "2 endpoints" in captured.out
        assert "/tmp/openapi.json" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
