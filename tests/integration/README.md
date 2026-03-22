# Integration Tests

This directory contains integration tests that validate the complete UI recording workflow from end to end.

## Test Files

### `test_ui_recording_workflow.py`

Comprehensive integration tests for the record → generate workflow.

**Test Coverage:**

1. **Correlation Loading** (3 tests)
   - ✅ Load valid correlation results
   - ✅ Handle missing files
   - ✅ Handle malformed JSON
   - ✅ Fallback for unknown event types

2. **Complete Workflow** (3 tests)
   - ✅ Generate with basic template
   - ✅ Generate with comprehensive template
   - ✅ Generate with Python format

3. **Template Testing** (1 parameterized test)
   - ✅ Test all 3 templates: basic, comprehensive, regression

4. **Output Format Testing** (1 parameterized test)
   - ✅ Test all 3 formats: TypeScript, JavaScript, Python

5. **Error Scenarios** (5 tests)
   - ✅ Missing session directory
   - ✅ Missing correlation file
   - ✅ API errors (rate limits, network)
   - ✅ Missing API key
   - ✅ Invalid JSON in correlation

6. **Confidence Threshold** (1 test)
   - ✅ Filter events by confidence threshold

7. **Performance Benchmarks** (2 tests)
   - ✅ Standard session (<30 seconds)
   - ✅ Large session with 100+ events (<30 seconds)

8. **Output Quality** (2 tests)
   - ✅ TypeScript syntax validation
   - ✅ Python syntax validation

9. **Configuration** (2 tests)
   - ✅ Base URL configuration
   - ✅ Verbose logging

**Total Tests:** 20+ test cases

## Running Tests

### With pip install (development mode)

```bash
# Install package in development mode
pip install -e ".[dev]"

# Run all integration tests
pytest tests/integration/ -v

# Run specific test
pytest tests/integration/test_ui_recording_workflow.py::test_generate_with_mock_api_basic_template -v

# Run with coverage
pytest tests/integration/ --cov=src/tracetap/generators --cov=src/tracetap/cli
```

### Without installation

```bash
# Set PYTHONPATH and run
PYTHONPATH=. python3 -m pytest tests/integration/ -v
```

### Run specific test categories

```bash
# Error scenario tests only
pytest tests/integration/ -k "error" -v

# Performance tests only
pytest tests/integration/ -k "performance" -v

# Template tests only
pytest tests/integration/ -k "template" -v
```

## Test Fixtures

### Session Directory Structure

Tests use a temporary session directory with this structure:

```
sample-session/
├── metadata.json       # Session metadata (URL, timestamp, duration)
└── correlation.json    # Correlated UI+network events
```

### Mock Data

All tests use **mock data** and **mock API responses**. No actual:
- Anthropic API key required
- Browser recording needed
- Network calls made

### Sample Correlation Data

Tests include realistic correlation data simulating a login flow:

1. Navigate to `/login`
2. Fill username field
3. Fill password field
4. Click submit button → Triggers `/auth/login` API call

## Coverage Goals

- **80%+ code coverage** for `src/tracetap/generators/` module
- **100% coverage** for CLI commands
- **All error paths** tested

## Performance Requirements

All tests must complete in:
- Individual test: **<5 seconds**
- Full suite: **<2 minutes**
- Large session (100+ events): **<30 seconds**

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:
- No external dependencies
- Fast execution
- Deterministic results
- Clear failure messages

## Extending Tests

To add new test cases:

1. **Add fixture** in the fixtures section if needed
2. **Add test function** following naming convention `test_<feature>_<scenario>`
3. **Use mocking** via `unittest.mock` to avoid external dependencies
4. **Assert meaningful outcomes** not just "no errors"

Example:

```python
@pytest.mark.asyncio
async def test_new_feature(sample_session_dir, mock_claude_response, tmp_path):
    """Test description of what this verifies."""
    output_file = tmp_path / "output.spec.ts"

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = mock_claude_response

        result = await generate_tests_from_session(
            session_dir=sample_session_dir,
            output_file=output_file,
            # ... other parameters
        )

        assert result == 0
        assert output_file.exists()
        # Add specific assertions
```

## Troubleshooting

### Import Errors

If you get import errors:

```bash
# Install package in development mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH=".:$PYTHONPATH"
```

### Async Test Warnings

Tests use `pytest-asyncio`. Install it if you see warnings:

```bash
pip install pytest-asyncio
```

### Timeout Issues

Tests have a default 120-second timeout. Increase if needed:

```bash
pytest tests/integration/ --timeout=300
```

## Related Documentation

- [Test Generator API](../../src/tracetap/generators/test_from_recording.py)
- [CLI Documentation](../../src/tracetap/cli/generate_tests.py)
- [Unit Tests](../README.md)
