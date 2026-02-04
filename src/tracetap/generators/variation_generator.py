"""Test variation generator for TraceTap.

Generates multiple test files from a single recording with varied input data.
Uses AI to create contextually appropriate variations for edge cases, boundary
testing, error scenarios, and security testing.
"""

import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False

from ..common.constants import DEFAULT_CLAUDE_MODEL, MAX_VARIATION_TOKENS

logger = logging.getLogger(__name__)


class VariationType(str, Enum):
    """Types of test variations to generate."""

    HAPPY_PATH = "happy_path"
    EDGE_CASE = "edge_case"
    BOUNDARY = "boundary"
    ERROR_CASE = "error_case"
    SECURITY = "security"


@dataclass
class TestVariation:
    """Specification for a single test variation.

    Attributes:
        variation_number: Sequential variation number (1 = happy path)
        variation_type: Type of variation
        description: Human-readable description of what this variation tests
        modified_events: List of events with modified input values
        expected_outcome: Expected result ("success", "validation_error", "security_blocked")
    """

    variation_number: int
    variation_type: VariationType
    description: str
    modified_events: List[Any]
    expected_outcome: str


class VariationGenerator:
    """Generates test data variations using AI.

    This class uses Claude AI to generate intelligent test variations
    that explore edge cases, boundaries, errors, and security scenarios.

    Example:
        >>> generator = VariationGenerator(api_key="sk-ant-...")
        >>> variations = generator.generate_variations(correlated_events, count=3)
        >>> for var in variations:
        ...     print(f"Variation {var.variation_number}: {var.description}")
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize variation generator.

        Args:
            api_key: Claude API key (if not provided, reads from ANTHROPIC_API_KEY env var)
        """
        if not ANTHROPIC_AVAILABLE:
            logger.warning(
                "Anthropic library not installed. Install with: pip install anthropic"
            )
            self.client = None
            self.api_key = None
            return

        import os

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning(
                "No Anthropic API key found. Set ANTHROPIC_API_KEY environment variable."
            )
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate_variations(
        self, correlated_events: List[Any], count: int
    ) -> List[TestVariation]:
        """Generate N test variations from correlated events.

        Args:
            correlated_events: List of CorrelatedEvent objects from recording
            count: Number of variations to generate (including happy path)

        Returns:
            List of TestVariation objects with modified input data

        Raises:
            RuntimeError: If API call fails or client not initialized
        """
        if not self.client:
            raise RuntimeError(
                "Claude API client not initialized. Set ANTHROPIC_API_KEY environment variable."
            )

        if count < 1:
            return []

        # Extract input fields from events
        input_fields = self._extract_input_fields(correlated_events)

        if not input_fields:
            logger.warning("No input fields found in events - cannot generate variations")
            return []

        # Generate variations using AI
        variations = []

        # Variation 1: Happy path (original data)
        variations.append(
            TestVariation(
                variation_number=1,
                variation_type=VariationType.HAPPY_PATH,
                description="Happy path with original input data",
                modified_events=correlated_events,
                expected_outcome="success",
            )
        )

        # Generate remaining variations
        variation_types = [
            VariationType.EDGE_CASE,
            VariationType.BOUNDARY,
            VariationType.ERROR_CASE,
            VariationType.SECURITY,
        ]

        for i in range(1, count):
            variation_type = variation_types[(i - 1) % len(variation_types)]

            try:
                variation = self._generate_single_variation(
                    correlated_events, input_fields, i + 1, variation_type
                )
                variations.append(variation)
            except Exception as e:
                logger.error(f"Failed to generate variation {i + 1}: {e}")
                # Continue with next variation

        return variations

    def _extract_input_fields(self, events: List[Any]) -> List[Dict[str, Any]]:
        """Extract input fields from UI events.

        Args:
            events: List of correlated events

        Returns:
            List of input field dictionaries with selector, value, and context
        """
        input_fields = []

        for event in events:
            ui_event = getattr(event, "ui_event", None)
            if not ui_event:
                continue

            event_type = getattr(ui_event, "type", "")
            selector = getattr(ui_event, "selector", None)
            value = getattr(ui_event, "value", None)

            # Only extract fill/type events (input fields)
            if event_type in ["fill", "type"] and selector and value:
                input_fields.append(
                    {
                        "selector": selector,
                        "value": value,
                        "type": event_type,
                        "context": self._infer_field_context(selector, value),
                    }
                )

        return input_fields

    def _infer_field_context(self, selector: str, value: str) -> str:
        """Infer the context/purpose of an input field.

        Args:
            selector: CSS selector string
            value: Original input value

        Returns:
            Context type (e.g., "email", "password", "phone", "text")
        """
        selector_lower = selector.lower()

        # Pattern matching for common field types
        if any(pattern in selector_lower for pattern in ["email", "mail"]):
            return "email"
        elif any(pattern in selector_lower for pattern in ["password", "passwd", "pwd"]):
            return "password"
        elif any(pattern in selector_lower for pattern in ["phone", "tel", "mobile"]):
            return "phone"
        elif any(pattern in selector_lower for pattern in ["name", "username"]):
            return "name"
        elif any(pattern in selector_lower for pattern in ["age", "number", "count"]):
            return "number"
        elif any(pattern in selector_lower for pattern in ["date", "birthday"]):
            return "date"
        elif any(pattern in selector_lower for pattern in ["url", "website", "link"]):
            return "url"
        elif any(pattern in selector_lower for pattern in ["zip", "postal"]):
            return "zipcode"

        # Infer from value format
        if "@" in value:
            return "email"
        elif value.isdigit():
            return "number"

        return "text"

    def _generate_single_variation(
        self,
        original_events: List[Any],
        input_fields: List[Dict[str, Any]],
        variation_number: int,
        variation_type: VariationType,
    ) -> TestVariation:
        """Generate a single test variation using AI.

        Args:
            original_events: Original correlated events
            input_fields: Extracted input fields
            variation_number: Sequential variation number
            variation_type: Type of variation to generate

        Returns:
            TestVariation with modified input data
        """
        # Build AI prompt
        prompt = self._build_variation_prompt(input_fields, variation_type)

        # Call Claude API
        logger.info(f"Generating variation {variation_number} ({variation_type.value})...")

        try:
            message = self.client.messages.create(
                model=DEFAULT_CLAUDE_MODEL,
                max_tokens=MAX_VARIATION_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text

            # Parse JSON response
            variation_data = json.loads(response_text)

        except Exception as e:
            logger.error(f"AI call failed for variation: {e}")
            # Fallback: create simple variation
            variation_data = self._create_fallback_variation(
                input_fields, variation_type
            )

        # Apply modifications to events
        modified_events = self._apply_modifications(
            original_events, variation_data.get("modified_values", {})
        )

        return TestVariation(
            variation_number=variation_number,
            variation_type=variation_type,
            description=variation_data.get(
                "description", f"{variation_type.value} test"
            ),
            modified_events=modified_events,
            expected_outcome=variation_data.get("expected_outcome", "success"),
        )

    def _build_variation_prompt(
        self, input_fields: List[Dict[str, Any]], variation_type: VariationType
    ) -> str:
        """Build AI prompt for variation generation.

        Args:
            input_fields: Input field data
            variation_type: Type of variation

        Returns:
            Formatted prompt string
        """
        guidelines = {
            VariationType.EDGE_CASE: (
                "Generate edge case variations:\n"
                "- Empty strings for text fields\n"
                "- Maximum length values (255 characters)\n"
                "- Unicode characters and special symbols\n"
                "- Leading/trailing whitespace"
            ),
            VariationType.BOUNDARY: (
                "Generate boundary value variations:\n"
                "- Minimum/maximum numeric values\n"
                "- Date boundaries (past, future, leap years)\n"
                "- Length boundaries (exactly at limits)\n"
                "- Zero, negative, very large numbers"
            ),
            VariationType.ERROR_CASE: (
                "Generate error case variations:\n"
                "- Invalid formats (wrong email, phone format)\n"
                "- Wrong data types (text in number field)\n"
                "- Missing required fields\n"
                "- Mismatched confirmations"
            ),
            VariationType.SECURITY: (
                "Generate security test variations:\n"
                "- XSS attempts: <script>alert('xss')</script>\n"
                "- SQL injection: '; DROP TABLE users; --\n"
                "- Path traversal: ../../etc/passwd\n"
                "- Command injection: $(whoami)"
            ),
            VariationType.HAPPY_PATH: "Keep original data unchanged",
        }

        input_fields_json = json.dumps(input_fields, indent=2)

        return f"""You are generating TEST DATA VARIATIONS for automated testing.

**VARIATION TYPE: {variation_type.value.upper()}**

{guidelines[variation_type]}

**Input Fields:**
```json
{input_fields_json}
```

**Task:**
Generate modified input values for this variation type. Return ONLY valid JSON with this structure:

{{
  "modified_values": {{
    "selector1": "new_value1",
    "selector2": "new_value2"
  }},
  "expected_outcome": "success|validation_error|security_blocked",
  "description": "Brief description of what this variation tests"
}}

**Requirements:**
- Modify values appropriately for the variation type
- Use contextually appropriate modifications based on field type
- Set expected_outcome based on whether the test should pass or fail
- Keep description under 100 characters
- Return ONLY the JSON, no explanations
"""

    def _create_fallback_variation(
        self, input_fields: List[Dict[str, Any]], variation_type: VariationType
    ) -> Dict[str, Any]:
        """Create a simple fallback variation if AI fails.

        Args:
            input_fields: Input field data
            variation_type: Type of variation

        Returns:
            Variation data dictionary
        """
        modified_values = {}

        for field in input_fields:
            selector = field["selector"]
            context = field["context"]

            if variation_type == VariationType.EDGE_CASE:
                # Empty string for all fields
                modified_values[selector] = ""
            elif variation_type == VariationType.BOUNDARY:
                if context == "number":
                    modified_values[selector] = "999999999"
                else:
                    modified_values[selector] = "x" * 255
            elif variation_type == VariationType.ERROR_CASE:
                modified_values[selector] = "INVALID"
            elif variation_type == VariationType.SECURITY:
                modified_values[selector] = "<script>alert('xss')</script>"

        return {
            "modified_values": modified_values,
            "expected_outcome": "validation_error"
            if variation_type != VariationType.SECURITY
            else "security_blocked",
            "description": f"Fallback {variation_type.value} test",
        }

    def _apply_modifications(
        self, original_events: List[Any], modifications: Dict[str, str]
    ) -> List[Any]:
        """Apply input value modifications to events.

        Args:
            original_events: Original correlated events
            modifications: Dictionary mapping selectors to new values

        Returns:
            List of modified events (deep copies)
        """
        import copy

        modified_events = []

        for event in original_events:
            # Deep copy to avoid modifying original
            modified_event = copy.deepcopy(event)

            # Check if this event has a UI input
            ui_event = getattr(modified_event, "ui_event", None)
            if ui_event:
                selector = getattr(ui_event, "selector", None)
                if selector and selector in modifications:
                    # Apply modification
                    ui_event.value = modifications[selector]
                    logger.debug(
                        f"Modified {selector}: {getattr(ui_event, 'value', None)} -> {modifications[selector]}"
                    )

            modified_events.append(modified_event)

        return modified_events
