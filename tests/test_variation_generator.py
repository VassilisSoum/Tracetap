"""
Tests for Variation Generator

Tests test data variation generation with AI mocking.
"""

import json
import pytest
from pathlib import Path
from dataclasses import dataclass
from unittest.mock import Mock, patch, MagicMock

# Add src to path

from tracetap.generators.variation_generator import (
    VariationGenerator,
    TestVariation,
    VariationType,
)


# Mock UI event for testing
@dataclass
class MockUIEvent:
    """Mock UI event"""

    type: str
    selector: str
    value: str


# Mock correlated event for testing
@dataclass
class MockCorrelatedEvent:
    """Mock correlated event"""

    ui_event: MockUIEvent


class TestVariationGenerator:
    """Test variation generation (with mocked AI)"""

    def test_initialization_without_api_key(self):
        """Test initialization without API key"""
        with patch.dict("os.environ", {}, clear=True):
            generator = VariationGenerator()

            assert generator.client is None

    def test_initialization_with_api_key(self):
        """Test initialization with API key"""
        with patch("tracetap.generators.variation_generator.anthropic") as mock_anthropic:
            generator = VariationGenerator(api_key="sk-test-key")

            mock_anthropic.Anthropic.assert_called_once_with(api_key="sk-test-key")

    def test_extract_input_fields(self):
        """Test extracting input fields from events"""
        generator = VariationGenerator(api_key="test")

        events = [
            MockCorrelatedEvent(
                ui_event=MockUIEvent(
                    type="fill", selector="#email", value="test@example.com"
                )
            ),
            MockCorrelatedEvent(
                ui_event=MockUIEvent(
                    type="fill", selector="#password", value="secret123"
                )
            ),
            MockCorrelatedEvent(
                ui_event=MockUIEvent(
                    type="click", selector="#submit-button", value=""
                )
            ),
        ]

        input_fields = generator._extract_input_fields(events)

        # Should extract only fill/type events with values
        assert len(input_fields) == 2

        # Check email field
        email_field = next(f for f in input_fields if "email" in f["selector"])
        assert email_field["value"] == "test@example.com"
        assert email_field["type"] == "fill"
        assert email_field["context"] == "email"

        # Check password field
        password_field = next(f for f in input_fields if "password" in f["selector"])
        assert password_field["value"] == "secret123"
        assert password_field["context"] == "password"

    def test_infer_email_context(self):
        """Test email field context inference"""
        generator = VariationGenerator(api_key="test")

        context = generator._infer_field_context("#email-input", "user@example.com")
        assert context == "email"

        context = generator._infer_field_context("#user-email", "test@test.com")
        assert context == "email"

    def test_infer_password_context(self):
        """Test password field context inference"""
        generator = VariationGenerator(api_key="test")

        context = generator._infer_field_context("#password", "secret")
        assert context == "password"

        context = generator._infer_field_context('input[type="password"]', "pass123")
        assert context == "password"

    def test_infer_phone_context(self):
        """Test phone field context inference"""
        generator = VariationGenerator(api_key="test")

        context = generator._infer_field_context("#phone", "555-1234")
        assert context == "phone"

        context = generator._infer_field_context("#mobile-number", "123-456-7890")
        assert context == "phone"

    def test_infer_name_context(self):
        """Test name field context inference"""
        generator = VariationGenerator(api_key="test")

        context = generator._infer_field_context("#username", "john_doe")
        assert context == "name"

        context = generator._infer_field_context("#full-name", "John Doe")
        assert context == "name"

    def test_infer_number_context(self):
        """Test number field context inference"""
        generator = VariationGenerator(api_key="test")

        context = generator._infer_field_context("#age", "25")
        assert context == "number"

        # Also infer from value
        context = generator._infer_field_context("#input", "12345")
        assert context == "number"

    def test_infer_fallback_to_text(self):
        """Test fallback to text context"""
        generator = VariationGenerator(api_key="test")

        context = generator._infer_field_context("#unknown-field", "some value")
        assert context == "text"

    @patch("tracetap.generators.variation_generator.anthropic")
    def test_generate_variations_happy_path(self, mock_anthropic):
        """Test generating variations including happy path"""
        # Mock AI response
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = json.dumps(
            {
                "modified_values": {"#email": "edge@example.com"},
                "expected_outcome": "validation_error",
                "description": "Edge case with empty email",
            }
        )
        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        generator = VariationGenerator(api_key="test-key")

        events = [
            MockCorrelatedEvent(
                ui_event=MockUIEvent(type="fill", selector="#email", value="test@test.com")
            )
        ]

        variations = generator.generate_variations(events, count=2)

        assert len(variations) == 2

        # First variation should be happy path
        assert variations[0].variation_number == 1
        assert variations[0].variation_type == VariationType.HAPPY_PATH
        assert variations[0].description == "Happy path with original input data"
        assert variations[0].modified_events == events

        # Second variation should be AI-generated
        assert variations[1].variation_number == 2
        assert variations[1].variation_type == VariationType.EDGE_CASE

    @patch("tracetap.generators.variation_generator.anthropic")
    def test_build_variation_prompt(self, mock_anthropic):
        """Test variation prompt building"""
        mock_anthropic.Anthropic.return_value = MagicMock()

        generator = VariationGenerator(api_key="test")

        input_fields = [
            {
                "selector": "#email",
                "value": "test@example.com",
                "type": "fill",
                "context": "email",
            }
        ]

        prompt = generator._build_variation_prompt(
            input_fields, VariationType.EDGE_CASE
        )

        assert "EDGE_CASE" in prompt
        assert "empty strings" in prompt.lower()
        assert "max length" in prompt.lower()
        assert "#email" in prompt
        assert "modified_values" in prompt
        assert "expected_outcome" in prompt

    @patch("tracetap.generators.variation_generator.anthropic")
    def test_variation_types_prompts(self, mock_anthropic):
        """Test different variation type prompts"""
        mock_anthropic.Anthropic.return_value = MagicMock()

        generator = VariationGenerator(api_key="test")

        input_fields = [{"selector": "#test", "value": "test", "type": "fill", "context": "text"}]

        # Test each variation type
        for var_type in [
            VariationType.EDGE_CASE,
            VariationType.BOUNDARY,
            VariationType.ERROR_CASE,
            VariationType.SECURITY,
        ]:
            prompt = generator._build_variation_prompt(input_fields, var_type)

            assert var_type.value.upper() in prompt
            assert "modified_values" in prompt

    def test_fallback_variation_edge_case(self):
        """Test fallback variation for edge cases"""
        generator = VariationGenerator(api_key="test")

        input_fields = [
            {"selector": "#email", "value": "test@example.com", "context": "email"},
            {"selector": "#name", "value": "John Doe", "context": "text"},
        ]

        fallback = generator._create_fallback_variation(
            input_fields, VariationType.EDGE_CASE
        )

        assert fallback["expected_outcome"] == "validation_error"
        assert fallback["modified_values"]["#email"] == ""
        assert fallback["modified_values"]["#name"] == ""

    def test_fallback_variation_boundary(self):
        """Test fallback variation for boundary values"""
        generator = VariationGenerator(api_key="test")

        input_fields = [
            {"selector": "#age", "value": "25", "context": "number"},
            {"selector": "#name", "value": "John", "context": "text"},
        ]

        fallback = generator._create_fallback_variation(
            input_fields, VariationType.BOUNDARY
        )

        assert fallback["modified_values"]["#age"] == "999999999"
        assert fallback["modified_values"]["#name"] == "x" * 255

    def test_fallback_variation_error_case(self):
        """Test fallback variation for error cases"""
        generator = VariationGenerator(api_key="test")

        input_fields = [{"selector": "#input", "value": "test", "context": "text"}]

        fallback = generator._create_fallback_variation(
            input_fields, VariationType.ERROR_CASE
        )

        assert fallback["expected_outcome"] == "validation_error"
        assert fallback["modified_values"]["#input"] == "INVALID"

    def test_fallback_variation_security(self):
        """Test fallback variation for security tests"""
        generator = VariationGenerator(api_key="test")

        input_fields = [{"selector": "#input", "value": "test", "context": "text"}]

        fallback = generator._create_fallback_variation(
            input_fields, VariationType.SECURITY
        )

        assert fallback["expected_outcome"] == "security_blocked"
        assert "<script>" in fallback["modified_values"]["#input"]

    def test_apply_modifications(self):
        """Test applying modifications to events"""
        generator = VariationGenerator(api_key="test")

        original_events = [
            MockCorrelatedEvent(
                ui_event=MockUIEvent(
                    type="fill", selector="#email", value="original@example.com"
                )
            ),
            MockCorrelatedEvent(
                ui_event=MockUIEvent(type="fill", selector="#name", value="John Doe")
            ),
        ]

        modifications = {
            "#email": "modified@example.com",
            "#name": "Jane Smith",
        }

        modified_events = generator._apply_modifications(original_events, modifications)

        # Check modifications were applied
        assert len(modified_events) == 2
        assert modified_events[0].ui_event.value == "modified@example.com"
        assert modified_events[1].ui_event.value == "Jane Smith"

        # Check originals unchanged
        assert original_events[0].ui_event.value == "original@example.com"
        assert original_events[1].ui_event.value == "John Doe"

    def test_apply_modifications_selective(self):
        """Test applying modifications to only matching selectors"""
        generator = VariationGenerator(api_key="test")

        original_events = [
            MockCorrelatedEvent(
                ui_event=MockUIEvent(type="fill", selector="#email", value="test@test.com")
            ),
            MockCorrelatedEvent(
                ui_event=MockUIEvent(type="fill", selector="#name", value="John")
            ),
        ]

        # Only modify email
        modifications = {"#email": "new@example.com"}

        modified_events = generator._apply_modifications(original_events, modifications)

        # Email should be modified
        assert modified_events[0].ui_event.value == "new@example.com"

        # Name should remain unchanged
        assert modified_events[1].ui_event.value == "John"

    def test_generate_no_variations(self):
        """Test generating zero variations"""
        generator = VariationGenerator(api_key="test")

        events = [
            MockCorrelatedEvent(
                ui_event=MockUIEvent(type="fill", selector="#input", value="test")
            )
        ]

        variations = generator.generate_variations(events, count=0)

        assert len(variations) == 0

    def test_generate_variations_no_input_fields(self):
        """Test generating variations when no input fields found"""
        generator = VariationGenerator(api_key="test")

        # Events with no fill/type actions
        events = [
            MockCorrelatedEvent(
                ui_event=MockUIEvent(type="click", selector="#button", value="")
            )
        ]

        variations = generator.generate_variations(events, count=3)

        # Should return empty list if no input fields
        assert len(variations) == 0

    @patch("tracetap.generators.variation_generator.anthropic")
    def test_generate_variations_ai_failure_uses_fallback(self, mock_anthropic):
        """Test that fallback is used when AI call fails"""
        # Mock AI to raise exception
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.Anthropic.return_value = mock_client

        generator = VariationGenerator(api_key="test-key")

        events = [
            MockCorrelatedEvent(
                ui_event=MockUIEvent(type="fill", selector="#input", value="test")
            )
        ]

        variations = generator.generate_variations(events, count=2)

        # Should still generate variations using fallback
        assert len(variations) == 2
        assert variations[0].variation_type == VariationType.HAPPY_PATH
        assert variations[1].variation_type == VariationType.EDGE_CASE

    def test_variation_number_sequence(self):
        """Test that variation numbers are sequential"""
        with patch("tracetap.generators.variation_generator.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_content = MagicMock()
            mock_content.text = json.dumps(
                {
                    "modified_values": {},
                    "expected_outcome": "success",
                    "description": "Test variation",
                }
            )
            mock_message.content = [mock_content]
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.Anthropic.return_value = mock_client

            generator = VariationGenerator(api_key="test-key")

            events = [
                MockCorrelatedEvent(
                    ui_event=MockUIEvent(type="fill", selector="#input", value="test")
                )
            ]

            variations = generator.generate_variations(events, count=5)

            # Check sequential numbering
            for i, variation in enumerate(variations):
                assert variation.variation_number == i + 1


class TestVariationType:
    """Test VariationType enum"""

    def test_variation_types(self):
        """Test all variation types are defined"""
        assert VariationType.HAPPY_PATH == "happy_path"
        assert VariationType.EDGE_CASE == "edge_case"
        assert VariationType.BOUNDARY == "boundary"
        assert VariationType.ERROR_CASE == "error_case"
        assert VariationType.SECURITY == "security"


class TestTestVariation:
    """Test TestVariation dataclass"""

    def test_test_variation_creation(self):
        """Test creating TestVariation"""
        events = [
            MockCorrelatedEvent(
                ui_event=MockUIEvent(type="fill", selector="#test", value="value")
            )
        ]

        variation = TestVariation(
            variation_number=1,
            variation_type=VariationType.HAPPY_PATH,
            description="Test description",
            modified_events=events,
            expected_outcome="success",
        )

        assert variation.variation_number == 1
        assert variation.variation_type == VariationType.HAPPY_PATH
        assert variation.description == "Test description"
        assert variation.modified_events == events
        assert variation.expected_outcome == "success"


class TestContextInference:
    """Test field context inference edge cases"""

    def test_infer_from_selector_and_value(self):
        """Test inference from both selector and value"""
        generator = VariationGenerator(api_key="test")

        # Email in value but not selector
        context = generator._infer_field_context("#input", "user@example.com")
        assert context == "email"

        # Number in value
        context = generator._infer_field_context("#field", "12345")
        assert context == "number"

    def test_infer_url_context(self):
        """Test URL field detection"""
        generator = VariationGenerator(api_key="test")

        context = generator._infer_field_context("#website", "http://example.com")
        assert context == "url"

        context = generator._infer_field_context("#link-input", "https://test.com")
        assert context == "url"

    def test_infer_date_context(self):
        """Test date field detection"""
        generator = VariationGenerator(api_key="test")

        context = generator._infer_field_context("#birthdate", "2000-01-01")
        assert context == "date"

        context = generator._infer_field_context("#birthday-input", "01/01/2000")
        assert context == "date"

    def test_infer_zipcode_context(self):
        """Test zipcode field detection"""
        generator = VariationGenerator(api_key="test")

        context = generator._infer_field_context("#zipcode", "12345")
        assert context == "zipcode"

        context = generator._infer_field_context("#postal-code", "90210")
        assert context == "zipcode"


class TestRealWorldScenarios:
    """Test realistic variation generation scenarios"""

    def test_login_form_variations(self):
        """Test variations for login form"""
        generator = VariationGenerator(api_key="test")

        events = [
            MockCorrelatedEvent(
                ui_event=MockUIEvent(
                    type="fill", selector="#email", value="user@example.com"
                )
            ),
            MockCorrelatedEvent(
                ui_event=MockUIEvent(
                    type="fill", selector='input[type="password"]', value="password123"
                )
            ),
        ]

        input_fields = generator._extract_input_fields(events)

        assert len(input_fields) == 2

        # Check email field extracted
        email_field = next(f for f in input_fields if "email" in f["selector"])
        assert email_field["context"] == "email"

        # Check password field extracted
        password_field = next(
            f for f in input_fields if "password" in f["selector"]
        )
        assert password_field["context"] == "password"

    def test_registration_form_variations(self):
        """Test variations for registration form"""
        generator = VariationGenerator(api_key="test")

        events = [
            MockCorrelatedEvent(
                ui_event=MockUIEvent(type="fill", selector="#username", value="johndoe")
            ),
            MockCorrelatedEvent(
                ui_event=MockUIEvent(
                    type="fill", selector="#email", value="john@example.com"
                )
            ),
            MockCorrelatedEvent(
                ui_event=MockUIEvent(
                    type="fill", selector="#password", value="SecurePass123!"
                )
            ),
            MockCorrelatedEvent(
                ui_event=MockUIEvent(type="fill", selector="#age", value="25")
            ),
        ]

        input_fields = generator._extract_input_fields(events)

        assert len(input_fields) == 4

        # Verify contexts
        contexts = {f["context"] for f in input_fields}
        assert "name" in contexts
        assert "email" in contexts
        assert "password" in contexts
        assert "number" in contexts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
