# Generating Tests from Captured Traffic

Convert your captured API traffic into executable tests.

## Table of Contents

- [Overview](#overview)
- [Test Generators](#test-generators)
- [Playwright Tests](#playwright-tests)
- [Postman Collections](#postman-collections)
- [WireMock Stubs](#wiremock-stubs)
- [Comparing Generators](#comparing-generators)
- [Customization](#customization)
- [Best Practices](#best-practices)

---

## Overview

TraceTap can convert captured traffic into three types of test artifacts:

1. **Playwright Tests** - Executable pytest tests
2. **Postman Collections** - Interactive manual or automated testing
3. **WireMock Stubs** - Mock server for isolated testing

### Quick Comparison

| Generator | Best For | Output | Executable |
|-----------|----------|--------|-----------|
| Playwright | Automated API testing | `.py` test files | ✅ Yes (pytest) |
| Postman | Manual testing, collaboration | `.json` collection | ✅ Yes (Newman) |
| WireMock | Mocking, isolated testing | `.json` stubs | ✅ Yes (Java) |

---

## Test Generators

### Playwright Tests

Generate pytest tests with assertions:

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

### Postman Collections

Generate Postman collection:

```bash
python tracetap-ai-postman.py captured.json -o postman.json
```

Import into Postman:
1. Open Postman
2. Click "Import" → "File"
3. Select `postman.json`
4. Run requests manually or with Newman

### WireMock Stubs

Generate mock server stubs:

```bash
python tracetap2wiremock.py captured.json -o wiremock-stubs.json
```

Use with WireMock:
```bash
java -jar wiremock.jar --root-dir . --port 8080
```

---

## Playwright Tests

### Basic Generation

```bash
python tracetap-playwright.py captured.json -o tests/
```

Generated test file structure:

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
  --test-file test_custom.py \
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

- ✅ HTTP Status codes
- ✅ Response headers
- ✅ Response body structure
- ✅ Required fields
- ✅ Field types
- ✅ Response timing
- ✅ Request/response encoding

---

## Postman Collections

### Basic Generation

```bash
python tracetap-ai-postman.py captured.json -o postman.json
```

Generated collection includes:
- ✅ All requests organized in folders
- ✅ Headers and authentication
- ✅ Request bodies
- ✅ Pre-request scripts
- ✅ Test scripts
- ✅ Environment variables

### AI-Enhanced Generation

Let Claude organize requests intelligently:

```bash
python tracetap-ai-postman.py captured.json \
  --infer-flow \
  --output postman.json
```

This:
- 🤖 Analyzes request patterns
- 🤖 Identifies workflows
- 🤖 Organizes into logical folders
- 🤖 Removes duplicates
- 🤖 Adds descriptions

### Import Into Postman

1. Open Postman
2. Click "Import" button
3. Select the generated `postman.json` file
4. Collection appears in left sidebar
5. Click any request to run it

### Run with Newman (CLI)

Automate Postman collection execution:

```bash
# Install Newman
npm install -g newman

# Run collection
newman run postman.json

# Run with environment variables
newman run postman.json \
  -e environment.json

# Generate report
newman run postman.json \
  --reporters cli,json \
  --reporter-json-export report.json
```

### Export as Test Cases

Postman can use requests as tests:

```bash
# In Postman:
# 1. Click request
# 2. Go to "Tests" tab
# 3. Add test script:

// Check status code
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

// Check response has fields
pm.test("Response has required fields", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('id');
    pm.expect(jsonData).to.have.property('name');
});

# 4. Run collection with tests
```

---

## WireMock Stubs

### Basic Generation

```bash
python tracetap2wiremock.py captured.json -o wiremock-stubs.json
```

Generated stub format:

```json
{
  "mappings": [
    {
      "request": {
        "method": "GET",
        "url": "/api/users/123"
      },
      "response": {
        "status": 200,
        "headers": {
          "Content-Type": "application/json"
        },
        "body": "{\"id\": 123, \"name\": \"Alice\"}"
      }
    }
  ]
}
```

### Start WireMock Server

```bash
# Copy stubs file
cp wiremock-stubs.json wiremock/mappings/

# Start WireMock
docker run -it --rm \
  -p 8080:8080 \
  -v $(pwd)/wiremock:/home/wiremock \
  wiremock/wiremock:latest

# Or locally (requires Java)
java -jar wiremock-standalone.jar --port 8080
```

### Use Mocked API

```bash
# Point your app to WireMock instead of real API
export API_URL=http://localhost:8080

# Run tests against mock
pytest tests/

# All responses come from WireMock stubs
```

### Advanced Stub Matching

Generate stubs with flexible matching:

```bash
# Match by path pattern
python tracetap2wiremock.py captured.json \
  --matcher-strategy url-pattern \
  -o wiremock-stubs.json

# Match by request body
python tracetap2wiremock.py captured.json \
  --matcher-strategy body-pattern \
  -o wiremock-stubs.json

# Match with priority
python tracetap2wiremock.py captured.json \
  --priority 100 \
  -o wiremock-stubs.json
```

---

## Comparing Generators

### Use Case: Testing a Feature

**Scenario**: You built a new user authentication feature. You want to:
- Test locally (don't want to call real API)
- Test in CI/CD
- Share tests with team
- Run manually to verify behavior

**Solution Options**:

#### Option 1: Playwright + WireMock

```bash
# 1. Capture auth API traffic
python tracetap.py --listen 8080 --filter-host "auth.example.com" --export auth.json

# 2. Generate Playwright tests
python tracetap-playwright.py auth.json -o tests/

# 3. Generate WireMock stubs
python tracetap2wiremock.py auth.json -o wiremock/mappings/auth-stubs.json

# 4. Run tests against mock
pytest tests/

# 5. Also run in CI/CD
# (WireMock stubs ensure consistent mock responses)
```

#### Option 2: Postman + Newman

```bash
# 1. Capture auth API traffic
python tracetap.py --listen 8080 --filter-host "auth.example.com" --export auth.json

# 2. Generate Postman collection
python tracetap-ai-postman.py auth.json --infer-flow -o auth.json

# 3. Run manually in Postman for exploration
# 4. Run with Newman in CI/CD
newman run auth.json --reporters cli,json
```

#### Option 3: Playwright Only

```bash
# 1. Capture auth API traffic
python tracetap.py --listen 8080 --filter-host "auth.example.com" --export auth.json

# 2. Generate Playwright tests
python tracetap-playwright.py auth.json -o tests/

# 3. Run in CI/CD
pytest tests/

# 4. Create stub manually for local testing
# (More work, but fine for simple cases)
```

---

## Customization

### Custom Test Generation

Modify generated tests:

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

### Custom Postman Scripts

Add custom test logic to Postman:

```javascript
// Pre-request script
// Set up variables before request
pm.environment.set('user_id', 123);
pm.environment.set('timestamp', new Date().toISOString());

// Test script
// Assertions run after request
pm.test("Response time is acceptable", function () {
    pm.expect(pm.response.responseTime).to.be.below(500);
});

pm.test("Auth token refreshed", function () {
    var jsonData = pm.response.json();
    pm.environment.set('auth_token', jsonData.token);
});
```

### Custom Stub Matching

Modify WireMock stubs for flexible matching:

```json
{
  "request": {
    "method": "POST",
    "url": "/api/users",
    "bodyPatterns": [
      {
        "matchesJsonPath": "$.email",
        "contains": "@"
      }
    ]
  },
  "response": {
    "status": 201,
    "body": "{\"id\": 1, \"email\": \"{{jsonPath request.body '$.email'}}\"}",
    "transformers": ["response-template"]
  }
}
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

### 2. Combine Multiple Captures

Generate tests from multiple captures:

```bash
# Capture 1: Happy path
python tracetap.py --listen 8080 --session "happy" --export happy.json

# Capture 2: Error cases
python tracetap.py --listen 8080 --session "errors" --export errors.json

# Generate tests from both
python tracetap-playwright.py happy.json -o tests/happy/
python tracetap-playwright.py errors.json -o tests/errors/

# Results in comprehensive test coverage
pytest tests/
```

### 3. Use Generator-Specific Features

Each generator has unique strengths:

```bash
# Use Playwright for: Automated, CI/CD-friendly tests
python tracetap-playwright.py captured.json -o tests/

# Use Postman for: Manual testing, team collaboration
python tracetap-ai-postman.py captured.json -o postman.json

# Use WireMock for: Isolated local testing, testing without real API
python tracetap2wiremock.py captured.json -o wiremock-stubs.json
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

### 5. Use Focus Areas

Focus test generation on specific concerns:

```bash
# AI-powered suggestions
python tracetap-playwright.py captured.json \
  --ai-suggestions \
  --focus-areas edge_cases error_handling \
  -o tests/

# Or manually select endpoints
python tracetap-playwright.py captured.json \
  --endpoint-filter "^/api/critical" \
  -o tests/
```

---

## Next Steps

- **[Capturing Traffic](capturing-traffic.md)** - Learn how to capture traffic
- **[Regression Testing](../features/regression-testing.md)** - Use generated tests as regression suite
- **[CI/CD Integration](ci-cd-integration.md)** - Run tests in CI/CD
