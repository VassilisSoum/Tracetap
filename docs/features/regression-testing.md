# Regression Testing with TraceTap

Automatically detect API breaking changes and regressions before they reach production.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Getting Started](#getting-started)
- [Generate Regression Tests](#generate-regression-tests)
- [Run Tests](#run-tests)
- [Continuous Integration](#continuous-integration)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)

---

## Overview

Regression testing catches bugs that appear in new versions of software. TraceTap makes this easy by:

1. **Capturing baseline traffic** from your working API
2. **Generating assertion-based tests** that verify behavior
3. **Running tests against new versions** to catch breaking changes
4. **Reporting differences** between versions

### Why It Matters

APIs change. Sometimes those changes are bugs:

- **Response schema changes**: New/missing fields break clients
- **Status code changes**: Error handling breaks downstream services
- **Response timing**: Performance regressions cause timeouts
- **Header changes**: Security headers or content-type changes break consumers

Regression tests catch these *before* they become production incidents.

### Example Problem

Version 1 of your API:
```bash
GET /api/users/123
200 OK
{"id": 123, "name": "Alice", "email": "alice@example.com"}
```

Version 2 of your API (with bug):
```bash
GET /api/users/123
200 OK
{"id": 123, "name": "Alice"}  # ❌ email field missing!
```

A regression test catches this immediately.

---

## How It Works

### The Regression Testing Pipeline

```
┌─────────────────────────────────────────────────────────┐
│ 1. Capture Baseline Traffic from Working API           │
│    python tracetap.py --listen 8080 --export api.json  │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Generate Regression Tests from Captures             │
│    python tracetap-playwright.py api.json -o tests/    │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Version Your Baseline                               │
│    git add tests/api_regression_tests.py                │
│    git commit -m "Baseline regression tests"            │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Run Tests on New Versions                           │
│    pytest tests/api_regression_tests.py                 │
│    (Run in CI/CD on every deployment)                   │
└─────────────────────────────────────────────────────────┘
```

Each test includes assertions on:
- ✅ Status codes
- ✅ Response headers
- ✅ Response body structure
- ✅ Response timing
- ✅ Required fields

---

## Getting Started

### Step 1: Capture Baseline Traffic

Capture traffic from your working API version:

```bash
# Start TraceTap
python tracetap.py --listen 8080 --export baseline.json

# In another terminal, exercise your API
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Make requests that exercise key API flows
curl -k https://api.example.com/users
curl -k https://api.example.com/users/123
curl -k -X POST https://api.example.com/users -d '{"name":"Bob"}'
curl -k https://api.example.com/posts?user_id=123

# Press Ctrl+C in TraceTap terminal
```

Result: `baseline.json` contains captured requests and responses.

### Step 2: Generate Regression Tests

Generate Playwright tests with automatic assertions:

```bash
# Generate tests
python tracetap-playwright.py baseline.json -o tests/

# View generated tests
cat tests/api_regression_tests.py
```

Generated test file includes:

```python
def test_get_users():
    """Test: GET /users"""
    response = requests.get('https://api.example.com/users')

    # Status code assertion
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Headers assertions
    assert 'content-type' in response.headers
    assert 'application/json' in response.headers['content-type']

    # Response structure assertions
    data = response.json()
    assert isinstance(data, list), "Expected array response"
    assert len(data) > 0, "Expected non-empty user list"

    # Field assertions
    for user in data:
        assert 'id' in user, "Missing 'id' field"
        assert 'name' in user, "Missing 'name' field"
        assert 'email' in user, "Missing 'email' field"  # ← Catches missing fields!
```

### Step 3: Run Tests Against New Version

```bash
# Run against current version (should pass)
pytest tests/ -v

# Deploy new version, run again
pytest tests/ -v

# ❌ If regression detected:
# FAILED test_get_users - AssertionError: Missing 'email' field
```

---

## Generate Regression Tests

### Using Playwright Generator

The Playwright generator creates comprehensive test files:

```bash
python tracetap-playwright.py baseline.json \
  --output tests/ \
  --class-name APIRegressionTests \
  --include-assertions
```

### Using WireMock Stubs

Create WireMock stubs for contract verification:

```bash
python tracetap2wiremock.py baseline.json \
  --output wiremock-stubs.json \
  --priority 100
```

### Using Postman Collection

Generate a Postman collection with tests:

```bash
python tracetap-ai-postman.py baseline.json \
  --output postman-regression.json \
  --infer-flow
```

---

## Run Tests

### Local Testing

```bash
# Run all regression tests
pytest tests/ -v

# Run specific test
pytest tests/api_regression_tests.py::test_get_users -v

# Show detailed output
pytest tests/ -vv --tb=short

# Generate coverage report
pytest tests/ --cov=src/tracetap --cov-report=html
```

### Against Different Environments

```bash
# Test against staging
API_URL=https://staging-api.example.com pytest tests/

# Test against production
API_URL=https://api.example.com pytest tests/

# Test with timeout
pytest tests/ --timeout=10
```

### Generate Reports

```bash
# HTML report
pytest tests/ --html=report.html --self-contained-html

# JSON report (for parsing)
pytest tests/ --json-report --json-report-file=report.json

# JUnit XML (for CI/CD)
pytest tests/ --junitxml=results.xml
```

---

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/regression-tests.yml`:

```yaml
name: API Regression Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    # Run daily at 2 AM UTC
    - cron: '0 2 * * *'

jobs:
  regression-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run regression tests
        env:
          API_URL: https://staging-api.example.com
        run: |
          pytest tests/ --junitxml=results.xml --html=report.html

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: regression-test-results
          path: |
            results.xml
            report.html

      - name: Comment on PR
        if: failure() && github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '❌ API regression tests failed. See artifacts for details.'
            })
```

### GitLab CI Example

Create `.gitlab-ci.yml`:

```yaml
regression-tests:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pip install -r requirements-dev.txt
    - pytest tests/ --junitxml=results.xml
  artifacts:
    reports:
      junit: results.xml
  only:
    - main
    - develop
    - merge_requests
```

---

## Advanced Usage

### Custom Assertions

Modify generated tests to add custom assertions:

```python
def test_get_users_with_custom_logic():
    """Test with custom business logic assertions"""
    response = requests.get('https://api.example.com/users')

    assert response.status_code == 200

    data = response.json()

    # Custom assertion: all users have valid email
    for user in data:
        email = user.get('email', '')
        assert '@' in email, f"Invalid email: {email}"

    # Custom assertion: creation dates are recent
    for user in data:
        created_at = user.get('created_at')
        created_date = datetime.fromisoformat(created_at)
        assert created_date.year >= 2023, "User from before 2023"
```

### Parameterized Tests

Test multiple users/scenarios:

```python
import pytest

@pytest.mark.parametrize('user_id', [1, 2, 3, 123, 456])
def test_get_user_by_id(user_id):
    """Test GET /users/{id} for multiple users"""
    response = requests.get(f'https://api.example.com/users/{user_id}')

    assert response.status_code == 200
    data = response.json()
    assert data['id'] == user_id
    assert 'name' in data
    assert 'email' in data
```

### Smoke Tests

Create fast smoke tests from baseline:

```bash
# Generate minimal tests
python tracetap-playwright.py baseline.json \
  --output tests/ \
  --skip-body-assertions \
  --class-name SmokeTesting
```

Test only status codes and headers (fast):

```python
def test_all_endpoints_responsive():
    """Smoke test: all endpoints return 2xx/3xx"""
    with open('baseline.json') as f:
        captures = json.load(f)

    for capture in captures['requests']:
        response = requests.request(
            method=capture['method'],
            url=capture['url'],
            headers=capture['headers']
        )

        assert 200 <= response.status_code < 400, \
            f"{capture['method']} {capture['url']} returned {response.status_code}"
```

---

## Best Practices

### 1. Capture Representative Traffic

- ✅ Include happy path workflows
- ✅ Include error cases (invalid IDs, missing fields)
- ✅ Include edge cases (empty results, large payloads)
- ❌ Avoid including production data (PII)

```bash
# Good: Mix of success and error cases
curl https://api.example.com/users/123          # Success
curl https://api.example.com/users/999999       # Not found
curl https://api.example.com/users               # List
curl -X POST https://api.example.com/users \
  -d '{"name":""}' # Validation error
```

### 2. Version Your Baselines

```bash
# Use date-based naming
python tracetap.py --listen 8080 --export baseline-2024-02-01.json

# Or version-based
python tracetap.py --listen 8080 --export baseline-v2.1.0.json

# Commit to version control
git add baseline-*.json
git commit -m "Add API baseline for regression testing"
```

### 3. Update When Intentional Changes Occur

When you intentionally change your API:

```bash
# Capture new baseline
python tracetap.py --listen 8080 --export baseline-v2.2.0.json

# Regenerate tests
python tracetap-playwright.py baseline-v2.2.0.json -o tests/

# Update CI/CD to use new baseline
git add tests/ baseline-v2.2.0.json
git commit -m "Update regression tests for API v2.2.0"
```

### 4. Monitor Test Failures

```bash
# Add failure tracking
pytest tests/ \
  --junitxml=results.xml \
  --json-report \
  --json-report-file=report.json

# Parse for metrics
python -c "
import json
with open('report.json') as f:
    data = json.load(f)
    print(f'Passed: {data[\"summary\"][\"passed\"]}')
    print(f'Failed: {data[\"summary\"][\"failed\"]}')
"
```

### 5. Exclude Flaky Data

Skip tests for values that change:

```python
def test_get_user():
    response = requests.get('https://api.example.com/users/123')

    data = response.json()

    # Fixed assertions
    assert data['id'] == 123
    assert data['name'] == 'Alice'

    # Skip timestamp (always changes)
    assert 'updated_at' in data  # Just check it exists

    # Skip dynamic fields
    assert 'session_id' in data  # Just check presence
```

### 6. Document Test Expectations

Add comments explaining what each test validates:

```python
def test_post_user():
    """
    Test user creation endpoint.

    This test validates:
    - POST /users accepts name, email
    - Returns 201 Created
    - Response includes auto-generated id
    - Response includes created_at timestamp

    Note: Only captures one successful scenario.
    Error cases (validation errors, duplicates) not tested here.
    """
    response = requests.post(...)
    # ...
```

---

## Troubleshooting

### Tests Pass Locally But Fail in CI

**Problem**: Tests pass when run manually, fail in CI.

**Solution**:
- Ensure environment variables are set (`API_URL`, auth tokens, etc.)
- Check network access from CI environment
- Verify API is running/accessible from CI runner

### Too Many Assertion Failures

**Problem**: When updating API, hundreds of test assertions fail.

**Solution**:
- This is expected when making breaking changes
- Capture new baseline traffic with new API version
- Regenerate tests
- Commit both new baseline and updated tests

### Timing-based Failures

**Problem**: Tests fail intermittently due to timeouts.

**Solution**:
- Remove timing assertions from generated tests
- Skip `response_time` assertions if flaky
- Increase timeout values in CI environment

---

## Next Steps

- **[CI/CD Integration](../guides/ci-cd-integration.md)** - Automate regression testing
- **[Generating Tests](../guides/generating-tests.md)** - Learn more test generation options
- **[Contract Testing](contract-testing.md)** - Combine with contract tests for stronger validation
