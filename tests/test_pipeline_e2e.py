"""
End-to-end tests proving the core pipeline works.

Tests the full flow: events + traffic -> correlate -> generate
without requiring Playwright (browser) or real API calls.

Uses mock data that represents what the InteractionRecorder would capture,
then verifies correlation and generation produce usable output.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from tracetap.record.correlator import (
    EventCorrelator,
    CorrelationOptions,
    NetworkRequest,
    CorrelationResult,
)
from tracetap.record.parser import TraceTapEvent, EventType
from tracetap.generators.test_from_recording import (
    TestGenerator,
    GenerationOptions,
    CodeSynthesizer,
)


# ============================================================================
# Realistic test data (mimics what InteractionRecorder captures)
# ============================================================================

SAMPLE_UI_EVENTS = [
    TraceTapEvent(
        type=EventType.NAVIGATE,
        timestamp=1000000,
        duration=0,
        selector=None,
        value=None,
        url="https://shop.example.com/login",
    ),
    TraceTapEvent(
        type=EventType.FILL,
        timestamp=1002000,
        duration=0,
        selector='input[name="email"]',
        value="user@example.com",
    ),
    TraceTapEvent(
        type=EventType.FILL,
        timestamp=1003500,
        duration=0,
        selector='input[type="password"]',
        value="***REDACTED***",
    ),
    TraceTapEvent(
        type=EventType.CLICK,
        timestamp=1005000,
        duration=0,
        selector='button:has-text("Sign In")',
        value=None,
    ),
    TraceTapEvent(
        type=EventType.NAVIGATE,
        timestamp=1006000,
        duration=0,
        selector=None,
        value=None,
        url="https://shop.example.com/dashboard",
    ),
]

SAMPLE_NETWORK_REQUESTS = [
    NetworkRequest(
        method="GET",
        url="https://shop.example.com/login",
        host="shop.example.com",
        path="/login",
        timestamp=1000100,
        request_headers={"accept": "text/html"},
        response_status=200,
        response_headers={"content-type": "text/html"},
        duration=150,
    ),
    NetworkRequest(
        method="POST",
        url="https://shop.example.com/api/auth/login",
        host="shop.example.com",
        path="/api/auth/login",
        timestamp=1005200,
        request_headers={"content-type": "application/json"},
        request_body='{"email":"user@example.com","password":"secret123"}',
        response_status=200,
        response_headers={"content-type": "application/json"},
        response_body='{"token":"jwt-token-here","user":{"id":1,"name":"Test User"}}',
        duration=300,
    ),
    NetworkRequest(
        method="GET",
        url="https://shop.example.com/api/dashboard",
        host="shop.example.com",
        path="/api/dashboard",
        timestamp=1006100,
        request_headers={"authorization": "Bearer jwt-token-here"},
        response_status=200,
        response_headers={"content-type": "application/json"},
        response_body='{"widgets":[{"type":"sales","count":42}]}',
        duration=200,
    ),
]


# ============================================================================
# Correlation tests
# ============================================================================


class TestCorrelation:
    """Test that UI events and network calls are correctly correlated."""

    def test_correlation_produces_results(self):
        """Events that are temporally close should be correlated."""
        correlator = EventCorrelator(CorrelationOptions(window_ms=1000))
        result = correlator.correlate(SAMPLE_UI_EVENTS, SAMPLE_NETWORK_REQUESTS)

        assert isinstance(result, CorrelationResult)
        assert len(result.correlated_events) > 0

    def test_click_correlates_with_post(self):
        """A click event should correlate with a POST that follows closely."""
        correlator = EventCorrelator(CorrelationOptions(window_ms=1000))
        result = correlator.correlate(SAMPLE_UI_EVENTS, SAMPLE_NETWORK_REQUESTS)

        # Find the click event correlation
        click_events = [
            e for e in result.correlated_events
            if e.ui_event.type == EventType.CLICK
        ]

        assert len(click_events) > 0, "Click event should be in correlated results"

        # The click on "Sign In" should correlate with the POST /api/auth/login
        click_event = click_events[0]
        post_calls = [
            nc for nc in click_event.network_calls
            if nc.method == "POST"
        ]
        assert len(post_calls) > 0, "Click should correlate with POST request"
        assert "/auth/login" in post_calls[0].url

    def test_navigate_correlates_with_get(self):
        """A navigation event should correlate with a GET request."""
        correlator = EventCorrelator(CorrelationOptions(window_ms=1000))
        result = correlator.correlate(SAMPLE_UI_EVENTS, SAMPLE_NETWORK_REQUESTS)

        nav_events = [
            e for e in result.correlated_events
            if e.ui_event.type == EventType.NAVIGATE
        ]
        assert len(nav_events) > 0, "Navigate events should be correlated"

    def test_correlation_stats_are_populated(self):
        """Correlation result should have meaningful stats."""
        correlator = EventCorrelator(CorrelationOptions(window_ms=1000))
        result = correlator.correlate(SAMPLE_UI_EVENTS, SAMPLE_NETWORK_REQUESTS)

        assert "correlation_rate" in result.stats
        assert "average_confidence" in result.stats
        assert result.stats["correlation_rate"] > 0

    def test_empty_events_produce_empty_result(self):
        """Empty input should produce empty output, not crash."""
        correlator = EventCorrelator(CorrelationOptions())
        result = correlator.correlate([], [])
        assert len(result.correlated_events) == 0

    def test_correlation_format_result_is_valid_json(self):
        """format_result should produce valid JSON."""
        correlator = EventCorrelator(CorrelationOptions(window_ms=1000))
        result = correlator.correlate(SAMPLE_UI_EVENTS, SAMPLE_NETWORK_REQUESTS)
        json_str = correlator.format_result(result)

        parsed = json.loads(json_str)
        assert "correlated_events" in parsed
        assert "stats" in parsed


# ============================================================================
# Session file round-trip tests
# ============================================================================


class TestSessionFiles:
    """Test that session data can be saved and reloaded correctly."""

    def test_save_and_reload_correlation(self, tmp_path):
        """Correlation result should survive JSON serialization round-trip."""
        correlator = EventCorrelator(CorrelationOptions(window_ms=1000))
        result = correlator.correlate(SAMPLE_UI_EVENTS, SAMPLE_NETWORK_REQUESTS)

        # Save
        json_str = correlator.format_result(result)
        file_path = tmp_path / "correlation.json"
        file_path.write_text(json_str)

        # Reload (using the same loader as cmd_generate)
        from tracetap.cli.cmd_generate import _load_correlation
        reloaded = _load_correlation(file_path)

        assert len(reloaded.correlated_events) == len(result.correlated_events)

    def test_save_events_and_traffic(self, tmp_path):
        """Events and traffic files should be valid JSON."""
        events_file = tmp_path / "events.json"
        traffic_file = tmp_path / "traffic.json"

        # Simulate what session.save() writes
        events_data = {"events": [
            {"type": e.type.value, "timestamp": e.timestamp,
             "selector": e.selector, "value": e.value, "url": e.url}
            for e in SAMPLE_UI_EVENTS
        ]}
        traffic_data = {"requests": [
            {"method": r.method, "url": r.url, "timestamp": r.timestamp,
             "request_headers": r.request_headers, "request_body": r.request_body,
             "response_status": r.response_status, "response_headers": r.response_headers,
             "response_body": r.response_body, "duration": r.duration}
            for r in SAMPLE_NETWORK_REQUESTS
        ]}

        events_file.write_text(json.dumps(events_data))
        traffic_file.write_text(json.dumps(traffic_data))

        # Reload via re-correlation
        from tracetap.cli.cmd_generate import _correlate_from_raw
        result = _correlate_from_raw(events_file, traffic_file)

        assert len(result.correlated_events) > 0


# ============================================================================
# Generation tests (mocked API)
# ============================================================================


MOCK_GENERATED_TS = '''import { test, expect } from '@playwright/test';

test('login flow', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="email"]', 'user@example.com');
  await page.fill('input[type="password"]', 'password123');
  await page.click('button:has-text("Sign In")');

  const response = await page.waitForResponse('**/api/auth/login');
  expect(response.status()).toBe(200);

  await expect(page).toHaveURL('/dashboard');
});
'''

MOCK_GENERATED_PYTHON = '''"""Generated by TraceTap"""
import pytest
from playwright.sync_api import Page, expect

def test_login_flow(page: Page):
    page.goto("/login")
    page.fill('input[name="email"]', "user@example.com")
    page.fill('input[type="password"]', "password123")
    page.click('button:has-text("Sign In")')
    expect(page).to_have_url("/dashboard")
'''


class TestGeneration:
    """Test that generation produces valid output (mocked API)."""

    @pytest.mark.asyncio
    async def test_generate_typescript(self):
        """Should generate valid TypeScript test code."""
        correlator = EventCorrelator(CorrelationOptions(window_ms=1000))
        result = correlator.correlate(SAMPLE_UI_EVENTS, SAMPLE_NETWORK_REQUESTS)

        generator = TestGenerator(api_key="sk-ant-fake-key")

        with patch.object(
            generator.synthesizer, 'synthesize',
            new_callable=AsyncMock,
            return_value=MOCK_GENERATED_TS
        ):
            code = await generator.generate_tests(
                result,
                GenerationOptions(template="comprehensive", output_format="typescript"),
            )

        assert "import" in code
        assert "test(" in code
        assert "expect(" in code
        assert "page.goto" in code

    @pytest.mark.asyncio
    async def test_generate_python(self):
        """Should generate valid Python test code."""
        correlator = EventCorrelator(CorrelationOptions(window_ms=1000))
        result = correlator.correlate(SAMPLE_UI_EVENTS, SAMPLE_NETWORK_REQUESTS)

        generator = TestGenerator(api_key="sk-ant-fake-key")

        with patch.object(
            generator.synthesizer, 'synthesize',
            new_callable=AsyncMock,
            return_value=MOCK_GENERATED_PYTHON
        ):
            code = await generator.generate_tests(
                result,
                GenerationOptions(template="basic", output_format="python"),
            )

        # Python code should compile without syntax errors
        compile(code, "<test>", "exec")
        assert "def test_" in code

    @pytest.mark.asyncio
    async def test_pii_sanitization_enabled(self):
        """PII sanitizer should redact sensitive data before sending to AI."""
        correlator = EventCorrelator(CorrelationOptions(window_ms=1000))
        result = correlator.correlate(SAMPLE_UI_EVENTS, SAMPLE_NETWORK_REQUESTS)

        generator = TestGenerator(api_key="sk-ant-fake-key", sanitize_pii=True)

        captured_prompt = None

        async def capture_synthesize(prompt, config):
            nonlocal captured_prompt
            captured_prompt = prompt
            return MOCK_GENERATED_TS

        with patch.object(
            generator.synthesizer, 'synthesize',
            side_effect=capture_synthesize
        ):
            await generator.generate_tests(result, GenerationOptions())

        assert captured_prompt is not None
        # captured_prompt is now a list of content blocks - check text blocks
        prompt_text = " ".join(
            block.get("text", "") for block in captured_prompt
            if isinstance(block, dict) and block.get("type") == "text"
        )
        # The prompt should not contain the raw password from the POST body
        assert "secret123" not in prompt_text


# ============================================================================
# Syntax validation tests
# ============================================================================


class TestSyntaxValidation:
    """Test the syntax validator used in the retry loop."""

    def test_valid_typescript(self):
        from tracetap.cli.cmd_generate import _validate_test_syntax
        assert _validate_test_syntax(MOCK_GENERATED_TS, "typescript") == ""

    def test_valid_python(self):
        from tracetap.cli.cmd_generate import _validate_test_syntax
        assert _validate_test_syntax(MOCK_GENERATED_PYTHON, "python") == ""

    def test_invalid_python_syntax(self):
        from tracetap.cli.cmd_generate import _validate_test_syntax
        # Must be >50 chars to pass length check, but have invalid syntax
        bad_code = "# This is a generated test with invalid syntax below\ndef test_foo(:\n    pass\n# end of test\n" + "# padding " * 5
        result = _validate_test_syntax(bad_code, "python")
        assert "syntax error" in result.lower()

    def test_markdown_code_fence_detected(self):
        from tracetap.cli.cmd_generate import _validate_test_syntax
        code_with_fence = "```typescript\nimport { test } from '@playwright/test';\ntest('x', () => {});\n```"
        result = _validate_test_syntax(code_with_fence, "typescript")
        assert "markdown" in result.lower() or "code fence" in result.lower()

    def test_missing_imports_detected(self):
        from tracetap.cli.cmd_generate import _validate_test_syntax
        code_no_import = "test('login', async ({ page }) => {\n  await page.goto('/');\n  expect(page).toBeTruthy();\n});"
        result = _validate_test_syntax(code_no_import, "typescript")
        assert "import" in result.lower()

    def test_empty_code_rejected(self):
        from tracetap.cli.cmd_generate import _validate_test_syntax
        assert _validate_test_syntax("", "typescript") != ""
        assert _validate_test_syntax("   ", "python") != ""


# ============================================================================
# Playwright config generation
# ============================================================================


class TestPlaywrightConfig:
    """Test that playwright.config.ts is generated correctly."""

    def test_config_generated(self, tmp_path):
        from tracetap.cli.cmd_generate import _write_playwright_config
        _write_playwright_config(tmp_path, "https://myapp.com")

        config_path = tmp_path / "playwright.config.ts"
        assert config_path.exists()

        content = config_path.read_text()
        assert "https://myapp.com" in content
        assert "baseURL" in content
        assert "defineConfig" in content

    def test_config_not_overwritten(self, tmp_path):
        """Existing config should not be overwritten."""
        config_path = tmp_path / "playwright.config.ts"
        config_path.write_text("// my existing config")

        from tracetap.cli.cmd_generate import _write_playwright_config
        _write_playwright_config(tmp_path, "https://other.com")

        assert config_path.read_text() == "// my existing config"
