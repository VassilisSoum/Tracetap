# Getting Started with TraceTap

Welcome to TraceTap! This guide will get you up and running in 5 minutes.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Your First Capture](#your-first-capture)
- [Next Steps](#next-steps)

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Install TraceTap

```bash
# Clone the repository
git clone https://github.com/yourusername/tracetap.git
cd tracetap

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Optional: For AI features (test generation, variable extraction)
pip install -r requirements-ai.txt
export ANTHROPIC_API_KEY='your-api-key-here'
```

### Verify Installation

```bash
python tracetap.py --help
```

You should see the help message with available options.

---

## Quick Start

### Set Up HTTP Proxy

Before running TraceTap, configure your system to use the proxy. Open a new terminal (keep TraceTap running in another).

```bash
# Linux/macOS
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Windows (PowerShell)
$env:HTTP_PROXY = 'http://localhost:8080'
$env:HTTPS_PROXY = 'http://localhost:8080'
```

### Start TraceTap

In your first terminal, start the capture proxy:

```bash
python tracetap.py --listen 8080 --raw-log captured.json
```

You'll see output like:
```
[16:42:31] TraceTap HTTP Proxy started on port 8080
[16:42:31] Ready to capture traffic...
```

---

## Your First Capture

### Step 1: Make API Requests

In your terminal with the proxy configured, make some API calls:

```bash
# Example: Capture GitHub API traffic
curl -k https://api.github.com/users/github

# Or use your own API
curl -k https://api.example.com/endpoint
```

You'll see requests appear in the TraceTap terminal:
```
[16:43:12] -> GET https://api.github.com/users/github
[16:43:12] <- 200 OK (142ms)
```

### Step 2: Stop and Export

After making requests, stop TraceTap with `Ctrl+C`:

```
[16:44:00] Stopping proxy...
[16:44:01] Exported 5 requests to captured.json
```

### Step 3: View Captured Traffic

The `captured.json` file contains all your traffic. You can open it with any text editor:

```bash
cat captured.json | jq .
```

It includes:
- Request/response headers
- Request/response bodies
- Timing information
- Status codes
- Metadata

---

## 5-Minute Workflow

Here's the complete flow from capture to testing:

### 1. Capture Traffic (2 minutes)

```bash
# Terminal 1: Start TraceTap
python tracetap.py --listen 8080 --raw-log api-capture.json

# Terminal 2: Generate traffic
export HTTP_PROXY=http://localhost:8080
curl -k https://api.example.com/users
curl -k https://api.example.com/posts
# ... do your API interactions

# Terminal 1: Press Ctrl+C to stop
```

### 2. Generate Tests with AI (2 minutes)

```bash
# Generate Playwright tests with AI suggestions
python tracetap-playwright.py api-capture.json \
  --ai-suggestions \
  -o tests/
```

### 3. Run Tests (1 minute)

```bash
# Run generated tests
pytest tests/
```

---

## Next Steps

### Learn About Core Features

1. **[Capturing Traffic](guides/capturing-traffic.md)** - Advanced capture options
   - Filtering by host/regex
   - Certificate management
   - Debug mode

2. **[Generating Tests](guides/generating-tests.md)** - Create tests from captures
   - AI-powered test generation
   - Focus areas (security, edge cases)
   - Custom test structures

3. **[Contract Verification](guides/contract-verification.md)** - Validate API contracts
   - Contract creation
   - Contract verification
   - Integration testing

### Explore Feature Highlights

- **[Regression Testing](features/regression-testing.md)** - Catch breaking changes early
- **[AI Test Suggestions](features/ai-test-suggestions.md)** - Let AI help generate tests
- **[Contract Testing](features/contract-testing.md)** - Verify API backwards compatibility

### Advanced Topics

- **[CI/CD Integration](guides/ci-cd-integration.md)** - Automate with GitHub Actions, GitLab CI, etc.
- **[CLI Reference](api/cli-reference.md)** - Complete command reference
- **[Python API](api/python-api.md)** - Use TraceTap as a library

### Troubleshooting

Having issues? Check [Troubleshooting Guide](troubleshooting.md) for:
- Common installation problems
- SSL/HTTPS certificate issues
- Proxy configuration problems
- API key setup

---

## Common Commands

Here are some frequently used commands:

```bash
# Basic capture with raw JSON export
python tracetap.py --listen 8080 --raw-log api.json

# Capture only specific host
python tracetap.py --listen 8080 --filter-host api.example.com --raw-log api.json

# Capture with multiple filters (OR logic)
python tracetap.py --listen 8080 \
  --filter-host api.example.com \
  --filter-host *.github.com \
  --raw-log api.json

# Capture using regex pattern
python tracetap.py --listen 8080 --filter-regex "api\..*\.com" --raw-log api.json

# Generate Playwright tests with AI
python tracetap-playwright.py api.json --ai-suggestions -o tests/
```

---

## Getting Help

- **Documentation**: See the [full docs](../README.md)
- **Examples**: Check the tests directory for working examples
- **Issues**: Report bugs on GitHub
- **Contributing**: Pull requests welcome!

---

## What's Next?

Pick your next action:

- **Just captured traffic?** -> Read [Generating Tests](guides/generating-tests.md)
- **Want to understand contracts?** -> Read [Contract Testing](guides/contract-verification.md)
- **Integrating with CI/CD?** -> Read [CI/CD Integration](guides/ci-cd-integration.md)
- **Hitting issues?** -> Check [Troubleshooting](troubleshooting.md)
