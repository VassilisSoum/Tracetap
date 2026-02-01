# Playwright Integration Workflow

Complete guide for integrating TraceTap with Playwright tests to capture traffic, generate tests, and build regression suites.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Workflow 1: Capture During Test Execution](#workflow-1-capture-during-test-execution)
4. [Workflow 2: Generate Tests from Captures](#workflow-2-generate-tests-from-captures)
5. [Workflow 3: Regression Test Suite](#workflow-3-regression-test-suite)
6. [Advanced Integration](#advanced-integration)
7. [Common Pitfalls](#common-pitfalls)
8. [Best Practices](#best-practices)

---

## Overview

TraceTap integrates with Playwright in two powerful ways:

1. **Capture traffic during Playwright tests** - Record API calls made by your application during automated browser tests
2. **Generate Playwright API tests** - Convert captured traffic into standalone API test suites

This enables a complete testing workflow:
```
Browser Tests → Traffic Capture → API Test Generation → Regression Suite
```

---

## Prerequisites

### Install Required Tools

```bash
# Install TraceTap
pip install tracetap

# Install Playwright
npm install -D @playwright/test
npx playwright install

# Verify installations
tracetap --version
npx playwright --version
```

### Set Environment Variables

```bash
# For AI-powered features (optional but recommended)
export ANTHROPIC_API_KEY='your-api-key'
```

---

## Workflow 1: Capture During Test Execution

### Step 1: Configure Playwright to Use Proxy

Create or modify `playwright.config.ts`:

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  use: {
    // Configure TraceTap proxy
    proxy: {
      server: 'http://localhost:8080',
    },

    // Accept self-signed certificates from TraceTap
    ignoreHTTPSErrors: true,
  },

  // Optional: Configure base URL
  webServer: {
    command: 'npm run dev',
    port: 3000,
    reuseExistingServer: !process.env.CI,
  },
});
```

### Step 2: Start TraceTap Proxy

In a separate terminal, start the TraceTap proxy:

```bash
# Capture all traffic
tracetap capture \
  --port 8080 \
  --session-name "playwright-test-run" \
  --export playwright-api-calls.json

# Or with filtering for specific API
tracetap capture \
  --port 8080 \
  --session-name "playwright-test-run" \
  --filter api.example.com \
  --export playwright-api-calls.json
```

**Tip:** Use `--verbose` flag to see captured requests in real-time:
```bash
tracetap capture --port 8080 --verbose --export output.json
```

### Step 3: Install TraceTap Certificate

For HTTPS traffic, install the TraceTap certificate:

```bash
# Automatic installation
tracetap cert install

# Verify installation
tracetap cert verify
```

Platform-specific instructions:
- **Linux/Chrome**: Uses NSS certificate database
- **macOS**: Adds to system keychain
- **Windows**: Uses certutil

### Step 4: Run Playwright Tests

```bash
# Run tests through proxy
npx playwright test

# Or specific tests
npx playwright test tests/user-flow.spec.ts
```

### Step 5: Verify Captured Traffic

```bash
# Check the output file
cat playwright-api-calls.json | jq '.requests | length'

# View summary
cat playwright-api-calls.json | jq '.metadata'
```

Example output structure:
```json
{
  "metadata": {
    "session_name": "playwright-test-run",
    "timestamp": "2024-01-15T10:30:00Z",
    "total_requests": 47,
    "filter": "api.example.com"
  },
  "requests": [
    {
      "method": "POST",
      "url": "https://api.example.com/auth/login",
      "headers": {...},
      "body": {...},
      "response": {...}
    }
  ]
}
```

---

## Workflow 2: Generate Tests from Captures

### Step 1: Review Captured Traffic

```bash
# Quick overview
tracetap-replay.py variables playwright-api-calls.json --ai
```

This shows:
- Detected variables (IDs, tokens, UUIDs)
- Request patterns
- Authentication methods
- Common headers

### Step 2: Generate Playwright Tests

```bash
# Basic generation
tracetap-playwright playwright-api-calls.json \
  --output tests/api/

# With AI-enhanced test organization
tracetap-playwright playwright-api-calls.json \
  --output tests/api/ \
  --ai

# Without AI (pattern-based)
tracetap-playwright playwright-api-calls.json \
  --output tests/api/ \
  --no-ai
```

**Output structure:**
```
tests/api/
├── playwright-test-run.spec.ts    # Generated test file
└── fixtures.ts                     # Auth and variable fixtures
```

### Step 3: Review Generated Tests

Example generated test:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('POST /auth/login - User login', async ({ request }) => {
    const response = await request.post('https://api.example.com/auth/login', {
      data: {
        email: 'user@example.com',
        password: 'password123'
      }
    });

    expect(response.status()).toBe(200);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('token');
    expect(data.token).toBeTruthy();
  });
});
```

### Step 4: Customize and Run Tests

```bash
# Install dependencies if needed
npm install -D @playwright/test

# Run generated tests
npx playwright test tests/api/

# Run with reporter
npx playwright test tests/api/ --reporter=html
```

---

## Workflow 3: Regression Test Suite

Build a comprehensive regression suite from multiple test runs.

### Step 1: Capture Multiple Scenarios

```bash
# Scenario 1: Happy path
tracetap capture --port 8080 --export captures/happy-path.json &
PROXY_PID=$!
npx playwright test tests/happy-path.spec.ts
kill $PROXY_PID

# Scenario 2: Error handling
tracetap capture --port 8080 --export captures/error-cases.json &
PROXY_PID=$!
npx playwright test tests/error-handling.spec.ts
kill $PROXY_PID

# Scenario 3: Edge cases
tracetap capture --port 8080 --export captures/edge-cases.json &
PROXY_PID=$!
npx playwright test tests/edge-cases.spec.ts
kill $PROXY_PID
```

### Step 2: Generate Test Suite for Each Scenario

```bash
# Generate separate test files
for capture in captures/*.json; do
  tracetap-playwright "$capture" \
    --output tests/regression/ \
    --ai
done
```

### Step 3: Organize Tests

```
tests/regression/
├── happy-path.spec.ts
├── error-cases.spec.ts
├── edge-cases.spec.ts
├── fixtures.ts
└── playwright.config.ts
```

### Step 4: Create Playwright Config

```bash
# Generate config template
tracetap-playwright --config-template > tests/regression/playwright.config.ts
```

Edit the config:

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/regression',
  timeout: 30000,
  retries: process.env.CI ? 2 : 0,

  use: {
    baseURL: process.env.API_BASE_URL || 'https://api.example.com',
    extraHTTPHeaders: {
      'X-Test-Run': 'regression'
    },
  },

  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results.json' }],
  ],
});
```

### Step 5: Run Regression Suite

```bash
# Run all regression tests
npx playwright test --config tests/regression/playwright.config.ts

# Run specific category
npx playwright test --grep "happy-path"

# Parallel execution
npx playwright test --workers=4
```

---

## Advanced Integration

### Automatic Capture Script

Create `scripts/capture-and-test.sh`:

```bash
#!/bin/bash

SESSION_NAME="${1:-test-run}"
TEST_FILE="${2:-tests/}"

# Start TraceTap in background
tracetap capture \
  --port 8080 \
  --session-name "$SESSION_NAME" \
  --export "captures/${SESSION_NAME}.json" \
  --verbose &

PROXY_PID=$!
echo "TraceTap started (PID: $PROXY_PID)"

# Wait for proxy to start
sleep 2

# Run tests
echo "Running Playwright tests..."
npx playwright test "$TEST_FILE"
TEST_EXIT_CODE=$?

# Stop TraceTap
echo "Stopping TraceTap..."
kill $PROXY_PID

# Generate API tests
if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo "Generating Playwright API tests..."
  tracetap-playwright "captures/${SESSION_NAME}.json" \
    --output "tests/generated/" \
    --ai
fi

exit $TEST_EXIT_CODE
```

Usage:
```bash
chmod +x scripts/capture-and-test.sh
./scripts/capture-and-test.sh "user-registration" tests/user-flow.spec.ts
```

### Environment-Specific Configuration

`playwright.config.ts` with conditional proxy:

```typescript
import { defineConfig } from '@playwright/test';

const useProxy = process.env.CAPTURE_TRAFFIC === 'true';

export default defineConfig({
  use: {
    ...(useProxy && {
      proxy: { server: 'http://localhost:8080' },
      ignoreHTTPSErrors: true,
    }),
  },
});
```

Usage:
```bash
# Normal test run
npx playwright test

# Capture traffic
CAPTURE_TRAFFIC=true npx playwright test
```

### Variable Extraction and Fixtures

```bash
# Extract variables from capture
tracetap-replay.py variables captures/session.json \
  --ai \
  --output variables.json

# Generate fixtures
cat variables.json | jq -r '.[] | "export const \(.name) = \"\(.example_values[0])\";"' > fixtures.ts
```

---

## Common Pitfalls

### Issue 1: Certificate Errors

**Problem:** `SSL_ERROR_UNKNOWN_CA_ALERT` or certificate warnings

**Solution:**
```bash
# Re-install certificate
tracetap cert install --force

# Verify installation
tracetap cert verify

# In playwright.config.ts, ensure:
use: {
  ignoreHTTPSErrors: true,
}
```

### Issue 2: No Traffic Captured

**Problem:** Playwright tests run but no requests captured

**Checklist:**
1. ✓ Proxy is running before tests start
2. ✓ Playwright config has correct proxy settings
3. ✓ Application makes external API calls (not mocked)
4. ✓ Filters aren't too restrictive

**Debug:**
```bash
# Use verbose mode to see all traffic
tracetap capture --port 8080 --verbose
```

### Issue 3: Generated Tests Fail

**Problem:** Generated Playwright tests don't pass

**Common causes:**
- **Dynamic data**: Captures contain specific IDs/tokens that don't exist in test environment
- **Authentication**: Tests missing authentication setup
- **Environment differences**: URLs, ports, or endpoints differ

**Solution:**
```typescript
// Use fixtures for dynamic data
test.use({
  extraHTTPHeaders: {
    'Authorization': `Bearer ${process.env.API_TOKEN}`,
  },
});

// Use variables
const userId = process.env.TEST_USER_ID || '12345';
```

### Issue 4: Duplicate Tests

**Problem:** Multiple similar tests generated for same endpoint

**Solution:**
```bash
# Use AI for intelligent deduplication
tracetap-playwright captures/session.json \
  --output tests/ \
  --ai

# Or manually deduplicate using contract approach
tracetap contract create captures/session.json --output contract.yaml
tracetap-playwright contract.yaml --output tests/
```

---

## Best Practices

### 1. Organize Captures by Feature

```bash
captures/
├── auth/
│   ├── login.json
│   ├── logout.json
│   └── refresh-token.json
├── users/
│   ├── create-user.json
│   ├── update-profile.json
│   └── delete-user.json
└── products/
    ├── list-products.json
    └── product-details.json
```

### 2. Use Meaningful Session Names

```bash
# Bad
tracetap capture --session-name "test1"

# Good
tracetap capture --session-name "user-registration-happy-path"
```

### 3. Filter Aggressively

```bash
# Capture only relevant API calls
tracetap capture \
  --filter api.example.com \
  --filter-regex "^/api/(users|products)" \
  --export output.json
```

### 4. Version Control Generated Tests

```bash
# Add to .gitignore
captures/
test-results/

# Commit generated tests
git add tests/api/*.spec.ts
git commit -m "Add generated API regression tests"
```

### 5. Combine with Existing Tests

```typescript
// tests/integration.spec.ts
import { test, expect } from '@playwright/test';
import { generatedTests } from './generated/api-tests';

test.describe('Full Integration Flow', () => {
  // Your manual tests
  test('custom user flow', async ({ page }) => {
    // ...
  });

  // Include generated API tests
  test.describe('API Regression', () => {
    generatedTests.forEach(apiTest => {
      test(apiTest.name, apiTest.testFn);
    });
  });
});
```

### 6. Parameterize Tests

```typescript
// Use test.describe with parameters
const environments = [
  { name: 'staging', baseURL: 'https://staging-api.example.com' },
  { name: 'production', baseURL: 'https://api.example.com' },
];

environments.forEach(env => {
  test.describe(`Tests on ${env.name}`, () => {
    test.use({ baseURL: env.baseURL });
    // Your tests here
  });
});
```

---

## Related Documentation

- [CI/CD Integration](./ci-cd-integration.md) - Automate capture and testing in CI/CD
- [Local Development](./local-development.md) - Quick workflows for daily development
- [Contract-First](./contract-first.md) - Contract-based testing approach
- [TraceTap README](../../README.md) - Full feature documentation
- [Replay Guide](../../REPLAY.md) - Advanced replay and mock features

---

## Quick Reference

### Essential Commands

```bash
# Start capture proxy
tracetap capture --port 8080 --export output.json

# Install certificate
tracetap cert install

# Generate tests
tracetap-playwright capture.json --output tests/

# Run tests
npx playwright test

# Generate config
tracetap-playwright --config-template > playwright.config.ts
```

### Playwright Config Template

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  use: {
    proxy: { server: 'http://localhost:8080' },
    ignoreHTTPSErrors: true,
  },
});
```

---

**Need Help?** Check [troubleshooting section](#common-pitfalls) or see the main [README](../../README.md) for more examples.
