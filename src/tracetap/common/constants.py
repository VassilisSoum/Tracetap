"""TraceTap configuration constants.

Centralized configuration for API models, timeouts, and limits.
Environment variables can override defaults for flexibility.
"""

import os

# Claude AI Model Configuration
DEFAULT_CLAUDE_MODEL = os.environ.get(
    "TRACETAP_CLAUDE_MODEL",
    "claude-sonnet-4-5-20250514"
)

# Token limits per operation
MAX_GENERATION_TOKENS = int(os.environ.get("TRACETAP_MAX_TOKENS", "8192"))
MAX_VARIATION_TOKENS = int(os.environ.get("TRACETAP_VARIATION_TOKENS", "4096"))

# Timeout configurations (in seconds)
API_TIMEOUT_SECONDS = int(os.environ.get("TRACETAP_API_TIMEOUT", "300"))

# Retry configuration
MAX_API_RETRIES = int(os.environ.get("TRACETAP_MAX_RETRIES", "3"))
MAX_GENERATION_RETRIES = int(os.environ.get("TRACETAP_MAX_GENERATION_RETRIES", "2"))


def get_model_config(model: str = None) -> dict:
    """Get configuration for a specific model.

    Args:
        model: Model name. If None, uses DEFAULT_CLAUDE_MODEL.

    Returns:
        Dictionary with model configuration.
    """
    model = model or DEFAULT_CLAUDE_MODEL
    return {"max_tokens": MAX_GENERATION_TOKENS}
