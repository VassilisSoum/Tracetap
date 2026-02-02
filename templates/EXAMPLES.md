# Template Output Examples

This document shows example outputs for each template to help users understand what kind of tests will be generated.

## Example Input Data

All examples use this sample correlated event data:

```json
{
  "flow_name": "User Login",
  "events": [
    {
      "ui_event": {
        "type": "navigate",
        "url": "https://app.example.com/login",
        "timestamp": 1675234560000
      },
      "network_calls": [],
      "confidence": 1.0
    },
    {
      "ui_event": {
        "type": "fill",
        "selector": "input[name='email']",
        "value": "user@test.com",
        "timestamp": 1675234562000
      },
      "network_calls": [],
      "confidence": 1.0
    },
    {
      "ui_event": {
        "type": "fill",
        "selector": "input[name='password']",
        "value": "••••••••",
        "timestamp": 1675234563500
      },
      "network_calls": [],
      "confidence": 1.0
    },
    {
      "ui_event": {
        "type": "click",
        "selector": "button[type='submit']",
        "timestamp": 1675234565000
      },
      "network_calls": [
        {
          "method": "POST",
          "url": "https://api.example.com/auth/login",
          "request": {
            "email": "user@test.com",
            "password": "password123"
          },
          "response": {
            "status": 200,
            "headers": {
              "content-type": "application/json"
            },
            "body": {
              "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
              "userId": 42,
              "expiresAt": "2024-02-01T12:00:00Z"
            }
          },
          "duration_ms": 85,
          "timestamp": 1675234565080
        }
      ],
      "confidence": 0.95,
      "time_delta_ms": 80
    }
  ]
}
```

---

## basic.txt Output

### TypeScript

```typescript
import { test, expect } from '@playwright/test';

test('user login flow', async ({ page }) => {
  // Navigate to login page
  await page.goto('https://app.example.com/login');

  // Fill email
  await page.fill('input[name="email"]', 'user@test.com');

  // Fill password
  await page.fill('input[name="password"]', 'test-password');

  // Submit form and wait for API response
  const responsePromise = page.waitForResponse(resp =>
    resp.url().includes('/auth/login') &&
    resp.request().method() === 'POST'
  );

  await page.click('button[type="submit"]');

  // Validate response
  const response = await responsePromise;
  expect(response.status()).toBe(200);

  const body = await response.json();
  expect(body).toHaveProperty('token');
  expect(body).toHaveProperty('userId');
  expect(body).toHaveProperty('expiresAt');

  // Verify navigation after successful login
  await expect(page).toHaveURL(/\/dashboard/);
});
```

### Python

```python
import pytest
from playwright.sync_api import Page, expect

def test_user_login_flow(page: Page) -> None:
    """Test user login flow."""
    # Navigate to login page
    page.goto('https://app.example.com/login')

    # Fill email
    page.fill('input[name="email"]', 'user@test.com')

    # Fill password
    page.fill('input[name="password"]', 'test-password')

    # Submit form and wait for API response
    with page.expect_response(
        lambda r: '/auth/login' in r.url and r.request.method == 'POST'
    ) as response_info:
        page.click('button[type="submit"]')

    response = response_info.value

    # Validate response
    assert response.status == 200

    body = response.json()
    assert 'token' in body
    assert 'userId' in body
    assert 'expiresAt' in body

    # Verify navigation after successful login
    expect(page).to_have_url(re.compile(r'/dashboard'))
```

**Characteristics:**
- Simple, readable test structure
- Basic assertions only (has property, status code)
- Minimal comments
- No edge case handling
- ~30 lines of code

---

## comprehensive.txt Output

### TypeScript

