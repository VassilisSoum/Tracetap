# TraceTap Documentation

Complete guide to using TraceTap for API traffic capture, test generation, and verification.

## Quick Navigation

### New to TraceTap?

Start here: **[Getting Started](getting-started.md)** (5-minute tutorial)

### What Can You Do?

**Core Features:**
- 📡 [Capture HTTP/HTTPS Traffic](guides/capturing-traffic.md) - Record API interactions with your proxy
- 🧪 [Generate Tests](guides/generating-tests.md) - Create executable tests from traffic
- 🔄 [Regression Testing](features/regression-testing.md) - Catch breaking changes early
- 🎯 [Contract Testing](features/contract-testing.md) - Ensure API compatibility
- 🤖 [AI Test Suggestions](features/ai-test-suggestions.md) - Let Claude suggest tests
- 🔁 [Replay Traffic](REPLAY.md) - Replay captures to different servers
- 🎭 [Mock Servers](REPLAY.md) - Run mock HTTP server for isolated testing

### By Use Case

| Use Case | Guide |
|----------|-------|
| **"I want to test my API"** | [Generating Tests](guides/generating-tests.md) |
| **"I need regression tests"** | [Regression Testing](features/regression-testing.md) |
| **"We use Postman"** | [Generating Tests → Postman Collections](guides/generating-tests.md#postman-collections) |
| **"Testing without real API"** | [Mock Server](REPLAY.md#mock-http-server) |
| **"Verify API contracts"** | [Contract Testing](features/contract-testing.md) |
| **"Automate in CI/CD"** | [CI/CD Integration](guides/ci-cd-integration.md) |
| **"Something is wrong"** | [Troubleshooting](troubleshooting.md) |

---

## Documentation Structure

```
docs/
├── README.md (you are here)
├── getting-started.md              ← Start here!
├── troubleshooting.md              ← Problems?
│
├── features/
│   ├── regression-testing.md        (Killer Feature #1)
│   ├── ai-test-suggestions.md       (Killer Feature #2)
│   └── contract-testing.md          (Killer Feature #3)
│
├── guides/
│   ├── capturing-traffic.md         (Complete capture guide)
│   ├── generating-tests.md          (All test generation options)
│   ├── contract-verification.md     (Practical examples)
│   └── ci-cd-integration.md         (Automate everything)
│
├── api/
│   ├── cli-reference.md             (All commands)
│   └── python-api.md                (Library usage)
│
└── REPLAY.md                        (Traffic replay & mock servers)
```

---

## Complete Feature Guide

### 1. Capturing Traffic

Intercept and record all HTTP/HTTPS traffic from your application.

**Document:** [Capturing Traffic Guide](guides/capturing-traffic.md)

What you'll learn:
- ✅ Start a capture proxy
- ✅ Filter traffic by host or regex
- ✅ Install SSL certificates
- ✅ Export in multiple formats

**5-minute example:**
```bash
# Start capture
python tracetap.py --listen 8080 --export api.json

# Configure proxy in another terminal
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Make requests (your app traffic is captured)
curl -k https://api.example.com/users

# Stop with Ctrl+C
# Result: api.json contains captured traffic
```

---

### 2. Generating Tests

Convert captured traffic into executable tests.

**Document:** [Generating Tests Guide](guides/generating-tests.md)

#### Playwright Tests (Automated)
```bash
python tracetap-playwright.py api.json -o tests/
pytest tests/  # Run tests
```

---

### 3. Regression Testing

Automatically detect breaking changes in your API.

**Document:** [Regression Testing Feature](features/regression-testing.md)

Why it matters:
- Catch API regressions before they reach production
- Verify backwards compatibility
- Automate in CI/CD

**Workflow:**
```bash
# 1. Capture working API
python tracetap.py --listen 8080 --export baseline.json

# 2. Generate tests
python tracetap-playwright.py baseline.json -o tests/

# 3. Run tests on new versions
pytest tests/  # Pass = no breaking changes ✓
```

---

### 4. AI-Powered Test Suggestions

Let Claude AI analyze your traffic and suggest tests.

**Document:** [AI Test Suggestions Feature](features/ai-test-suggestions.md)

AI suggests tests for:
- Edge cases (empty results, null fields, max values)
- Error scenarios (invalid input, unauthorized, rate limits)
- Security issues (SQL injection, XSS, data exposure)
- Performance (timeouts, slow endpoints)

**Example:**
```bash
python tracetap-playwright.py api.json \
  --ai-suggestions \
  --focus-areas edge_cases security \
  -o tests/
```

---

### 5. Contract Testing

Ensure API providers and consumers stay in sync.

**Document:** [Contract Testing Feature](features/contract-testing.md)

Prevents:
- ❌ Provider breaks API without notifying consumers
- ❌ Consumer assumes fields exist when they don't
- ❌ Unexpected response format changes

**Example:**
```bash
# 1. Create contract
python -c "
from src.tracetap.contract import ContractCreator
import json

with open('api.json') as f:
    captures = json.load(f)

creator = ContractCreator(provider='my-api', consumer='my-app')
contract = creator.create_from_captures(captures['requests'])

with open('contract.json', 'w') as f:
    json.dump(contract, f, indent=2)
"

# 2. Verify contract in CI/CD
pytest tests/test_contract.py
```

---

### 6. Traffic Replay

Replay captured requests to different servers.

**Document:** [Replay & Mock Server](REPLAY.md)

Use cases:
- Test new API version with production traffic
- Load testing
- Debugging production issues
- Offline development with mock server

**Example:**
```bash
# Replay to staging
python tracetap-replay.py replay prod-api.json \
  --target https://staging-api.example.com

# Or start mock server
python tracetap-replay.py mock api.json --port 8080
```

---

### 7. CI/CD Integration

Automate everything in your pipeline.

**Document:** [CI/CD Integration Guide](guides/ci-cd-integration.md)

Includes ready-to-use workflows for:
- GitHub Actions
- GitLab CI
- Generic CI/CD

**Example (GitHub Actions):**
```yaml
name: Regression Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: pytest tests/
```

---

## Command Reference

### Main Tools

| Tool | Purpose | Command |
|------|---------|---------|
| **tracetap.py** | Capture traffic | `python tracetap.py --listen 8080 --export api.json` |
| **tracetap-playwright.py** | Generate pytest tests | `python tracetap-playwright.py api.json -o tests/` |
| **tracetap-replay.py** | Replay traffic / mock server | `python tracetap-replay.py replay api.json --target http://...` |

**Full reference:** [CLI Reference](api/cli-reference.md)

---

## Python Library

Use TraceTap programmatically:

```python
from src.tracetap.contract import ContractVerifier

# Verify contract
verifier = ContractVerifier(contract)
result = verifier.verify(base_url='http://localhost:3000')
```

**Full reference:** [Python API Reference](api/python-api.md)

---

## Common Workflows

### Workflow 1: Generate Tests from Real Traffic

Perfect for: **New API, no tests yet**

```bash
# 1. Capture traffic
python tracetap.py --listen 8080 --export api.json

# 2. Generate tests
python tracetap-playwright.py api.json -o tests/

# 3. Run tests
pytest tests/

# 4. Version control
git add tests/ api.json
git commit -m "Add API tests from capture"
```

---

### Workflow 2: Regression Testing

Perfect for: **Catch breaking changes**

```bash
# 1. Create baseline
python tracetap.py --listen 8080 --export baseline-v1.0.json

# 2. Generate tests (commit with baseline)
python tracetap-playwright.py baseline-v1.0.json -o tests/
git add baseline-v1.0.json tests/

# 3. Later: Run tests on new version
pytest tests/

# If new version breaks API:
# ❌ FAILED test_users - AssertionError: Missing 'email' field
```

---

### Workflow 3: Contract-Based Testing

Perfect for: **Microservices coordination**

```bash
# Service A (Consumer) and Service B (Provider) agree on contract

# 1. Provider captures API
python tracetap.py --listen 8080 --export api.json

# 2. Create contract
python -c "
from src.tracetap.contract import ContractCreator
creator = ContractCreator('service-b', 'service-a')
contract = creator.create_from_captures(json.load(open('api.json'))['requests'])
with open('contract.json', 'w') as f:
    json.dump(contract, f, indent=2)
"

# 3. Provider verifies contract
python tracetap-replay.py verify-contract contract.json --target http://localhost:3000

# 4. Consumer validates contract after provider deploys
# (In CI/CD - runs automated contract tests)
```

---

### Workflow 4: Test Without Real API

Perfect for: **Offline development, isolation**

```bash
# 1. Capture real API traffic
python tracetap.py --listen 8080 --export api.json

# 2. Start mock server
python tracetap-replay.py mock api.json --port 8080

# 3. Point your app to mock and develop
API_URL=http://localhost:8080 npm test
```

---

## Getting Help

### Problems?

→ **[Troubleshooting Guide](troubleshooting.md)**

Common issues covered:
- Installation errors
- No requests being captured
- SSL/HTTPS issues
- Test generation failures
- CI/CD failures
- Performance problems

### Want Examples?

→ **[Guides](guides/)** have step-by-step examples

### Need Command Details?

→ **[CLI Reference](api/cli-reference.md)** documents every option

### Using as Library?

→ **[Python API](api/python-api.md)** shows code examples

---

## What's Next?

**Just getting started?**
→ Read [Getting Started](getting-started.md) (5 minutes)

**Want to capture traffic?**
→ Read [Capturing Traffic](guides/capturing-traffic.md)

**Need tests?**
→ Read [Generating Tests](guides/generating-tests.md)

**Worried about breaking changes?**
→ Read [Regression Testing](features/regression-testing.md)

**Building microservices?**
→ Read [Contract Testing](features/contract-testing.md)

**Stuck?**
→ Read [Troubleshooting](troubleshooting.md)

---

## Document Index

### Getting Started
- [Getting Started Guide](getting-started.md) - 5-minute tutorial

### Core Features
- [Capturing Traffic](guides/capturing-traffic.md) - HTTP/HTTPS proxy
- [Generating Tests](guides/generating-tests.md) - Playwright and Postman tests
- [Regression Testing](features/regression-testing.md) - Breaking change detection
- [AI Test Suggestions](features/ai-test-suggestions.md) - Claude-powered test ideas
- [Contract Testing](features/contract-testing.md) - Provider/consumer contracts

### Advanced Topics
- [Traffic Replay & Mock Server](REPLAY.md) - Replay and offline testing
- [Contract Verification](guides/contract-verification.md) - Practical examples
- [CI/CD Integration](guides/ci-cd-integration.md) - GitHub Actions, GitLab CI, etc.

### Reference
- [CLI Reference](api/cli-reference.md) - All command-line tools
- [Python API](api/python-api.md) - Library usage

### Help
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

---

## Version

**TraceTap** v1.0.0

Last updated: February 2024

---

## Quick Links

- **Repository**: [GitHub](https://github.com/yourusername/tracetap)
- **Issues**: [Bug Reports & Features](https://github.com/yourusername/tracetap/issues)
- **Contributing**: See CONTRIBUTING.md
- **License**: See LICENSE file
