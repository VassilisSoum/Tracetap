"""
Tests for CLI output and error handling utilities
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tracetap.common.errors import (
    APIKeyMissingError,
    InvalidSessionError,
    CorruptFileError,
    TraceTapError,
)
from tracetap.common.output import (
    format_path,
    format_command,
)


class TestErrorMessages:
    """Test error message formatting"""

    def test_api_key_missing_error_has_suggestion(self):
        """Test APIKeyMissingError includes helpful suggestion"""
        error = APIKeyMissingError()
        assert "ANTHROPIC_API_KEY" in error.message
        assert "export" in error.suggestion
        assert "ANTHROPIC_API_KEY" in error.suggestion
        assert error.docs_link is not None

    def test_invalid_session_error_with_reason(self):
        """Test InvalidSessionError provides clear reason"""
        error = InvalidSessionError("/path/to/session", "Missing metadata.json")
        assert "/path/to/session" in error.message
        assert "Missing metadata.json" in error.suggestion
        assert "metadata.json" in error.suggestion
        assert "correlation.json" in error.suggestion
        assert "tracetap-record" in error.suggestion

    def test_corrupt_file_error_with_detail(self):
        """Test CorruptFileError provides recovery steps"""
        error = CorruptFileError("/path/to/file.json", "Invalid JSON at line 10")
        assert "/path/to/file.json" in error.message
        assert "Invalid JSON at line 10" in error.suggestion
        assert "re-record" in error.suggestion.lower()

    def test_generic_error_with_custom_suggestion(self):
        """Test generic TraceTapError with custom message"""
        error = TraceTapError(
            message="Something went wrong",
            suggestion="Try doing X, Y, and Z",
            docs_link="https://example.com/docs",
        )
        assert error.message == "Something went wrong"
        assert error.suggestion == "Try doing X, Y, and Z"
        assert error.docs_link == "https://example.com/docs"


class TestOutputFormatting:
    """Test output formatting utilities"""

    def test_format_path_adds_color_markup(self):
        """Test format_path adds magenta color markup"""
        result = format_path("/path/to/file.ts")
        assert "[magenta]" in result
        assert "/path/to/file.ts" in result
        assert "[/magenta]" in result

    def test_format_command_adds_bold_markup(self):
        """Test format_command adds bold white markup"""
        result = format_command("npm install")
        assert "[bold white]" in result
        assert "npm install" in result
        assert "[/bold white]" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
