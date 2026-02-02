# Getting Started with UI Recording

Learn how to record your manual tests and generate Playwright code with AI in under 15 minutes.

## What You'll Learn

In this tutorial, you'll:
1. Install TraceTap and required dependencies
2. Record a real user interaction on a demo application
3. Generate comprehensive Playwright tests with AI
4. Understand how correlation works
5. Run and validate your generated tests

**Time to complete:** 15-20 minutes
**Prerequisites:** Python 3.8+, Node.js 16+ (optional but recommended)

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.8 or higher** - Check with `python --version`
- **pip** - Python package manager
- **Anthropic API key** - Get one free at [console.anthropic.com](https://console.anthropic.com)
- **Chromium browser** - Installed via Playwright (we'll do this)
- **Node.js 16+** (optional but recommended for running tests) - Check with `node --version`

---

## Step 1: Install TraceTap (2 minutes)

### Install the Main Package

```bash
pip install tracetap
```

### Install Playwright Dependencies

TraceTap uses Playwright to record browser interactions. Install the Chromium browser:

```bash
playwright install chromium
```

### Install mitmproxy

To capture network traffic, install mitmproxy:

```bash
pip install mitmproxy
```

### Set Up Anthropic API Key

Get your API key from [Anthropic Console](https://console.anthropic.com), then save it as an environment variable:

**Linux/macOS:**
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = 'sk-ant-api03-...'
```

**Persistent setup (Linux/macOS):**
Add this line to your `~/.bashrc` or `~/.zshrc`:
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

Then run:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

### Verify Installation

```bash
# Check Python installation
python --version

# Check TraceTap is installed
python -c "import tracetap; print('✅ TraceTap installed')"

# Check Playwright is installed
python -c "from playwright.async_api import async_playwright; print('✅ Playwright installed')"

# Check API key is set
echo $ANTHROPIC_API_KEY  # Should show your sk-ant-... key
```

---

## Step 2: Record Your First Session (5 minutes)

We'll record a simple interaction on a public demo application.

### Start Recording

Open a terminal and run:

```bash
tracetap record https://todomvc.com/examples/vanilla-es6/ -n first-test
```

**What this command does:**
- `tracetap record` - Starts the recording session
- `https://todomvc.com/examples/vanilla-es6/` - The application to record
- `-n first-test` - Names your session "first-test" (optional but recommended)

### Expected Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬 Recording Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Target URL: https://todomvc.com/examples/vanilla-es6/
Session Name: first-test
Output Directory: ./recordings
Headless Mode: False
Proxy Port: 8888
Correlation Window: 500ms
Min Confidence: 0.5

Browser will open. Interact with the application, then press ENTER to stop.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 Starting recording session...

✓ Recording started
  Session ID: 20260202_143022_abc123
  Browser opened at: https://todomvc.com/examples/vanilla-es6/
```

A Chromium browser window will open with the TodoMVC application. **Don't close this window yet!**

### Interact with the Application

Perform these actions in the opened browser:

1. **Add a todo:**
   - Click the input field at the top
   - Type: "Buy groceries"
   - Press Enter

2. **Add another todo:**
   - Type: "Walk the dog"
   - Press Enter

3. **Complete a todo:**
   - Click the checkbox next to "Buy groceries"
   - The item should appear crossed out

4. **Filter by status:**
   - Click the "Active" button
   - Only incomplete todos should appear

5. **View all again:**
   - Click the "All" button

**Tips for best results:**
- ✅ Wait for the UI to respond before the next action (1-2 seconds)
- ✅ Perform realistic, human-like interactions
- ✅ Include actions that trigger API/network calls
- ❌ Avoid rapid clicking or very fast interactions
- ❌ Don't keep the browser open for longer than 5 minutes

### Stop Recording

Once you're done interacting, **return to the terminal** and press **Enter**:

```
👉 Press ENTER in this terminal when you're done...
```

### Expected Result

```
🟡 Stopping recording...

✓ Recording stopped
  Duration: 42.3s
  Trace file: ./recordings/first-test/trace.zip

🟡 Analyzing session...

✓ Analysis complete

📊 Parse Results:
   UI Events: 8
   Event Types: click, fill, navigate

🔗 Event Correlation:
   Total UI Events: 8
   Network Calls: 2
   Correlation Rate: 75% (6/8 events)
   Average Confidence: 82%

✓ Session saved successfully!
   Location: ./recordings/first-test
   Metadata: ./recordings/first-test/metadata.json
```

The browser will close automatically. Your session is now saved!

---

## Step 3: Examine Your Recording (2 minutes)

Let's look at what was captured.

### List Recording Files

```bash
ls -la recordings/first-test/
```

You'll see:
```
-rw-r--r--  metadata.json       # Session metadata
-rw-r--r--  trace.zip           # Playwright trace (UI events)
-rw-r--r--  traffic.json        # Network traffic capture
-rw-r--r--  events.json         # Parsed UI events
-rw-r--r--  correlation.json    # Correlated UI + API events
```

### View the Metadata

```bash
cat recordings/first-test/metadata.json | jq .
```

**You'll see:**
```json
{
  "session_id": "20260202_143022_abc123",
  "session_name": "first-test",
  "url": "https://todomvc.com/examples/vanilla-es6/",
  "start_time": "2026-02-02T14:30:22.123456",
  "end_time": "2026-02-02T14:31:04.456789",
  "duration": 42.3,
  "output_dir": "./recordings/first-test"
}
```

### View Parsed UI Events

```bash
cat recordings/first-test/events.json | jq '.events[0:3]'
```

**Example output:**
```json
[
  {
    "sequence": 1,
    "type": "navigate",
    "url": "https://todomvc.com/examples/vanilla-es6/",
    "timestamp": 1738500622123
  },
  {
    "sequence": 2,
    "type": "click",
    "selector": "input.new-todo",
    "timestamp": 1738500628456
  },
  {
    "sequence": 3,
    "type": "fill",
    "selector": "input.new-todo",
    "value": "Buy groceries",
    "timestamp": 1738500630789
  }
]
```

### View Correlation Results

```bash
cat recordings/first-test/correlation.json | jq '.correlated_events[0:2]'
```

**Example output:**
```json
{
  "sequence": 1,
  "ui_event": {
    "type": "click",
    "selector": "input.new-todo",
    "timestamp": 1738500628456
  },
  "network_calls": [
    {
      "method": "POST",
      "url": "https://todomvc.com/api/todos",
      "request_body": {
        "title": "Buy groceries"
      },
      "response_status": 201,
      "response_body": {
        "id": 123,
        "title": "Buy groceries",
        "completed": false
      },
      "timestamp": 1738500628543
    }
  ],
  "correlation": {
    "confidence": 0.92,
    "time_delta": 87,
    "method": "temporal",
    "reasoning": "POST request received 87ms after click event"
  }
}
```

**Understanding Confidence:**
- **0.8-1.0 (High):** Event almost certainly triggered the API call
- **0.5-0.8 (Medium):** Probably related but less certain
- **0.0-0.5 (Low):** Weak correlation

---

## Step 4: Generate Tests with AI (2 minutes)

Now let's create Playwright tests from your recording.

### Generate Comprehensive Tests

```bash
tracetap-generate-tests recordings/first-test -o tests/generated.spec.ts
```

### Expected Output

```
📂 Loading session from recordings/first-test...
✅ Loaded 6 correlated events
   Correlation rate: 75.0%
   Average confidence: 82.5%

🤖 Initializing AI test generator...

✨ Generating comprehensive tests...
   Output format: typescript
   Confidence threshold: 0.5

✅ Tests generated successfully!
   Output file: tests/generated.spec.ts
   Lines: 127
   Size: 4234 bytes

💡 Next steps:
   1. Review the generated test: tests/generated.spec.ts
   2. Run tests: npx playwright test tests/generated.spec.ts
```

### View the Generated Code

```bash
cat tests/generated.spec.ts
```

**You'll see a complete Playwright test like this:**

```typescript
import { test, expect } from '@playwright/test';

test.describe('TodoMVC Application', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('https://todomvc.com/examples/vanilla-es6/');
  });

  test('user can add todos and filter by status', async ({ page }) => {
    // Add first todo
    await page.click('input.new-todo');
    await page.fill('input.new-todo', 'Buy groceries');
    await page.press('input.new-todo', 'Enter');

    // Verify todo was added
    const todoText = await page.textContent('.todo-list li:first-child');
    expect(todoText).toContain('Buy groceries');

    // Add second todo
    await page.fill('input.new-todo', 'Walk the dog');
    await page.press('input.new-todo', 'Enter');

    // Complete a todo
    await page.click('.todo-list li:first-child input[type="checkbox"]');

    // Filter to show only active items
    await page.click('text=Active');

    // Verify only one todo is visible
    const todos = await page.locator('.todo-list li').count();
    expect(todos).toBe(1);
  });

  test('verifies API contracts', async ({ page }) => {
    // Verify POST /api/todos creates todo with correct schema
    const createResponse = await page.waitForResponse(
      response => response.url().includes('/api/todos') &&
                   response.request().method() === 'POST'
    );

    expect(createResponse.status()).toBe(201);
    const body = await createResponse.json();
    expect(body).toHaveProperty('id');
    expect(body).toHaveProperty('title');
    expect(body).toHaveProperty('completed');
  });
});
```

**What the generated tests include:**

✅ **UI Actions** - All the clicks, fills, and navigation from your recording
✅ **Network Assertions** - Verifies API responses match expected schemas
✅ **Element Selectors** - Automatically detected from the recording
✅ **Comments** - Explains what each section does
✅ **Multiple Test Cases** - Different scenarios extracted from your session

---

## Step 5: Run Your Generated Tests (3 minutes)

Now let's execute the tests with Playwright.

### Install Playwright Test Runner (One-time Setup)

```bash
npm init playwright@latest
```

This creates a `playwright.config.ts` file. You can accept the defaults by pressing Enter.

### Run Your Tests

```bash
npx playwright test tests/generated.spec.ts
```

### Expected Output

```
Running 2 tests using 1 worker

  ✓ tests/generated.spec.ts:6:1 › user can add todos and filter by status (2.1s)
  ✓ tests/generated.spec.ts:30:1 › verifies API contracts (1.8s)

  2 passed (3.9s)
```

### View Test Report with UI

For a visual view of your tests running:

```bash
npx playwright test tests/generated.spec.ts --ui
```

This opens an interactive window where you can:
- Watch tests play back step-by-step
- See which selectors matched which elements
- Debug failed assertions
- Re-run individual tests

### Run Tests in Debug Mode

```bash
npx playwright test tests/generated.spec.ts --debug
```

This pauses before each action, letting you see exactly what's happening.

---

## Understanding the Complete Workflow

Now that you've completed the full cycle, let's understand what happened behind the scenes.

### Phase 1: Recording

**What TraceTap captures:**
1. **UI Events** - Every click, keystroke, navigation
2. **Network Traffic** - All HTTP/HTTPS API calls
3. **Timestamps** - With millisecond precision

**Files created:**
- `trace.zip` - Playwright's internal trace format (can replay with `playwright show-trace`)
- `traffic.json` - mitmproxy's raw network capture
- `events.json` - Parsed UI events in JSON format

### Phase 2: Correlation

**What correlation does:**
- Matches UI events to network calls by timestamp
- Calculates confidence scores
- Groups related events together

**Key metrics:**
- **Correlation Rate** - What percentage of UI events triggered API calls?
- **Average Confidence** - How certain are the correlations?
- **Time Delta** - How many milliseconds between UI action and network call?

**Example correlation:**
```
User clicks button (timestamp: 1000ms)
    ↓
POST request fires (timestamp: 1050ms)
    ↓
Difference: 50ms → "Highly likely related" → Confidence: 0.95
```

### Phase 3: Test Generation

**What the AI does:**
1. Reads all correlated events from your session
2. Analyzes UI patterns (clicks, form fills, navigation)
3. Extracts network request/response patterns
4. Generates Playwright test code with assertions

**Quality factors:**
- **High confidence correlations** → Strict assertions (`toBe()`, exact values)
- **Medium confidence** → Flexible assertions (`toContain()`, patterns)
- **Low confidence** → Skipped or soft assertions (won't fail test)

---

## Troubleshooting

### Browser Doesn't Open

**Problem:** No browser window appears when running `tracetap record`

**Solution:**
```bash
# Reinstall Playwright
rm -rf ~/.cache/ms-playwright
playwright install chromium
```

### API Key Not Found

**Problem:** Error: "Anthropic API key required"

**Solution:**
```bash
# Check if API key is set
echo $ANTHROPIC_API_KEY

# If empty, set it again
export ANTHROPIC_API_KEY=sk-ant-...

# Verify it's set
echo $ANTHROPIC_API_KEY  # Should show your key
```

### Low Correlation Rate

**Problem:** Only 20-30% of events are correlated

**Possible causes:**
- Recording a client-side-only app (no API calls)
- Long delays between UI action and API call
- mitmproxy not capturing traffic properly

**Solutions:**
1. **Use an app with API calls** - TodoMVC is a good demo
2. **Wait between actions** - Let network requests complete
3. **Check the traffic file** - `cat recordings/<session>/traffic.json | jq`
4. **Increase correlation window:**
   ```bash
   tracetap record <url> --window-ms 1000
   ```

### Generated Tests Have Syntax Errors

**Problem:** Generated `.spec.ts` file won't run

**Solution:**
1. Check Claude AI status - ensure `ANTHROPIC_API_KEY` is valid
2. Try again - sometimes AI generation is flaky
3. Check the error - `npx playwright test` shows the specific line
4. Report the issue with your session data

### Port 8888 Already in Use

**Problem:** Error: "Port 8888 already in use"

**Solution:**
```bash
# Use a different port
tracetap record <url> --proxy-port 8889

# Or kill the process using port 8888
lsof -i :8888  # Find process
kill -9 <PID>  # Kill it
```

### Playwright Tests Won't Run

**Problem:** `npx playwright test` fails with module errors

**Solution:**
```bash
# Ensure Node.js is installed
node --version  # Should be 16+

# Install dependencies in project
npm install -D @playwright/test

# Try again
npx playwright test tests/generated.spec.ts
```

---

## Advanced Usage

### Generate Different Templates

TraceTap offers three templates for different needs:

**Basic (Smoke Tests)**
```bash
tracetap-generate-tests recordings/first-test \
  -o tests/basic.spec.ts \
  --template basic
```
Generates ~30 lines of simple checks. Good for quick validation.

**Comprehensive (Recommended)**
```bash
tracetap-generate-tests recordings/first-test \
  -o tests/full.spec.ts \
  --template comprehensive
```
Generates ~120 lines with full assertions. Best for production use.

**Regression (API Testing)**
```bash
tracetap-generate-tests recordings/first-test \
  -o tests/regression.spec.ts \
  --template regression
```
Generates ~150 lines focused on API contracts. Best for preventing breaking changes.

### Filter by Confidence

Only generate from high-quality correlations:

```bash
tracetap-generate-tests recordings/first-test \
  -o tests/strict.spec.ts \
  --min-confidence 0.8
```

This skips low-confidence correlations, resulting in fewer but higher-quality tests.

### Generate Python Tests

```bash
tracetap-generate-tests recordings/first-test \
  -o tests/test_flow.py \
  --format python
```

Generates pytest-compatible Python tests instead of TypeScript.

### Custom Base URL

Test against a different environment:

```bash
tracetap-generate-tests recordings/first-test \
  -o tests/prod.spec.ts \
  --base-url https://production.example.com
```

The tests will run against your production URL instead of the original recorded URL.

---

## Best Practices

### Recording

1. **Plan before recording** - Know what you'll test
2. **Use realistic scenarios** - Mimic actual user workflows
3. **Go slow** - Wait 1-2 seconds between actions
4. **Test complete flows** - Not just single actions
5. **Name sessions clearly** - Use descriptive names like "checkout-flow" not "test123"
6. **Keep it focused** - Record 1 scenario per session
7. **Avoid timeouts** - Keep recording under 10 minutes

**Bad recording:** Rapid clicking, lots of waiting, 20+ unrelated actions
**Good recording:** Deliberate clicks, focused workflow, 5-10 related actions

### Test Generation

1. **Start with comprehensive template** - Best balance
2. **Review before using** - AI-generated code needs review
3. **Understand assertions** - Know what each test checks
4. **Use version control** - Commit both recordings and tests
5. **Iterate** - Re-record and regenerate as your app changes

### Test Maintenance

1. **Keep recordings** - They're your source of truth
2. **Version control everything** - Recordings, tests, config
3. **Re-generate when app changes** - Don't manually edit
4. **Add to CI/CD** - Automate test runs
5. **Monitor failures** - Failed tests mean something changed

---

## Next Steps

### Learn More

- **[Advanced Recording Techniques](../guides/advanced-recording.md)** - Complex workflows
- **[Template Customization](../advanced/custom-templates.md)** - Customize test generation
- **[CI/CD Integration](../guides/ci-cd-integration.md)** - Automate in pipelines
- **[Best Practices](../guides/best-practices.md)** - Expert tips

### Explore Examples

- **[E-commerce Checkout](../../examples/ecommerce-api/)** - Full workflow example
- **[Form Submission](../../examples/forms/)** - Multi-step form testing
- **[Authentication](../../examples/auth/)** - Login flow testing

### Get Help

- **[Full Documentation](../README.md)** - Complete reference
- **[Troubleshooting Guide](../troubleshooting.md)** - Common issues
- **[CLI Reference](../api/cli-reference.md)** - All commands
- **[GitHub Issues](https://github.com/anthropics/tracetap/issues)** - Report bugs

---

## What's Possible Now

You've mastered the basics. Here's what you can do:

**Simple scenarios:** 5-minute recording → 10 tests in 30 seconds
**Complex workflows:** 20-minute recording → 50 tests with multiple scenarios
**API-heavy apps:** 10-minute session → Full contract testing suite
**Regression testing:** Monthly re-recordings → Catch breaking changes instantly

---

## Key Concepts Reference

| Concept | Meaning |
|---------|---------|
| **Session** | One recording of user interactions (start → stop) |
| **Session ID** | Unique identifier for a recording (e.g., `20260202_143022_abc123`) |
| **UI Event** | A user action (click, type, navigate, etc.) |
| **Network Call** | An API request/response |
| **Correlation** | Linking UI events to network calls by timestamp |
| **Confidence** | Probability the correlation is correct (0.0 to 1.0) |
| **Trace** | Playwright's recording of DOM changes and interactions |
| **Traffic** | mitmproxy's capture of HTTP/HTTPS traffic |

---

## Summary

You've now:
1. ✅ Installed TraceTap and dependencies
2. ✅ Recorded a real user interaction
3. ✅ Examined captured events and correlations
4. ✅ Generated Playwright tests with AI
5. ✅ Run and verified your tests

**Total time: ~15 minutes**
**Tests generated: 2-5 comprehensive test cases**
**Time saved vs manual writing: 3-4 hours**

---

<div align="center">

**Congratulations! You've successfully mastered TraceTap UI Recording.**

The next time you need to create tests, you'll know exactly what to do:

1. `tracetap record <url>` - Record
2. `tracetap-generate-tests <session> -o tests/generated.spec.ts` - Generate
3. `npx playwright test tests/generated.spec.ts` - Run

**Happy testing! 🎉**

[Back to Documentation](../README.md)

</div>
