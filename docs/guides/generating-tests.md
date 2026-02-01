# Generating Tests from Captured Traffic

Convert your captured API traffic into executable tests using AI transformation.

## Table of Contents

- [Overview](#overview)
- [AI-Powered Test Generation](#ai-powered-test-generation)
- [Playwright Tests](#playwright-tests)
- [Customization](#customization)
- [Best Practices](#best-practices)

---

## Overview

TraceTap captures raw API traffic and uses AI to transform it into meaningful test artifacts. The workflow is:

1. **Capture** - Record HTTP/HTTPS traffic as raw JSON
2. **Transform** - Use AI to generate tests from the raw data
3. **Run** - Execute the generated tests

### Key Benefits

- **AI-Powered Analysis** - Claude analyzes your API patterns intelligently
- **Edge Case Generation** - AI suggests additional test scenarios
- **Custom Focus Areas** - Target security, performance, or error handling
- **Clean Code Output** - Well-structured, documented test code

---

## AI-Powered Test Generation

### Basic Generation

Generate pytest tests with AI analysis:

```bash
python tracetap-playwright.py captured.json -o tests/
```

Creates:
```
tests/
├── test_api_calls.py          # Main test file
├── conftest.py                # Pytest configuration
└── fixtures.py                # Reusable fixtures
```

### With AI Suggestions

Let Claude analyze your captures and suggest additional test cases:

```bash
python tracetap-playwright.py captured.json \
  --ai-suggestions \
  -o tests/
```

This:
- Analyzes request/response patterns
- Identifies edge cases to test
- Suggests error handling scenarios
- Adds security-focused assertions

### Focus Areas

Direct AI attention to specific concerns:

```bash
python tracetap-playwright.py captured.json \
  --ai-suggestions \
  --focus-areas edge_cases security error_handling \
  -o tests/
```

Available focus areas:
- `edge_cases` - Boundary conditions, empty inputs, large payloads
- `error_handling` - Error responses, timeouts, invalid data
- `security` - Authentication, authorization, injection attacks
- `performance` - Response times, concurrency

---

## Playwright Tests

### Generated Test Structure

```python
import pytest
import requests
from fixtures import API_BASE_URL

class TestAPIEndpoints:
    """Tests generated from captured traffic"""

    def test_get_users(self):
        """Test: GET /api/users"""
        response = requests.get(f'{API_BASE_URL}/api/users')

        # Assertions
        assert response.status_code == 200
        assert 'content-type' in response.headers
        assert 'application/json' in response.headers['content-type']

        # Response body assertions
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Field assertions
        for user in data:
            assert 'id' in user
            assert 'name' in user
            assert isinstance(user['id'], int)
```

### Run Tests

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_api_calls.py::TestAPIEndpoints::test_get_users

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/
```

### Customize Test Output

```bash
# Custom test class name
python tracetap-playwright.py captured.json \
  --class-name MyAPITests \
  -o tests/

# Custom test file name
python tracetap-playwright.py captured.json \
  --test-file test_custom \
  -o tests/

# With docstrings and comments
python tracetap-playwright.py captured.json \
  --include-docstrings \
  --include-comments \
  -o tests/
```

### Advanced Options

```bash
# Skip body assertions (faster tests)
python tracetap-playwright.py captured.json \
  --skip-body-assertions \
  -o tests/

# Skip timing assertions
python tracetap-playwright.py captured.json \
  --skip-timing \
  -o tests/

# Only test status codes
python tracetap-playwright.py captured.json \
  --minimal-assertions \
  -o tests/

# Include parameterized tests
python tracetap-playwright.py captured.json \
  --parameterized \
  -o tests/
```

### Generated Test Features

Tests include assertions for:

- HTTP Status codes
- Response headers
- Response body structure
- Required fields
- Field types
- Response timing
- Request/response encoding

---

## Customization

### Modify Generated Tests

Generated tests are a starting point. Customize for your needs:

```python
# Custom assertions based on business logic
def test_user_creation_validates_email():
    """Custom: Email must be valid"""
    response = requests.post(
        f'{BASE_URL}/api/users',
        json={'name': 'Test', 'email': 'invalid-email'}
    )

    assert response.status_code == 400
    errors = response.json().get('errors', {})
    assert 'email' in errors

# Custom fixtures
@pytest.fixture
def authenticated_request():
    """Fixture with auth headers"""
    return {
        'headers': {
            'Authorization': f'Bearer {os.getenv("TEST_TOKEN")}'
        }
    }

# Use fixture
def test_protected_endpoint(authenticated_request):
    response = requests.get(
        f'{BASE_URL}/api/protected',
        **authenticated_request
    )
    assert response.status_code == 200
```

### AI-Assisted Customization

Use Claude to transform captures into specific formats:

```bash
# Through the AI interface, you can request:
# - Different test frameworks (pytest, unittest, nose)
# - Different assertion styles
# - Custom test structures
# - Integration with specific CI systems
```

---

## Best Practices

### 1. Generate, Review, Customize

Don't use generated tests as-is:

```bash
# 1. Generate
python tracetap-playwright.py captured.json -o tests/

# 2. Review generated code
cat tests/test_api_calls.py

# 3. Customize for your needs
# - Remove flaky assertions
# - Add business logic checks
# - Improve test names and documentation
```

### 2. Capture Multiple Scenarios

Generate tests from multiple captures:

```bash
# Capture 1: Happy path
python tracetap.py --listen 8080 --session "happy" --raw-log happy.json

# Capture 2: Error cases
python tracetap.py --listen 8080 --session "errors" --raw-log errors.json

# Generate tests from both
python tracetap-playwright.py happy.json -o tests/happy/
python tracetap-playwright.py errors.json -o tests/errors/

# Results in comprehensive test coverage
pytest tests/
```

### 3. Use Focus Areas

Focus test generation on specific concerns:

```bash
# AI-powered suggestions
python tracetap-playwright.py captured.json \
  --ai-suggestions \
  --focus-areas edge_cases error_handling \
  -o tests/
```

### 4. Version Your Captures

Keep baseline captures for regeneration:

```bash
# Store baseline
git add baseline.json
git commit -m "Add API baseline"

# Later, if API changes, regenerate tests
python tracetap-playwright.py baseline.json -o tests/
```

### 5. Iterate with AI

Use Claude to refine generated tests:

```
"Take these generated tests and add:
- Parameterized tests for different user roles
- Error handling for network timeouts
- Assertions for rate limiting headers"
```

---

## Next Steps

- **[Capturing Traffic](capturing-traffic.md)** - Learn how to capture traffic
- **[Regression Testing](../features/regression-testing.md)** - Use generated tests as regression suite
- **[CI/CD Integration](ci-cd-integration.md)** - Run tests in CI/CD
