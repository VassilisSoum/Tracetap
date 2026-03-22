"""
Integration Tests for TraceTap v2.1 Features

Tests all new features in combination with real workflow scenarios.
"""

import json
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tracetap.generators import TestGenerator, GenerationOptions
from tracetap.generators.pii_sanitizer import PIISanitizer
from tracetap.generators.performance_analyzer import PerformanceAnalyzer
from tracetap.generators.file_organizer import FileOrganizer
from tracetap.generators.variation_generator import VariationGenerator
from tracetap.record.correlator import CorrelationResult, CorrelatedEvent


class TestPIISanitizationIntegration:
    """Test PII sanitization in real workflow"""

    def test_sanitization_enabled_by_default(self):
        """Test that TestGenerator sanitizes by default"""
        generator = TestGenerator(api_key="test-key")

        assert generator.sanitize_pii is True
        assert generator.pii_sanitizer is not None

    def test_sanitization_disabled_with_flag(self):
        """Test that sanitization can be disabled"""
        generator = TestGenerator(api_key="test-key", sanitize_pii=False)

        assert generator.sanitize_pii is False
        assert generator.pii_sanitizer is None

    def test_sanitization_in_event_serialization(self):
        """Test that events are sanitized during serialization"""
        from tracetap.record.correlator import (
            CorrelatedEvent,
            CorrelationMetadata,
            CorrelationMethod,
        )
        from tracetap.record.parser import TraceTapEvent, EventType

        generator = TestGenerator(api_key="test-key", sanitize_pii=True)

        # Create event with PII
        ui_event = TraceTapEvent(
            type=EventType.FILL,
            timestamp=1000,
            duration=10,
            selector='input[type="password"]',
            value="mySecretPassword123",
        )

        from dataclasses import dataclass

        @dataclass
        class MockNetworkCall:
            method: str
            url: str
            request_body: str
            response_body: str
            timestamp: int
            duration: int

        network_call = MockNetworkCall(
            method="POST",
            url="/api/login",
            request_body=json.dumps({"email": "user@example.com", "password": "secret"}),
            response_body=json.dumps({"token": "abc123"}),
            timestamp=1010,
            duration=100,
        )

        correlation = CorrelationMetadata(
            confidence=0.9,
            time_delta=10,
            method=CorrelationMethod.WINDOW,
            reasoning="Test",
        )

        event = CorrelatedEvent(
            sequence=1,
            ui_event=ui_event,
            network_calls=[network_call],
            correlation=correlation,
        )

        # Serialize with sanitization
        serialized = generator._serialize_event(event)

        # Password should be redacted
        assert "REDACTED" in serialized["ui_event"]["value"]
        assert "mySecretPassword123" not in str(serialized)

        # Email in request should be redacted
        request_data = json.loads(serialized["network_calls"][0]["request"])
        assert request_data["email"] == "[email protected]"


class TestPerformanceIntegration:
    """Test performance features in real workflow"""

    def test_extract_thresholds_from_correlation_result(self):
        """Test extracting performance thresholds from real data"""
        from dataclasses import dataclass

        @dataclass
        class MockUIEvent:
            type: str
            timestamp: int
            duration: int

        @dataclass
        class MockNetworkCall:
            url: str
            method: str
            duration: int

        @dataclass
        class MockCorrelation:
            confidence: float
            time_delta: int
            method: str
            reasoning: str

        @dataclass
        class MockEvent:
            ui_event: MockUIEvent
            network_calls: list
            correlation: MockCorrelation

        events = [
            MockEvent(
                ui_event=MockUIEvent(type="click", timestamp=1000, duration=10),
                network_calls=[
                    MockNetworkCall(url="/api/users", method="GET", duration=250),
                    MockNetworkCall(url="/api/orders", method="POST", duration=400),
                ],
                correlation=MockCorrelation(
                    confidence=0.9, time_delta=10, method="window", reasoning="test"
                ),
            )
        ]

        analyzer = PerformanceAnalyzer()
        thresholds = analyzer.extract_thresholds(events)

        assert len(thresholds) == 2
        assert thresholds[0].observed_duration_ms == 250
        assert thresholds[0].threshold_ms == 375  # 1.5x
        assert thresholds[1].observed_duration_ms == 400
        assert thresholds[1].threshold_ms == 600  # 1.5x

    def test_performance_prompt_injection(self):
        """Test that performance context is injected into prompts"""
        generator = TestGenerator(api_key="test-key")

        template = "Test template\n{events_json}\n{output_format}"

        from tracetap.generators.performance_analyzer import PerformanceThreshold

        thresholds = [
            PerformanceThreshold(
                endpoint="/api/test",
                method="GET",
                observed_duration_ms=200,
                threshold_ms=300,
            )
        ]

        options = GenerationOptions(
            template="comprehensive",
            output_format="typescript",
            performance_thresholds=thresholds,
        )

        prompt = generator._build_ai_prompt([], template, options)

        # Performance context should be injected
        assert "Performance Thresholds" in prompt
        assert "200ms" in prompt
        assert "300ms" in prompt


