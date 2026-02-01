# AI-Powered Test Suggestions

Let Claude AI analyze your API traffic and suggest smart tests you might have missed.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Getting Started](#getting-started)
- [Usage Examples](#usage-examples)
- [Customizing AI Suggestions](#customizing-ai-suggestions)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

Writing comprehensive tests is hard. You capture traffic, but you don't always think of edge cases. TraceTap's AI analysis helps by:

1. **Analyzing captured traffic** to understand API patterns
2. **Suggesting additional test cases** you might have missed
3. **Recommending assertions** that would catch common bugs
4. **Identifying edge cases** and error scenarios
5. **Generating test code** in your preferred format

### What AI Can Suggest

Given your captured traffic, AI can recommend tests for:

- **Boundary conditions**: Empty strings, null values, very large numbers
- **Error handling**: What happens with invalid IDs, expired tokens?
- **Race conditions**: What if requests come in different order?
- **Data validation**: Do dates parse correctly? Are IDs in valid format?
- **Performance**: How should slow endpoints behave?
- **Security**: Are sensitive fields properly protected?
- **Concurrency**: What happens with simultaneous requests?

### Example: AI Analyzing Traffic

**Captured requests:**
```
POST /api/users
GET /api/users/123
GET /api/users/123/posts
```

**AI Suggests:**
- ✅ Test with invalid user ID (999999)
- ✅ Test with empty POST body
- ✅ Test with null name field
- ✅ Test pagination (limit, offset)
- ✅ Test unauthorized access (no token)
- ✅ Test race conditions (concurrent posts)
- ✅ Test deletion cascades (user deleted, posts still accessible?)

---

## How It Works

### The AI Analysis Pipeline

```
┌──────────────────────────────────┐
│ 1. Captured Traffic              │
│    baseline.json                 │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 2. Claude AI Analyzes Patterns           │
│    - Endpoint structure                  │
│    - Data types and formats              │
│    - Relationships between requests      │
│    - Common failure modes                │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 3. AI Generates Test Suggestions         │
│    - Edge cases                          │
│    - Error scenarios                     │
│    - Performance tests                   │
│    - Security tests                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 4. Tests Generated & Ready to Run        │
│    test_edge_cases.py                    │
│    test_error_handling.py                │
│    test_security.py                      │
└──────────────────────────────────────────┘
```

### What AI Analyzes

**Request Patterns:**
- HTTP methods (GET, POST, PUT, DELETE, etc.)
- URL structure and path patterns
- Query parameters and their purposes
- Request headers and authentication

**Response Patterns:**
- Status codes (200, 201, 400, 404, 500)
- Response structure (arrays, objects, primitives)
- Field types and nullable fields
- Error message formats

**Data Relationships:**
- How requests relate (e.g., create user, then get user)
- ID patterns and generation
- Timestamp formats and ranges
- State transitions and side effects

---

## Getting Started

### Prerequisites

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY='sk-ant-...'

# Verify it works
python3 -c "import anthropic; print('✓ API key valid')"
```

### Step 1: Capture Traffic

Capture representative API traffic:

```bash
python tracetap.py --listen 8080 --export api.json

# In another terminal, exercise your API
export HTTP_PROXY=http://localhost:8080
curl -k https://api.example.com/users
curl -k https://api.example.com/users/123
curl -k -X POST https://api.example.com/users -d '{"name":"Bob"}'

# Stop capture (Ctrl+C)
```

### Step 2: Analyze with AI

Use the AI test suggester to analyze traffic:

```bash
# Analyze captured traffic
python -c "
from src.tracetap.ai import TestSuggester
import json

# Load captures
with open('api.json') as f:
    data = json.load(f)

# Create suggester
suggester = TestSuggester(api_key='your-key')

# Get suggestions
suggestions = suggester.suggest_tests(
    captures=data['requests'],
    focus_areas=['edge_cases', 'error_handling', 'security']
)

# Print suggestions
for category, tests in suggestions.items():
    print(f'\n{category}:')
    for test in tests:
        print(f'  - {test[\"name\"]}: {test[\"description\"]}')
"
```

### Step 3: Generate Test Code

Generate executable tests from suggestions:

```bash
# Generate tests
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --output tests/

# View generated tests
cat tests/test_edge_cases.py
cat tests/test_error_handling.py
```

---

## Usage Examples

### Example 1: Edge Case Testing

Analyze API and generate edge case tests:

```bash
python -c "
from src.tracetap.ai import TestSuggester, TestGenerator
import json

with open('api.json') as f:
    data = json.load(f)

suggester = TestSuggester(api_key='sk-ant-...')
generator = TestGenerator()

# Get suggestions
suggestions = suggester.suggest_tests(
    captures=data['requests'],
    focus_areas=['edge_cases']
)

# Generate code
for test in suggestions.get('edge_cases', []):
    code = generator.generate_test_code(
        test=test,
        language='python',
        framework='pytest'
    )
    print(f'# Test: {test[\"name\"]}')
    print(code)
    print()
"
```

**Sample output:**

```python
# Test: Empty user list
@pytest.mark.edge_case
def test_list_users_empty_result():
    \"\"\"Test GET /users when no users exist\"\"\"
    response = requests.get('https://api.example.com/users')

    assert response.status_code == 200
    data = response.json()
    assert data == []
    assert response.headers.get('X-Total-Count') == '0'


# Test: Maximum user ID
@pytest.mark.edge_case
def test_get_user_with_max_id():
    \"\"\"Test GET /users with very large ID\"\"\"
    max_id = 9223372036854775807  # Max int64

    response = requests.get(f'https://api.example.com/users/{max_id}')

    assert response.status_code in [404, 400]  # Not found or bad request


# Test: Null name field
@pytest.mark.edge_case
def test_create_user_with_null_name():
    \"\"\"Test POST /users with null name field\"\"\"
    response = requests.post(
        'https://api.example.com/users',
        json={'name': None, 'email': 'test@example.com'}
    )

    assert response.status_code == 400
    assert 'name' in response.json().get('errors', {})
```

### Example 2: Error Handling Tests

Focus on error scenarios:

```bash
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --focus-error-handling \
  --output tests/error_handling.py
```

Generated tests:

```python
class TestErrorHandling:
    \"\"\"Error handling tests suggested by AI\"\"\"

    def test_invalid_user_id_format(self):
        \"\"\"Test with non-numeric user ID\"\"\"
        response = requests.get('https://api.example.com/users/abc123')
        assert response.status_code == 400

    def test_missing_required_field(self):
        \"\"\"Test POST without required email field\"\"\"
        response = requests.post(
            'https://api.example.com/users',
            json={'name': 'Test'}
        )
        assert response.status_code == 400
        errors = response.json().get('errors', {})
        assert 'email' in errors

    def test_unauthorized_access(self):
        \"\"\"Test without authentication token\"\"\"
        response = requests.get(
            'https://api.example.com/users',
            headers={}  # No auth
        )
        assert response.status_code == 401

    def test_rate_limit_exceeded(self):
        \"\"\"Test behavior when rate limit is hit\"\"\"
        for i in range(101):  # Assume limit is 100
            response = requests.get('https://api.example.com/users')

        assert response.status_code == 429  # Too Many Requests
        assert 'Retry-After' in response.headers
```

### Example 3: Security Tests

Generate security-focused tests:

```bash
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --focus-security \
  --output tests/security.py
```

Generated tests:

```python
class TestSecurity:
    \"\"\"Security tests suggested by AI\"\"\"

    def test_sql_injection_attempt(self):
        \"\"\"Test SQL injection prevention\"\"\"
        response = requests.get(
            'https://api.example.com/users/123 OR 1=1'
        )
        assert response.status_code == 400  # Bad request
        assert response.json().get('error') != 'all_users'

    def test_xss_prevention(self):
        \"\"\"Test XSS prevention in POST body\"\"\"
        response = requests.post(
            'https://api.example.com/users',
            json={'name': '<script>alert(1)</script>'}
        )
        data = response.json()
        assert '<script>' not in data.get('name', '')

    def test_sensitive_data_exposure(self):
        \"\"\"Test that sensitive fields are not exposed\"\"\"
        response = requests.get('https://api.example.com/users/123')
        data = response.json()

        # Should not expose password hash
        assert 'password' not in data
        assert 'password_hash' not in data

        # Should not expose internal IDs
        assert 'internal_id' not in data
        assert 'db_id' not in data

    def test_cors_headers_present(self):
        \"\"\"Test CORS security headers\"\"\"
        response = requests.get('https://api.example.com/users')

        assert 'Access-Control-Allow-Origin' in response.headers
        assert response.headers['Access-Control-Allow-Origin'] != '*'
```

---

## Customizing AI Suggestions

### Focus on Specific Areas

```bash
# Focus on edge cases only
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --focus-areas edge_cases \
  --output tests/

# Focus on multiple areas
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --focus-areas edge_cases error_handling performance \
  --output tests/

# Available focus areas:
# - edge_cases
# - error_handling
# - security
# - performance
# - concurrency
# - validation
# - integration
```

### Provide Custom Instructions

Guide AI with your specific concerns:

```bash
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --ai-instructions "
    This is a fintech API. Focus heavily on:
    - Transaction consistency and atomicity
    - Audit logging of all operations
    - Permission validation (who can access what)
    - Handling of negative balances
    - Decimal precision in calculations
  " \
  --output tests/
```

### Filter by Endpoint

Test only specific endpoints:

```bash
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --endpoint-filter "^/api/users" \
  --output tests/

# Multiple filters
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --endpoint-filter "^/api/users" "^/api/posts" \
  --output tests/
```

---

## Best Practices

### 1. Start with AI Suggestions

When you first start testing:

```bash
# Capture traffic
python tracetap.py --listen 8080 --export api.json

# Let AI suggest what to test
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --output tests/

# Review and adapt suggestions
# (Don't blindly trust AI - verify suggestions make sense)
```

### 2. Review Before Running

Always review AI-generated tests before running:

```python
# ✓ Good test - clear and actionable
def test_create_user_with_null_email():
    response = requests.post(
        'https://api.example.com/users',
        json={'name': 'Test', 'email': None}
    )
    assert response.status_code == 400

# ❌ Bad test - assumption incorrect for your API
def test_get_user_returns_password():
    # You know your API doesn't return passwords
    # So this test is pointless
    pass
```

### 3. Combine with Manual Tests

AI suggestions + manual tests = comprehensive coverage:

```bash
# AI-generated tests (catch patterns)
pytest tests/test_edge_cases.py

# Manual tests (test your specific business logic)
pytest tests/test_business_logic.py

# Together they provide good coverage
pytest tests/
```

### 4. Use for Regression Prevention

When you fix a bug, add an AI-suggested test:

```bash
# 1. Bug found: missing validation on email field
# 2. Add AI test that catches this
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --custom-focus "email validation" \
  --output tests/

# 3. Add that test to your test suite
# 4. Now this bug can't regress
```

### 5. Iterate with Focus Areas

Start broad, then focus:

```bash
# First pass: all suggestions
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --output tests/v1/

# Second pass: focus on security
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --focus-security \
  --output tests/v2/

# Third pass: add custom concerns
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --ai-instructions "Focus on payment processing edge cases" \
  --output tests/v3/
```

---

## Troubleshooting

### API Key Not Working

```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Test the key
python3 -c "
import anthropic
client = anthropic.Anthropic()
msg = client.messages.create(
    model='claude-3-5-sonnet-20241022',
    max_tokens=10,
    messages=[{'role': 'user', 'content': 'test'}]
)
print('✓ API key works')
"
```

### AI Suggestions Don't Make Sense

**Problem**: AI suggests tests that don't fit your API

**Solution**:
- Provide better custom instructions
- Include more representative traffic samples
- Focus on specific concern areas
- Review and edit suggestions before running

### Tests Fail Due to Different Environment

**Problem**: Generated tests pass locally but fail in CI

**Solution**:
```bash
# Update base URL for different environment
API_URL=https://staging-api.example.com pytest tests/

# Or modify tests to use environment variable
# In generated tests:
BASE_URL = os.getenv('API_URL', 'https://api.example.com')
```

### Too Many Suggestions

**Problem**: AI generates hundreds of suggestions

**Solution**:
```bash
# Limit to specific focus areas
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --focus-areas edge_cases \
  --max-suggestions 20 \
  --output tests/

# Or focus on specific endpoints
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --endpoint-filter "^/api/critical" \
  --output tests/
```

---

## Next Steps

- **[Regression Testing](regression-testing.md)** - Use AI tests as regression suite
- **[Contract Testing](contract-testing.md)** - Combine AI tests with contract verification
- **[Generating Tests](../guides/generating-tests.md)** - Learn more generation options
