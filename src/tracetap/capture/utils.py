"""
Utility functions for TraceTap.

Provides helper functions for:
- Body text extraction
- Request duration calculation
- Console color formatting
"""

from mitmproxy import http


def safe_body(text: str, raw: bytes, max_bytes: int = 64 * 1024) -> str:
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
    except Exception:
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
            return int(duration * 1000)
    except Exception:
        # If timing data is not available, return 0
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
    if 200 <= status < 300:
        return "\033[32m"  # Green
    elif 300 <= status < 400:
        return "\033[36m"  # Cyan
    elif 400 <= status < 500:
        return "\033[33m"  # Yellow
    elif 500 <= status < 600:
        return "\033[31m"  # Red
    return ""
