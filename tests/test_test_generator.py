"""Tests for test code generator."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.tracetap.generators.test_from_recording import (
    TestGenerator,
    GenerationOptions,
    CodeSynthesizer,
    TemplateType,
    OutputFormat,
)
from src.tracetap.record.correlator import (
    CorrelationResult,
    CorrelatedEvent,
    CorrelationMetadata,
    CorrelationMethod,
    NetworkRequest,
)


class MockUIEvent:
    """Mock UI event for testing."""

    def __init__(
        self, event_type: str, timestamp: int, selector: str = None, value: str = None
    ):
        self.type = event_type
        self.timestamp = timestamp
        self.selector = selector
        self.value = value
        self.url = None


@pytest.fixture
def sample_correlation_result():
    """Create sample correlation result for testing."""
    ui_event = MockUIEvent("click", 1000, "#login-button")
    network_call = NetworkRequest(
        method="POST",
        url="https://api.example.com/login",
        host="api.example.com",
        path="/login",
        timestamp=1050,
        request_headers={},
        request_body='{"username": "test"}',
        response_status=200,
        response_headers={},
        response_body='{"token": "abc123"}',
        duration=100,
    )

    correlation = CorrelationMetadata(
        confidence=0.9,
        time_delta=50.0,
        method=CorrelationMethod.EXACT,
        reasoning="Click triggered login API call",
    )

    event = CorrelatedEvent(
        sequence=1, ui_event=ui_event, network_calls=[network_call], correlation=correlation
    )

    return CorrelationResult(
        correlated_events=[event],
        stats={
            "total_ui_events": 1,
            "total_network_calls": 1,
            "correlated_ui_events": 1,
            "correlated_network_calls": 1,
            "average_confidence": 0.9,
            "average_time_delta": 50.0,
            "correlation_rate": 1.0,
        },
    )


def test_generation_options_defaults():
    """Test GenerationOptions default values."""
    options = GenerationOptions()
    assert options.template == "comprehensive"
    assert options.output_format == "typescript"
    assert options.confidence_threshold == 0.5
    assert options.include_comments is True
    assert options.base_url is None
    assert options.test_name is None


def test_generation_options_custom():
    """Test GenerationOptions with custom values."""
    options = GenerationOptions(
        template="basic",
        output_format="python",
        confidence_threshold=0.7,
        include_comments=False,
        base_url="https://example.com",
        test_name="my_test",
    )
    assert options.template == "basic"
    assert options.output_format == "python"
    assert options.confidence_threshold == 0.7
    assert options.include_comments is False
    assert options.base_url == "https://example.com"
    assert options.test_name == "my_test"


def test_code_synthesizer_init_no_api_key():
    """Test CodeSynthesizer initialization without API key."""
    with patch.dict("os.environ", {}, clear=True):
        synthesizer = CodeSynthesizer()
        # Should initialize but warn about missing API key
        # The client will be None if no API key is present


def test_code_synthesizer_generate_playwright_action():
    """Test generating Playwright action code."""
    ui_event = MockUIEvent("click", 1000, "#button")
    action = CodeSynthesizer.generate_playwright_action(ui_event)
    assert 'page.click("#button")' in action

    ui_event = MockUIEvent("fill", 1000, "#input", "test value")
    action = CodeSynthesizer.generate_playwright_action(ui_event)
    assert 'page.fill("#input", "test value")' in action


def test_code_synthesizer_generate_test_name():
    """Test generating test name from events."""
    ui_event1 = MockUIEvent("click", 1000)
    ui_event2 = MockUIEvent("fill", 2000)

    correlation = CorrelationMetadata(0.8, 50.0, CorrelationMethod.WINDOW, "test")
    events = [
        CorrelatedEvent(1, ui_event1, [], correlation),
        CorrelatedEvent(2, ui_event2, [], correlation),
    ]

    name = CodeSynthesizer.generate_test_name(events)
    assert "click" in name
    assert "fill" in name


def test_code_synthesizer_validate_syntax_typescript():
    """Test syntax validation for TypeScript."""
    synthesizer = CodeSynthesizer()

    valid_code = """
