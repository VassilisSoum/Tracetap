"""
Utility functions for TraceTap.

Provides helper functions for:
- Body text extraction
- Request duration calculation
- Console color formatting
"""

from mitmproxy import http

# Constants for body size limiting
MAX_BODY_SIZE = 64 * 1024  # 64 KB

# HTTP status code ranges
HTTP_STATUS_2XX_MIN = 200
HTTP_STATUS_2XX_MAX = 300
HTTP_STATUS_3XX_MIN = 300
HTTP_STATUS_3XX_MAX = 400
HTTP_STATUS_4XX_MIN = 400
HTTP_STATUS_4XX_MAX = 500
HTTP_STATUS_5XX_MIN = 500
HTTP_STATUS_5XX_MAX = 600

# ANSI color codes
ANSI_GREEN = "\033[32m"
ANSI_CYAN = "\033[36m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"
ANSI_RESET = "\033[0m"

# Time conversion
MILLISECONDS_PER_SECOND = 1000


def safe_body(text: str, raw: bytes, max_bytes: int = MAX_BODY_SIZE) -> str:
    """
    Safely extract body text, limiting size to prevent memory issues.

    Handles both text and binary data gracefully:
    - If text is available, use it (already decoded)
    - Otherwise, try to decode raw bytes as UTF-8
    - If binary/non-UTF-8, return a placeholder

    Args:
        text: Decoded text body (may be empty)
        raw: Raw bytes of body
        max_bytes: Maximum size to capture (default 64KB)

    Returns:
        Body as string, or placeholder for binary data
    """
    try:
        if text:
            # Text is already decoded, just limit size
            return text[:max_bytes]
        elif raw:
            # Try to decode raw bytes as UTF-8
            return raw[:max_bytes].decode('utf-8', errors='replace')
        return ""
    except (UnicodeDecodeError, AttributeError, TypeError):
        # Fallback for binary data or encoding errors
        return f"[binary data: {len(raw)} bytes]" if raw else ""


def calc_duration(flow: http.HTTPFlow) -> int:
    """
    Calculate request duration in milliseconds.

    Duration is measured from when the server connection started to when
    it completed. This includes:
    - DNS resolution
    - TCP handshake
    - TLS handshake (for HTTPS)
    - Request transmission
    - Server processing
    - Response transmission

    Args:
        flow: The HTTP flow object

    Returns:
        Duration in milliseconds, or 0 if not available
    """
    try:
        # Check if we have server connection timing data
        if hasattr(flow, 'server_conn') and flow.server_conn and flow.server_conn.timestamp_end:
            # Calculate duration in seconds, then convert to milliseconds
            duration = flow.server_conn.timestamp_end - flow.server_conn.timestamp_start
            return int(duration * MILLISECONDS_PER_SECOND)
    except (AttributeError, TypeError):
        # If timing data is not available or calculation fails, return 0
        pass
    return 0


def status_color(status: int) -> str:
    """
    Get ANSI color code for HTTP status code.

    Color coding:
    - 2xx (Success): Green
    - 3xx (Redirect): Cyan
    - 4xx (Client Error): Yellow
    - 5xx (Server Error): Red

    Args:
        status: HTTP status code (200, 404, 500, etc.)

    Returns:
        ANSI escape code for color
    """
    if HTTP_STATUS_2XX_MIN <= status < HTTP_STATUS_2XX_MAX:
        return ANSI_GREEN
    elif HTTP_STATUS_3XX_MIN <= status < HTTP_STATUS_3XX_MAX:
        return ANSI_CYAN
    elif HTTP_STATUS_4XX_MIN <= status < HTTP_STATUS_4XX_MAX:
        return ANSI_YELLOW
    elif HTTP_STATUS_5XX_MIN <= status < HTTP_STATUS_5XX_MAX:
        return ANSI_RED
    return ""
