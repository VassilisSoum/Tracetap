# tracetap generate-tests

Generate Playwright tests from recorded sessions using AI.

## Overview

The `tracetap-generate-tests` command uses Claude AI to automatically generate executable Playwright tests from recorded user interactions. It analyzes correlated UI events and network traffic to create comprehensive, production-ready test suites.

## Installation

```bash
# Install with AI test generation support
pip install -e .

# Ensure you have an Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

## Usage

```bash
tracetap-generate-tests <session-dir> -o <output-file> [options]
```

### Arguments

- `session-dir`: Path to recorded session directory (from `tracetap record`)
- `-o, --output`: Output file path for generated tests (required)

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-t, --template` | Template type (basic, comprehensive, regression) | comprehensive |
| `-f, --format` | Output format (typescript, javascript, python) | typescript |
| `--min-confidence` | Minimum correlation confidence (0.0-1.0) | 0.5 |
| `--base-url` | Base URL for application under test | (extracted from session) |
| `--api-key` | Anthropic API key | ANTHROPIC_API_KEY env var |
| `-v, --verbose` | Enable verbose output | false |

## Examples

### Basic Usage

Generate tests from a recorded session:

```bash
tracetap-generate-tests recordings/my-session -o tests/generated.spec.ts
```

### Comprehensive Template

Use the comprehensive template for production-ready tests:

```bash
tracetap-generate-tests recordings/login-flow \
  -o tests/login.spec.ts \
  --template comprehensive
```

### Python Output

Generate Python/Pytest tests instead of TypeScript:

```bash
tracetap-generate-tests recordings/checkout \
  -o tests/test_checkout.py \
  --format python
```

### High Confidence Only

Only include high-confidence correlations (≥80%):

```bash
tracetap-generate-tests recordings/critical-flow \
  -o tests/critical.spec.ts \
  --min-confidence 0.8
```

### Specify Base URL

Override the base URL extracted from the session:

```bash
tracetap-generate-tests recordings/my-session \
  -o tests/output.spec.ts \
  --base-url https://staging.myapp.com
```

### Custom API Key

Provide Anthropic API key directly:

```bash
tracetap-generate-tests recordings/my-session \
  -o tests/output.spec.ts \
  --api-key sk-ant-api03-...
```

## Complete Workflow

### 1. Record Session

First, record a user interaction session:

```bash
tracetap record https://myapp.com -n my-session
# Interact with the application in the browser
# Press Enter when done
```

This creates a session directory at `recordings/<session-id>/` containing:
- `trace.zip` - Playwright trace
- `traffic.json` - Network traffic
- `events.json` - Parsed UI events
- `correlation.json` - Correlated UI+network events
- `metadata.json` - Session metadata

### 2. Generate Tests

Generate tests from the recorded session:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
tracetap-generate-tests recordings/<session-id> -o tests/generated.spec.ts
```

### 3. Review Generated Tests

The generated test file includes:
- Header with generation metadata
- Import statements
- Test fixtures and setup
- Individual test cases
- API response validations
- Comments explaining key actions

### 4. Run Tests

Execute the generated tests:

```bash
# TypeScript/JavaScript
npx playwright test tests/generated.spec.ts

# Python
pytest tests/test_generated.py
```

## Templates

### basic

Quick smoke tests for rapid validation:
- Essential user flows only
- Minimal assertions
- Fast execution
- Good for CI/CD gates

### comprehensive (default)

Production-ready test suites:
- Full user flow coverage
- API response validation
- Edge case handling
- Performance checks
- Detailed error messages
- Retry logic

### regression

API contract validation for detecting breaking changes:
- Schema validation
- Response structure checks
- Status code validation
- Version tracking
- Breaking change detection

## Output Formats

### TypeScript (default)

```typescript
import { test, expect } from '@playwright/test';

