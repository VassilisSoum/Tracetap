# CLI Reference

Complete reference for all TraceTap command-line tools.

## Table of Contents

- [tracetap.py](#tracetappy) - Main capture tool
- [tracetap-playwright.py](#tracetap-playwrightpy) - Generate Playwright tests
- [tracetap-ai-postman.py](#tracetap-ai-postmanpy) - Generate Postman collections
- [tracetap2wiremock.py](#tracetap2wiremockpy) - Generate WireMock stubs
- [tracetap-replay.py](#tracetap-replaypy) - Replay traffic
- [tracetap-update-collection.py](#tracetap-update-collectionpy) - Update Postman collections

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
--export FILE
  Export Postman collection
  Example: --export api.json

--raw-log FILE
  Export raw JSON log
  Example: --raw-log captures.json

--export-openapi FILE
  Export OpenAPI 3.0 specification
  Example: --export-openapi openapi.json

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
# Basic capture
python tracetap.py --listen 8080 --export api.json

# With host filtering
python tracetap.py --listen 8080 \
  --filter-host api.example.com \
  --export api.json

# Multiple filters
python tracetap.py --listen 8080 \
  --filter-host "*.example.com" \
  --filter-regex "/api/v[0-9]+" \
  --export api.json

# With OpenAPI export
python tracetap.py --listen 8080 \
  --export postman.json \
  --raw-log raw.json \
  --export-openapi openapi.json

# Debug mode
python tracetap.py --listen 8080 --debug --filter-verbose --export api.json
```

---

## tracetap-playwright.py

Generate pytest tests from captured traffic.

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

#### Generation

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

## tracetap-ai-postman.py

Generate Postman collections from captured traffic.

### Usage

```bash
python tracetap-ai-postman.py <capture_file> [OPTIONS]
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
-o, --output FILE
  Output Postman collection file
  Example: -o postman.json
  Default: postman-collection.json
```

#### AI-Powered Features

```bash
--infer-flow
  Use AI to infer request workflows
  AI analyzes traffic to understand sequences

--flow-intent TEXT
  Specify what the workflow does
  Example: --flow-intent "User registration and verification"

--flow-strict
  Strict mode - fewer inferred connections

--emit-flow
  Export flow specification

--force-regenerate
  Regenerate even if collection exists

--from-flow FILE
  Generate from YAML flow spec

--match-flow FILE
  Match against flow specification

--ai-instructions TEXT
  Custom instructions for AI
  Example: --ai-instructions "Focus on payment endpoints"
```

#### Variable Handling

```bash
--no-variables
  Don't extract variables

--no-jwt-params
  Skip JWT parameter extraction

--no-path-params
  Skip path parameter extraction

--no-base-url-params
  Don't extract base URL parameters

--no-response-extraction
  Don't extract from responses
```

### Examples

```bash
# Basic generation
python tracetap-ai-postman.py captured.json -o postman.json

# With AI flow inference
python tracetap-ai-postman.py captured.json \
  --infer-flow \
  -o postman.json

# With custom flow intent
python tracetap-ai-postman.py captured.json \
  --infer-flow \
  --flow-intent "Complete checkout process" \
  -o postman.json

# Skip variable extraction
python tracetap-ai-postman.py captured.json \
  --no-variables \
  -o postman.json
```

---

## tracetap2wiremock.py

Generate WireMock stubs from captured traffic.

### Usage

```bash
python tracetap2wiremock.py <capture_file> [OPTIONS]
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
-o, --output FILE
  Output WireMock stubs file
  Example: -o wiremock-stubs.json
  Default: wiremock-stubs.json
```

#### Matching

```bash
--matcher-strategy STRATEGY
  How to match requests
  Options: exact url-pattern body-pattern
  Default: exact

--priority PRIORITY
  Stub priority (higher = match first)
  Example: --priority 100
  Default: 5
```

#### Filtering

```bash
--flow FILE
  Generate stubs only for this flow
  Example: --flow flow.json

--captures FILE
  Only use specific captures
  Example: --captures api.json

--api-key KEY
  API key for AI features (if available)
```

### Examples

```bash
# Basic generation
python tracetap2wiremock.py captured.json -o wiremock-stubs.json

# With URL pattern matching
python tracetap2wiremock.py captured.json \
  --matcher-strategy url-pattern \
  -o wiremock-stubs.json

# High priority (match first)
python tracetap2wiremock.py captured.json \
  --priority 100 \
  -o wiremock-stubs.json
```

---

## tracetap-replay.py

Replay captured traffic to different servers.

### Usage

```bash
python tracetap-replay.py <command> <file> [OPTIONS]
```

### Commands

#### replay

Replay captured requests to target server:

```bash
python tracetap-replay.py replay session.json --target http://localhost:8080
```

Options:
```bash
--target URL
  Target base URL (required)
  Example: --target http://staging-api.example.com

--variables KEY=VALUE
  Variable substitution
  Example: --variables user_id=123 token=abc
  Repeatable: --variables var1=val1 --variables var2=val2

--workers COUNT
  Concurrent workers
  Example: --workers 10
  Default: 5

--timeout SECONDS
  Request timeout
  Default: 30

--retries COUNT
  Max retries per request
  Default: 3

--no-verify-ssl
  Disable SSL verification

--filter-method METHOD
  Only replay specific methods
  Example: --filter-method GET POST

-o, --output FILE
  Save results to JSON file

--verbose
  Verbose output
```

#### mock

Start mock HTTP server:

```bash
python tracetap-replay.py mock session.json --port 8080
```

Options:
```bash
--port PORT
  Listen port
  Default: 8080

--host HOST
  Listen host
  Default: localhost
  Example: --host 0.0.0.0

--strategy STRATEGY
  Matching strategy
  Options: exact fuzzy pattern semantic
  Default: fuzzy

--chaos
  Enable chaos engineering (failures)

--chaos-rate RATE
  Failure rate (0.0-1.0)
  Example: --chaos-rate 0.1 (10% failures)
  Default: 0.1

--delay MILLISECONDS
  Add response delay
  Example: --delay 200

--verbose
  Verbose output
```

#### variables

Extract variables from captures:

```bash
python tracetap-replay.py variables session.json
```

Options:
```bash
--ai
  Use Claude AI for intelligent extraction

-o, --output FILE
  Save to JSON file
```

#### scenario

Generate test scenario:

```bash
python tracetap-replay.py scenario session.json --ai
```

Options:
```bash
--ai
  Use AI to generate scenario

--name NAME
  Scenario name

--intent DESCRIPTION
  What the scenario tests

-o, --output FILE
  Output YAML file
```

### Examples

```bash
# Replay all traffic
python tracetap-replay.py replay api.json --target http://localhost:8080

# Replay with variables
python tracetap-replay.py replay api.json \
  --target http://staging-api.example.com \
  --variables user_id=123 auth_token=abc

# Start mock server
python tracetap-replay.py mock api.json --port 8080

# Mock with chaos engineering
python tracetap-replay.py mock api.json \
  --port 8080 \
  --chaos \
  --chaos-rate 0.2

# Extract variables
python tracetap-replay.py variables api.json --ai

# Generate test scenario
python tracetap-replay.py scenario api.json \
  --ai \
  --intent "User registration flow" \
  -o test-scenario.yaml
```

---

## tracetap-update-collection.py

Update existing Postman collection with new captures.

### Usage

```bash
python tracetap-update-collection.py <existing> <captures> [OPTIONS]
```

### Arguments

```bash
existing
  Existing Postman collection file
  Example: existing-collection.json

captures
  New captures to merge
  Example: new-captures.json
```

### Options

#### Output

```bash
-o, --output FILE
  Output updated collection
  Default: existing_collection_updated.json

--backup
  Create backup of original (default: true)

--no-backup
  Don't create backup
```

#### Matching

```bash
--match-threshold PERCENT
  Similarity threshold for matching requests
  Example: --match-threshold 0.8
  Default: 0.85
```

#### Reporting

```bash
--new-requests
  Show newly added requests

--removed-requests
  Show removed requests

--dry-run
  Show changes without writing file

--report FILE
  Save change report to file
```

#### Preservation

```bash
--preserve-tests
  Keep existing test scripts (default: true)

--no-preserve-tests
  Overwrite test scripts

--preserve-auth
  Keep existing auth settings (default: true)

--no-preserve-auth
  Overwrite auth settings
```

#### Verbosity

```bash
-v, --verbose
  Verbose output

-q, --quiet
  Quiet mode
```

### Examples

```bash
# Basic update
python tracetap-update-collection.py \
  existing-collection.json \
  new-captures.json \
  -o updated-collection.json

# With dry-run to preview
python tracetap-update-collection.py \
  existing-collection.json \
  new-captures.json \
  --dry-run \
  --report changes.json

# Update with reporting
python tracetap-update-collection.py \
  existing-collection.json \
  new-captures.json \
  -o updated-collection.json \
  --report changes.json \
  --new-requests \
  --removed-requests
```

---

## Common Options

### API Key (for AI features)

Set environment variable:

```bash
export ANTHROPIC_API_KEY='sk-ant-...'

# Then use commands with --ai flag
python tracetap-ai-postman.py api.json --infer-flow -o postman.json
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

## Next Steps

- **[Python API](python-api.md)** - Use TraceTap as a library
- **[Guides](../guides/)** - Learn how to use these tools