class TestOrganizationIntegration:
    """Test file organization in real workflow"""

    def test_organize_realistic_api_structure(self):
        """Test organizing realistic API endpoints"""
        from dataclasses import dataclass

        @dataclass
        class MockNetworkCall:
            url: str
            method: str

        @dataclass
        class MockEvent:
            network_calls: list

        events = [
            MockEvent(network_calls=[MockNetworkCall(url="/api/auth/login", method="POST")]),
            MockEvent(network_calls=[MockNetworkCall(url="/api/users", method="GET")]),
            MockEvent(network_calls=[MockNetworkCall(url="/api/users/123", method="GET")]),
            MockEvent(network_calls=[MockNetworkCall(url="/api/users", method="POST")]),
            MockEvent(network_calls=[MockNetworkCall(url="/api/orders", method="POST")]),
            MockEvent(
                network_calls=[MockNetworkCall(url="/api/orders/abc-123", method="GET")]
            ),
        ]

        organizer = FileOrganizer()
        specs = organizer.organize(events, Path("tests"))

        # Should create organized structure
        assert len(specs) > 0

        # Check feature grouping
        features = {spec.relative_path.parts[0] for spec in specs}
        assert "auth" in features
        assert "users" in features
        assert "orders" in features

        # Check method separation
        user_specs = [s for s in specs if "users" in str(s.relative_path)]
        assert len(user_specs) >= 2  # At least GET and POST

    def test_organization_statistics(self):
        """Test statistics for organized structure"""
        from dataclasses import dataclass

        @dataclass
        class MockNetworkCall:
            url: str
            method: str

        @dataclass
        class MockEvent:
            network_calls: list

        events = [
            MockEvent(network_calls=[MockNetworkCall(url="/api/users", method="GET")]),
            MockEvent(network_calls=[MockNetworkCall(url="/api/orders", method="POST")]),
            MockEvent(network_calls=[MockNetworkCall(url="/api/products", method="GET")]),
        ]

        organizer = FileOrganizer()
        specs = organizer.organize(events, Path("tests"))
        stats = organizer.get_statistics(specs)

        assert stats["file_count"] == 3
        assert stats["feature_count"] == 3
        assert stats["total_events"] == 3
        assert len(stats["features"]) == 3


class TestVariationIntegration:
    """Test variation generation in real workflow"""

    @patch("tracetap.generators.variation_generator.anthropic")
    def test_generate_variations_with_ai(self, mock_anthropic):
        """Test variation generation with mocked AI"""
        # Mock AI response
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = json.dumps(
            {
                "modified_values": {"#email": ""},
                "expected_outcome": "validation_error",
                "description": "Empty email field test",
            }
        )
        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        from dataclasses import dataclass

        @dataclass
        class MockUIEvent:
            type: str
            selector: str
            value: str

        @dataclass
        class MockEvent:
            ui_event: MockUIEvent

        events = [
            MockEvent(
                ui_event=MockUIEvent(
                    type="fill", selector="#email", value="test@example.com"
                )
            ),
            MockEvent(
                ui_event=MockUIEvent(type="fill", selector="#password", value="secret123")
            ),
        ]

        generator = VariationGenerator(api_key="test-key")
        variations = generator.generate_variations(events, count=3)

        assert len(variations) == 3

        # First should be happy path
        assert variations[0].variation_number == 1
        assert variations[0].variation_type.value == "happy_path"

        # Others should be AI-generated
        assert variations[1].variation_number == 2
        assert variations[2].variation_number == 3


