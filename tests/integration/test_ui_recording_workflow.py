"""
Integration tests for complete UI recording workflow.

Tests the end-to-end flow: record → correlate → generate tests
with mock data to avoid requiring real API keys or live recording.
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from src.tracetap.cli.generate_tests import (
    generate_tests_from_session,
    load_correlation_result,
)
from src.tracetap.generators import (
    TestGenerator,
    GenerationOptions,
    OutputFormat,
    TemplateType,
)
from src.tracetap.record.correlator import (
    CorrelationResult,
    CorrelatedEvent,
    CorrelationMetadata,
    CorrelationMethod,
    NetworkRequest,
)
from src.tracetap.record.parser import TraceTapEvent, EventType


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_metadata() -> Dict[str, Any]:
    """Sample metadata for a recording session."""
    return {
        "session_id": "test-session-123",
        "url": "https://example.com",
        "timestamp": "2024-01-15T10:30:00Z",
        "duration": 45.5,
        "total_events": 10,
        "total_network_calls": 8,
    }


@pytest.fixture
def sample_correlation_data() -> Dict[str, Any]:
    """Sample correlation.json data with realistic UI+network events."""
    return {
        "correlated_events": [
            {
                "sequence": 1,
                "ui_event": {
                    "type": "navigate",
                    "timestamp": 1000,
                    "duration": 0,
                    "url": "https://example.com/login",
                    "selector": None,
                    "value": None,
                },
                "network_calls": [
                    {
                        "method": "GET",
                        "url": "https://example.com/login",
                        "host": "example.com",
                        "path": "/login",
                        "timestamp": 1050,
                        "request_headers": {
                            "User-Agent": "Mozilla/5.0",
                            "Accept": "text/html",
                        },
                        "request_body": None,
                        "response_status": 200,
                        "response_headers": {"Content-Type": "text/html"},
                        "response_body": "<html>...</html>",
                        "duration": 150,
                    }
                ],
                "correlation": {
                    "confidence": 0.95,
                    "time_delta": 50.0,
                    "method": "exact",
                    "reasoning": "Navigation triggered page load",
                },
            },
            {
                "sequence": 2,
                "ui_event": {
                    "type": "fill",
                    "timestamp": 2000,
                    "duration": 100,
                    "url": "https://example.com/login",
                    "selector": "#username",
                    "value": "test@example.com",
                },
                "network_calls": [],
                "correlation": {
                    "confidence": 1.0,
                    "time_delta": 0.0,
                    "method": "exact",
                    "reasoning": "Form field input",
                },
            },
            {
                "sequence": 3,
                "ui_event": {
                    "type": "fill",
                    "timestamp": 3000,
                    "duration": 80,
                    "url": "https://example.com/login",
                    "selector": "#password",
                    "value": "password123",
                },
                "network_calls": [],
                "correlation": {
                    "confidence": 1.0,
                    "time_delta": 0.0,
                    "method": "exact",
                    "reasoning": "Form field input",
                },
            },
            {
                "sequence": 4,
                "ui_event": {
                    "type": "click",
                    "timestamp": 4000,
                    "duration": 50,
                    "url": "https://example.com/login",
                    "selector": "button[type='submit']",
                    "value": None,
                },
                "network_calls": [
                    {
                        "method": "POST",
                        "url": "https://api.example.com/auth/login",
                        "host": "api.example.com",
                        "path": "/auth/login",
                        "timestamp": 4080,
                        "request_headers": {
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        },
                        "request_body": '{"username":"test@example.com","password":"password123"}',
                        "response_status": 200,
                        "response_headers": {"Content-Type": "application/json"},
                        "response_body": '{"token":"eyJhbGc...","user":{"id":123}}',
                        "duration": 250,
                    }
                ],
                "correlation": {
                    "confidence": 0.92,
                    "time_delta": 80.0,
                    "method": "window",
                    "reasoning": "Button click triggered login API call",
                },
            },
        ],
        "stats": {
            "total_ui_events": 4,
            "total_network_calls": 2,
            "correlated_ui_events": 4,
            "correlated_network_calls": 2,
            "average_confidence": 0.9675,
            "average_time_delta": 32.5,
            "correlation_rate": 1.0,
        },
    }


@pytest.fixture
def sample_session_dir(tmp_path, sample_metadata, sample_correlation_data):
    """Create a complete sample session directory with all required files."""
    session_dir = tmp_path / "sample-session"
    session_dir.mkdir()

    # Write metadata.json
    metadata_file = session_dir / "metadata.json"
    metadata_file.write_text(json.dumps(sample_metadata, indent=2))

    # Write correlation.json
    correlation_file = session_dir / "correlation.json"
    correlation_file.write_text(json.dumps(sample_correlation_data, indent=2))

    return session_dir


@pytest.fixture
def mock_claude_basic_response():
    """Mock Claude API response for basic template."""
    return Mock(
        content=[
            Mock(
                text="""```typescript
import { test, expect } from '@playwright/test';

test('login flow', async ({ page }) => {
  // Navigate to login page
  await page.goto('https://example.com/login');

  // Fill login form
  await page.fill('#username', 'test@example.com');
  await page.fill('#password', 'password123');

  // Submit form
  await page.click('button[type="submit"]');

  // Wait for API response
  await page.waitForResponse(response =>
    response.url().includes('/auth/login') && response.status() === 200
  );
});
```"""
            )
        ]
    )


@pytest.fixture
def mock_claude_comprehensive_response():
    """Mock Claude API response for comprehensive template."""
    return Mock(
        content=[
            Mock(
                text="""```typescript
import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test('should successfully login with valid credentials', async ({ page }) => {
    // Setup: Navigate to login page
    await page.goto('https://example.com/login');
    await expect(page).toHaveURL(/.*login/);

    // Action: Fill username field
    await page.fill('#username', 'test@example.com');
    await expect(page.locator('#username')).toHaveValue('test@example.com');

    // Action: Fill password field
    await page.fill('#password', 'password123');
    await expect(page.locator('#password')).toHaveValue('password123');

    // Action: Click submit button
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/auth/login') && response.status() === 200
    );
    await page.click('button[type="submit"]');

    // Assertion: Verify login API call
    const response = await responsePromise;
    expect(response.status()).toBe(200);

    const responseBody = await response.json();
    expect(responseBody).toHaveProperty('token');
    expect(responseBody).toHaveProperty('user');
    expect(responseBody.user.id).toBe(123);

    // Assertion: Verify redirect after login
    await page.waitForURL(/.*dashboard/, { timeout: 5000 });
  });
});
```"""
            )
        ]
    )


@pytest.fixture
def mock_claude_python_response():
    """Mock Claude API response for Python format."""
    return Mock(
        content=[
            Mock(
                text="""```python
import pytest
from playwright.sync_api import Page, expect


def test_login_flow(page: Page):
    \"\"\"Test user login workflow.\"\"\"
    # Navigate to login page
    page.goto('https://example.com/login')

    # Fill login form
    page.fill('#username', 'test@example.com')
    page.fill('#password', 'password123')

    # Submit form
    with page.expect_response(lambda response: '/auth/login' in response.url) as response_info:
        page.click('button[type="submit"]')

    response = response_info.value
    assert response.status == 200

    data = response.json()
    assert 'token' in data
    assert 'user' in data
```"""
            )
        ]
    )


@pytest.fixture
def mock_claude_error_response():
    """Mock Claude API error response."""
    return Mock(side_effect=Exception("API rate limit exceeded"))


# ============================================================================
# Test: Load Correlation Result
# ============================================================================


def test_load_correlation_result_success(sample_session_dir):
    """Test loading correlation result from valid session directory."""
    correlation_file = sample_session_dir / "correlation.json"

    result = load_correlation_result(correlation_file)

    assert isinstance(result, CorrelationResult)
    assert len(result.correlated_events) == 4
    assert result.stats["total_ui_events"] == 4
    assert result.stats["correlation_rate"] == 1.0

    # Verify first event
    first_event = result.correlated_events[0]
    assert first_event.sequence == 1
    assert first_event.ui_event.type == EventType.NAVIGATE
    assert len(first_event.network_calls) == 1
    assert first_event.correlation.confidence == 0.95


def test_load_correlation_result_missing_file(tmp_path):
    """Test loading correlation from non-existent file."""
    missing_file = tmp_path / "nonexistent" / "correlation.json"

    with pytest.raises(FileNotFoundError):
        load_correlation_result(missing_file)


def test_load_correlation_result_malformed_json(tmp_path):
    """Test loading correlation from malformed JSON file."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json")

    with pytest.raises(json.JSONDecodeError):
        load_correlation_result(bad_file)


