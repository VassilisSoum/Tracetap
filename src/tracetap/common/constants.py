"""TraceTap configuration constants.

Centralized configuration for API models, timeouts, and limits.
Environment variables can override defaults for flexibility.
"""

import os

# Claude AI Model Configuration
DEFAULT_CLAUDE_MODEL = os.environ.get(
    "TRACETAP_CLAUDE_MODEL",
    "claude-sonnet-4-5-20250929"
)

# Token limits per operation
MAX_GENERATION_TOKENS = int(os.environ.get("TRACETAP_MAX_TOKENS", "4096"))
MAX_VARIATION_TOKENS = int(os.environ.get("TRACETAP_VARIATION_TOKENS", "2048"))

# Timeout configurations (in seconds)
API_TIMEOUT_SECONDS = int(os.environ.get("TRACETAP_API_TIMEOUT", "300"))

# Retry configuration
MAX_API_RETRIES = int(os.environ.get("TRACETAP_MAX_RETRIES", "3"))

# Model-specific configurations
MODEL_CONFIGS = {
    "claude-sonnet-4-5-20250929": {
        "max_tokens": 4096,
        "supports_vision": False,
    },
    "claude-opus-4-5-20251101": {
        "max_tokens": 4096,
        "supports_vision": True,
    },
}


def get_model_config(model: str = None) -> dict:
    """Get configuration for a specific model.

    Args:
        model: Model name. If None, uses DEFAULT_CLAUDE_MODEL.

    Returns:
        Dictionary with model configuration.
        Falls back to sensible defaults if model not recognized.
    """
    model = model or DEFAULT_CLAUDE_MODEL
    return MODEL_CONFIGS.get(
        model,
        {"max_tokens": 4096, "supports_vision": False}  # Default fallback
    )
