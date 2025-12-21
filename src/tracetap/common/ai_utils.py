"""
AI Utilities for TraceTap

Centralized AI client initialization to reduce code duplication.
"""

import os
from typing import Optional, Any, Tuple

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False


def create_anthropic_client(
    api_key: Optional[str] = None,
    raise_on_error: bool = False,
    verbose: bool = True
) -> Tuple[Optional[Any], bool, str]:
    """
    Create Anthropic AI client with standardized error handling.

    This is the centralized function for AI client initialization across TraceTap.
    Eliminates ~150 lines of duplicate code across 7+ files.

    Args:
        api_key: Optional API key (if not provided, reads from ANTHROPIC_API_KEY env var)
        raise_on_error: If True, raises exceptions. If False, returns None client with error message
        verbose: If True, prints status messages to stdout

    Returns:
        Tuple of (client, is_available, status_message)
        - client: Anthropic client instance or None
        - is_available: Boolean indicating if AI is available
        - status_message: Status message (success or error description)

    Examples:
        # Raise exceptions on errors (for strict initialization)
        client, available, msg = create_anthropic_client(raise_on_error=True)

        # Silent failure with status (for optional AI features)
        client, available, msg = create_anthropic_client(verbose=False)
        if not available:
            print(msg)

        # With custom API key
        client, available, msg = create_anthropic_client(api_key="custom-key")
    """
    # Check if anthropic library is available
    if not ANTHROPIC_AVAILABLE:
        error_msg = (
            "⚠ Claude AI not available: anthropic library not installed\n"
            "  Install: pip install anthropic"
        )
        if raise_on_error:
            raise ImportError(error_msg)
        if verbose:
            print(error_msg)
        return None, False, error_msg

    # SECURITY: Get API key from environment only (never accept via CLI)
    if api_key is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        error_msg = (
            "⚠ Claude AI not available: ANTHROPIC_API_KEY not set\n"
            "  Set: export ANTHROPIC_API_KEY=your_key\n"
            "  Get key: https://console.anthropic.com/"
        )
        if raise_on_error:
            raise ValueError(
                "API key required for AI conversion. Set ANTHROPIC_API_KEY environment variable.\n"
                "Example: export ANTHROPIC_API_KEY=your_key"
            )
        if verbose:
            print(error_msg)
        return None, False, error_msg

    # Initialize client
    try:
        client = anthropic.Anthropic(api_key=api_key)
        success_msg = "✓ Claude AI enabled"
        if verbose:
            print(success_msg)
        return client, True, success_msg
    except Exception as e:
        error_msg = f"⚠ Claude AI initialization failed: {e}"
        if raise_on_error:
            raise
        if verbose:
            print(error_msg)
        return None, False, error_msg