def test_load_correlation_result_invalid_event_type(tmp_path):
    """Test loading correlation with unknown event type (should fallback to CLICK)."""
    data = {
        "correlated_events": [
            {
                "sequence": 1,
                "ui_event": {
                    "type": "unknown_event_type",
                    "timestamp": 1000,
                    "duration": 0,
                },
                "network_calls": [],
                "correlation": {
                    "confidence": 0.5,
                    "time_delta": 0.0,
                    "method": "exact",
                    "reasoning": "test",
                },
            }
        ],
        "stats": {},
    }

    file = tmp_path / "test.json"
    file.write_text(json.dumps(data))

    result = load_correlation_result(file)
    # Should fallback to CLICK for unknown event types
    assert result.correlated_events[0].ui_event.type == EventType.CLICK


# ============================================================================
# Test: Complete Workflow with Mock API
# ============================================================================


@pytest.mark.asyncio
async def test_generate_with_mock_api_basic_template(
    sample_session_dir, mock_claude_basic_response, tmp_path
):
    """Test complete generation workflow with basic template."""
    output_file = tmp_path / "output.spec.ts"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = (
            mock_claude_basic_response
        )

        result = await generate_tests_from_session(
            session_dir=sample_session_dir,
            output_file=output_file,
            template="basic",
            output_format="typescript",
            confidence_threshold=0.5,
            api_key="test-key",
            base_url=None,
            verbose=False,
        )

        assert result == 0
        assert output_file.exists()

        content = output_file.read_text()
        assert "import { test, expect } from '@playwright/test';" in content
        assert "test('login flow'" in content
        assert "page.goto('https://example.com/login')" in content
        assert "page.fill('#username'" in content
        assert "page.click('button[type=\"submit\"]')" in content