test('user login flow', async ({ page }) => {
  await page.goto('https://myapp.com/login');
  await page.fill('[data-testid="email"]', 'user@example.com');
  await page.fill('[data-testid="password"]', 'password123');
  await page.click('[data-testid="submit"]');

  // Validate API response
  const response = await page.waitForResponse('**/api/auth/login');
  expect(response.status()).toBe(200);
});
```

### JavaScript

Same as TypeScript but with JSDoc comments instead of type annotations.

### Python

```python
import pytest
from playwright.sync_api import Page, expect

def test_user_login_flow(page: Page):
    page.goto('https://myapp.com/login')
    page.fill('[data-testid="email"]', 'user@example.com')
    page.fill('[data-testid="password"]', 'password123')
    page.click('[data-testid="submit"]')

    # Validate API response
    with page.expect_response('**/api/auth/login') as response_info:
        response = response_info.value
        assert response.status == 200
```

## API Key

Get your Anthropic API key from: https://console.anthropic.com/

Set it as an environment variable:

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

Or pass it directly via `--api-key` flag.

## Error Messages

### "Session directory not found"
**Cause:** The specified session directory doesn't exist.
**Solution:** Ensure you ran `tracetap record` first and the session path is correct.

### "No correlation file found"
**Cause:** The session directory doesn't contain `correlation.json`.
**Solution:** The session may not have completed analysis. Re-run `tracetap record` to completion.

### "Anthropic API key required"
**Cause:** No API key found in environment or arguments.
**Solution:** Set `ANTHROPIC_API_KEY` environment variable or use `--api-key` flag.

### "Invalid JSON format in correlation file"
**Cause:** The correlation.json file is corrupted or malformed.
**Solution:** Delete the session and re-record it.

## Advanced Usage

### Filtering by Confidence

Control which events are included based on correlation confidence:

```bash
# Only high-confidence events (≥70%)
tracetap-generate-tests recordings/session \
  -o tests/strict.spec.ts \
  --min-confidence 0.7

# Include all events (≥0%)
tracetap-generate-tests recordings/session \
  -o tests/all.spec.ts \
  --min-confidence 0.0
```

### Verbose Mode

Enable detailed logging for debugging:

```bash
tracetap-generate-tests recordings/session \
  -o tests/output.spec.ts \
  --verbose
```

Shows:
- Loaded event count
- Correlation statistics
- AI generation progress
- Syntax validation results

## Tips

1. **Review Generated Tests**: Always review generated tests before committing to version control.

2. **Adjust Selectors**: Replace generic selectors with `data-testid` attributes for stability.

3. **Add Custom Assertions**: Enhance generated tests with domain-specific validations.

4. **Combine Templates**: Start with `basic` for quick validation, then use `comprehensive` for production.

5. **Version Control**: Commit both the session directory and generated tests for reproducibility.

6. **CI Integration**: Use generated tests in your CI/CD pipeline for automated regression testing.

## Troubleshooting

### Tests Fail After Generation

**Common causes:**
- Selectors changed in the application
- API endpoints changed
- Authentication tokens expired
- Network conditions different

**Solutions:**
- Update selectors to use `data-testid`
- Parameterize API endpoints
- Use environment variables for credentials
- Add retry logic and timeouts

### Low Correlation Quality

If correlation rate is low (<40%):
- Increase time window: Re-record with slower interactions
- Check network capture: Ensure mitmproxy captured all traffic
- Verify HTTPS: Check certificate installation for HTTPS apps

### Generated Tests Look Wrong

If tests don't match expected flow:
- Review session: Check `correlation.json` for accuracy
- Increase confidence: Use `--min-confidence 0.7` to filter noise
- Try different template: Switch between basic/comprehensive/regression
- Re-record: Perform clearer, more deliberate actions

## Related Commands

- `tracetap record` - Record user interaction sessions
- `tracetap-replay` - Replay recorded sessions
- `tracetap-playwright` - Run Playwright tests with mocking

## Exit Codes

- `0` - Success
- `1` - Error (invalid arguments, file not found, generation failed)
- `130` - Interrupted by user (Ctrl+C)
