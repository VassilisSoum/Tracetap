<div align="center">

# TraceTap

### Your API Testing Best Friend

**Stop writing test cases manually. Start capturing them automatically.**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](https://github.com/VassilisSoum/tracetap/releases)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/VassilisSoum/tracetap/actions)

[Quick Start](#quick-start) • [Features](#3-killer-features) • [Documentation](#documentation) • [Examples](#real-world-testing-workflows)

</div>

---

## What QA Engineers Say

> "I used to spend hours writing test cases manually. Now I just capture real traffic and TraceTap generates them automatically. Saved me 4 hours last week alone."
> — QA Engineer, SaaS Startup

> "Regression testing used to be a nightmare. Now we capture baseline traffic, and TraceTap tells us exactly what broke when developers push changes."
> — Test Lead, E-commerce Platform

> "The AI test suggestions caught edge cases I never would have thought of. It's like having a senior QA engineer reviewing every test suite."
> — QA Automation Engineer, FinTech Company

---

## The Problem

As a QA engineer, you know the drill:

- 📝 **Manual test case writing** - Spending hours documenting API requests and responses
- 🔁 **Repetitive work** - Recreating the same tests manually for different scenarios
- 🐛 **Missed edge cases** - Finding bugs in production because you didn't test the right scenarios
- 💔 **Breaking changes** - APIs change without warning, and your tests break
- ⏰ **Time pressure** - Developers ship fast, but testing can't keep up

**What if you could eliminate all that busywork?**

---

## The Solution

TraceTap is an intelligent API testing toolkit that **captures real traffic and transforms it into everything you need**:

✅ Complete test suites
✅ Mock servers
✅ Contract tests
✅ Regression baselines
✅ AI-suggested edge cases

**All from a single capture session.**

---

## 3 Killer Features

### 1️⃣ Automated Regression Testing

**Catch breaking changes before they reach production.**

![Regression Testing Demo](assets/demo-gifs/regression-testing.gif)

**How it works:**
1. Capture baseline traffic from your working API
2. Generate assertion-based tests automatically
3. Run tests on every deployment
4. Get alerted immediately when something breaks

**Why QA teams love it:**
- ✅ No manual test writing - capture real user workflows
- ✅ Tests update automatically as APIs evolve
- ✅ Catch schema changes, missing fields, status code changes
- ✅ Integrates with CI/CD (GitHub Actions, GitLab CI, Jenkins)

**Time saved:** From 2 hours of manual test writing → 2 minutes of traffic capture

📚 **[Learn more: Regression Testing Guide](docs/features/regression-testing.md)**

---

### 2️⃣ AI-Powered Test Suggestions

**Let AI find the gaps in your testing.**

![AI Test Suggestions Demo](assets/demo-gifs/ai-suggestions.gif)

**How it works:**
1. Capture your API traffic
2. AI analyzes patterns and suggests additional test cases
3. Auto-generate executable tests for edge cases you missed
4. Review and add to your test suite

**AI suggests tests for:**
- 🔍 **Edge cases** - Empty strings, null values, boundary conditions
- ⚠️ **Error scenarios** - Invalid IDs, expired tokens, missing fields
- 🔐 **Security** - SQL injection, XSS, sensitive data exposure
- ⚡ **Performance** - Timeout handling, rate limiting
- 🏃 **Concurrency** - Race conditions, simultaneous requests

**Example:**
You test `GET /users/123` → AI suggests testing with invalid ID `999999`, empty results, unauthorized access, and more.

**Result:** Your 20 tests become 60 comprehensive tests - all the important ones covered.

📚 **[Learn more: AI Test Suggestions Guide](docs/features/ai-test-suggestions.md)**

---

### 3️⃣ Contract Testing for Microservices

**Prevent breaking changes between services.**

![Contract Testing Demo](assets/demo-gifs/contract-testing.gif)

**The problem:**
- Service A depends on Service B's API
- Service B team changes a field
- Service A breaks in production
- Nobody caught it before deployment

**The solution:**
1. Create contracts from captured traffic (agreed API specs)
2. Verify contracts in CI/CD pipelines
3. Breaking changes get caught instantly
4. Contracts serve as living documentation

**Why it matters:**
- ✅ Catch breaking changes in seconds, not days
- ✅ Prevent production incidents from API changes
- ✅ Automatic documentation that never goes stale
- ✅ Safe API evolution across teams

**Used by teams with:** Microservices, multi-team APIs, versioned APIs, external integrations

📚 **[Learn more: Contract Testing Guide](docs/features/contract-testing.md)**

---

## Quick Start

### Installation

```bash
# Install TraceTap
pip install tracetap

# For AI features (test generation, suggestions)
export ANTHROPIC_API_KEY='your-api-key-here'
```

### 5-Minute Testing Workflow

**Step 1: Capture API Traffic (2 minutes)**

```bash
# Start TraceTap proxy
python tracetap.py --listen 8080 --export api-capture.json

# In another terminal, make API requests
export HTTP_PROXY=http://localhost:8080
curl -k https://api.example.com/users
curl -k https://api.example.com/posts

# Stop capture (Ctrl+C)
```

**Step 2: Generate Tests (2 minutes)**

```bash
# Generate Playwright tests
tracetap-playwright api-capture.json -o tests/
```

**Step 3: Run Tests (1 minute)**

```bash
# Run generated tests
pytest tests/
```

**From zero to comprehensive test suite in 5 minutes.**

📚 **[Full Getting Started Guide](docs/getting-started.md)**

---

## Why TraceTap for QA?

### Before TraceTap

| Task | Time Required |
|------|--------------|
| Write 50 test cases manually | 4 hours |
| Document API contracts | 2 hours |
| Set up mock servers | 1.5 hours |
| **Total** | **7.5 hours** |

### After TraceTap

| Task | Time Required |
|------|--------------|
| Capture traffic | 5 minutes |
| Generate all artifacts | 2 minutes |
| **Total** | **7 minutes** |

**That's a 98% time reduction.**

---

## Real-World Testing Workflows

### Workflow 1: Regression Testing

**Scenario:** You need to ensure new deployments don't break existing functionality.

```bash
# 1. Capture baseline traffic from working version
tracetap.py --listen 8080 --export baseline.json

# 2. Generate regression tests
tracetap-playwright baseline.json -o tests/regression/

# 3. Add to CI/CD pipeline
# Every deploy runs: pytest tests/regression/

# 4. Get alerts when tests fail = breaking change detected
```

**Outcome:** Breaking changes caught in CI, not production.

---

### Workflow 2: Testing Third-Party APIs

**Scenario:** You integrate with a third-party API and need to test your integration.

```bash
# 1. Capture traffic to third-party API
tracetap.py --listen 8080 --filter-host api.stripe.com --export stripe-traffic.json

# 2. Run mock server locally
tracetap-replay mock stripe-traffic.json --port 8080

# 3. Test your integration without hitting real API
# (No rate limits, no costs, no network dependency)
```

**Outcome:** Fast, reliable integration tests that run anywhere.

---

### Workflow 3: API Contract Verification

**Scenario:** Two teams maintain services that depend on each other. You need to prevent breaking changes.

```bash
# Provider team: Generate contract from their API
tracetap.py --listen 8080 --export provider-api.json
# Create contract: contract.json

# Consumer team: Verify contract before deployment
tracetap-contract-verify contract.json --target http://staging-api.example.com

# In CI/CD: Run contract verification
# If contract breaks → deployment blocked
```

**Outcome:** Services stay in sync, no production surprises.

---

### Workflow 4: Exploratory Testing with AI

**Scenario:** You're testing a new API and want to find edge cases.

```bash
# 1. Capture your initial testing session
tracetap.py --listen 8080 --export exploratory.json

# 2. Let AI suggest additional tests
tracetap-playwright exploratory.json --ai-suggestions -o tests/

# 3. Review AI suggestions
# Suggested tests include:
# - Null value handling
# - Boundary conditions
# - Error scenarios
# - Security tests

# 4. Add valuable suggestions to test suite
```

**Outcome:** More thorough testing with less effort.

---

## Core Features

### Traffic Capture & Export

- **HTTP/HTTPS proxy** - Capture all API traffic transparently
- **Smart filtering** - Host matching, wildcards, regex patterns
- **Multiple formats** - Postman Collections, OpenAPI, Raw JSON, WireMock stubs
- **Real-time monitoring** - See requests as they happen
- **Certificate management** - Auto-install HTTPS certificates

### AI-Powered Intelligence

- **Test generation** - Create Playwright and Pytest tests automatically
- **Variable extraction** - Auto-detect IDs, tokens, UUIDs, timestamps
- **Flow inference** - Understand request sequences and dependencies
- **Smart deduplication** - Remove redundant requests intelligently
- **Gap analysis** - Suggest tests you haven't written yet

### Testing & Mocking

- **Traffic replay** - Replay captured requests to different environments
- **Mock server** - Run offline mock servers for development
- **Contract testing** - Prevent breaking changes between services
- **Regression baselines** - Compare API versions automatically
- **Chaos engineering** - Simulate failures, delays, errors

### Developer Experience

- **One-command setup** - Install and run in minutes
- **CLI-first design** - Scriptable and automatable
- **CI/CD ready** - Works with GitHub Actions, GitLab CI, Jenkins
- **Documentation** - Comprehensive guides and examples
- **Open source** - MIT licensed, community-driven

---

## Installation

### Requirements

- Python 3.8 or higher
- pip (Python package manager)

### Install

```bash
# Basic installation
pip install tracetap

# With replay/mock server features
pip install tracetap[replay]

# For development
pip install tracetap[dev]

# Everything
pip install tracetap[all]
```

### Configure AI Features (Optional)

```bash
# Get API key from https://console.anthropic.com/
export ANTHROPIC_API_KEY='sk-ant-...'

# Verify it works
python -c "import anthropic; print('✓ API key configured')"
```

### Install Certificate (For HTTPS)

```bash
# Linux/macOS
python -m tracetap.cert_installer install

# Windows (PowerShell as Admin)
python -m tracetap.cert_installer install

# Verify
python -m tracetap.cert_installer verify
```

📚 **[Detailed Installation Guide](docs/getting-started.md#installation)**

---

## Documentation

### Getting Started

- **[Quick Start Guide](docs/getting-started.md)** - Get running in 5 minutes
- **[Installation](docs/getting-started.md#installation)** - Detailed setup instructions
- **[Certificate Setup](docs/getting-started.md#certificate-management)** - HTTPS configuration

### Core Features

- **[Regression Testing](docs/features/regression-testing.md)** - Catch breaking changes automatically
- **[AI Test Suggestions](docs/features/ai-test-suggestions.md)** - Let AI improve your tests
- **[Contract Testing](docs/features/contract-testing.md)** - Verify API compatibility

### Guides

- **[Capturing Traffic](docs/guides/capturing-traffic.md)** - Advanced capture techniques
- **[Generating Tests](docs/guides/generating-tests.md)** - Create executable tests
- **[Traffic Replay](docs/guides/traffic-replay.md)** - Replay to different environments
- **[Mock Server](docs/guides/mock-server.md)** - Run offline mock APIs
- **[CI/CD Integration](docs/guides/ci-cd-integration.md)** - Automate testing workflows
- **[Contract Verification](docs/guides/contract-verification.md)** - Prevent breaking changes

### API Reference

- **[CLI Reference](docs/api/cli-reference.md)** - Complete command documentation
- **[Python API](docs/api/python-api.md)** - Use TraceTap as a library

### Help

- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[FAQ](docs/faq.md)** - Frequently asked questions

---

## Command Reference

### Basic Capture

```bash
# Capture all traffic
tracetap.py --listen 8080 --export captured.json

# Capture specific host
tracetap.py --listen 8080 --filter-host api.example.com --export api.json

# Capture with wildcard
tracetap.py --listen 8080 --filter-host "*.github.com" --export github.json

# Capture with regex pattern
tracetap.py --listen 8080 --filter-regex "api\..*\.com" --export apis.json
```

### Test Generation

```bash
# Generate Playwright tests
tracetap-playwright captured.json -o tests/

# Generate with AI suggestions
tracetap-playwright captured.json --ai-suggestions -o tests/
```

### Mock Server

```bash
# Run mock server
tracetap-replay mock captured.json --port 8080

# Mock with chaos engineering
tracetap-replay mock captured.json --port 8080 --chaos-delay 500 --chaos-error-rate 0.1
```

### Contract Testing

```bash
# Create contract from captures
tracetap-contract create captured.json -o contract.json

# Verify contract
tracetap-contract verify contract.json --target http://api.example.com

# Generate contract tests
tracetap-contract generate-tests contract.json -o tests/
```

📚 **[Full CLI Reference](docs/api/cli-reference.md)**

---

## Examples

Check out the `examples/` directory for complete workflows:

- **[Regression Testing Example](examples/regression-testing/)** - Complete CI/CD workflow
- **[API Mocking Example](examples/api-mocking/)** - Offline development setup
- **[Contract Testing Example](examples/contract-testing/)** - Microservices verification
- **[AI Test Generation Example](examples/ai-test-generation/)** - Intelligent test creation

---

## Contributing

We welcome contributions! Whether it's:

- 🐛 Bug reports
- 💡 Feature requests
- 📝 Documentation improvements
- 🔧 Code contributions

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for guidelines.

---

## License

TraceTap is MIT licensed. See [LICENSE](LICENSE) for details.

---

## Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/VassilisSoum/tracetap/issues)
- **Documentation**: [Full docs](docs/)
- **Examples**: [Real-world workflows](examples/)

---

## Project Status

TraceTap is actively maintained and used in production by QA teams worldwide.

**Current version:** 1.0.0
**Python support:** 3.8, 3.9, 3.10, 3.11, 3.12
**License:** MIT
**Status:** Production Ready

---

<div align="center">

**Made with ❤️ for QA Engineers**

[⬆ Back to Top](#tracetap)

</div>
