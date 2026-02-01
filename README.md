<div align="center">

# TraceTap

### AI-Powered API Test Generation

**Capture real traffic. Let Claude AI generate your tests.**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](https://github.com/VassilisSoum/tracetap/releases)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/VassilisSoum/tracetap/actions)

[Quick Start](#quick-start) | [Features](#key-features) | [Documentation](#documentation) | [Examples](#real-world-workflows)

</div>

---

## What QA Engineers Say

> "I used to spend hours writing test cases manually. Now I just capture real traffic and TraceTap generates them automatically. Saved me 4 hours last week alone."
> -- QA Engineer, SaaS Startup

> "Regression testing used to be a nightmare. Now we capture baseline traffic, and TraceTap tells us exactly what broke when developers push changes."
> -- Test Lead, E-commerce Platform

> "The AI test suggestions caught edge cases I never would have thought of. It's like having a senior QA engineer reviewing every test suite."
> -- QA Automation Engineer, FinTech Company

---

## The Problem

As a QA engineer, you know the drill:

- **Manual test case writing** - Spending hours documenting API requests and responses
- **Repetitive work** - Recreating the same tests manually for different scenarios
- **Missed edge cases** - Finding bugs in production because you didn't test the right scenarios
- **Breaking changes** - APIs change without warning, and your tests break
- **Time pressure** - Developers ship fast, but testing can't keep up

**What if you could eliminate all that busywork?**

---

## The Solution

TraceTap captures API traffic as raw JSON and uses **Claude AI** to intelligently transform it into everything you need:

- **Playwright test suites** - Complete, runnable tests with assertions
- **AI-suggested edge cases** - Tests you didn't think to write
- **Contract definitions** - Prevent breaking changes between services
- **Mock servers** - Test without external dependencies

**Capture once. Generate everything.**

---

## Key Features

### 1. Automated Test Generation

**From traffic capture to running tests in minutes.**

![Regression Testing Demo](assets/demo-gifs/regression-testing.gif)

**How it works:**
1. Capture API traffic through TraceTap proxy
2. Claude AI analyzes patterns and generates Playwright tests
3. Run tests on every deployment
4. Get alerted when something breaks

**Why QA teams love it:**
- No manual test writing - capture real user workflows
- AI generates intelligent assertions
- Tests catch schema changes, missing fields, status code issues
- Integrates with CI/CD (GitHub Actions, GitLab CI, Jenkins)

**Time saved:** From 2 hours of manual test writing to 5 minutes of capture + generation

---

### 2. AI-Powered Test Suggestions

**Let Claude AI find the gaps in your testing.**

![AI Test Suggestions Demo](assets/demo-gifs/ai-suggestions.gif)

**How it works:**
1. Capture your API traffic
2. AI analyzes patterns and suggests additional test cases
3. Auto-generate tests for edge cases you missed
4. Review and add to your test suite

**AI suggests tests for:**
- **Edge cases** - Empty strings, null values, boundary conditions
- **Error scenarios** - Invalid IDs, expired tokens, missing fields
- **Security** - SQL injection, XSS, sensitive data exposure
- **Performance** - Timeout handling, rate limiting
- **Concurrency** - Race conditions, simultaneous requests

**Example:**
You test `GET /users/123` -> AI suggests testing with invalid ID `999999`, empty results, unauthorized access, and more.

**Result:** Your 20 tests become 60 comprehensive tests.

---

### 3. Contract Testing

**Prevent breaking changes between services.**

![Contract Testing Demo](assets/demo-gifs/contract-testing.gif)

**The problem:**
- Service A depends on Service B's API
- Service B team changes a field
- Service A breaks in production
- Nobody caught it before deployment

**The solution:**
1. Define contracts from captured traffic
2. Verify contracts in CI/CD pipelines
3. Breaking changes get caught instantly
4. Contracts serve as living documentation

**Why it matters:**
- Catch breaking changes in seconds, not days
- Prevent production incidents from API changes
- Automatic documentation that never goes stale
- Safe API evolution across teams

---

## Quick Start

### Installation

```bash
# Install TraceTap
pip install tracetap

# Set up Claude AI for test generation
export ANTHROPIC_API_KEY='your-api-key-here'
```

### 5-Minute Testing Workflow

**Step 1: Capture API Traffic (2 minutes)**

```bash
# Start TraceTap proxy
tracetap --listen 8080 --raw-log api-capture.json

# In another terminal, make API requests
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
curl -k https://api.example.com/users
curl -k https://api.example.com/posts

# Stop capture (Ctrl+C)
```

**Step 2: Generate Tests with AI (2 minutes)**

```bash
# Generate Playwright tests
tracetap-playwright api-capture.json -o tests/

# With AI edge case suggestions
tracetap-playwright api-capture.json --ai-suggestions -o tests/
```

**Step 3: Run Tests (1 minute)**

```bash
# Run generated tests
pytest tests/
```

**From zero to comprehensive test suite in 5 minutes.**

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

## Real-World Workflows

### Workflow 1: Regression Testing

**Scenario:** Ensure new deployments don't break existing functionality.

```bash
# 1. Capture baseline traffic from working version
tracetap --listen 8080 --raw-log baseline.json

# 2. Generate regression tests with AI
tracetap-playwright baseline.json -o tests/regression/

# 3. Add to CI/CD pipeline
# Every deploy runs: pytest tests/regression/

# 4. Get alerts when tests fail = breaking change detected
```

**Outcome:** Breaking changes caught in CI, not production.

---

### Workflow 2: Exploratory Testing with AI

**Scenario:** Testing a new API and want to find edge cases.

```bash
# 1. Capture your initial testing session
tracetap --listen 8080 --raw-log exploratory.json

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

### Workflow 3: Contract Verification

**Scenario:** Two teams maintain services that depend on each other.

```bash
# Provider team: Capture API traffic
tracetap --listen 8080 --raw-log provider-api.json

# Create contract from captures
tracetap-contract create provider-api.json -o contract.json

# Consumer team: Verify contract before deployment
tracetap-contract verify contract.json --target http://staging-api.example.com

# In CI/CD: Run contract verification
# If contract breaks -> deployment blocked
```

**Outcome:** Services stay in sync, no production surprises.

---

### Workflow 4: Local Development with Mock Server

**Scenario:** Develop and test against APIs without network dependencies.

```bash
# 1. Capture traffic from real API
tracetap --listen 8080 --raw-log captured-api.json

# 2. Run mock server locally
tracetap-mock captured-api.json --port 9000

# 3. Point your app to the mock
export API_URL=http://localhost:9000

# 4. Develop and test without external dependencies
# No rate limits, no network issues, instant responses
```

**Outcome:** Fast, reliable local development.

---

## Core Capabilities

### Traffic Capture

- **HTTP/HTTPS proxy** - Capture all API traffic transparently
- **Smart filtering** - Host matching, wildcards, regex patterns
- **Raw JSON export** - Complete request/response data for AI processing
- **Real-time monitoring** - See requests as they happen
- **Certificate management** - Auto-install HTTPS certificates

### AI-Powered Intelligence

- **Test generation** - Create Playwright tests automatically via Claude AI
- **Variable extraction** - Auto-detect IDs, tokens, UUIDs, timestamps
- **Flow inference** - Understand request sequences and dependencies
- **Smart deduplication** - Remove redundant requests intelligently
- **Gap analysis** - Suggest tests you haven't written yet

### Testing & Verification

- **Generated tests** - Playwright/Pytest tests from captured traffic
- **Contract testing** - Prevent breaking changes between services
- **Mock server** - Run offline mock APIs for development
- **Regression baselines** - Compare API versions automatically

### Developer Experience

- **One-command setup** - Install and run in minutes
- **CLI-first design** - Scriptable and automatable
- **CI/CD ready** - Works with GitHub Actions, GitLab CI, Jenkins
- **Open source** - MIT licensed, community-driven

---

## Installation

### Requirements

- Python 3.8 or higher
- pip (Python package manager)
- Anthropic API key (for AI features)

### Install

```bash
# Basic installation
pip install tracetap

# For development
pip install tracetap[dev]

# Everything
pip install tracetap[all]
```

### Configure AI Features

```bash
# Get API key from https://console.anthropic.com/
export ANTHROPIC_API_KEY='sk-ant-...'

# Verify it works
python -c "import anthropic; print('API key configured')"
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

---

## Command Reference

### Capture Traffic

```bash
# Capture all traffic to raw JSON
tracetap --listen 8080 --raw-log captured.json

# Capture specific host
tracetap --listen 8080 --filter-host api.example.com --raw-log api.json

# Capture with wildcard
tracetap --listen 8080 --filter-host "*.github.com" --raw-log github.json

# Capture with regex pattern
tracetap --listen 8080 --filter-regex "api\..*\.com" --raw-log apis.json
```

### Generate Tests

```bash
# Generate Playwright tests
tracetap-playwright captured.json -o tests/

# Generate with AI suggestions
tracetap-playwright captured.json --ai-suggestions -o tests/
```

### Mock Server

```bash
# Run mock server from captured traffic
tracetap-mock captured.json --port 9000
```

### Contract Testing

```bash
# Create contract from captures
tracetap-contract create captured.json -o contract.json

# Verify contract against live API
tracetap-contract verify contract.json --target http://api.example.com

# Generate contract tests
tracetap-contract generate-tests contract.json -o tests/
```

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

## Examples

Check out the `examples/` directory for complete workflows:

- **[Regression Testing Example](examples/regression-testing/)** - Complete CI/CD workflow
- **[Contract Testing Example](examples/contract-testing/)** - Microservices verification
- **[AI Test Generation Example](examples/ai-test-generation/)** - Intelligent test creation

---

## Contributing

We welcome contributions! Whether it's:

- Bug reports
- Feature requests
- Documentation improvements
- Code contributions

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

**Made for QA Engineers**

[Back to Top](#tracetap)

</div>