```typescript
import { test, expect } from '@playwright/test';

test.describe('User Login Flow', () => {
  test('should successfully login with valid credentials', async ({ page }) => {
    // Test metadata from correlation analysis
    test.info().annotations.push(
      { type: 'correlation_confidence', description: '0.95 (HIGH)' },
      { type: 'flow', description: 'Login form submission with API validation' },
      { type: 'time_delta', description: '80ms between click and API call' }
    );

    // Navigate to login page
    await page.goto('https://app.example.com/login');

    // Wait for form to be ready
    await page.waitForSelector('form', { state: 'visible' });
    await expect(page.locator('input[name="email"]')).toBeVisible();

    // Fill login form
    await page.fill('input[name="email"]', 'user@test.com');
    await page.fill('input[name="password"]', 'test-password');

    // Verify form state before submission
    await expect(page.locator('button[type="submit"]')).toBeEnabled();

    // Intercept and validate API call
    const startTime = Date.now();
    const responsePromise = page.waitForResponse(resp => {
      return resp.url().includes('/auth/login') &&
             resp.request().method() === 'POST';
    });

    // Submit form - HIGH confidence correlation (0.95)
    await page.click('button[type="submit"]');

    const response = await responsePromise;
    const duration = Date.now() - startTime;

    // Performance assertion based on correlation timing (80ms observed)
    expect(duration).toBeLessThan(150); // Allow 70ms buffer

    // Validate HTTP response
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('application/json');

    // Validate request structure
    const requestBody = response.request().postDataJSON();
    expect(requestBody).toEqual({
      email: 'user@test.com',
      password: expect.any(String)
    });

    // Validate response schema with strict types
    const body = await response.json();
    expect(body).toMatchObject({
      token: expect.stringMatching(/^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$/), // JWT
      userId: expect.any(Number),
      expiresAt: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/) // ISO 8601
    });

    // Additional type validations
    expect(typeof body.token).toBe('string');
    expect(body.token.length).toBeGreaterThan(20);
    expect(body.userId).toBeGreaterThan(0);

    // Validate UI state changes after successful login
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 5000 });
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();

    // Verify token is stored (if applicable)
    const localStorage = await page.evaluate(() => window.localStorage.getItem('authToken'));
    expect(localStorage).toBeTruthy();
  });

  test('should handle invalid credentials gracefully', async ({ page }) => {
    test.info().annotations.push(
      { type: 'test_type', description: 'Error handling validation' }
    );

    await page.goto('https://app.example.com/login');

    await page.fill('input[name="email"]', 'invalid@test.com');
    await page.fill('input[name="password"]', 'wrongpassword');

    const responsePromise = page.waitForResponse(resp =>
      resp.url().includes('/auth/login')
    );

    await page.click('button[type="submit"]');

    const response = await responsePromise;

    // Validate error response
    expect(response.status()).toBe(401);

    const body = await response.json();
    expect(body).toHaveProperty('error');
    expect(body.error).toMatch(/invalid|credentials/i);

    // Verify error message displayed to user
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('Invalid');

    // Ensure user remains on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test('should handle network failures gracefully', async ({ page, context }) => {
    // Simulate offline mode
    await context.setOffline(true);

    await page.goto('https://app.example.com/login');

    await page.fill('input[name="email"]', 'user@test.com');
    await page.fill('input[name="password"]', 'test-password');

    await page.click('button[type="submit"]');

    // Verify error UI for network failure
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText(/network|connection/i);
  });
});
```

**Characteristics:**
- Multiple test cases (happy path + error scenarios)
- Extensive schema validation with regex patterns
- Performance assertions based on correlation data
- UI state verification before and after actions
- Request/response body validation
- Annotations with correlation metadata
- Edge case handling (network failures)
- ~120 lines of code

---

## regression.txt Output

### TypeScript

