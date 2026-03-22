"""TraceTap configuration constants.

Centralized configuration for API models, timeouts, and limits.
Environment variables can override defaults for flexibility.
"""

import os

# Claude AI Model Configuration
# Users can override via env var if the default doesn't work on their plan
DEFAULT_CLAUDE_MODEL = os.environ.get(
    "TRACETAP_CLAUDE_MODEL",
    "claude-sonnet-4-5-20250514"
)

# Fallback models to try if the default returns 404
MODEL_FALLBACKS = [
    "claude-sonnet-4-5-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-haiku-20240307",
]

# Token limits per operation
MAX_GENERATION_TOKENS = int(os.environ.get("TRACETAP_MAX_TOKENS", "8192"))
MAX_VARIATION_TOKENS = int(os.environ.get("TRACETAP_VARIATION_TOKENS", "4096"))

# Timeout configurations (in seconds)
API_TIMEOUT_SECONDS = int(os.environ.get("TRACETAP_API_TIMEOUT", "300"))

# Retry configuration
MAX_API_RETRIES = int(os.environ.get("TRACETAP_MAX_RETRIES", "3"))
MAX_GENERATION_RETRIES = int(os.environ.get("TRACETAP_MAX_GENERATION_RETRIES", "2"))