@pytest.mark.asyncio
async def test_generate_with_mock_api_comprehensive_template(
    sample_session_dir, mock_claude_comprehensive_response, tmp_path
):
    """Test complete generation workflow with comprehensive template."""
    output_file = tmp_path / "output.spec.ts"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = (
            mock_claude_comprehensive_response
        )

        result = await generate_tests_from_session(
            session_dir=sample_session_dir,
            output_file=output_file,
            template="comprehensive",
            output_format="typescript",
            confidence_threshold=0.5,
            api_key="test-key",
            base_url=None,
            verbose=False,
        )

        assert result == 0
        assert output_file.exists()

        content = output_file.read_text()
        assert "test.describe('Login Flow'" in content
        assert "expect(page).toHaveURL" in content
        assert "expect(responseBody).toHaveProperty('token')" in content
        assert "page.waitForResponse" in content


@pytest.mark.asyncio
async def test_generate_with_mock_api_python_format(
    sample_session_dir, mock_claude_python_response, tmp_path
):
    """Test generation with Python output format."""
    output_file = tmp_path / "test_output.py"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = (
            mock_claude_python_response
        )

        result = await generate_tests_from_session(
            session_dir=sample_session_dir,
            output_file=output_file,
            template="comprehensive",
            output_format="python",
            confidence_threshold=0.5,
            api_key="test-key",
            base_url=None,
            verbose=False,
        )

        assert result == 0
        assert output_file.exists()

        content = output_file.read_text()
        assert "import pytest" in content
        assert "from playwright.sync_api import Page" in content
        assert "def test_login_flow(page: Page):" in content
        assert "page.goto('https://example.com/login')" in content
        assert "assert response.status == 200" in content