class TestFeatureCombinations:
    """Test combinations of multiple features"""

    def test_sanitization_with_performance(self):
        """Test PII sanitization + performance assertions together"""
        generator = TestGenerator(api_key="test-key", sanitize_pii=True)

        from tracetap.generators.performance_analyzer import PerformanceThreshold

        thresholds = [
            PerformanceThreshold(
                endpoint="/api/login",
                method="POST",
                observed_duration_ms=200,
                threshold_ms=300,
            )
        ]

        options = GenerationOptions(
            template="comprehensive",
            output_format="typescript",
            performance_thresholds=thresholds,
            sanitize_pii=True,
        )

        # Both features should be configured
        assert generator.sanitize_pii is True
        assert options.performance_thresholds is not None

    def test_organization_with_variations(self):
        """Test file organization + variations together"""
        from dataclasses import dataclass

        @dataclass
        class MockNetworkCall:
            url: str
            method: str

        @dataclass
        class MockUIEvent:
            type: str
            selector: str
            value: str

        @dataclass
        class MockEvent:
            network_calls: list
            ui_event: MockUIEvent

        events = [
            MockEvent(
                network_calls=[MockNetworkCall(url="/api/users", method="GET")],
                ui_event=MockUIEvent(type="fill", selector="#search", value="john"),
            ),
            MockEvent(
                network_calls=[MockNetworkCall(url="/api/orders", method="POST")],
                ui_event=MockUIEvent(type="fill", selector="#item", value="widget"),
            ),
        ]

        # Organize
        organizer = FileOrganizer()
        specs = organizer.organize(events, Path("tests"))

        assert len(specs) == 2  # users/get, orders/post

        # Each spec could have variations
        for spec in specs:
            assert len(spec.events) >= 1

    def test_all_features_enabled(self):
        """Test all features enabled simultaneously"""
        # Sanitization
        generator = TestGenerator(api_key="test-key", sanitize_pii=True)
        assert generator.sanitize_pii is True

        # Performance
        from tracetap.generators.performance_analyzer import PerformanceThreshold

        thresholds = [
            PerformanceThreshold(
                endpoint="/api/test", method="GET", observed_duration_ms=100, threshold_ms=150
            )
        ]

        # Organization (implied by having multiple specs)
        # Variations (would be generated in CLI)

        options = GenerationOptions(
            template="comprehensive",
            output_format="typescript",
            performance_thresholds=thresholds,
            sanitize_pii=True,
        )

        # All should be configured
        assert generator.sanitize_pii is True
        assert options.performance_thresholds is not None
        assert options.template == "comprehensive"


