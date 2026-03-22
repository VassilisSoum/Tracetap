"""
TraceTap Common Utilities

Shared utilities and helpers used across TraceTap modules.
"""

from .utils import get_api_key_from_env, CaptureLoader, safe_json_parse, filter_interesting_headers
from .ai_utils import create_anthropic_client, ANTHROPIC_AVAILABLE
from .constants import (
    DEFAULT_CLAUDE_MODEL,
    MAX_GENERATION_TOKENS,
    MAX_VARIATION_TOKENS,
    API_TIMEOUT_SECONDS,
    MAX_API_RETRIES,
    get_model_config,
)
from .errors import (
    TraceTapError,
    APIKeyMissingError,
    InvalidSessionError,
    CorruptFileError,
    PortConflictError,
    CertificateError,
    BrowserLaunchError,
    NetworkError,
    handle_common_errors,
)
from .output import (
    console,
    success,
    error,
    warning,
    info,
    section_header,
    print_panel,
    print_stats,
    correlation_progress,
    generation_progress,
    recording_progress,
    print_summary,
    print_next_steps,
    print_troubleshooting,
    format_path,
    format_command,
    prompt_confirm,
    prompt_choice,
)

__all__ = [
    'get_api_key_from_env',
    'CaptureLoader',
    'safe_json_parse',
    'filter_interesting_headers',
    'create_anthropic_client',
    'ANTHROPIC_AVAILABLE',
    # Configuration constants
    'DEFAULT_CLAUDE_MODEL',
    'MAX_GENERATION_TOKENS',
    'MAX_VARIATION_TOKENS',
    'API_TIMEOUT_SECONDS',
    'MAX_API_RETRIES',
    'get_model_config',
    # Error handling
    'TraceTapError',
    'APIKeyMissingError',
    'InvalidSessionError',
    'CorruptFileError',
    'PortConflictError',
    'CertificateError',
    'BrowserLaunchError',
    'NetworkError',
    'handle_common_errors',
    # Output formatting
    'console',
    'success',
    'error',
    'warning',
    'info',
    'section_header',
    'print_panel',
    'print_stats',
    'correlation_progress',
    'generation_progress',
    'recording_progress',
    'print_summary',
    'print_next_steps',
    'print_troubleshooting',
    'format_path',
    'format_command',
    'prompt_confirm',
    'prompt_choice',
]