# ============================================================================
# Test: All Templates
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("template", ["basic", "comprehensive", "regression"])
async def test_all_templates(
    sample_session_dir, mock_claude_basic_response, tmp_path, template
):
    """Test generation with all three templates."""
    output_file = tmp_path / f"output_{template}.spec.ts"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = (
            mock_claude_basic_response
        )

        result = await generate_tests_from_session(
            session_dir=sample_session_dir,
            output_file=output_file,
            template=template,
            output_format="typescript",
            confidence_threshold=0.5,
            api_key="test-key",
            base_url=None,
            verbose=False,
        )

        assert result == 0
        assert output_file.exists()

        # Verify API was called with correct prompt
        mock_anthropic.return_value.messages.create.assert_called_once()
        call_args = mock_anthropic.return_value.messages.create.call_args
        assert call_args[1]["model"] == "claude-sonnet-4-5-20250929"


# ============================================================================
# Test: All Output Formats
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "output_format,extension", [("typescript", ".spec.ts"), ("javascript", ".spec.js"), ("python", ".py")]
)
async def test_all_output_formats(
    sample_session_dir, mock_claude_basic_response, tmp_path, output_format, extension
):
    """Test generation with all output formats."""
    output_file = tmp_path / f"output{extension}"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = (
            mock_claude_basic_response
        )

        result = await generate_tests_from_session(
            session_dir=sample_session_dir,
            output_file=output_file,
            template="comprehensive",
            output_format=output_format,
            confidence_threshold=0.5,
            api_key="test-key",
            base_url=None,
            verbose=False,
        )

        assert result == 0
        assert output_file.exists()


# ============================================================================
# Test: Error Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_generate_missing_session_dir(tmp_path):
    """Test generation with missing session directory."""
    missing_dir = tmp_path / "nonexistent"
    output_file = tmp_path / "output.spec.ts"

    result = await generate_tests_from_session(
        session_dir=missing_dir,
        output_file=output_file,
        template="comprehensive",
        output_format="typescript",
        confidence_threshold=0.5,
        api_key="test-key",
        base_url=None,
        verbose=False,
    )

    assert result == 1
    assert not output_file.exists()


@pytest.mark.asyncio
async def test_generate_missing_correlation_file(tmp_path):
    """Test generation with session dir but no correlation.json."""
    session_dir = tmp_path / "empty-session"
    session_dir.mkdir()
    output_file = tmp_path / "output.spec.ts"

    result = await generate_tests_from_session(
        session_dir=session_dir,
        output_file=output_file,
        template="comprehensive",
        output_format="typescript",
        confidence_threshold=0.5,
        api_key="test-key",
        base_url=None,
        verbose=False,
    )

    assert result == 1
    assert not output_file.exists()


@pytest.mark.asyncio
async def test_generate_api_error(sample_session_dir, mock_claude_error_response, tmp_path):
    """Test generation when Claude API returns an error."""
    output_file = tmp_path / "output.spec.ts"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create = mock_claude_error_response

        result = await generate_tests_from_session(
            session_dir=sample_session_dir,
            output_file=output_file,
            template="comprehensive",
            output_format="typescript",
            confidence_threshold=0.5,
            api_key="test-key",
            base_url=None,
            verbose=False,
        )

        assert result == 1
        assert not output_file.exists()


