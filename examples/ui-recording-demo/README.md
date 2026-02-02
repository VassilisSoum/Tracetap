# UI Recording Examples

Complete examples demonstrating TraceTap's UI recording and test generation workflow.

## Available Examples

### 1. [TodoMVC Demo](todomvc/) - Best for Learning
**Difficulty:** Beginner
**Time:** 10 minutes
**What it demonstrates:**
- Basic UI interactions (add, complete, filter)
- Simple API calls
- All three generation templates
- Complete workflow from record to test

**Start here if you're new to TraceTap.**

### 2. [E-commerce Checkout](ecommerce/) - Real-World Application
**Difficulty:** Intermediate
**Time:** 20 minutes
**What it demonstrates:**
- Multi-page workflow
- Form validation
- Cart management
- Payment processing simulation

### 3. [Authentication Flow](auth/) - Common Pattern
**Difficulty:** Intermediate
**Time:** 15 minutes
**What it demonstrates:**
- Login/logout workflow
- Session management
- Protected routes
- Token-based auth

## Quick Start

Each example includes:
- 📁 **Pre-recorded session** - Skip recording, jump to generation
- 🧪 **Generated tests** - See what TraceTap produces
- 📖 **Step-by-step guide** - Follow along and learn

### Run an Example

```bash
# 1. Navigate to an example
cd examples/ui-recording-demo/todomvc

# 2. Install dependencies
npm install

# 3. Run the pre-generated tests
npx playwright test

# 4. Generate your own tests
tracetap-generate-tests session-example -o generated-tests/my-test.spec.ts
```

## What to Expect

### Session Files

Each example includes a pre-recorded session:
- `metadata.json` - Session info (URL, timestamp, duration)
- `correlation.json` - UI events linked to API calls
- ⚠️ `trace.zip` NOT included (too large for git)

**Note:** trace.zip files are omitted from git due to size (10-50MB). The correlation.json contains all data needed for test generation.

### Generated Tests

Each example shows tests generated from all three templates:

1. **basic.spec.ts** (~30 lines)
   - Essential assertions only
   - Quick smoke tests
   - Good for CI pipelines

2. **comprehensive.spec.ts** (~120 lines)
   - Full schema validation
   - Edge case handling
   - Production-ready

3. **regression.spec.ts** (~150 lines)
   - API contract testing
   - Breaking change detection
   - Version tracking

## Learning Path

**New to TraceTap?**
1. Start with [TodoMVC](todomvc/) - Learn the basics
2. Try [E-commerce](ecommerce/) - See real-world complexity
3. Study [Auth](auth/) - Understand session management

**Want to record your own?**
1. Review the pre-recorded sessions
2. Follow the "Record Your Own" sections
3. Compare your results with the examples

## CI/CD Integration

See how to integrate TraceTap in your pipeline:

```yaml
# .github/workflows/tracetap-tests.yml
name: TraceTap Generated Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: |
          pip install tracetap
          npm install

      - name: Run generated tests
        run: npx playwright test
        env:
          CI: true
```

## Contributing

Have an interesting use case? Contribute an example:

1. Create a new directory under `examples/ui-recording-demo/`
2. Include session data and generated tests
3. Write a comprehensive README
4. Submit a PR

## Support

- [Getting Started Guide](../../docs/getting-started/UI_RECORDING.md)
- [Troubleshooting](../../docs/troubleshooting.md)
- [GitHub Issues](https://github.com/anthropics/tracetap/issues)
