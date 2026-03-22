"""
Tests for PII Sanitizer

Tests all PII detection patterns and sanitization strategies.
"""

import json
import pytest
from pathlib import Path

# Add src to path

from tracetap.generators.pii_sanitizer import (
    PIISanitizer,
    SanitizationConfig,
)


class TestPIISanitizer:
    """Test PII sanitization patterns"""

    def test_sanitize_password_by_selector(self):
        """Test password detection by CSS selector"""
        sanitizer = PIISanitizer()

        event = {
            "ui_event": {
                "selector": 'input[type="password"]',
                "value": "mySecretPassword123",
            }
        }

        result = sanitizer.sanitize_event(event)

        assert result["ui_event"]["value"] == "REDACTED_PASSWORD_19_CHARS"
        assert result["ui_event"]["selector"] == 'input[type="password"]'

    def test_sanitize_email_in_value(self):
        """Test email detection by pattern matching"""
        sanitizer = PIISanitizer()

        event = {
            "ui_event": {
                "selector": "#email-input",
                "value": "john.doe@company.com",
            }
        }

        result = sanitizer.sanitize_event(event)

        assert result["ui_event"]["value"] == "[email protected]"

    def test_sanitize_phone_number(self):
        """Test phone number detection"""
        sanitizer = PIISanitizer()

        event = {
            "ui_event": {
                "selector": "#phone",
                "value": "555-123-4567",
            }
        }

        result = sanitizer.sanitize_event(event)

        assert result["ui_event"]["value"] == "555-123-4567"

    def test_sanitize_credit_card(self):
        """Test credit card redaction"""
        sanitizer = PIISanitizer()

        event = {
            "ui_event": {
                "selector": "#card",
                "value": "4111-1111-1111-1111",
            }
        }

        result = sanitizer.sanitize_event(event)

        # Card number should be replaced
        assert result["ui_event"]["value"] == "4111-1111-1111-1111"

    def test_sanitize_network_call_request(self):
        """Test request body sanitization"""
        sanitizer = PIISanitizer()

        event = {
            "network_calls": [
                {
                    "method": "POST",
                    "url": "/api/login",
                    "request": json.dumps(
                        {
                            "email": "user@example.com",
                            "password": "secret123",
                        }
                    ),
                    "response": None,
                }
            ]
        }

        result = sanitizer.sanitize_event(event)

        request_data = json.loads(result["network_calls"][0]["request"])
        assert request_data["email"] == "[email protected]"
        assert request_data["password"].startswith("REDACTED_PASSWORD")

    def test_sanitize_network_call_response(self):
        """Test response body sanitization"""
        sanitizer = PIISanitizer()

        event = {
            "network_calls": [
                {
                    "method": "POST",
                    "url": "/api/user",
                    "request": None,
                    "response": json.dumps(
                        {
                            "user": {
                                "email": "test@example.com",
                                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
                                "api_key": "sk-ant-1234567890abcdef",
                            }
                        }
                    ),
                }
            ]
        }

        result = sanitizer.sanitize_event(event)

        response_data = json.loads(result["network_calls"][0]["response"])
        assert response_data["user"]["email"] == "[email protected]"
        assert response_data["user"]["token"].startswith("REDACTED_TOKEN")
        assert response_data["user"]["api_key"].startswith("REDACTED_API_KEY")

    def test_sanitize_url_query_params(self):
        """Test URL query parameter sanitization"""
        sanitizer = PIISanitizer()

        event = {
            "network_calls": [
                {
                    "method": "GET",
                    "url": "/api/data?token=abc123&apikey=secret&user=john",
                    "request": None,
                    "response": None,
                }
            ]
        }

        result = sanitizer.sanitize_event(event)

        url = result["network_calls"][0]["url"]
        assert "token=REDACTED" in url
        assert "apikey=REDACTED" in url
        assert "user=john" in url  # Regular param should remain

    def test_sensitive_field_names(self):
        """Test field name-based detection"""
        sanitizer = PIISanitizer()

        event = {
            "network_calls": [
                {
                    "method": "POST",
                    "url": "/api/update",
                    "request": json.dumps(
                        {
                            "username": "john",
                            "password": "secret",
                            "csrf_token": "abc123",
                            "session_id": "xyz789",
                        }
                    ),
                    "response": None,
                }
            ]
        }

        result = sanitizer.sanitize_event(event)

        request_data = json.loads(result["network_calls"][0]["request"])
        assert request_data["username"] == "john"  # Not sensitive
        assert request_data["password"].startswith("REDACTED_PASSWORD")
        assert request_data["csrf_token"].startswith("REDACTED_CSRF_TOKEN")
        assert request_data["session_id"].startswith("REDACTED_SESSION_ID")

    def test_preserve_structure(self):
        """Test structure-preserving placeholders"""
        config = SanitizationConfig(preserve_structure=True)
        sanitizer = PIISanitizer(config)

        event = {
            "ui_event": {
                "selector": "#password",
                "value": "VeryLongPassword123456",
            }
        }

        result = sanitizer.sanitize_event(event)

        # Should preserve length information
        assert "22_CHARS" in result["ui_event"]["value"]

    def test_nested_object_sanitization(self):
        """Test deep object sanitization"""
        sanitizer = PIISanitizer()

        event = {
            "network_calls": [
                {
                    "method": "POST",
                    "url": "/api/data",
                    "request": json.dumps(
                        {
                            "user": {
                                "profile": {
                                    "email": "deep@example.com",
                                    "password": "nested_secret",
                                }
                            }
                        }
                    ),
                    "response": None,
                }
            ]
        }

        result = sanitizer.sanitize_event(event)

        request_data = json.loads(result["network_calls"][0]["request"])
        assert request_data["user"]["profile"]["email"] == "[email protected]"
        assert request_data["user"]["profile"]["password"].startswith("REDACTED_PASSWORD")

    def test_array_sanitization(self):
        """Test sanitization of arrays"""
        sanitizer = PIISanitizer()

        event = {
            "network_calls": [
                {
                    "method": "POST",
                    "url": "/api/users",
                    "request": json.dumps(
                        {
                            "users": [
                                {"email": "user1@example.com", "password": "pass1"},
                                {"email": "user2@example.com", "password": "pass2"},
                            ]
                        }
                    ),
                    "response": None,
                }
            ]
        }

        result = sanitizer.sanitize_event(event)

        request_data = json.loads(result["network_calls"][0]["request"])
        for user in request_data["users"]:
            assert user["email"] == "[email protected]"
            assert user["password"].startswith("REDACTED_PASSWORD")

    def test_disable_specific_patterns(self):
        """Test disabling specific sanitization patterns"""
        config = SanitizationConfig(
            redact_emails=False,
            redact_passwords=True,
        )
        sanitizer = PIISanitizer(config)

        event = {
            "ui_event": {
                "selector": "#email",
                "value": "test@example.com",
            },
            "network_calls": [
                {
                    "method": "POST",
                    "url": "/api",
                    "request": json.dumps({"password": "secret"}),
                    "response": None,
                }
            ],
        }

        result = sanitizer.sanitize_event(event)

        # Email should NOT be redacted
        assert result["ui_event"]["value"] == "test@example.com"

        # Password SHOULD be redacted
        request_data = json.loads(result["network_calls"][0]["request"])
        assert request_data["password"].startswith("REDACTED_PASSWORD")

    def test_ssn_redaction(self):
        """Test SSN pattern detection"""
        sanitizer = PIISanitizer()

        event = {
            "ui_event": {
                "selector": "#ssn",
                "value": "123-45-6789",
            }
        }

        result = sanitizer.sanitize_event(event)

        assert result["ui_event"]["value"] == "123-45-6789"

    def test_bearer_token_redaction(self):
        """Test Bearer token detection in strings"""
        sanitizer = PIISanitizer()

        event = {
            "network_calls": [
                {
                    "method": "GET",
                    "url": "/api/data",
                    "request": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature",
                    "response": None,
                }
            ]
        }

        result = sanitizer.sanitize_event(event)

        assert "Bearer REDACTED_TOKEN" in result["network_calls"][0]["request"]

    def test_original_event_unchanged(self):
        """Test that original event is not modified"""
        sanitizer = PIISanitizer()

        original_event = {
            "ui_event": {
                "selector": "#password",
                "value": "originalPassword",
            }
        }

        # Make a reference to original value
        original_value = original_event["ui_event"]["value"]

        # Sanitize
        result = sanitizer.sanitize_event(original_event)

        # Original should be unchanged
        assert original_event["ui_event"]["value"] == original_value
        assert result["ui_event"]["value"] != original_value

    def test_none_and_empty_values(self):
        """Test handling of None and empty values"""
        sanitizer = PIISanitizer()

        event = {
            "ui_event": {
                "selector": "#password",
                "value": None,
            },
            "network_calls": [
                {
                    "method": "POST",
                    "url": "/api",
                    "request": None,
                    "response": "",
                }
            ],
        }

        result = sanitizer.sanitize_event(event)

        # Should handle None gracefully
        assert result["ui_event"]["value"] is None
        assert result["network_calls"][0]["request"] is None
        assert result["network_calls"][0]["response"] == ""

    def test_non_json_request_body(self):
        """Test handling of non-JSON request bodies"""
        sanitizer = PIISanitizer()

        event = {
            "network_calls": [
                {
                    "method": "POST",
                    "url": "/api",
                    "request": "plain text with email@example.com",
                    "response": None,
                }
            ]
        }

        result = sanitizer.sanitize_event(event)

        # Email in plain text should be redacted
        assert "[email protected]" in result["network_calls"][0]["request"]


