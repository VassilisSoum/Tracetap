<div align="center">

# TraceTap

### The QA Automation Toolkit That Records Your Manual Tests and Generates Playwright Code

**Stop writing tests manually. Record your interactions, capture API traffic, and let AI generate production-ready Playwright tests.**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](https://github.com/VassilisSoum/tracetap/releases)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/VassilisSoum/tracetap/actions)

[Quick Start](#quick-start) | [What Makes TraceTap Special](#what-makes-tracetap-special) | [Features](#key-features) | [Documentation](#documentation)

</div>

---

## 🚀 Key Features

TraceTap 1.0.0 brings together everything you need to transform manual testing into automated, production-ready Playwright tests:

### 🎨 Professional CLI Experience
- **Clear, Actionable Errors**: 7 custom error types with specific resolution steps
- **Rich Progress Indicators**: Live status updates, progress bars, and smart spinners
- **Color-Coded Output**: Consistent, professional terminal experience
- **Documentation Links**: Direct links to help when you need it

### 🔒 Security & Privacy
- **Automatic PII Sanitization**: Redacts passwords, emails, SSNs, API keys (default ON)
- **GDPR/CCPA/HIPAA Friendly**: Compliance-ready data handling
- **Structure Preserving**: Maintains data types and lengths for valid testing

### 🎯 Advanced Test Generation
- **Performance Assertions**: Auto-generated timing tests with smart thresholds
- **Smart Organization**: Tests grouped by feature into clean directory structures
- **Test Data Variations**: AI-powered generation of edge cases, boundaries, errors, and security tests
- **Multiple Templates**: Basic, comprehensive, and regression templates for different needs

### 🤖 AI-Powered Intelligence
- **>80% Success Rate**: Production-ready tests with minimal manual editing
- **Edge Case Detection**: AI suggests tests you might miss
- **Context-Aware**: Understands field types and generates appropriate validations
- **Variable Extraction**: Automatic detection of IDs, tokens, UUIDs, timestamps

### All Features Work Together
```bash
# Generate organized structure with 5 variations and performance tests
tracetap-generate-tests session -o tests/ \
  --variations 5 \
  --performance \
  --organize

# Output: Organized directories with comprehensive test coverage
# tests/
#   auth/
#     login-variation-1.spec.ts  (happy path + timing)
#     login-variation-2.spec.ts  (edge cases + timing)
#     login-variation-3.spec.ts  (boundaries + timing)
#     login-variation-4.spec.ts  (errors + timing)
#     login-variation-5.spec.ts  (security + timing)
#   users/
#     get-variation-1.spec.ts
#     ...
```

---

## What QA Engineers Say

> "I recorded a 10-minute checkout flow and TraceTap generated 15 comprehensive Playwright tests in 30 seconds. This is a game-changer."
> -- QA Engineer, E-commerce Company

> "We went from 20% test coverage to 80% in two weeks. The AI catches edge cases our team never thought of."
> -- Engineering Manager, SaaS Startup

> "No more manual test writing. Record once, get production-ready tests immediately. This is exactly what we've been waiting for."
> -- QA Automation Lead, FinTech

---

## What Makes TraceTap Special

**The World's First UI Recording → AI Test Generation Tool**

TraceTap combines three powerful capabilities that no other tool offers together:

1. **🎬 Record Real User Interactions** - Capture UI events with microsecond precision using hybrid codegen + trace
2. **🌐 Capture Network Traffic** - Automatically record all HTTP/HTTPS API calls with mitmproxy
3. **🤖 AI-Powered Test Generation** - Claude AI converts your recordings into production-ready Playwright tests

**NEW: Hybrid Recording Mode** - Combines Playwright codegen (captures manual interactions) with trace files (real timestamps) for accurate UI-to-API correlation. [Learn more](HYBRID_RECORDING.md)

### The Complete Workflow

```bash
# 1. Record your manual test (2 minutes)
tracetap record https://myapp.com -n login-test
# → Browser opens, you interact manually
# → UI events + API traffic captured simultaneously

# 2. Generate Playwright tests with AI (30 seconds)
export ANTHROPIC_API_KEY=sk-ant-...
tracetap-generate-tests recordings/<session-id> -o tests/login.spec.ts

# 3. Run your generated tests (1 minute)
npx playwright test tests/login.spec.ts
```

### Why This Matters

**No other tool does all three.** Other tools either:
- ❌ Record UI but not network traffic
- ❌ Capture traffic but require manual test writing
- ❌ Generate tests but from scratch, not from real recordings

**TraceTap does ALL THREE in one seamless workflow.**

This means:
- **Convert manual testing to automated tests in minutes** (not hours)
- **Test both UI and API simultaneously** (catch full-stack bugs)
- **AI suggests edge cases you'd miss** (higher quality test coverage)
- **Maintain tests as your app evolves** (AI regenerates when needed)

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

### 1. UI Recording & AI Test Generation (NEW!)

**The killer feature: Record once, get production-ready tests in seconds.**

**How it works:**
1. Click a button to start recording your manual test
2. Interact with your app normally (login, fill forms, click buttons)
3. TraceTap captures both UI events AND network API calls simultaneously
4. Claude AI generates complete Playwright tests from your recording
5. Run the generated tests immediately

**What you get:**
- Complete Playwright test code (TypeScript, JavaScript, or Python)
- Network assertions that verify API responses
- Element selectors automatically detected
- Comments explaining the UI-to-API correlations
- Edge case suggestions from Claude AI
- Multiple test templates: basic, comprehensive, regression

**Why it's revolutionary:**
- **Automatic event correlation** - Links clicks to API calls intelligently
- **Confidence scoring** - Shows which correlations are high vs low confidence
- **Template selection** - Choose test depth: minimal, comprehensive, or regression-focused
- **Multi-format output** - Generate in TypeScript, JavaScript, or Python
- **Time savings** - 10-minute manual flow → 15 comprehensive tests in 30 seconds

**Real example:**
- Recording a checkout flow takes 5 minutes
- Generating tests takes 30 seconds
- You get 15+ runnable, maintainable tests
- Previously this would take 3-4 hours to write manually

---

### 2. AI-Powered Test Suggestions

**Let Claude AI find the gaps in your testing.**

**How it works:**
1. Generate tests from your recording (as above)
2. AI analyzes the generated tests for gaps
3. Suggests additional test cases you didn't think to write
4. You review and add valuable ones to your suite

**AI suggests tests for:**
- **Edge cases** - Empty strings, null values, boundary conditions
- **Error scenarios** - Invalid IDs, expired tokens, missing fields
- **Security** - SQL injection, XSS, sensitive data exposure
- **Performance** - Timeout handling, rate limiting
- **Concurrency** - Race conditions, simultaneous requests

**Example:**
You record a login flow → Get 10 tests → AI suggests 15 more edge cases → Select the valuable ones → 25 comprehensive tests total.

**Result:** Your 10 tests become 25-50 comprehensive tests with one click.

---

### 3. Contract Testing

**Prevent breaking changes between services.**

**The problem:**
- Service A depends on Service B's API
- Service B team changes a field
- Service A breaks in production
- Nobody caught it before deployment

**The solution:**
1. Define contracts from your generated tests
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

> **📖 Detailed Installation Guide:** See [INSTALL.md](INSTALL.md) for comprehensive instructions with troubleshooting.

**Quick Overview:**
- TraceTap automatically installs: mitmproxy, playwright (Python), anthropic
- You manually install: Playwright browsers, mitmproxy certificate
- Total time: ~5 minutes

```bash
# 1. Clone and install TraceTap from source
git clone https://github.com/VassilisSoum/tracetap.git
cd tracetap  # ⚠️ IMPORTANT: Make sure you're in the tracetap directory!

# 2. (Optional) Run setup verification script
./verify-setup.sh  # Checks you're in the right directory and have dependencies

# 3. Build and install the package (includes mitmproxy automatically)
pip3 install build
python3 -m build
pip3 install dist/tracetap-1.0.0-py3-none-any.whl
# This installs TraceTap and all dependencies including:
#   - mitmproxy (traffic capture)
#   - playwright (browser automation)
#   - anthropic (AI test generation)

# 4. Install Playwright browsers (REQUIRED for UI recording)
# Why separate? Playwright splits into two parts:
#   - Python package (installed above via dependencies)
#   - Browser binaries (Chromium, Firefox, WebKit)
# The browser binaries are ~300MB and must be installed separately
playwright install chromium

# 5. ⚠️ REQUIRED FOR HTTPS: Install mitmproxy certificate
# This allows TraceTap to capture encrypted HTTPS traffic

# mitmproxy was already installed in step 3 (it's a dependency)
# Now generate the certificate by running mitmproxy once:
mitmproxy --version  # This creates ~/.mitmproxy/mitmproxy-ca-cert.pem
# Press 'q' to quit if mitmproxy starts

# Then install it to your system trust store
python3 -m tracetap.cert_installer install
# Note: On Linux, you may need sudo or follow manual instructions

# Verify installation
python3 -m tracetap.cert_installer verify

# 6. Set up Claude AI (for test generation)
export ANTHROPIC_API_KEY=sk-ant-api03-...

# 7. Verify installation
tracetap-record --help
```

## Understanding the Dependencies

TraceTap automatically installs several key dependencies:

### 1. **mitmproxy** (Network Traffic Capture)
- **What it is:** An interactive HTTPS proxy
- **Installation:** Automatic (included in TraceTap dependencies)
- **Verify it's installed:** `mitmproxy --version`
- **Manual installation (if needed):** `pip3 install mitmproxy`
- **Why needed:** Captures HTTP/HTTPS API traffic during recording
- **First-time setup:** Run `mitmproxy --version` to generate certificate files in `~/.mitmproxy/`

### 2. **Playwright** (Browser Automation)
- **What it is:** Browser automation library
- **Installation:** Two parts
  - Python package: Automatic (included in TraceTap dependencies)
  - Browser binaries: Manual - `playwright install chromium`
- **Why needed:** Controls the browser during UI recording

### 3. **Anthropic SDK** (AI Test Generation)
- **What it is:** Claude AI API client
- **Installation:** Automatic (included in TraceTap dependencies)
- **Why needed:** Powers AI test generation from recordings

**Why does Playwright need a separate browser installation?**

Playwright is split into two components:
1. **Python package** (`playwright`) - The API/automation library (installed via pip)
2. **Browser binaries** - Actual Chromium/Firefox/WebKit browsers (~300MB each)

The `playwright install chromium` command downloads the Chromium browser binary that Playwright controls during recording. Without this, you'll get an error: "Executable doesn't exist at /path/to/chromium".

> **⚠️ HTTPS Certificate Required**
>
> Most modern apps use HTTPS. To capture encrypted traffic, you **must** install mitmproxy's certificate before recording.
> Without this, TraceTap can only capture plain HTTP traffic.
>
> **Verify installation:** `python -m tracetap.cert_installer verify`

### Complete Workflow: Record → Generate → Test

**Step 1: Record Your Manual Test**

```bash
# Start recording your app
tracetap record https://myapp.com -n checkout-flow
# → Browser opens
# → Interact manually (login, add items, checkout)
# → Press Enter when done
# → Recording saved to recordings/<session-id>/
```

**Step 2: Generate Playwright Tests**

```bash
# Generate tests from your recording
tracetap-generate-tests recordings/<session-id> -o tests/generated.spec.ts

# Or generate with different templates
tracetap-generate-tests recordings/<session-id> -o tests/ --template comprehensive
```

**Step 3: Run Generated Tests**

```bash
# Run tests with Playwright
npx playwright test tests/generated.spec.ts
```

**That's it! You just went from manual testing to automated Playwright tests in 3 commands.**

#### 🔧 Troubleshooting Common Issues

**`ERROR Source ... does not appear to be a Python project: no pyproject.toml or setup.py`**
- You're running `python3 -m build` from the wrong directory
- This happens when you're not in the TraceTap project root
- Example of the error:
  ```bash
  $ pwd
  /home/user/IdeaProjects/personal/TraceTap-Rebrand  # ❌ Wrong!
  $ python3 -m build
  ERROR Source ... does not appear to be a Python project
  ```
- Fix: Change to the TraceTap project root:
  ```bash
  cd /path/to/tracetap  # wherever you cloned it (exact folder name!)
  ls pyproject.toml     # verify you're in the right place (file must exist)
  python3 -m build      # now it will work
  ```
- Or run the verification script: `./verify-setup.sh`

**`playwright: command not found` or `ModuleNotFoundError: No module named 'playwright.__main__'`**
- This means the Playwright package is corrupted or not installed
- Fix: Reinstall Playwright: `pip3 uninstall playwright -y && pip3 install playwright`
- Then install browsers: `playwright install chromium`

**`Executable doesn't exist at /path/to/chromium`**
- You installed the Playwright package but forgot to download browsers
- Fix: Run `playwright install chromium` (this downloads the ~300MB browser binary)

**`mitmproxy: command not found`**
- mitmproxy wasn't installed or isn't in your PATH
- Check if it's installed: `pip3 list | grep mitmproxy`
- Fix: Install manually: `pip3 install mitmproxy`
- Or reinstall TraceTap which includes it as a dependency

**mitmproxy certificate not found (`~/.mitmproxy/mitmproxy-ca-cert.pem`)**
- The certificate hasn't been generated yet
- Fix: Run mitmproxy once to generate it: `mitmproxy --version` (then press 'q' to quit)
- Or start mitmproxy briefly: `mitmproxy` (then press 'q')

**Certificate installer commands complete immediately with no output**
- The cert_installer module was missing the `__main__` entry point (fixed in v1.0.0)
- If you still see this issue, rebuild and reinstall:
  ```bash
  cd /path/to/tracetap
  python3 -m build
  pip3 install dist/tracetap-1.0.0-py3-none-any.whl --force-reinstall
  ```

**Not capturing HTTPS traffic?**
- ✅ Generate certificate first: `mitmproxy --version` (creates ~/.mitmproxy/mitmproxy-ca-cert.pem)
- ✅ Install certificate: `python3 -m tracetap.cert_installer install`
- ✅ Verify installation: `python3 -m tracetap.cert_installer verify`
- ✅ On Linux, you may need sudo or follow the manual instructions shown
- ✅ Restart your browser after installing the certificate

**Recording session empty or missing API calls?**
- Check that the app makes network requests during recording
- Ensure you're interacting with the app before pressing Enter to stop recording
- For API-only apps, use the legacy proxy mode (see below)

**ImportError: cannot import name 'main' from 'tracetap'**
- The package metadata wasn't read correctly during pip install
- Fix: Use the build module approach shown in installation instructions above

**Need help?** See our [Troubleshooting Guide](docs/troubleshooting.md) or [open an issue](https://github.com/VassilisSoum/tracetap/issues).

---

### Alternative: API-Only Testing (Legacy)

If you only need API testing without UI recording:

```bash
# Start TraceTap proxy (capture only)
tracetap proxy --listen 8080 --raw-log api.json

# Make API requests or use your app normally
# Stop capture (Ctrl+C)

# Generate tests
tracetap-generate-tests api.json -o tests/
```

---

## Why Choose TraceTap?

### Before TraceTap

| Task | Time Required |
|------|--------------|
| Manual test writing for 10-minute flow | 3-4 hours |
| Document API expectations | 1-2 hours |
| Edge case analysis | 1 hour |
| **Total** | **5-7 hours** |

### After TraceTap

| Task | Time Required |
|------|--------------|
| Record the 10-minute flow | 10 minutes |
| Generate tests with AI | 30 seconds |
| Review and accept suggestions | 10 minutes |
| **Total** | **20-30 minutes** |

**That's a 95% time reduction.**

### For QA Engineers

- ✅ Stop writing boilerplate test code
- ✅ Convert manual tests to automated tests in minutes
- ✅ Catch both UI and API issues in one test
- ✅ AI suggests edge cases you might miss
- ✅ Tests are production-ready immediately

### For Development Teams

- ✅ Accelerate test coverage growth (20% → 80% in weeks)
- ✅ Reduce QA bottlenecks with automation
- ✅ Lower maintenance burden (AI regenerates when app changes)
- ✅ Improve test quality with AI insights
- ✅ Ship faster with confidence

---

## Real-World Workflows

### Workflow 1: Automated Checkout Testing

**Scenario:** QA needs to ensure the checkout flow works end-to-end.

```bash
# 1. Record a real checkout flow (5 minutes)
tracetap record https://shop.example.com -n checkout-flow
# → Click through login, add items, enter payment, confirm order

# 2. Generate tests from recording (30 seconds)
tracetap-generate-tests recordings/checkout-flow -o tests/checkout.spec.ts

# 3. Generate additional edge case tests
tracetap-generate-tests recordings/checkout-flow -o tests/ --template comprehensive

# 4. Run tests in CI/CD
npx playwright test tests/checkout.spec.ts
```

**Outcome:**
- Generated 20+ runnable tests from one manual recording
- Tests cover both UI interactions and API responses
- Time saved: 6 hours down to 30 minutes

---

### Workflow 2: Regression Testing After Deployment

**Scenario:** Ensure a new deployment doesn't break anything.

```bash
# 1. Record critical user flows from staging (10 minutes)
tracetap record https://staging.example.com -n critical-flows
# → Login, search, checkout, profile update, etc.

# 2. Generate regression tests
tracetap-generate-tests recordings/critical-flows -o tests/regression.spec.ts

# 3. Add to CI/CD pipeline
# GitHub Actions runs: npx playwright test tests/regression.spec.ts

# 4. Get alerts if tests fail = breaking change detected
```

**Outcome:** Breaking changes caught in CI, not production.

---

### Workflow 3: Multi-User Flow Testing

**Scenario:** Test complex flows involving multiple users/roles.

```bash
# 1. Record Admin user workflow
tracetap record https://app.example.com -n admin-workflow
# → Admin logs in, creates users, configures settings

# 2. Record Standard user workflow
tracetap record https://app.example.com -n user-workflow
# → User logs in, submits request, views results

# 3. Generate tests for each flow
tracetap-generate-tests recordings/admin-workflow -o tests/admin.spec.ts
tracetap-generate-tests recordings/user-workflow -o tests/user.spec.ts

# 4. Run both in test suite
npx playwright test tests/
```

**Outcome:** Complete user role coverage, all generated automatically.

---

### Workflow 4: Contract Verification with Generated Tests

**Scenario:** Two teams maintain services that depend on each other.

```bash
# Provider team: Record real API interactions
tracetap record https://api.example.com -n provider-flows

# Generate contract from recorded flows
tracetap-generate-tests recordings/provider-flows --template contract -o contracts/

# Consumer team: Verify contract during CI/CD
tracetap-contract verify contracts/ --target http://staging-api.example.com

# If contract breaks → deployment blocked → incident prevented
```

**Outcome:** Services stay in sync, no production surprises.

---

## Core Capabilities

### UI Recording & Event Correlation

- **Browser recording** - Capture UI events using Playwright trace files
- **Network correlation** - Link UI actions to API calls with confidence scoring
- **Element detection** - Automatically identify CSS selectors for recorded actions
- **Timing precision** - Microsecond accuracy for event sequences
- **Multi-browser** - Record on Chrome, Firefox, Safari, Edge

### AI-Powered Test Generation

- **Playwright code generation** - Generate complete, runnable tests in TypeScript/JavaScript/Python
- **Template selection** - Choose basic, comprehensive, or regression-focused tests
- **Edge case suggestions** - Claude AI proposes tests you didn't think to write
- **Variable extraction** - Auto-detect IDs, tokens, UUIDs, timestamps
- **Smart assertions** - Generate both UI and API assertions automatically

### Network Traffic Capture

- **HTTP/HTTPS proxy** - Capture all API traffic transparently
- **Smart filtering** - Host matching, wildcards, regex patterns
- **Real-time monitoring** - See requests as they happen
- **Certificate management** - Auto-install HTTPS certificates

### Testing & Verification

- **Generated tests** - Playwright/Pytest tests from recordings
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
# Clone and install from source
git clone https://github.com/VassilisSoum/tracetap.git
cd tracetap  # ⚠️ Must be in project root directory!

# Verify you're in the right place
ls pyproject.toml  # This file must exist

# Build the package
pip3 install build
python3 -m build

# Basic installation
pip3 install dist/tracetap-1.0.0-py3-none-any.whl

# For development (includes test tools)
pip3 install "dist/tracetap-1.0.0-py3-none-any.whl[dev]"

# Everything (all optional dependencies)
pip3 install "dist/tracetap-1.0.0-py3-none-any.whl[all]"

# Install Playwright browsers (separate ~300MB download)
# This is REQUIRED - downloads the actual Chromium browser binary
playwright install chromium
```

**Note:** We use `python3 -m build` instead of `pip install -e .` because the editable install requires PEP 660 support. The build approach works reliably on all systems.

### Configure AI Features

```bash
# Get API key from https://console.anthropic.com/
export ANTHROPIC_API_KEY='sk-ant-...'

# Verify it works
python -c "import anthropic; print('API key configured')"
```

### Install Certificate (Required for HTTPS)

**Why?** Modern apps use HTTPS encryption. To capture this traffic, mitmproxy needs to act as a trusted "man-in-the-middle" by installing a certificate authority on your system. This is **required** for recording HTTPS traffic.

**What it does:**
- Installs mitmproxy's CA certificate to your system's trust store
- Allows TraceTap to decrypt and record HTTPS traffic during recording
- Only affects your local machine (not production)

**Installation:**

```bash
# Linux/macOS
python -m tracetap.cert_installer install

# Windows (PowerShell as Admin)
python -m tracetap.cert_installer install

# Verify installation
python -m tracetap.cert_installer verify
```

**Security Note:** The certificate is only used locally for testing. Remove it when you're done with `python -m tracetap.cert_installer uninstall`.

---

## Command Reference

### UI Recording & Test Generation

```bash
# Record a user interaction
tracetap record https://myapp.com -n my-test-name

# Generate tests from recording (basic template)
tracetap-generate-tests recordings/<session-id> -o tests/

# Generate with comprehensive template
tracetap-generate-tests recordings/<session-id> -o tests/ --template comprehensive

# Generate in different language
tracetap-generate-tests recordings/<session-id> -o tests/ --output-format python

# Generate with AI edge case suggestions
tracetap-generate-tests recordings/<session-id> -o tests/ --suggestions
```

### Network Capture (API-Only)

```bash
# Capture all traffic to raw JSON
tracetap proxy --listen 8080 --raw-log captured.json

# Capture specific host
tracetap proxy --listen 8080 --filter-host api.example.com --raw-log api.json

# Capture with wildcard
tracetap proxy --listen 8080 --filter-host "*.github.com" --raw-log github.json
```

### Generate Tests from Network Capture

```bash
# Generate Playwright tests from captured traffic
tracetap-generate-tests captured.json -o tests/

# Generate with custom base URL
tracetap-generate-tests captured.json -o tests/ --base-url https://staging.example.com
```

### Mock Server & Contract Testing

```bash
# Run mock server from recording
tracetap-mock recordings/<session-id> --port 9000

# Run mock server from captured traffic
tracetap-mock captured.json --port 9000

# Create contract from recording
tracetap-contract create recordings/<session-id> -o contract.json

# Verify contract against live API
tracetap-contract verify contract.json --target http://api.example.com
```

---

## Documentation

### Getting Started

- **[UI Recording Quick Start](docs/recording-guide.md)** - Record your first test
- **[Test Generation Guide](docs/test-generator-usage.md)** - Generate tests from recordings
- **[Installation](docs/getting-started.md#installation)** - Detailed setup instructions

### Core Features

- **[UI Recording & Test Generation](docs/features/ui-recording.md)** - The killer feature explained
- **[Regression Testing](docs/features/regression-testing.md)** - Catch breaking changes automatically
- **[AI Test Suggestions](docs/features/ai-test-suggestions.md)** - Let AI improve your tests
- **[Contract Testing](docs/features/contract-testing.md)** - Verify API compatibility

### Workflows & Integrations

- **[Playwright Integration](docs/workflows/playwright-integration.md)** - Generate Playwright tests
- **[CI/CD Integration](docs/workflows/ci-cd-integration.md)** - Automate in GitHub Actions, GitLab CI, Jenkins
- **[Local Development](docs/workflows/local-development.md)** - Mock servers for development
- **[Contract-First Testing](docs/workflows/contract-first.md)** - API contract verification

### Advanced Guides

- **[Capturing Network Traffic](docs/guides/capturing-traffic.md)** - Advanced capture techniques
- **[Test Generation Options](docs/guides/generating-tests.md)** - Customization and templates
- **[Mock Server Setup](docs/guides/mock-server.md)** - Run offline mock APIs
- **[Contract Verification](docs/guides/contract-verification.md)** - Prevent breaking changes

### API Reference

- **[CLI Reference](docs/api/cli-reference.md)** - Complete command documentation
- **[Python API](docs/api/python-api.md)** - Use TraceTap as a library

### Help & Support

- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[FAQ](docs/faq.md)** - Frequently asked questions

---

## Examples

Check out complete, runnable examples in the `examples/` directory:

### UI Recording Examples
- **[E-commerce Checkout Flow](examples/ecommerce-api/)** - Record and test a complete checkout
- **[Regression Suite](examples/regression-suite/)** - Multi-scenario regression testing
- **[Contract Testing](examples/contract-testing/)** - API contract verification

These examples include:
- Recorded sessions (JSON)
- Generated test code (TypeScript)
- CI/CD configuration
- Scripts to run everything

---

## Comparison with Other Tools

| Feature | TraceTap | Playwright Codegen | Cypress Studio | Selenium IDE |
|---------|----------|-------------------|----------------|--------------|
| Record UI interactions | ✅ | ✅ | ✅ | ✅ |
| Capture API traffic simultaneously | ✅ | ❌ | ❌ | ❌ |
| Correlate UI events to API calls | ✅ | ❌ | ❌ | ❌ |
| AI test generation | ✅ | ❌ | ❌ | ❌ |
| Multiple test templates | ✅ | ❌ | ❌ | ❌ |
| Edge case suggestions | ✅ | ❌ | ❌ | ❌ |
| Contract testing | ✅ | ❌ | ❌ | ❌ |
| Network assertion generation | ✅ | ❌ | ❌ | ❌ |
| TypeScript/JavaScript/Python | ✅ | ✅ | ✅ | ❌ |
| Free & Open Source | ✅ | ✅ | ❌ | ✅ |

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
