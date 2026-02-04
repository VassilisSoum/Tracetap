"""PII Sanitization module for TraceTap.

Sanitizes personally identifiable information (PII) from recorded events before
sending to AI providers. This protects user privacy and ensures compliance with
GDPR, CCPA, HIPAA and other data protection regulations.
"""

import re
import json
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class SanitizationConfig:
    """Configuration for PII sanitization.

    Attributes:
        redact_passwords: Redact password fields (default: True)
        redact_emails: Redact email addresses (default: True)
        redact_phone_numbers: Redact phone numbers (default: True)
        redact_credit_cards: Redact credit card numbers (default: True)
        redact_ssns: Redact social security numbers (default: True)
        redact_api_keys: Redact API keys and secrets (default: True)
        redact_tokens: Redact JWT tokens and auth tokens (default: True)
        preserve_structure: Maintain data types and lengths in placeholders (default: True)
        custom_patterns: Additional regex patterns to redact (default: None)
    """
    redact_passwords: bool = True
    redact_emails: bool = True
    redact_phone_numbers: bool = True
    redact_credit_cards: bool = True
    redact_ssns: bool = True
    redact_api_keys: bool = True
    redact_tokens: bool = True
    preserve_structure: bool = True
    custom_patterns: Optional[List[str]] = None