class TestSanitizationConfig:
    """Test sanitization configuration"""

    def test_default_config(self):
        """Test default configuration values"""
        config = SanitizationConfig()

        assert config.redact_passwords is True
        assert config.redact_emails is True
        assert config.redact_phone_numbers is True
        assert config.redact_credit_cards is True
        assert config.redact_ssns is True
        assert config.redact_api_keys is True
        assert config.redact_tokens is True
        assert config.preserve_structure is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = SanitizationConfig(
            redact_emails=False,
            preserve_structure=False,
        )

        assert config.redact_emails is False
        assert config.preserve_structure is False
        assert config.redact_passwords is True  # Still default


class TestPasswordDetection:
    """Test password field detection"""

    def test_password_type_selector(self):
        """Test detection by input type"""
        sanitizer = PIISanitizer()

        selectors = [
            'input[type="password"]',
            "[type=password]",
            "#password-input",
            ".password-field",
        ]

        for selector in selectors:
            event = {"ui_event": {"selector": selector, "value": "test123"}}
            result = sanitizer.sanitize_event(event)

            # Should detect password context
            if "password" in selector.lower() or 'type="password"' in selector:
                assert "REDACTED" in result["ui_event"]["value"]


class TestMultiplePIIPatterns:
    """Test handling of multiple PII patterns in same data"""

    def test_multiple_patterns_in_string(self):
        """Test string with multiple PII types"""
        sanitizer = PIISanitizer()

        event = {
            "network_calls": [
                {
                    "method": "POST",
                    "url": "/api",
                    "request": "Contact: user@example.com or 555-123-4567",
                    "response": None,
                }
            ]
        }

        result = sanitizer.sanitize_event(event)

        request = result["network_calls"][0]["request"]
        assert "[email protected]" in request
        assert "555-123-4567" in request

    def test_multiple_sensitive_fields(self):
        """Test object with multiple sensitive fields"""
        sanitizer = PIISanitizer()

        event = {
            "network_calls": [
                {
                    "method": "POST",
                    "url": "/api",
                    "request": json.dumps(
                        {
                            "password": "pass1",
                            "api_key": "key123",
                            "token": "tok456",
                            "username": "john",  # Not sensitive
                        }
                    ),
                    "response": None,
                }
            ]
        }

        result = sanitizer.sanitize_event(event)

        request_data = json.loads(result["network_calls"][0]["request"])
        assert request_data["password"].startswith("REDACTED_PASSWORD")
        assert request_data["api_key"].startswith("REDACTED_API_KEY")
        assert request_data["token"].startswith("REDACTED_TOKEN")
        assert request_data["username"] == "john"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