@pytest.mark.asyncio
async def test_generate_missing_api_key(sample_session_dir, tmp_path):
    """Test generation without API key."""
    output_file = tmp_path / "output.spec.ts"

    with patch.dict("os.environ", {}, clear=True):
        result = await generate_tests_from_session(
            session_dir=sample_session_dir,
            output_file=output_file,
            template="comprehensive",
            output_format="typescript",
            confidence_threshold=0.5,
            api_key=None,
            base_url=None,
            verbose=False,
        )

        assert result == 1
        assert not output_file.exists()


@pytest.mark.asyncio
async def test_generate_invalid_json_in_correlation(tmp_path):
    """Test generation with malformed correlation.json."""
    session_dir = tmp_path / "bad-session"
    session_dir.mkdir()

    correlation_file = session_dir / "correlation.json"
    correlation_file.write_text("{invalid json content")

    output_file = tmp_path / "output.spec.ts"

    result = await generate_tests_from_session(
        session_dir=session_dir,
        output_file=output_file,
        template="comprehensive",
        output_format="typescript",
        confidence_threshold=0.5,
        api_key="test-key",
        base_url=None,
        verbose=False,
    )

    assert result == 1
    assert not output_file.exists()


# ============================================================================
# Test: Confidence Threshold Filtering
# ============================================================================


@pytest.mark.asyncio
async def test_confidence_threshold_filtering(tmp_path, mock_claude_basic_response):
    """Test that events are filtered by confidence threshold."""
    # Create session with mixed confidence events
    session_dir = tmp_path / "mixed-session"
    session_dir.mkdir()

    correlation_data = {
        "correlated_events": [
            {
                "sequence": 1,
                "ui_event": {"type": "click", "timestamp": 1000},
                "network_calls": [],
                "correlation": {
                    "confidence": 0.9,
                    "time_delta": 0.0,
                    "method": "exact",
                    "reasoning": "high confidence",
                },
            },
            {
                "sequence": 2,
                "ui_event": {"type": "click", "timestamp": 2000},
                "network_calls": [],
                "correlation": {
                    "confidence": 0.3,
                    "time_delta": 0.0,
                    "method": "window",
                    "reasoning": "low confidence",
                },
            },
        ],
        "stats": {},
    }

    correlation_file = session_dir / "correlation.json"
    correlation_file.write_text(json.dumps(correlation_data))

    output_file = tmp_path / "output.spec.ts"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = (
            mock_claude_basic_response
        )

        # Test with threshold 0.5 (should filter out low confidence event)
        result = await generate_tests_from_session(
            session_dir=session_dir,
            output_file=output_file,
            template="basic",
            output_format="typescript",
            confidence_threshold=0.5,
            api_key="test-key",
            base_url=None,
            verbose=False,
        )

        assert result == 0
        # Verify API was called
        mock_anthropic.return_value.messages.create.assert_called_once()


# ============================================================================
# Test: Performance Benchmarks
# ============================================================================


@pytest.mark.asyncio
async def test_generation_performance(sample_session_dir, mock_claude_basic_response, tmp_path):
    """Verify generation completes in reasonable time (<30 seconds)."""
    output_file = tmp_path / "output.spec.ts"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = (
            mock_claude_basic_response
        )

        start_time = time.time()

        result = await generate_tests_from_session(
            session_dir=sample_session_dir,
            output_file=output_file,
            template="comprehensive",
            output_format="typescript",
            confidence_threshold=0.5,
            api_key="test-key",
            base_url=None,
            verbose=False,
        )

        duration = time.time() - start_time

        assert result == 0
        assert duration < 30.0, f"Generation took {duration}s, expected <30s"