class TestBackwardCompatibility:
    """Test that v2.1 features don't break existing functionality"""

    def test_default_behavior_unchanged(self):
        """Test default behavior is same as v2.0 (except sanitization)"""
        generator = TestGenerator(api_key="test-key")

        # Sanitization ON by default (security improvement)
        assert generator.sanitize_pii is True

        # But can be disabled for backward compat
        generator_no_sanitize = TestGenerator(api_key="test-key", sanitize_pii=False)
        assert generator_no_sanitize.sanitize_pii is False

    def test_generation_options_defaults(self):
        """Test GenerationOptions defaults are backward compatible"""
        options = GenerationOptions()

        assert options.template == "comprehensive"
        assert options.output_format == "typescript"
        assert options.confidence_threshold == 0.5
        assert options.sanitize_pii is True  # New default (security)
        assert options.performance_thresholds is None  # Optional
        assert options.sanitization_config is None  # Optional

    def test_existing_recordings_work(self):
        """Test that existing recordings work without modification"""
        # This would load a real correlation.json file
        # For now, just verify structure

        correlation_file = Path("examples/ui-recording-demo/todomvc/session-example/correlation.json")

        if correlation_file.exists():
            with open(correlation_file) as f:
                data = json.load(f)

            # Should have expected structure
            assert "correlated_events" in data
            assert isinstance(data["correlated_events"], list)

            # Should be processable
            assert len(data["correlated_events"]) > 0


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_correlation_result(self):
        """Test handling empty correlation result"""
        analyzer = PerformanceAnalyzer()
        thresholds = analyzer.extract_thresholds([])

        assert len(thresholds) == 0

    def test_events_without_network_calls(self):
        """Test events with no network calls"""
        from dataclasses import dataclass

        @dataclass
        class MockUIEvent:
            type: str

        @dataclass
        class MockEvent:
            network_calls: list
            ui_event: MockUIEvent

        events = [
            MockEvent(network_calls=[], ui_event=MockUIEvent(type="click")),
        ]

        analyzer = PerformanceAnalyzer()
        thresholds = analyzer.extract_thresholds(events)

        assert len(thresholds) == 0

    def test_sanitization_with_none_values(self):
        """Test sanitization handles None gracefully"""
        sanitizer = PIISanitizer()

        event = {"ui_event": {"value": None}, "network_calls": []}

        result = sanitizer.sanitize_event(event)

        assert result["ui_event"]["value"] is None

    def test_organization_with_malformed_urls(self):
        """Test organization handles malformed URLs"""
        from dataclasses import dataclass

        @dataclass
        class MockNetworkCall:
            url: str
            method: str

        @dataclass
        class MockEvent:
            network_calls: list

        events = [
            MockEvent(network_calls=[MockNetworkCall(url="", method="GET")]),
            MockEvent(network_calls=[MockNetworkCall(url="/", method="GET")]),
            MockEvent(
                network_calls=[MockNetworkCall(url="https://example.com", method="GET")]
            ),
        ]

        organizer = FileOrganizer()
        specs = organizer.organize(events, Path("tests"))

        # Should handle gracefully
        assert isinstance(specs, list)


class TestRealWorldScenarios:
    """Test realistic end-to-end scenarios"""

    def test_ecommerce_checkout_flow(self):
        """Test organizing e-commerce checkout flow"""
        from dataclasses import dataclass

        @dataclass
        class MockNetworkCall:
            url: str
            method: str
            duration: int

        @dataclass
        class MockUIEvent:
            type: str

        @dataclass
        class MockCorrelation:
            confidence: float
            time_delta: int
            method: str
            reasoning: str

        @dataclass
        class MockEvent:
            ui_event: MockUIEvent
            network_calls: list
            correlation: MockCorrelation

        # Simulate checkout flow
        events = [
            MockEvent(
                ui_event=MockUIEvent(type="click"),
                network_calls=[
                    MockNetworkCall(url="/api/auth/login", method="POST", duration=200)
                ],
                correlation=MockCorrelation(
                    confidence=0.9, time_delta=10, method="window", reasoning="test"
                ),
            ),
            MockEvent(
                ui_event=MockUIEvent(type="click"),
                network_calls=[
                    MockNetworkCall(url="/api/products", method="GET", duration=150)
                ],
                correlation=MockCorrelation(
                    confidence=0.9, time_delta=10, method="window", reasoning="test"
                ),
            ),
            MockEvent(
                ui_event=MockUIEvent(type="click"),
                network_calls=[
                    MockNetworkCall(url="/api/cart/items", method="POST", duration=100)
                ],
                correlation=MockCorrelation(
                    confidence=0.9, time_delta=10, method="window", reasoning="test"
                ),
            ),
            MockEvent(
                ui_event=MockUIEvent(type="click"),
                network_calls=[
                    MockNetworkCall(url="/api/checkout", method="POST", duration=500)
                ],
                correlation=MockCorrelation(
                    confidence=0.9, time_delta=10, method="window", reasoning="test"
                ),
            ),
        ]

        # Organize
        organizer = FileOrganizer()
        specs = organizer.organize(events, Path("tests"))

        features = {spec.relative_path.parts[0] for spec in specs}
        assert "auth" in features
        assert "products" in features or "api" in features
        assert "cart" in features or "api" in features
        assert "checkout" in features or "api" in features

        # Performance
        analyzer = PerformanceAnalyzer()
        thresholds = analyzer.extract_thresholds(events)

        assert len(thresholds) == 4
        # Checkout should have higher threshold
        checkout_threshold = next(
            t for t in thresholds if "checkout" in t.endpoint.lower()
        )
        assert checkout_threshold.threshold_ms == 750  # 1.5x of 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
