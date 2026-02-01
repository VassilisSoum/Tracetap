# CLI Reference

Complete reference for all TraceTap command-line tools.

## Table of Contents

- [tracetap.py](#tracetappy) - Main capture tool
- [tracetap-playwright.py](#tracetap-playwrightpy) - Generate Playwright tests

---

## tracetap.py

Main HTTP/HTTPS traffic capture proxy.

### Usage

```bash
python tracetap.py [OPTIONS]
```

### Options

#### Listening

```bash
--listen PORT
  Listen port (default: 8080)
  Example: --listen 8081

--listen HOST:PORT
  Listen on specific interface and port
  Example: --listen 0.0.0.0:8080
```

#### Export

```bash
--raw-log FILE
  Export raw JSON log (primary export format)
  Example: --raw-log captures.json

--session NAME
  Session name (used in exports)
  Example: --session "User Registration Flow"
```

#### Filtering

```bash
--filter-host HOST
  Capture only specific hosts (wildcard supported)
  Example: --filter-host api.example.com
  Repeatable: --filter-host host1 --filter-host host2

--filter-regex PATTERN
  Capture using regex pattern
  Example: --filter-regex "api\..*\.com"
  Repeatable: --filter-regex pattern1 --filter-regex pattern2

--filter-verbose
  Show filter matching decisions
```

#### Certificate Management

```bash
--install-cert
  Install CA certificate (one-time setup)

--renew-cert
  Generate new CA certificate

--cert-file PATH
  Use custom certificate file
  Example: --cert-file /path/to/cert.pem

--key-file PATH
  Use custom key file
  Example: --key-file /path/to/key.pem
```

#### Output

```bash
--quiet
  Suppress console output

--debug
  Verbose debug output

--color
  Force color output

--no-color
  Disable color output
```

#### Advanced

```bash
--socks-server HOST:PORT
  Forward through SOCKS proxy
  Example: --socks-server proxy.example.com:1080

--ssl-insecure
  Disable SSL verification (not recommended)
```

### Examples

```bash
# Basic capture with raw JSON export
python tracetap.py --listen 8080 --raw-log captures.json

# With host filtering
python tracetap.py --listen 8080 \
  --filter-host api.example.com \
  --raw-log captures.json

# Multiple filters
python tracetap.py --listen 8080 \
  --filter-host "*.example.com" \
  --filter-regex "/api/v[0-9]+" \
  --raw-log captures.json

# Debug mode
python tracetap.py --listen 8080 --debug --filter-verbose --raw-log captures.json
```

---

## tracetap-playwright.py

Generate pytest tests from captured traffic using AI transformation.

### Usage

```bash
python tracetap-playwright.py <capture_file> [OPTIONS]
```

### Arguments

```bash
capture_file
  Path to captured traffic file (JSON)
  Example: captured.json
```

### Options

#### Output

```bash
-o, --output DIRECTORY
  Output directory for generated tests
  Example: -o tests/
  Default: ./tests

--test-file NAME
  Name of test file (without .py extension)
  Example: --test-file test_api_calls
  Default: test_api_calls

--class-name NAME
  Name of test class
  Example: --class-name APITests
  Default: TestAPIEndpoints
```

#### Assertions

```bash
--include-assertions
  Include body assertions (default: true)

--skip-body-assertions
  Skip response body validation

--skip-timing
  Skip response time assertions

--minimal-assertions
  Only assert status codes

--include-docstrings
  Add docstrings to tests (default: true)

--include-comments
  Add explanatory comments
```

#### AI-Powered Generation

```bash
--ai-suggestions
  Use AI to suggest additional test cases

--focus-areas AREAS
  Focus on specific test areas
  Options: edge_cases error_handling security performance
  Example: --focus-areas edge_cases error_handling

--parameterized
  Generate parameterized tests for variations
```

### Examples

```bash
# Basic generation
python tracetap-playwright.py captured.json -o tests/

# With custom class name
python tracetap-playwright.py captured.json \
  --class-name MyAPITests \
  -o tests/

# Minimal assertions (fast tests)
python tracetap-playwright.py captured.json \
  --minimal-assertions \
  -o tests/

# With AI suggestions
python tracetap-playwright.py captured.json \
  --ai-suggestions \
  --focus-areas edge_cases security \
  -o tests/

# Parameterized tests
python tracetap-playwright.py captured.json \
  --parameterized \
  -o tests/
```

---

## Common Options

### API Key (for AI features)

Set environment variable:

```bash
export ANTHROPIC_API_KEY='sk-ant-...'

# Then use commands with --ai flag
python tracetap-playwright.py api.json --ai-suggestions -o tests/
```

### Working with Paths

All file paths are relative to current directory:

```bash
# Output to subdirectory
python tracetap-playwright.py captured.json -o ./tests/generated/

# Input from another directory
python tracetap-playwright.py ./data/captures/api.json -o tests/
```

---

## Workflow

The typical workflow with TraceTap is:

1. **Capture** - Record API traffic with `tracetap.py`
2. **Export** - Save to raw JSON format with `--raw-log`
3. **Transform** - Use AI (Claude) to transform captures into test artifacts
4. **Run** - Execute generated tests with pytest

```bash
# 1. Capture traffic
python tracetap.py --listen 8080 --raw-log captures.json

# 2. Generate tests with AI
python tracetap-playwright.py captures.json --ai-suggestions -o tests/

# 3. Run tests
pytest tests/
```

---

## Next Steps

- **[Python API](python-api.md)** - Use TraceTap as a library
- **[Guides](../guides/)** - Learn how to use these tools