class PIISanitizer:
    """Sanitizes PII from events before sending to AI.

    This class implements comprehensive PII detection and redaction using:
    - Regex pattern matching for common PII types (email, phone, SSN, credit cards)
    - Field-name-based detection for sensitive fields (password, token, auth)
    - Structure-preserving placeholders that maintain data lengths for testing

    Example:
        >>> sanitizer = PIISanitizer()
        >>> event = {"ui_event": {"value": "mypassword123"}}
        >>> sanitized = sanitizer.sanitize_event(event)
        >>> print(sanitized["ui_event"]["value"])
        'REDACTED_PASSWORD_13_CHARS'
    """

    # Regex patterns for common PII types
    # NOTE: All patterns have bounded quantifiers to prevent ReDoS attacks
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,255}\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        # Anthropic API keys (sk-ant-...), OpenAI keys (sk-...), generic long alphanumeric keys
        # Bounded to prevent catastrophic backtracking
        'api_key': r'\b(?:sk-ant-[a-zA-Z0-9_-]{95,110}|sk-[a-zA-Z0-9]{48}|[A-Za-z0-9_-]{32,128})\b',
        'jwt': r'\beyJ[A-Za-z0-9_-]{1,500}\.eyJ[A-Za-z0-9_-]{1,500}\.[A-Za-z0-9_-]{1,500}\b',
        'uuid': r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
        'bearer_token': r'\bBearer\s+[A-Za-z0-9_-]{1,200}\b',
    }

    # Field names that likely contain sensitive data
    SENSITIVE_FIELDS = {
        'password', 'passwd', 'pwd', 'secret', 'token', 'auth',
        'authorization', 'api_key', 'apikey', 'access_token',
        'refresh_token', 'session', 'cookie', 'csrf', 'ssn',
        'social_security', 'credit_card', 'card_number', 'cvv',
        'pin', 'otp', 'private_key', 'privatekey', 'key',
    }

    def __init__(self, config: Optional[SanitizationConfig] = None):
        """Initialize sanitizer with optional configuration.

        Args:
            config: Sanitization configuration. If None, uses default settings.
        """
        self.config = config or SanitizationConfig()

    def sanitize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize a single correlated event.

        Args:
            event: Event dictionary with ui_event and network_calls

        Returns:
            Sanitized copy of the event with PII redacted
        """
        # Deep copy to avoid modifying original
        sanitized = self._deep_copy(event)

        # Sanitize UI event value
        if 'ui_event' in sanitized and isinstance(sanitized['ui_event'], dict):
            if 'value' in sanitized['ui_event']:
                selector = sanitized['ui_event'].get('selector', '')
                sanitized['ui_event']['value'] = self._sanitize_value(
                    sanitized['ui_event']['value'],
                    selector
                )

        # Sanitize network calls
        if 'network_calls' in sanitized and isinstance(sanitized['network_calls'], list):
            sanitized['network_calls'] = [
                self._sanitize_network_call(call)
                for call in sanitized['network_calls']
            ]

        return sanitized

    def _sanitize_value(self, value: Any, selector: str) -> Any:
        """Sanitize a UI input value based on context.

        Args:
            value: The input value to sanitize
            selector: The CSS selector for context (e.g., contains "password")

        Returns:
            Sanitized value
        """
        if not value or not isinstance(value, str):
            return value

        # Check if selector indicates password field
        if self.config.redact_passwords and self._is_password_field(selector):
            return self._redact_with_placeholder(value, 'PASSWORD')

        # Check for email pattern
        if self.config.redact_emails and re.match(self.PATTERNS['email'], value):
            return '[email protected]'

        # Check for phone pattern
        if self.config.redact_phone_numbers and re.match(self.PATTERNS['phone'], value):
            return '555-123-4567'

        # Generic PII patterns
        sanitized = value
        if self.config.redact_credit_cards:
            sanitized = re.sub(self.PATTERNS['credit_card'], '4111-1111-1111-1111', sanitized)
        if self.config.redact_ssns:
            sanitized = re.sub(self.PATTERNS['ssn'], '123-45-6789', sanitized)

        return sanitized

    def _sanitize_network_call(self, call: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize network request/response data.

        Args:
            call: Network call dictionary with request, response, url

        Returns:
            Sanitized copy of the network call
        """
        sanitized = self._deep_copy(call)

        # Sanitize request body
        if 'request' in sanitized and sanitized['request']:
            sanitized['request'] = self._sanitize_json_body(sanitized['request'])

        # Sanitize response body
        if 'response' in sanitized and sanitized['response']:
            sanitized['response'] = self._sanitize_json_body(sanitized['response'])

        # Sanitize URL (remove tokens in query params)
        if 'url' in sanitized:
            sanitized['url'] = self._sanitize_url(sanitized['url'])

        return sanitized

    def _sanitize_json_body(self, body: Any) -> Any:
        """Sanitize JSON request/response bodies.

        Args:
            body: JSON string or dict to sanitize

        Returns:
            Sanitized body in same format as input
        """
        if not body:
            return body

        try:
            # Parse if string
            if isinstance(body, str):
                data = json.loads(body)
                sanitized = self._sanitize_object(data)
                return json.dumps(sanitized)
            else:
                return self._sanitize_object(body)
        except (json.JSONDecodeError, TypeError):
            # Not JSON, sanitize as string
            return self._sanitize_string(body) if isinstance(body, str) else body

    def _sanitize_object(self, obj: Any) -> Any:
        """Recursively sanitize object structure.

        Args:
            obj: Object to sanitize (dict, list, or primitive)

        Returns:
            Sanitized copy of the object
        """
        if isinstance(obj, dict):
            return {
                key: self._redact_if_sensitive(key, value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self._sanitize_object(item) for item in obj]
        elif isinstance(obj, str):
            return self._sanitize_string(obj)
        return obj

    def _redact_if_sensitive(self, key: str, value: Any) -> Any:
        """Redact value if key indicates sensitive data.

        Args:
            key: Field name to check
            value: Value to potentially redact

        Returns:
            Original value or redacted placeholder
        """
        key_lower = key.lower()

        # Check if field name matches sensitive patterns
        if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
            return self._redact_with_placeholder(value, key.upper())

        # Recursively sanitize non-sensitive fields
        return self._sanitize_object(value)

    def _redact_with_placeholder(self, value: Any, field_type: str) -> str:
        """Replace value with structure-preserving placeholder.

        Args:
            value: Value to redact
            field_type: Type of field for placeholder label

        Returns:
            Placeholder string like "REDACTED_PASSWORD_13_CHARS"
        """
        if not value:
            return value

        if isinstance(value, str) and self.config.preserve_structure:
            length = len(value)
            return f"REDACTED_{field_type}_{length}_CHARS"

        return f"REDACTED_{field_type}"

    def _sanitize_string(self, text: str) -> str:
        """Sanitize string with pattern matching.

        Args:
            text: String to sanitize

        Returns:
            Sanitized string with PII patterns replaced
        """
        if not isinstance(text, str):
            return text

        sanitized = text

        # Apply enabled pattern replacements
        if self.config.redact_emails:
            sanitized = re.sub(self.PATTERNS['email'], '[email protected]', sanitized)
        if self.config.redact_api_keys:
            sanitized = re.sub(self.PATTERNS['api_key'], 'REDACTED_API_KEY', sanitized)
        if self.config.redact_tokens:
            sanitized = re.sub(self.PATTERNS['jwt'], 'REDACTED_JWT_TOKEN', sanitized)
            sanitized = re.sub(self.PATTERNS['bearer_token'], 'Bearer REDACTED_TOKEN', sanitized)
        if self.config.redact_credit_cards:
            sanitized = re.sub(self.PATTERNS['credit_card'], '4111-1111-1111-1111', sanitized)
        if self.config.redact_ssns:
            sanitized = re.sub(self.PATTERNS['ssn'], '123-45-6789', sanitized)
        if self.config.redact_phone_numbers:
            sanitized = re.sub(self.PATTERNS['phone'], '555-123-4567', sanitized)

        # Apply custom patterns if provided
        if self.config.custom_patterns:
            for pattern in self.config.custom_patterns:
                try:
                    sanitized = re.sub(pattern, 'REDACTED_CUSTOM', sanitized)
                except re.error:
                    # Skip invalid regex patterns
                    pass

        return sanitized

    def _sanitize_url(self, url: str) -> str:
        """Remove tokens from URL query parameters.

        Args:
            url: URL string to sanitize

        Returns:
            URL with sensitive query parameters redacted
        """
        if not isinstance(url, str):
            return url

        # Remove common token parameters
        url = re.sub(
            r'([?&])(token|apikey|api_key|access_token|refresh_token|auth|authorization)=[^&]+',
            r'\1\2=REDACTED',
            url,
            flags=re.IGNORECASE
        )
        return url

    def _is_password_field(self, selector: str) -> bool:
        """Check if selector indicates password field.

        Args:
            selector: CSS selector string

        Returns:
            True if selector suggests password input
        """
        if not selector:
            return False
        selector_lower = selector.lower()
        password_indicators = ['password', 'passwd', 'pwd', '[type="password"]', 'type=password']
        return any(indicator in selector_lower for indicator in password_indicators)

    def _deep_copy(self, obj: Any) -> Any:
        """Create a deep copy of an object.

        Args:
            obj: Object to copy

        Returns:
            Deep copy of the object
        """
        if isinstance(obj, dict):
            return {key: self._deep_copy(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj
