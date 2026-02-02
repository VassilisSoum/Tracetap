# Quick Start - UI Recording Examples

Get started with TraceTap UI recording in 5 minutes.

## Choose Your Path

### Path 1: Learn the Basics (10 minutes)

**Best for:** First-time users, understanding core concepts

```bash
# 1. Navigate to TodoMVC example
cd examples/ui-recording-demo/todomvc

# 2. Install dependencies
npm install

# 3. Run pre-generated tests
npm test

# 4. Review test output
# Check playwright-report/index.html for results
```

**What you'll see:**
- TodoMVC app interactions
- Test results and screenshots
- Three different test templates

**Next:** Read `todomvc/README.md` for detailed explanations

---

### Path 2: See Real-World Testing (20 minutes)

**Best for:** Developers building e-commerce apps

```bash
# 1. Explore E-commerce example
cd examples/ui-recording-demo/ecommerce

# 2. Review the recorded session
cat session-example/metadata.json
cat session-example/correlation.json

# 3. Understand the correlation analysis
# See how clicks map to API calls with confidence scores

# 4. Generate your own tests
tracetap-generate-tests session-example \
  -o generated-tests/my-checkout.spec.ts \
  --template comprehensive
```

**What you'll learn:**
- Multi-step workflow recording
- Form validation patterns
- Cart state management
- Payment processing flows

**Next:** Read `ecommerce/README.md` for advanced patterns

---

### Path 3: Master Authentication (15 minutes)

**Best for:** Building secure applications with login flows

```bash
# 1. Study the auth example
cd examples/ui-recording-demo/auth

# 2. Review session data
cat session-example/correlation.json | jq '.events[4]'
# See POST /api/auth/login event

# 3. Understand token handling
# Review README.md "Authentication Testing Patterns" section

# 4. Check security patterns
# See "Security Testing" section for JWT validation
```

**What you'll learn:**
- Session persistence testing
- Protected route handling
- Token validation patterns
- CSRF and OAuth flows

**Next:** Read `auth/README.md` for security deep-dive

---

## Record Your Own Session

### Basic Recording (3 minutes)

```bash
# 1. Record a session
tracetap record https://demo.playwright.dev/todomvc/ \
  -n my-first-session

# 2. Interact with the app
# Add 2-3 todos, toggle completion, view different filters

# 3. Stop recording (press Enter)

# 4. See what was captured
tracetap list recordings
```

### Generate Tests from Your Session

```bash
# 1. Generate basic tests
tracetap-generate-tests recordings/<session-id> \
  -o my-basic-test.spec.ts \
  --template basic

# 2. Generate comprehensive tests
tracetap-generate-tests recordings/<session-id> \
  -o my-comprehensive-test.spec.ts \
  --template comprehensive

# 3. Run your tests
npx playwright test my-*-test.spec.ts
```

---

## Understanding the Examples

### File Structure

Each example includes:

```
example-name/
├── README.md                    # Detailed guide
├── session-example/
│   ├── metadata.json           # Session info
│   └── correlation.json        # UI → API mapping
├── generated-tests/
│   ├── basic.spec.ts           # Smoke tests
│   ├── comprehensive.spec.ts   # Full validation
│   └── regression.spec.ts      # Contract testing
└── package.json                # Dependencies
```

### Session Data Explained

#### metadata.json
```json
{
  "session_id": "...",           // Unique session ID
  "url": "...",                  // Application URL
  "duration": 45.3,              // Session length in seconds
  "events_count": 5              // Number of UI interactions
}
```

#### correlation.json
```json
{
  "events": [
    {
      "sequence": 1,
      "uiEvent": { ... },        // User action (click, fill, etc)
      "networkCalls": [ ... ],   // API calls triggered
      "correlation": {
        "confidence": 0.92,      // How sure (0-1)
        "timeDelta": 87          // Response time in ms
      }
    }
  ]
}
```

### Test Templates

| Template | Size | Use Case | Execution Time |
|----------|------|----------|-----------------|
| **Basic** | ~30 lines | Smoke tests, CI fast-path | 2-3 min |
| **Comprehensive** | ~120 lines | Production suite | 8-10 min |
| **Regression** | ~150 lines | Breaking change detection | 10-15 min |

---

## Common Commands

### Run Tests

```bash
# Run all tests
npm test

# Run specific template
npm run test:comprehensive

# Run with UI (watch test execute)
npm run test:ui

# Debug mode (step through)
npm run test:debug
```

### Record Sessions

```bash
# Record with defaults
tracetap record https://example.com

# Record with custom name
tracetap record https://example.com -n my-flow

# Record with proxy (for HTTPS)
tracetap record https://example.com --proxy localhost:8080

# List recorded sessions
tracetap list recordings
```

### Generate Tests

```bash
# Generate basic tests
tracetap-generate-tests <session> -o test.spec.ts --template basic

# Generate comprehensive tests
tracetap-generate-tests <session> -o test.spec.ts --template comprehensive

# Generate Python tests (pytest)
tracetap-generate-tests <session> -o test_flow.py --format python
```

---

## Troubleshooting

### "Tests fail with timeout error"
```bash
# Increase timeout in playwright.config.ts
# Or wait for element explicitly in test
await page.waitForLoadState('networkidle');
```

### "API calls show 404"
```bash
# The example endpoints are mock/demo only
# Either:
# 1. Update baseURL in playwright.config.ts to your app
# 2. Record your own session with your API
# 3. Mock API responses for testing
```

### "Cannot find tracetap command"
```bash
# Install tracetap package
pip install tracetap

# Or install from source (if in development)
cd /path/to/tracetap/repo
pip install -e .
```

### "Playwright not installed"
```bash
# Install Playwright browsers
playwright install chromium

# Or let it auto-install
pip install --upgrade tracetap
```

---

## Next Steps

### Learn More
1. **Read the main guide:** `examples/ui-recording-demo/README.md`
2. **Pick your example:** TodoMVC → E-commerce → Auth
3. **Read the example guide:** `examples/ui-recording-demo/{example}/README.md`
4. **Run the tests:** `npm install && npm test`
5. **Record your own:** Follow "Record Your Own Session" above

### Integrate with CI/CD
```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm install
      - run: npx playwright test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: playwright-report/
```

### Get Help
- **Docs:** `/docs/getting-started/UI_RECORDING.md`
- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions

---

## Example Quick Links

- **TodoMVC (Beginner):** `todomvc/README.md` - Learn basics in 10 minutes
- **E-commerce (Intermediate):** `ecommerce/README.md` - Real-world checkout flow
- **Auth (Intermediate):** `auth/README.md` - Login/logout and security

---

**Ready to start?** Pick a path above and run the commands!
