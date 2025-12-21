"""
TraceTap Common Utilities

Shared utilities and helpers to reduce code duplication and improve security.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


def get_api_key_from_env() -> Optional[str]:
    """
    Securely retrieve Anthropic API key from environment variable.

    This is the ONLY approved method for getting API keys in TraceTap.
    API keys should NEVER be passed via CLI arguments to prevent exposure
    in process lists, shell history, and logs.

    Returns:
        API key from ANTHROPIC_API_KEY environment variable, or None if not set

    Example:
        api_key = get_api_key_from_env()
        if not api_key:
            print("Error: ANTHROPIC_API_KEY environment variable not set")
            print("Set it with: export ANTHROPIC_API_KEY=your_key")
            sys.exit(1)
    """
    return os.environ.get('ANTHROPIC_API_KEY')


def safe_json_parse(json_string: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with error handling.

    Args:
        json_string: JSON string to parse
        default: Default value to return if parsing fails

    Returns:
        Parsed JSON object, or default if parsing fails

    Example:
        body = safe_json_parse(capture.get("request_body"), default={})
    """
    if not json_string:
        return default

    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default


class CaptureLoader:
    """
    Standardized loader for TraceTap capture files.

    Handles different JSON formats used by TraceTap:
    - Format 1: {"requests": [...]}  (wrapped format)
    - Format 2: [...]                (direct list format)

    This is the single source of truth for loading capture files.
    All code that loads captures should use this class.

    Example:
        loader = CaptureLoader("captures.json")
        captures = loader.load()

        for capture in captures:
            print(capture['url'])
    """

    def __init__(self, file_path: str):
        """
        Initialize capture loader.

        Args:
            file_path: Path to capture JSON file
        """
        self.file_path = Path(file_path)

    def load(self) -> List[Dict[str, Any]]:
        """
        Load captures from JSON file.

        Returns:
            List of capture dictionaries

        Raises:
            FileNotFoundError: If capture file doesn't exist
            ValueError: If JSON format is invalid or unrecognized
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Capture file not found: {self.file_path}")

        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle different JSON log formats
        if isinstance(data, dict):
            # Format 1: {"requests": [...]}
            if 'requests' in data:
                return data['requests']
            # Format 2: {"captures": [...]} (alternative wrapper)
            elif 'captures' in data:
                return data['captures']
            else:
                raise ValueError(
                    f"Unexpected JSON format in {self.file_path}. "
                    f"Expected dict with 'requests' or 'captures' key, "
                    f"or a list of captures. Found keys: {list(data.keys())}"
                )
        elif isinstance(data, list):
            # Format 3: [...]
            return data
        else:
            raise ValueError(
                f"Unexpected JSON format in {self.file_path}. "
                f"Expected dict or list, got {type(data).__name__}"
            )

    @staticmethod
    def load_from_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Convenience method to load captures in one call.

        Args:
            file_path: Path to capture JSON file

        Returns:
            List of capture dictionaries

        Example:
            captures = CaptureLoader.load_from_file("captures.json")
        """
        loader = CaptureLoader(file_path)
        return loader.load()

    def validate_capture(self, capture: Dict[str, Any]) -> bool:
        """
        Validate that a capture has required fields.

        Args:
            capture: Capture dictionary to validate

        Returns:
            True if capture has minimum required fields
        """
        required_fields = ['url', 'method']
        return all(field in capture for field in required_fields)

    def load_and_validate(self) -> List[Dict[str, Any]]:
        """
        Load captures and filter out invalid ones.

        Returns:
            List of valid capture dictionaries
        """
        captures = self.load()
        valid_captures = [c for c in captures if self.validate_capture(c)]

        if len(valid_captures) < len(captures):
            invalid_count = len(captures) - len(valid_captures)
            print(f"Warning: Skipped {invalid_count} invalid captures")

        return valid_captures


def filter_interesting_headers(
    headers: Dict[str, str],
    additional_headers: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Filter headers to only include interesting ones for analysis/matching.

    This consolidates duplicate header filtering logic used across the codebase
    for AI analysis, request matching, and debugging.

    Args:
        headers: Dictionary of headers to filter
        additional_headers: Optional list of additional header names to include

    Returns:
        Filtered dictionary containing only interesting headers

    Example:
        filtered = filter_interesting_headers(
            request.headers,
            additional_headers=['x-custom-id']
        )
    """
    # Comprehensive list of interesting headers from all use cases
    interesting = [
        'authorization',
        'cookie',
        'set-cookie',
        'x-api-key',
        'x-auth-token',
        'x-session-id',
        'x-request-id',
        'x-correlation-id',
        'x-csrf-token',
        'x-requested-with',
        'content-type',
        'accept',
    ]

    # Add any additional headers specified
    if additional_headers:
        interesting.extend(h.lower() for h in additional_headers)

    # Filter headers (case-insensitive match)
    return {k: v for k, v in headers.items() if k.lower() in interesting}
