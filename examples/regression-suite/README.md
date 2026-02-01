# REST API Regression Suite with TraceTap

This example demonstrates how to build a complete regression test suite for a REST API using TraceTap's automated test generation capabilities.

## Overview

In this example, you will:
1. Capture full CRUD operations from an API
2. Generate comprehensive Playwright regression tests
3. Configure assertion levels (status codes, schemas, data)
4. Set up an automated CI/CD testing workflow
5. See before/after comparison of API changes

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
│   ├── api-regression.spec.ts  # Generated regression tests
│   └── playwright.config.ts    # Playwright configuration
├── baseline/
│   └── api-baseline.json       # Baseline responses for comparison
├── scripts/
│   └── run-tests.sh           # Test runner script
└── ci-cd/
    └── github-actions.yml     # GitHub Actions workflow
```

## Quick Start

### Step 1: Examine the Captured Traffic

The `captured-traffic/crud-operations.json` contains a complete CRUD workflow:

```bash
cat captured-traffic/crud-operations.json | python3 -m json.tool | head -50
```

The traffic includes:
- **CREATE**: POST /users - Create new user
- **READ**: GET /users, GET /users/{id} - List and fetch users
- **UPDATE**: PUT /users/{id} - Update user data
- **DELETE**: DELETE /users/{id} - Remove user

### Step 2: Generate Regression Tests

Generate Playwright tests from the captured traffic:

```bash
# From project root
python tracetap-replay.py generate-regression \
    examples/regression-suite/captured-traffic/crud-operations.json \
    -o examples/regression-suite/generated-tests/api-regression.spec.ts \
    --grouping endpoint \
    --base-url http://localhost:3000 \
    --assert-types status,schema,data \
    --critical-fields id,email,status
```

**Options explained:**
- `--grouping endpoint` - Group tests by API endpoint
- `--assert-types status,schema,data` - Generate all assertion types
- `--critical-fields` - Fields that must always match

### Step 3: Run the Tests

```bash
# Install dependencies
cd examples/regression-suite/generated-tests
npm install

# Run tests
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

## Generated Test Structure

The generated tests include:

### 1. Status Code Assertions
```typescript
expect(response.status()).toBe(200);
```

### 2. Schema Assertions
```typescript
expect(user).toHaveProperty('id');
expect(user).toHaveProperty('name');
expect(user).toHaveProperty('email');
```

### 3. Data Type Assertions
```typescript
expect(typeof user.id).toBe('number');
expect(typeof user.name).toBe('string');
```

### 4. Value Assertions
```typescript
expect(user.email).toMatch(/.*@.*\..*/);
expect(user.status).toBe('active');
```

### 5. Flow Tests
```typescript
test('Complete CRUD workflow', async ({ request }) => {
  // CREATE
  const createResponse = await request.post('/users', {...});
  const user = await createResponse.json();

  // READ
  const getResponse = await request.get(`/users/${user.id}`);

  // UPDATE
  const updateResponse = await request.put(`/users/${user.id}`, {...});

  // DELETE
  const deleteResponse = await request.delete(`/users/${user.id}`);
});
```

## Assertion Levels

TraceTap supports multiple assertion levels:

| Level | What it checks | Use case |
|-------|---------------|----------|
| `status` | HTTP status codes only | Basic smoke tests |
| `schema` | Response structure | API contract validation |
| `data` | Actual values | Critical field verification |
| `performance` | Response times | SLA validation |

Example configuration:

```bash
# Minimal assertions
python tracetap-replay.py generate-regression traffic.json -o tests.ts \
    --assert-types status

# Full validation
python tracetap-replay.py generate-regression traffic.json -o tests.ts \
    --assert-types status,schema,data \
    --critical-fields id,email,created_at
```

## Baseline Comparison

Track API changes by comparing against a baseline:

```bash
# Create baseline
cp captured-traffic/crud-operations.json baseline/api-baseline.json

# After API changes, capture new traffic
python tracetap.py --listen 8080 --raw-log captured-traffic/new-traffic.json

# Compare
diff baseline/api-baseline.json captured-traffic/new-traffic.json
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

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install TraceTap
        run: pip install -e .

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

## Advanced Usage

### Custom Assertions

Add custom assertions by extending the generated tests:

```typescript
// Add after generated assertions
test('Custom business logic validation', async ({ request }) => {
  const response = await request.get('/users');
  const users = await response.json();

  // Custom assertion: at least one admin user exists
  const admins = users.filter(u => u.role === 'admin');
  expect(admins.length).toBeGreaterThan(0);
});
```

### Environment-Specific Testing

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

### Parallel Test Execution

```typescript
// playwright.config.ts
export default defineConfig({
  fullyParallel: true,
  workers: 4,
});
```

## Before/After: API Change Detection

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

## Troubleshooting

### Tests failing after API update

1. Check if changes are intentional
2. Re-capture traffic for new API version
3. Regenerate tests

```bash
# Re-capture
python tracetap.py --listen 8080 --raw-log new-traffic.json

# Regenerate
python tracetap-replay.py generate-regression new-traffic.json -o tests.ts
```

### Flaky tests

Add retry logic:

```typescript
// playwright.config.ts
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
- See [Contract Testing Example](../contract-testing/) for API contract validation
- Read the main [TraceTap documentation](../../README.md)