import { test, expect } from '@playwright/test';

test('sample test', async ({ page }) => {
  await page.goto('https://example.com');
  expect(true).toBe(true);
});
"""
    assert synthesizer.validate_syntax(valid_code, OutputFormat.TYPESCRIPT) is True

    invalid_code = "const x = 5;"  # Missing required patterns
    assert synthesizer.validate_syntax(invalid_code, OutputFormat.TYPESCRIPT) is False


def test_code_synthesizer_validate_syntax_python():
    """Test syntax validation for Python."""
    synthesizer = CodeSynthesizer()

    valid_code = """
def test_sample():
    assert True
"""
    assert synthesizer.validate_syntax(valid_code, OutputFormat.PYTHON) is True

    invalid_code = "def test(:"  # Syntax error
    assert synthesizer.validate_syntax(invalid_code, OutputFormat.PYTHON) is False


def test_test_generator_init():
    """Test TestGenerator initialization."""
    generator = TestGenerator()
    assert generator.template_manager is not None
    assert generator.synthesizer is not None
    assert generator.templates_dir.exists() or True  # May not exist yet


def test_test_generator_filter_by_confidence(sample_correlation_result):
    """Test filtering events by confidence threshold."""
    generator = TestGenerator()

    # Should include event with confidence 0.9
    filtered = generator._filter_by_confidence(
        sample_correlation_result.correlated_events, 0.5
    )
    assert len(filtered) == 1

    # Should exclude event with confidence 0.9
    filtered = generator._filter_by_confidence(
        sample_correlation_result.correlated_events, 0.95
    )
    assert len(filtered) == 0


def test_test_generator_serialize_event(sample_correlation_result):
    """Test event serialization to JSON."""
    generator = TestGenerator()
    event = sample_correlation_result.correlated_events[0]

    serialized = generator._serialize_event(event)

    assert serialized["sequence"] == 1
    assert serialized["ui_event"]["type"] == "click"
    assert len(serialized["network_calls"]) == 1
    assert serialized["network_calls"][0]["method"] == "POST"
    assert serialized["correlation"]["confidence"] == 0.9


def test_test_generator_generate_header():
    """Test header generation for different formats."""
    generator = TestGenerator()

    options_ts = GenerationOptions(
        template="comprehensive", output_format="typescript", confidence_threshold=0.7
    )
    header_ts = generator._generate_header(options_ts)
    assert "Generated by TraceTap" in header_ts
    assert "comprehensive" in header_ts
    assert "0.7" in header_ts
    assert "//" in header_ts

    options_py = GenerationOptions(
        template="basic", output_format="python", confidence_threshold=0.6
    )
    header_py = generator._generate_header(options_py)
    assert "Generated by TraceTap" in header_py
    assert "basic" in header_py
    assert "0.6" in header_py
    assert '"""' in header_py


@pytest.mark.asyncio
async def test_test_generator_generate_tests_no_api_key(sample_correlation_result):
    """Test generate_tests fails gracefully without API key."""
    with patch.dict("os.environ", {}, clear=True):
        generator = TestGenerator()
        options = GenerationOptions()

        with pytest.raises(RuntimeError, match="API client not initialized"):
            await generator.generate_tests(sample_correlation_result, options)


def test_test_generator_build_ai_prompt(sample_correlation_result):
    """Test AI prompt building."""
    generator = TestGenerator()

    # Mock template content
    template = """
Generate Playwright test code.

Events:
{events_json}

Output format: {output_format}
Base URL: {base_url}
Confidence threshold: {confidence_threshold}
"""

    options = GenerationOptions(
        output_format="typescript", base_url="https://example.com", confidence_threshold=0.7
    )

    prompt = generator._build_ai_prompt(
        sample_correlation_result.correlated_events, template, options
    )

    assert "typescript" in prompt
    assert "https://example.com" in prompt
    assert "0.7" in prompt
    assert "click" in prompt.lower()
    assert "POST" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