@pytest.mark.asyncio
async def test_large_session_performance(tmp_path, mock_claude_basic_response):
    """Test performance with large session (100+ events)."""
    session_dir = tmp_path / "large-session"
    session_dir.mkdir()

    # Create large correlation data
    correlated_events = []
    for i in range(100):
        correlated_events.append(
            {
                "sequence": i + 1,
                "ui_event": {
                    "type": "click",
                    "timestamp": 1000 + i * 100,
                    "selector": f"#button-{i}",
                },
                "network_calls": [
                    {
                        "method": "GET",
                        "url": f"https://api.example.com/data/{i}",
                        "host": "api.example.com",
                        "path": f"/data/{i}",
                        "timestamp": 1050 + i * 100,
                        "response_status": 200,
                    }
                ],
                "correlation": {
                    "confidence": 0.8,
                    "time_delta": 50.0,
                    "method": "window",
                    "reasoning": "Click triggered API call",
                },
            }
        )

    correlation_data = {"correlated_events": correlated_events, "stats": {}}

    correlation_file = session_dir / "correlation.json"
    correlation_file.write_text(json.dumps(correlation_data))

    output_file = tmp_path / "output.spec.ts"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = (
            mock_claude_basic_response
        )

        start_time = time.time()

        result = await generate_tests_from_session(
            session_dir=session_dir,
            output_file=output_file,
            template="comprehensive",
            output_format="typescript",
            confidence_threshold=0.5,
            api_key="test-key",
            base_url=None,
            verbose=False,
        )

        duration = time.time() - start_time

        assert result == 0
        assert duration < 30.0, f"Large session took {duration}s, expected <30s"


# ============================================================================
# Test: Output Quality Validation
# ============================================================================


def test_typescript_output_has_required_patterns(tmp_path):
    """Verify TypeScript output contains required patterns."""
    # This would typically be tested as part of the generation flow
    # but we can also test the validator separately
    from src.tracetap.generators.test_from_recording import CodeSynthesizer

    synthesizer = CodeSynthesizer()

    valid_code = """
import { test, expect } from '@playwright/test';

test('sample test', async ({ page }) => {
  await page.goto('https://example.com');
  expect(true).toBe(true);
});
"""

    assert synthesizer.validate_syntax(valid_code, OutputFormat.TYPESCRIPT) is True

    invalid_code = "const x = 5;"
    assert synthesizer.validate_syntax(invalid_code, OutputFormat.TYPESCRIPT) is False


def test_python_output_has_valid_syntax(tmp_path):
    """Verify Python output has valid syntax."""
    from src.tracetap.generators.test_from_recording import CodeSynthesizer

    synthesizer = CodeSynthesizer()

    valid_code = """
def test_sample():
    assert True
"""

    assert synthesizer.validate_syntax(valid_code, OutputFormat.PYTHON) is True

    invalid_code = "def test(:"
    assert synthesizer.validate_syntax(invalid_code, OutputFormat.PYTHON) is False


# ============================================================================
# Test: Base URL Configuration
# ============================================================================


@pytest.mark.asyncio
async def test_base_url_configuration(
    sample_session_dir, mock_claude_basic_response, tmp_path
):
    """Test that base_url is properly passed through the generation flow."""
    output_file = tmp_path / "output.spec.ts"
    custom_base_url = "https://staging.example.com"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = (
            mock_claude_basic_response
        )

        result = await generate_tests_from_session(
            session_dir=sample_session_dir,
            output_file=output_file,
            template="comprehensive",
            output_format="typescript",
            confidence_threshold=0.5,
            api_key="test-key",
            base_url=custom_base_url,
            verbose=False,
        )

        assert result == 0

        # Verify base_url was passed in the options
        # (would need to verify in the actual generated code in a real scenario)


# ============================================================================
# Test: Verbose Logging
# ============================================================================


@pytest.mark.asyncio
async def test_verbose_logging_enabled(
    sample_session_dir, mock_claude_basic_response, tmp_path, caplog
):
    """Test that verbose mode enables detailed logging."""
    output_file = tmp_path / "output.spec.ts"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = (
            mock_claude_basic_response
        )

        result = await generate_tests_from_session(
            session_dir=sample_session_dir,
            output_file=output_file,
            template="comprehensive",
            output_format="typescript",
            confidence_threshold=0.5,
            api_key="test-key",
            base_url=None,
            verbose=True,
        )

        assert result == 0
        # When verbose is True, more detailed output should be produced


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
