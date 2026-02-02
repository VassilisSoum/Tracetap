# TodoMVC Example - UI Recording & Test Generation

Learn TraceTap basics with this simple todo application.

## Overview

**Application:** [Playwright TodoMVC Demo](https://demo.playwright.dev/todomvc/)
**Difficulty:** Beginner
**Time:** 10-15 minutes
**Pre-requisites:** None

## What You'll Learn

- How to record UI interactions
- How correlated events work
- Differences between test templates
- How to run generated tests

## Session Overview

This example records a typical todo workflow:

1. **Add two todos** - "Buy groceries" and "Walk the dog"
2. **Complete one** - Check "Buy groceries"
3. **Filter by status** - Click "Active" to show incomplete
4. **Clear completed** - Remove completed items

## Files Included

```
todomvc/
├── README.md                          # This file
├── session-example/                   # Pre-recorded session
│   ├── metadata.json                  # Session metadata
│   └── correlation.json               # UI + API correlations
├── generated-tests/
│   ├── basic.spec.ts                  # Basic template (~30 lines)
│   ├── comprehensive.spec.ts          # Comprehensive (~120 lines)
│   └── regression.spec.ts             # Regression (~150 lines)
├── playwright.config.ts               # Playwright configuration
└── package.json                       # Test dependencies
```

## Quick Start

### Run Pre-Generated Tests

```bash
# Install dependencies
npm install

# Run all tests
npx playwright test

# Run specific template
npx playwright test generated-tests/comprehensive.spec.ts

# Run with UI mode (see tests in action)
npx playwright test --ui
```

## Understanding the Session

### Session Metadata

```bash
cat session-example/metadata.json
```

**Key information:**
- Session ID: `20260202_123456_todomvc`
- URL: `https://demo.playwright.dev/todomvc/`
- Duration: 45.3 seconds
- UI Events: 5
- Network Calls: 3
- Correlation Rate: 80% (4/5 events)

### Correlated Events

```bash
cat session-example/correlation.json | jq
```

**Event 1: Add First Todo**
```json
{
  "sequence": 1,
  "uiEvent": {
    "type": "fill",
    "selector": "input.new-todo",
    "value": "Buy groceries",
    "timestamp": 1675234567890
  },
  "networkCalls": [
    {
      "method": "POST",
      "url": "/api/todos",
      "request": {"text": "Buy groceries"},
      "response": {"status": 201, "body": {"id": 1, "text": "Buy groceries", "completed": false}}
    }
  ],
  "correlation": {
    "confidence": 0.92,
    "timeDelta": 87,
    "reasoning": "High confidence - Fill event triggered POST within 87ms"
  }
}
```

**Why 92% confidence?**
- Very short time delta (87ms)
- Clear cause-effect (fill input → create todo)
- Single API call (no ambiguity)
- POST method (mutation matches user intent)

## Template Comparison

### Basic Template (30 lines)

**What it generates:**
- Essential assertions only
- Status code checks
- Basic structure validation

**Example:**
```typescript
test('add todo', async ({ page }) => {
  await page.fill('input.new-todo', 'Buy groceries');
  await page.press('input.new-todo', 'Enter');

  const response = await page.waitForResponse('/api/todos');
  expect(response.status()).toBe(201);
});
```

**Use when:**
- Quick smoke tests
- CI/CD fast feedback
- Sanity checking

### Comprehensive Template (120 lines)

**What it generates:**
- Full schema validation
- Edge case handling (empty input, long text)
- Loading states
- Performance assertions

**Example:**
```typescript
test('add todo with full validation', async ({ page }) => {
  // Setup - verify initial state
  await expect(page.locator('.todo-list li')).toHaveCount(0);

  // Action
  await page.fill('input.new-todo', 'Buy groceries');
  await page.press('input.new-todo', 'Enter');

  // API validation
  const response = await page.waitForResponse('/api/todos');
  expect(response.status()).toBe(201);

  const body = await response.json();
  expect(body).toMatchObject({
    id: expect.any(Number),
    text: 'Buy groceries',
    completed: false,
    createdAt: expect.stringMatching(/\d{4}-\d{2}-\d{2}/)
  });

  // UI validation
  await expect(page.locator('.todo-list li')).toHaveCount(1);
  await expect(page.locator('.todo-list li')).toContainText('Buy groceries');

  // Input cleared
  await expect(page.locator('input.new-todo')).toHaveValue('');
});
```

**Use when:**
- Production test suites
- Critical user flows
- Comprehensive coverage needed

### Regression Template (150 lines)

**What it generates:**
- API contract definitions
- Schema validation with Zod
- Version tracking
- Breaking change detection

**Example:**
```typescript
import { z } from 'zod';

// Contract: POST /api/todos v1.0.0
const TodoSchema = z.object({
  id: z.number().positive(),
  text: z.string().min(1),
  completed: z.boolean(),
  createdAt: z.string().datetime()
});

test('create todo - contract validation', async ({ page }) => {
  await page.fill('input.new-todo', 'Buy groceries');
  await page.press('input.new-todo', 'Enter');

  const response = await page.waitForResponse('/api/todos');
  const body = await response.json();

  // This will FAIL if backend changes the contract
  const result = TodoSchema.safeParse(body);
  expect(result.success).toBe(true);

  if (!result.success) {
    console.error('Contract violation:', result.error.errors);
  }
});
```

**Use when:**
- API versioning
- Detecting breaking changes
- Contract testing

## Generate Your Own Tests

Want to generate tests from this session?

```bash
# Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# Generate with basic template
tracetap-generate-tests session-example \
  -o generated-tests/my-basic.spec.ts \
  --template basic

# Generate with comprehensive template
tracetap-generate-tests session-example \
  -o generated-tests/my-comprehensive.spec.ts \
  --template comprehensive

# Generate Python tests
tracetap-generate-tests session-example \
  -o generated-tests/test_my_flow.py \
  --format python
```

## Record Your Own Session

Want to record your own TodoMVC session?

```bash
# 1. Record
tracetap record https://demo.playwright.dev/todomvc/ -n my-todomvc

# 2. Interact with the app (suggestions):
#    - Add 3 different todos
#    - Complete 2 of them
#    - Try filtering (All/Active/Completed)
#    - Clear completed
#    - Edit a todo (double-click)

# 3. Press Enter when done

# 4. Generate tests
tracetap-generate-tests recordings/<your-session-id> \
  -o generated-tests/my-tests.spec.ts
```

## Understanding the Results

### Correlation Quality Indicators

**EXCELLENT (80%+):**
- Most UI actions triggered APIs
- High confidence scores
- Short time deltas

**GOOD (60-80%):**
- Most events correlated
- Some low-confidence matches
- Acceptable for test generation

**MODERATE (<60%):**
- Many uncorrelated events
- May need manual review
- Consider re-recording with clearer actions

### Why Some Events Don't Correlate

**Event not correlated:**
- Purely client-side (filter display)
- No API interaction
- UI-only state change

This is normal! Not every UI action triggers an API call.

## Next Steps

1. ✅ Run the pre-generated tests
2. ✅ Review the three template outputs
3. ✅ Try generating your own tests from this session
4. ✅ Record your own TodoMVC session
5. ⏭️ Move to the [E-commerce Example](../ecommerce/)

## Troubleshooting

**Tests fail with "Target closed" error:**
- Solution: Update `baseURL` in playwright.config.ts

**API calls show 404:**
- TodoMVC demo uses in-memory storage
- Endpoints may differ from this example
- Re-record to capture current behavior

## Support

- [Getting Started Guide](../../../docs/getting-started/UI_RECORDING.md)
- [API Reference](../../../docs/api/cli-reference.md)
- [GitHub Issues](https://github.com/anthropics/tracetap/issues)
