# REST API Regression Suite with TraceTap

This example demonstrates how to build a complete regression test suite for a REST API using TraceTap's traffic capture and AI-powered test generation.

## Overview

In this example, you will:
1. Capture full CRUD operations from an API
2. Export traffic as JSON for AI analysis
3. Use Claude AI to generate comprehensive Playwright regression tests
4. Set up an automated CI/CD testing workflow

## Prerequisites

```bash
# Install TraceTap (from project root)
pip install -e .

# Install Playwright
npm install @playwright/test
npx playwright install
```

## Directory Structure

```
regression-suite/
├── README.md                    # This file
├── captured-traffic/
│   └── crud-operations.json    # Captured CRUD traffic
├── generated-tests/
│   ├── api-regression.spec.ts  # AI-generated regression tests
│   └── playwright.config.ts    # Playwright configuration
└── ci-cd/
    └── github-actions.yml     # GitHub Actions workflow
```

## Quick Start

### Step 1: Capture API Traffic

Start TraceTap to capture your API's CRUD operations:

```bash
tracetap capture --port 8080 \
    --output captured-traffic/crud-operations.json \
    --filter-host "localhost:3000"
```

Then exercise your API through the proxy:

```bash
export HTTP_PROXY=http://localhost:8080

# CREATE
curl -X POST http://localhost:3000/users \
    -H "Content-Type: application/json" \
    -d '{"name": "John", "email": "john@example.com"}'

# READ
curl http://localhost:3000/users
curl http://localhost:3000/users/1

# UPDATE
curl -X PUT http://localhost:3000/users/1 \
    -H "Content-Type: application/json" \
    -d '{"name": "John Doe", "email": "john.doe@example.com"}'

# DELETE
curl -X DELETE http://localhost:3000/users/1
```

Press `Ctrl+C` to stop capture and export.

### Step 2: Generate Tests with Claude AI

Use the captured JSON with Claude to generate comprehensive regression tests:

```bash
# Use Claude CLI
claude "Generate comprehensive Playwright regression tests from this API traffic: $(cat captured-traffic/crud-operations.json)"
```

Or use Claude Code:

```
@crud-operations.json Generate a complete Playwright regression test suite for
this REST API. Include:
- Individual CRUD operation tests
- Full workflow test (create -> read -> update -> delete)
- Schema validation for all responses
- Error scenario tests
- Assertions for critical fields: id, email, status
```

### Step 3: Run the Tests

```bash
cd generated-tests
npm install
npx playwright test
```

### Step 4: View Test Report

```bash
npx playwright show-report
```

## Captured Traffic Format

The CRUD operations JSON structure:

```json
{
  "metadata": {
    "session_name": "crud-operations",
    "timestamp": "2024-01-20T14:00:00Z"
  },
  "requests": [
    {
      "method": "POST",
      "url": "http://localhost:3000/users",
      "status_code": 201,
      "body": "{\"name\": \"John\", \"email\": \"john@example.com\"}",
      "response_body": "{\"id\": 1, \"name\": \"John\", \"email\": \"john@example.com\"}"
    }
  ]
}
```

## AI-Generated Test Structure

When you provide captured traffic to Claude, it generates tests with multiple assertion types:

### Status Code Assertions
```typescript
expect(response.status()).toBe(200);
```

### Schema Assertions
```typescript
expect(user).toHaveProperty('id');
expect(user).toHaveProperty('name');
expect(user).toHaveProperty('email');
```

### Data Type Assertions
```typescript
expect(typeof user.id).toBe('number');
expect(typeof user.name).toBe('string');
```

### Value Assertions
```typescript
expect(user.email).toMatch(/.*@.*\..*/);
expect(user.status).toBe('active');
```

### Complete Workflow Test
```typescript
test('Complete CRUD workflow', async ({ request }) => {
  // CREATE
  const createResponse = await request.post('/users', {
    data: { name: 'Test User', email: 'test@example.com' }
  });
  expect(createResponse.status()).toBe(201);
  const user = await createResponse.json();
  expect(user.id).toBeDefined();

  // READ
  const getResponse = await request.get(`/users/${user.id}`);
  expect(getResponse.status()).toBe(200);
  const fetchedUser = await getResponse.json();
  expect(fetchedUser.email).toBe('test@example.com');

  // UPDATE
  const updateResponse = await request.put(`/users/${user.id}`, {
    data: { name: 'Updated User' }
  });
  expect(updateResponse.status()).toBe(200);

  // DELETE
  const deleteResponse = await request.delete(`/users/${user.id}`);
  expect(deleteResponse.status()).toBe(204);

  // VERIFY DELETION
  const verifyResponse = await request.get(`/users/${user.id}`);
  expect(verifyResponse.status()).toBe(404);
});
```

## Claude AI Prompts for Regression Tests

### Basic Regression Suite
```
Generate Playwright regression tests from this API traffic.
Group tests by endpoint and include status code assertions.
```

### Comprehensive Regression Suite
```
Generate a comprehensive Playwright regression test suite:
1. Individual tests for each captured endpoint
2. CRUD workflow tests that chain operations
3. Schema validation (check all response fields exist)
4. Data type validation
5. Critical field assertions for: id, email, created_at
6. Error handling tests (404, 400, 500 scenarios)
```

### Breaking Change Detection
```
Generate regression tests focused on detecting breaking changes:
- Field presence checks (will fail if fields are removed)
- Field type checks (will fail if types change)
- Status code verification
- Response structure validation
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/api-regression.yml
name: API Regression Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  regression-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Playwright
        run: |
          cd examples/regression-suite/generated-tests
          npm ci
          npx playwright install --with-deps

      - name: Start API Server
        run: |
          python examples/regression-suite/sample-api/server.py &
          sleep 5

      - name: Run Regression Tests
        run: |
          cd examples/regression-suite/generated-tests
          npx playwright test

      - name: Upload Test Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: examples/regression-suite/generated-tests/playwright-report/
```

## Environment-Specific Testing

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  use: {
    baseURL: process.env.API_URL || 'http://localhost:3000',
  },
});
```

Run against different environments:

```bash
API_URL=https://staging.api.example.com npx playwright test
API_URL=https://prod.api.example.com npx playwright test
```

## Detecting API Breaking Changes

### Scenario: Field Name Change

**Before (API v1):**
```json
{"user_name": "John"}
```

**After (API v2):**
```json
{"name": "John"}
```

**Test failure:**
```
Error: expect(received).toHaveProperty(path)
Expected path: "user_name"
Received object: {"name": "John"}
```

This catches breaking changes before deployment.

## Regenerating Tests After API Changes

When your API changes intentionally:

```bash
# 1. Re-capture traffic with new API
tracetap capture --port 8080 --output new-traffic.json

# 2. Regenerate tests with Claude
claude "Generate updated regression tests from: $(cat new-traffic.json)"

# 3. Review and commit new tests
```

## Troubleshooting

### Tests failing after API update

1. Check if changes are intentional
2. Re-capture traffic for new API version
3. Regenerate tests with Claude

### Flaky tests

Add retry logic in playwright.config.ts:

```typescript
export default defineConfig({
  retries: 2,
});
```

### Timeout issues

Increase timeout:

```typescript
test.setTimeout(30000);
```

## Next Steps

- Explore the [E-commerce Example](../ecommerce-api/) for workflow testing
- Read the main [TraceTap documentation](../../README.md)