```typescript
import { test, expect } from '@playwright/test';

/**
 * API Contract Tests - POST /auth/login
 * Version: 1.0.0
 * Last Updated: 2024-02-01
 *
 * These tests validate API contracts and will fail if breaking changes are introduced.
 *
 * Contract Summary:
 * - Endpoint: POST /auth/login
 * - Request: { email: string, password: string }
 * - Success Response (200): { token: string, userId: number, expiresAt: string }
 * - Error Response (401): { error: string }
 */

test.describe('POST /auth/login - Contract v1.0.0', () => {
  const CONTRACT_VERSION = '1.0.0';

  const REQUEST_CONTRACT = {
    required: ['email', 'password'],
    optional: [],
    types: {
      email: 'string',
      password: 'string'
    }
  };

  const SUCCESS_RESPONSE_CONTRACT = {
    status: 200,
    required: ['token', 'userId', 'expiresAt'],
    types: {
      token: 'string',
      userId: 'number',
      expiresAt: 'string'
    },
    patterns: {
      token: /^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$/, // JWT format
      expiresAt: /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/ // ISO 8601
    }
  };

  const ERROR_RESPONSE_CONTRACT = {
    status: 401,
    required: ['error'],
    types: {
      error: 'string'
    }
  };

  test('should match success response contract', async ({ page }) => {
    test.info().annotations.push(
      { type: 'contract_version', description: CONTRACT_VERSION },
      { type: 'breaking_change_detection', description: 'enabled' }
    );

    await page.goto('https://app.example.com/login');

    await page.fill('input[name="email"]', 'user@test.com');
    await page.fill('input[name="password"]', 'validpassword123');

    const responsePromise = page.waitForResponse(resp =>
      resp.url().includes('/auth/login') && resp.request().method() === 'POST'
    );

    await page.click('button[type="submit"]');

    const response = await responsePromise;
    const body = await response.json();

    // BREAKING CHANGE CHECK: Status code
    expect(response.status()).toBe(SUCCESS_RESPONSE_CONTRACT.status);

    // BREAKING CHANGE CHECK: All required fields present
    for (const field of SUCCESS_RESPONSE_CONTRACT.required) {
      expect(body).toHaveProperty(field);
    }

    // BREAKING CHANGE CHECK: Field types unchanged
    for (const [field, expectedType] of Object.entries(SUCCESS_RESPONSE_CONTRACT.types)) {
      expect(typeof body[field]).toBe(expectedType);
    }

    // BREAKING CHANGE CHECK: Field formats unchanged
    for (const [field, pattern] of Object.entries(SUCCESS_RESPONSE_CONTRACT.patterns)) {
      expect(body[field]).toMatch(pattern);
    }

    // BREAKING CHANGE CHECK: No required fields removed
    const actualFields = Object.keys(body);
    const expectedFields = SUCCESS_RESPONSE_CONTRACT.required;
    const missingFields = expectedFields.filter(f => !actualFields.includes(f));

    expect(missingFields).toEqual([]);

    // INFORMATIONAL: Detect new fields (potential breaking change for some clients)
    const newFields = actualFields.filter(f => !expectedFields.includes(f));
    if (newFields.length > 0) {
      console.log(`⚠️  New fields detected in response: ${newFields.join(', ')}`);
      console.log(`   Current contract version: ${CONTRACT_VERSION}`);
      console.log('   Consider updating contract version if these are now required');
    }
  });

  test('should match error response contract', async ({ page }) => {
    test.info().annotations.push({ type: 'contract_version', description: CONTRACT_VERSION });

    await page.goto('https://app.example.com/login');

    await page.fill('input[name="email"]', 'invalid@test.com');
    await page.fill('input[name="password"]', 'wrongpass');

    const responsePromise = page.waitForResponse(resp =>
      resp.url().includes('/auth/login')
    );

    await page.click('button[type="submit"]');

    const response = await responsePromise;
    const body = await response.json();

    // BREAKING CHANGE CHECK: Error status code
    expect(response.status()).toBe(ERROR_RESPONSE_CONTRACT.status);

    // BREAKING CHANGE CHECK: Error structure
    for (const field of ERROR_RESPONSE_CONTRACT.required) {
      expect(body).toHaveProperty(field);
    }

    for (const [field, expectedType] of Object.entries(ERROR_RESPONSE_CONTRACT.types)) {
      expect(typeof body[field]).toBe(expectedType);
    }
  });

  test('should validate request contract', async ({ page }) => {
    test.info().annotations.push({ type: 'contract_version', description: CONTRACT_VERSION });

    await page.goto('https://app.example.com/login');

    await page.fill('input[name="email"]', 'user@test.com');
    await page.fill('input[name="password"]', 'password123');

    const responsePromise = page.waitForResponse(resp =>
      resp.url().includes('/auth/login')
    );

    await page.click('button[type="submit"]');

    const response = await responsePromise;
    const requestBody = response.request().postDataJSON();

    // BREAKING CHANGE CHECK: All required request fields present
    for (const field of REQUEST_CONTRACT.required) {
      expect(requestBody).toHaveProperty(field);
    }

    // BREAKING CHANGE CHECK: Request field types
    for (const [field, expectedType] of Object.entries(REQUEST_CONTRACT.types)) {
      expect(typeof requestBody[field]).toBe(expectedType);
    }

    // INFORMATIONAL: Detect unexpected request fields
    const actualFields = Object.keys(requestBody);
    const expectedFields = [...REQUEST_CONTRACT.required, ...REQUEST_CONTRACT.optional];
    const unexpectedFields = actualFields.filter(f => !expectedFields.includes(f));

    if (unexpectedFields.length > 0) {
      console.log(`⚠️  Unexpected request fields: ${unexpectedFields.join(', ')}`);
      console.log('   This may indicate a client-side breaking change');
    }
  });
});

/**
 * Contract Change Log
 *
 * v1.0.0 (2024-02-01)
 * - Initial contract definition
 * - POST /auth/login endpoint
 * - Request: email (string), password (string)
 * - Success: 200 with token, userId, expiresAt
 * - Error: 401 with error message
 *
 * Future versions should be documented here with migration guides.
 */
```

**Characteristics:**
- Focused on API contracts, not UI behavior
- Explicit contract definitions at top of file
- Each assertion labeled with "BREAKING CHANGE CHECK"
- Detects new/missing/changed fields
- Version tracking and documentation
- Change log at bottom
- Informational warnings (don't fail test)
- ~150 lines of code
- Reusable contract definitions

---

## Comparison Summary

| Aspect | basic.txt | comprehensive.txt | regression.txt |
|--------|-----------|-------------------|----------------|
| **Lines of Code** | ~30 | ~120 | ~150 |
| **Test Cases** | 1 (happy path) | 3+ (happy + errors) | 3 (success + error + request) |
| **Assertions** | 5-8 | 20-30 | 15-20 |
| **Schema Validation** | Basic (has property) | Full (types, patterns) | Contract-based (types, patterns, required) |
| **Error Handling** | None | Multiple scenarios | Error contract validation |
| **Performance** | None | Timing assertions | None |
| **Documentation** | Minimal | Extensive comments | Contract changelog |
| **Version Tracking** | No | No | Yes |
| **Breaking Change Detection** | No | No | Yes |
| **UI Validation** | Basic URL check | Full state verification | None (API-focused) |
| **Best For** | Smoke tests | CI/CD pipelines | API versioning |

---

## Selection Guide

**Choose basic.txt when:**
- You need quick test coverage
- Testing simple flows
- Creating proof-of-concept tests
- Building initial test suite
- Time is constrained

**Choose comprehensive.txt when:**
- Tests will run in CI/CD
- Testing critical business flows
- Need full regression coverage
- Want edge case handling
- Performance matters

**Choose regression.txt when:**
- Managing API versions
- Need to detect breaking changes
- Implementing contract-first development
- Working with external API consumers
- Documentation is critical
