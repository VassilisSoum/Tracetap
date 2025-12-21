# TraceTap Complete Guide

**The Complete Reference for HTTP/HTTPS Traffic Capture, AI-Powered API Documentation, Traffic Replay, and Mock Server**

---

## Table of Contents

1. [What is TraceTap?](#what-is-tracetap)
2. [Features](#features)
3. [How TraceTap Works](#how-tracetap-works)
4. [Installation](#installation)
5. [Usage Scenarios](#usage-scenarios)
   - [Scenario 1: Basic Traffic Capture to Postman](#scenario-1-basic-traffic-capture-to-postman)
   - [Scenario 2: Capture with Host Filtering](#scenario-2-capture-with-host-filtering)
   - [Scenario 3: Multi-Format Export](#scenario-3-multi-format-export-postman--openapi--raw)
   - [Scenario 4: AI-Enhanced Postman Collections](#scenario-4-ai-enhanced-postman-collections)
   - [Scenario 5: Generate WireMock Stubs](#scenario-5-generate-wiremock-stubs)
   - [Scenario 6: Regex Filtering](#scenario-6-regex-filtering-for-specific-api-patterns)
   - [Scenario 7: Debug Mode](#scenario-7-debug-mode-with-verbose-output)
   - [Scenario 8: Certificate Management](#scenario-8-certificate-management)
   - [Scenario 9: Traffic Replay](#scenario-9-traffic-replay-to-different-server)
   - [Scenario 10: Mock Server](#scenario-10-mock-server-for-offline-development)
   - [Scenario 11: AI Variable Extraction](#scenario-11-ai-variable-extraction)
   - [Scenario 12: YAML Test Scenarios](#scenario-12-generate-yaml-test-scenarios)
   - [Scenario 13: Chaos Engineering](#scenario-13-mock-server-with-chaos-engineering)
   - [Scenario 14: Playwright Test Generation](#scenario-14-generate-playwright-tests-from-postman-collection)
   - [Scenario 15: Collection Updater](#scenario-15-update-existing-postman-collection)
6. [Command Reference](#command-reference)
7. [Troubleshooting](#troubleshooting)

---

## What is TraceTap?

TraceTap is a comprehensive HTTP/HTTPS traffic capture proxy that records API interactions and exports them to multiple formats. It combines the power of mitmproxy for traffic interception with AI-powered analysis using Claude Sonnet 4.5 to generate intelligent API documentation, organized Postman collections, WireMock stubs, replay captured traffic, and run mock servers.

**Key Use Cases:**
- Document APIs by capturing live traffic
- Generate Postman collections from real user workflows
- Create WireMock stubs for testing and mocking
- Generate Playwright API tests from Postman collections
- Update existing Postman collections with new captures
- Replay production traffic to staging/test environments
- Run mock HTTP servers for offline development
- Extract variables automatically with AI (IDs, tokens, UUIDs)
- Generate YAML test scenarios for integration testing
- Simulate failures and delays with chaos engineering
- Debug integration issues with detailed traffic logs
- Generate OpenAPI specifications automatically

---

## Features

### Core Capture Features

- **HTTP/HTTPS Traffic Capture** - Full proxy capability using mitmproxy
- **Real-Time Monitoring** - Color-coded console output showing captured requests
- **Smart Filtering**:
  - Exact host matching (`api.example.com`)
  - Wildcard matching (`*.example.com`)
  - Regex pattern matching on URLs and hosts
  - OR logic - capture if ANY filter matches
  - Verbose filtering mode for debugging

### Export Formats (3 Formats Supported)

#### 1. Postman Collection v2.1 (`--export`)
- Complete collection format ready to import into Postman
- Preserves headers, request bodies, query parameters
- URL parsing with proper host/path/query structure
- Session metadata and timestamps

#### 2. Raw JSON Log (`--raw-log`)
- Comprehensive JSON log with metadata
- Includes session name, timestamp, filter configuration
- Full request/response headers and bodies
- Duration tracking (milliseconds)
- Queryable format for custom processing

#### 3. OpenAPI 3.0 Specification (`--export-openapi`)
- Automatic API documentation generation
- Path parameter detection (numeric IDs, UUIDs, alphanumeric patterns)
- Endpoint grouping by HTTP method
- Request/response schema inference
- Server URL extraction
- Parameter extraction from query strings

### AI-Powered Features (Requires API Key)

#### 1. AI Postman Collection Generator (`tracetap-ai-postman.py`)
**Powered by Claude Sonnet 4.5**

- **Flow Inference**: Analyzes raw captures to understand user workflows
- **Intelligent Grouping**: Organizes requests into logical folders
- **YAML Flow Specs**: Supports custom flow specifications
- **Smart Deduplication**: Removes duplicate requests intelligently
- **Custom Instructions**: Guide AI with specific organization rules
- **Analysis Export**: Save AI analysis for review

**Features:**
- URLMatcher with multiple strategies (exact, pattern-based)
- RawLogProcessor for efficient log indexing
- Query parameter normalization
- Request sampling for large datasets (max 200 requests)

#### 2. AI WireMock Stub Generator (`tracetap2wiremock.py`)
**Powered by Claude Sonnet 4.5**

- **Dynamic Parameter Detection**: Identifies IDs, tokens, timestamps
- **Multiple URL Matching Strategies**: `url`, `urlPattern`, `urlPath`, `urlPathPattern`
- **Intelligent Priority Assignment**: Based on specificity
- **Flexible Matching**: Request body regex patterns
- **Header Matching**: Configurable header matching
- **Query Parameter Handling**: With ignore lists

#### 3. AI Traffic Replay & Intelligent Mock Server (`tracetap-replay.py`)
**Powered by Claude Sonnet 4.5**

**Replay Features:**
- **Intelligent Traffic Replay**: Replay captured requests to any target server
- **Concurrent Execution**: Configurable workers for parallel replay
- **Variable Substitution**: Dynamic values with JSONPath and regex extraction
- **Performance Metrics**: Response comparison and timing analysis
- **YAML Scenarios**: Configuration-driven test scenarios

**Intelligent Mock Server Features:**
- **AI Semantic Matching**: Understands request intent across different IDs
- **Request Recording**: Capture incoming requests during mock operation
- **Diff Tracking**: Identify mismatches and API changes
- **Match Caching**: Performance optimization with FIFO cache
- **Response Modes**: Static, template, transform, AI, intelligent
- **Chaos Engineering**: Simulate failures, delays, and errors
- **Admin API**: Runtime management and monitoring

**Matching Strategies:**
- **Exact**: Precise URL matching
- **Fuzzy**: Similarity scoring with ID recognition (UUID, numeric, MongoDB ObjectId, ULID, Base64)
- **Pattern**: Wildcard and regex patterns
- **Semantic**: AI-powered intent understanding

**AI-Powered Features:**
- Variable extraction (IDs, tokens, UUIDs, JWTs)
- Scenario generation from captures
- Intelligent response generation
- Request intent analysis

📚 **[See REPLAY.md for detailed documentation](REPLAY.md)**

#### 4. Playwright Test Generator (`tracetap-playwright.py`)
**Powered by Claude Sonnet 4.5**

- **Postman to Playwright Conversion**: Transform Postman collections into TypeScript Playwright tests
- **AI Test Script Conversion**: Automatically converts `pm.test()` assertions to Playwright `expect()` statements
- **Fixture Generation**: Creates authentication and variable fixtures
- **TypeScript Code Generation**: Produces clean, formatted TypeScript test files
- **Variable Extraction**: Detects and extracts response values for chaining tests
- **Folder Structure Preservation**: Maintains Postman folder organization in test suites

**Features:**
- Supports Postman Collection v2.1 format
- Pattern-based fallback when AI unavailable
- Generates complete test files with imports and fixtures
- Configurable output with comments and formatting
- Playwright config template generation

**Conversion Capabilities:**
- HTTP methods: GET, POST, PUT, DELETE, PATCH, etc.
- Headers with variable expansion
- Request bodies (JSON, formdata, urlencoded)
- Authentication (Bearer, API Key)
- Test assertions and validations
- Response variable extraction

### Certificate Management

- **Cross-Platform Support**: Linux, macOS, Windows
- **Automatic Installation**: One-command certificate setup
- **Verification**: Check if certificate is properly installed
- **Python CLI**: Unified interface across platforms

**Platform-Specific Scripts:**
- `chrome-cert-manager.sh` - Linux/Chrome
- `macos-cert-manager.sh` - macOS
- `windows-cert-manager.ps1` - Windows PowerShell

---

## How TraceTap Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         TraceTap System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐     ┌──────────────────┐                    │
│  │  HTTP Client  │────▶│   TraceTap Proxy │                    │
│  │  (Browser,    │     │   (mitmproxy)    │                    │
│  │   curl, etc)  │◀────│   Port 8080      │                    │
│  └───────────────┘     └────────┬─────────┘                    │
│                                 │                               │
│                    ┌────────────▼───────────┐                   │
│                    │  TraceTapAddon         │                   │
│                    │  - Intercepts flows    │                   │
│                    │  - Applies filters     │                   │
│                    │  - Records data        │                   │
│                    └────────┬───────────────┘                   │
│                             │                                   │
│              ┌──────────────┼──────────────┐                    │
│              │              │              │                    │
│         ┌────▼────┐   ┌────▼────┐   ┌────▼────┐               │
│         │ Postman │   │   Raw   │   │ OpenAPI │               │
│         │ Export  │   │   JSON  │   │  3.0    │               │
│         └─────────┘   └─────────┘   └─────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

                              │
                              │ Raw JSON Log
                              ▼
                    ┌──────────────────┐
                    │  AI Enhancement  │
                    │  (Claude Sonnet) │
                    └────────┬─────────┘
                             │
                ┌────────────┼────────────┐
                │                         │
         ┌──────▼────────┐      ┌────────▼────────┐
         │ AI Postman    │      │  WireMock       │
         │ Collection    │      │  Stubs          │
         └───────────────┘      └─────────────────┘
```

### Component Breakdown

#### 1. Core Capture System (`tracetap.py`)
- **Entry Point**: Command-line interface with argument parsing
- **Proxy Server**: mitmproxy-based HTTPS proxy
- **Addon System**: `TraceTapAddon` class intercepts HTTP flows
- **Configuration**: Environment variables for cross-module communication

#### 2. Modular Capture Components (`src/tracetap/capture/`)
- **tracetap_main.py**: Entry point for modular capture system
- **tracetap_addon.py**: mitmproxy addon (response callback, filtering, export)
- **exporters.py**: Three exporter classes (Postman, Raw, OpenAPI)
- **filters.py**: `RequestFilter` class for host/regex filtering
- **utils.py**: Utility functions (safe_body, calc_duration, status_color)

#### 3. AI Processing Layer
- **tracetap-ai-postman.py**: Claude-powered flow analysis and organization
- **tracetap2wiremock.py**: Intelligent WireMock stub generation
- **Model**: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **API**: Anthropic API (requires `ANTHROPIC_API_KEY`)

#### 4. Certificate Management
- **cert_installer.py**: Cross-platform certificate installation library
- **Platform Scripts**: Shell/PowerShell scripts for each OS
- **Certificate Location**: `~/.mitmproxy/mitmproxy-ca-cert.pem`

#### 5. Common Utilities (`src/tracetap/common/`)
- **ai_utils.py**: Centralized AI client initialization
  - Eliminates ~150 lines of duplicate code across 7+ files
  - `create_anthropic_client()` function with standardized error handling
  - Single source of truth for Anthropic client creation
  - Graceful degradation when AI unavailable
  - Security: API key from environment variable only
- **url_utils.py**: URL parsing, normalization, and matching utilities
  - `URLMatcher` class with multiple matching strategies
  - URL normalization with query parameter sorting
  - Flexible URL comparison (strict/fuzzy modes)
  - Eliminates duplicate URL handling code
- **utils.py**: Shared utility functions
  - `filter_interesting_headers()` for security-relevant header filtering
  - Common helper functions used across modules

### Data Flow

1. **Capture Phase**:
   - HTTP client sends request through TraceTap proxy
   - mitmproxy intercepts and decrypts HTTPS traffic
   - `TraceTapAddon.response()` receives complete flow
   - Filters applied (host, wildcard, regex)
   - Record created with request/response data
   - Stored in memory until shutdown

2. **Export Phase** (on Ctrl+C):
   - `TraceTapAddon.done()` triggered
   - Exporters process records based on configured outputs
   - Files written to specified paths

3. **AI Enhancement Phase** (optional):
   - Raw JSON log loaded
   - Sent to Claude API with instructions
   - AI analyzes flows, groups requests, organizes structure
   - Enhanced collection or WireMock stubs generated

---

## Installation

### Prerequisites

- **Python**: 3.8 or higher
- **pip**: Python package installer
- **Git**: For cloning the repository
- **Operating System**: Linux, macOS, or Windows

### Step 1: Clone the Repository

TraceTap is distributed as source code. Clone the repository to get started:

```bash
# Clone the repository
git clone https://github.com/VassilisSoum/tracetap.git
cd tracetap
```

### Step 2: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt
```

**Required Packages:**
- `mitmproxy>=8.0.0,<9.0.0` - HTTP proxy framework
- `anthropic>=0.71.0` - Claude AI API client (for AI features)
- `PyYAML>=6.0` - YAML parsing for flow specs
- `typing-extensions>=4.3,<=4.11.0` - Type hints compatibility

**Optional: Install Replay & Mock Server Dependencies**

```bash
# For traffic replay and mock server features
pip install -r requirements-replay.txt
```

**Replay/Mock Packages:**
- `requests>=2.31.0` - HTTP client for replay
- `fastapi>=0.104.0` - Web framework for mock server
- `uvicorn[standard]>=0.24.0` - ASGI server for FastAPI
- `jsonpath-ng>=1.6.0` - JSONPath for response extraction
- `pytest>=7.4.0` - Testing framework (for tests)

### Step 3: Install Certificate (REQUIRED for HTTPS)

TraceTap requires installing the mitmproxy CA certificate to intercept HTTPS traffic.

#### Option A: Automatic Installation (Recommended)

**Linux/Chrome:**
```bash
bash src/tracetap/scripts/chrome-cert-manager.sh install
```

**macOS:**
```bash
bash src/tracetap/scripts/macos-cert-manager.sh install
```

**Windows (PowerShell as Administrator):**
```powershell
.\src\tracetap\scripts\windows-cert-manager.ps1 -Action install
```

#### Option B: Python CLI (Cross-Platform)

```bash
python src/tracetap/scripts/cert_manager.py install --verbose
```

**Verify Installation:**
```bash
python src/tracetap/scripts/cert_manager.py verify
```

**View Certificate Info:**
```bash
python src/tracetap/scripts/cert_manager.py info
```

### Step 4: Set Up API Key (Optional - for AI Features)

If you want to use AI-powered features:

```bash
# Set environment variable
export ANTHROPIC_API_KEY="your-api-key-here"

# Or add to ~/.bashrc or ~/.zshrc for persistence
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**Get API Key:** Sign up at https://console.anthropic.com/

### Step 5: Verify Installation

```bash
# Test basic capture (should show help)
python tracetap.py --help

# Test AI tools (should show help)
python tracetap-ai-postman.py --help
python tracetap2wiremock.py --help

# Test replay/mock tools (if installed)
python tracetap-replay.py --help
```

---

## Usage Scenarios

### Scenario 1: Basic Traffic Capture to Postman

**Goal**: Capture HTTP/HTTPS traffic and export to Postman Collection

**Steps:**

1. **Start TraceTap proxy:**
```bash
python tracetap.py --listen 8080 --export captures.json --session "API Testing"
```

2. **Configure your HTTP client:**
```bash
# In another terminal
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
```

3. **Make requests:**
```bash
curl -k https://api.example.com/users
curl -k https://api.example.com/products
```

4. **Stop TraceTap** (Ctrl+C):
```
^C
📊 Captured 2 requests
✓ Exported 2 requests → captures.json
```

5. **Import to Postman:**
   - Open Postman
   - File → Import
   - Select `captures.json`

**Output**: `captures.json` - Postman Collection v2.1 format

---

### Scenario 2: Capture with Host Filtering

**Goal**: Capture only requests to specific hosts

**Use Case**: Testing multi-service application, only interested in specific APIs

**Command:**
```bash
# Single host
python tracetap.py --listen 8080 --export api.json --filter-host "api.example.com"

# Multiple hosts
python tracetap.py --listen 8080 --export api.json --filter-host "api.example.com,auth.example.com"

# Wildcard (all subdomains)
python tracetap.py --listen 8080 --export api.json --filter-host "*.example.com"
```

**Example Output:**
```
🔍 Filtering enabled:
   Hosts (1): ['api.example.com']

GET https://api.example.com/users → 200 (45 ms)
POST https://api.example.com/users → 201 (120 ms)
```

**Result**: Only requests matching host filters are captured

---

### Scenario 3: Multi-Format Export (Postman + OpenAPI + Raw)

**Goal**: Generate all three export formats simultaneously

**Use Case**: Complete API documentation and testing suite

**Command:**
```bash
python tracetap.py --listen 8080 \
  --export postman_collection.json \
  --raw-log raw_data.json \
  --export-openapi openapi_spec.json \
  --session "Complete API Capture"
```

**Output Files:**
- `postman_collection.json` - Import to Postman for testing
- `raw_data.json` - Complete data for custom processing
- `openapi_spec.json` - API documentation (OpenAPI 3.0)

**Example Output:**
```
📊 Captured 25 requests
✓ Exported 25 requests → postman_collection.json
✓ Exported raw log (156.4 KB) → raw_data.json
✓ Exported OpenAPI 3.0 spec with 12 endpoints → openapi_spec.json
```

---

### Scenario 4: AI-Enhanced Postman Collections

**Goal**: Use AI to organize and group requests intelligently

**Use Case**: Captured chaotic user session, want organized collection

**Steps:**

1. **Capture raw traffic:**
```bash
python tracetap.py --listen 8080 --raw-log session_capture.json
# ... make requests ...
# Ctrl+C to stop
```

2. **Enhance with AI:**
```bash
python tracetap-ai-postman.py session_capture.json \
  --output enhanced_collection.json \
  --instructions "Group by: Authentication, User Management, Product Catalog. Extract user IDs and product IDs as variables."
```

**Advanced: Save AI Analysis:**
```bash
python tracetap-ai-postman.py session_capture.json \
  --output collection.json \
  --save-analysis analysis.json \
  --instructions "Organize by business flow: Login → Browse → Add to Cart → Checkout"
```

**What AI Does:**
- Analyzes request patterns
- Groups related requests into folders
- Identifies variables (IDs, tokens)
- Removes duplicates intelligently
- Organizes by user workflow or business logic

**Output**: Enhanced Postman collection with intelligent organization

---

### Scenario 5: Generate WireMock Stubs

**Goal**: Create WireMock stubs from captured production traffic

**Use Case**: Local testing without hitting production APIs

**Steps:**

1. **Capture production traffic:**
```bash
python tracetap.py --listen 8080 --raw-log prod_traffic.json \
  --filter-host "api.production.com"
# ... interact with production ...
# Ctrl+C
```

2. **Generate WireMock stubs:**
```bash
python tracetap2wiremock.py prod_traffic.json --output wiremock/mappings/
```

3. **Start WireMock server:**
```bash
cd wiremock
java -jar wiremock-standalone.jar --port 9090
```

4. **Test against WireMock:**
```bash
curl http://localhost:9090/api/users/123
# Returns mocked response from captured data
```

**What Gets Generated:**
- Individual JSON stub files in `wiremock/mappings/`
- Request matching patterns (URL, headers, body)
- Response templates with status codes, headers, bodies
- Priority assignment for specificity

**Example Stub:**
```json
{
  "request": {
    "method": "GET",
    "urlPattern": "/api/users/[0-9]+"
  },
  "response": {
    "status": 200,
    "headers": {
      "Content-Type": "application/json"
    },
    "jsonBody": {
      "id": "123",
      "name": "John Doe"
    }
  },
  "priority": 5
}
```

---

### Scenario 6: Regex Filtering for Specific API Patterns

**Goal**: Capture only requests matching specific URL patterns

**Use Case**: API versioning, only want v2 endpoints

**Commands:**

```bash
# Capture only versioned API endpoints (v1, v2, v3, etc.)
python tracetap.py --listen 8080 --export api.json \
  --filter-regex "/api/v[0-9]+/"

# Capture only GraphQL endpoints
python tracetap.py --listen 8080 --export graphql.json \
  --filter-regex ".*graphql.*"

# Combine host and regex filters (OR logic)
python tracetap.py --listen 8080 --export combined.json \
  --filter-host "example.com" \
  --filter-regex ".*\\.api\\..*"
```

**Filtering Logic:**
- If no filters: captures EVERYTHING
- If filters present: captures if ANY filter matches (OR logic)
- Regex applies to both URL and host

**Verbose Mode** (see what's being filtered):
```bash
python tracetap.py --listen 8080 --export api.json \
  --filter-regex "/api/v2/" \
  --verbose
```

**Output:**
```
🔍 Filtering enabled:
   Regex: /api/v2/

✅ Matched (regex): GET https://api.example.com/api/v2/users
⏭️  Skipping: GET https://api.example.com/api/v1/users
✅ Matched (regex): POST https://api.example.com/api/v2/products
📝 Recorded (2 total): POST https://api.example.com/api/v2/products
```

---

### Scenario 7: Debug Mode with Verbose Output

**Goal**: Troubleshoot filtering issues or understand what's being captured

**Command:**
```bash
python tracetap.py --listen 8080 --export debug.json \
  --filter-host "*.example.com" \
  --verbose
```

**What Verbose Mode Shows:**
- Which filter matched each request
- Skipped requests with reason
- Recording confirmations with running total
- Detailed filtering decisions

**Example Output:**
```
🔍 Filtering enabled:
   Hosts (1): ['*.example.com']

✅ Matched (host wildcard): GET https://api.example.com/users
📝 Recorded (1 total): GET https://api.example.com/users
⏭️  Skipping: GET https://google.com/
✅ Matched (host wildcard): POST https://auth.example.com/login
📝 Recorded (2 total): POST https://auth.example.com/login
```

**Quiet Mode** (opposite - minimal output):
```bash
python tracetap.py --listen 8080 --export api.json --quiet
```

---

### Scenario 8: Certificate Management

**Goal**: Manage mitmproxy CA certificate installation

#### Install Certificate

**Linux:**
```bash
bash src/tracetap/scripts/chrome-cert-manager.sh install
```

**macOS:**
```bash
bash src/tracetap/scripts/macos-cert-manager.sh install
```

**Windows (PowerShell as Admin):**
```powershell
.\src\tracetap\scripts\windows-cert-manager.ps1 -Action install
```

#### Verify Certificate

```bash
python src/tracetap/scripts/cert_manager.py verify
```

**Success Output:**
```
✅ Certificate is properly installed
```

**Failure Output:**
```
❌ Certificate is NOT installed
Run: python src/tracetap/scripts/cert_manager.py install
```

#### View Certificate Information

```bash
python src/tracetap/scripts/cert_manager.py info
```

**Output:**
```
Certificate Information:
  Path: /home/user/.mitmproxy/mitmproxy-ca-cert.pem
  Issuer: mitmproxy
  Valid from: 2025-01-01
  Valid to: 2027-01-01
  Serial: 12345...
```

#### Uninstall Certificate

```bash
python src/tracetap/scripts/cert_manager.py uninstall
```

**Verbose Mode** (troubleshooting):
```bash
python src/tracetap/scripts/cert_manager.py install --verbose
```

---

### Scenario 9: Traffic Replay to Different Server

**Goal**: Replay captured requests to a staging or test server

**Use Case**: Test new server deployment with real production traffic patterns

**Steps:**

1. **Capture production traffic:**
```bash
python tracetap.py --listen 8080 --raw-log prod_traffic.json \
  --filter-host "api.production.com" \
  --session "Production Capture"
```

2. **Replay to staging server:**
```bash
python tracetap-replay.py replay prod_traffic.json \
  --target http://staging-api.example.com \
  --workers 10
```

**Advanced: With Variable Substitution**
```bash
# Extract variables from captures
python tracetap-replay.py variables prod_traffic.json \
  --output variables.json \
  --use-ai

# Replay with new values
python tracetap-replay.py replay prod_traffic.json \
  --target http://staging-api.example.com \
  --variables '{"user_id": "test-user-123", "auth_token": "staging-token"}' \
  --output replay_results.json
```

**Output:**
```
🎬 TraceTap Traffic Replayer
📂 Loaded 150 captures from prod_traffic.json
🎯 Target: http://staging-api.example.com
⚙️  Workers: 10

Replaying... ████████████████████ 150/150 (100%)

✅ Replay Summary:
   Total Requests:       150
   Successful:           148 (98.7%)
   Failed:               2 (1.3%)
   Status Matches:       145 (96.7%)

   Performance:
   Avg Duration:         125ms (original: 150ms)
   Total Time:           18.5s

📊 Saved detailed metrics → replay_results.json
```

**What Happens:**
- Original request URLs are mapped to target server
- Query parameters and paths preserved
- Performance metrics collected
- Status code comparison (original vs replayed)
- Variable substitution for dynamic values

---

### Scenario 10: Mock Server for Offline Development

**Goal**: Start HTTP mock server serving captured responses

**Use Case**: Frontend development without backend, offline testing, demo environments

**Steps:**

1. **Capture real API traffic:**
```bash
python tracetap.py --listen 8080 --raw-log api_captures.json \
  --filter-host "api.example.com"
# ... interact with API ...
# Ctrl+C
```

2. **Start mock server:**
```bash
python tracetap-replay.py mock api_captures.json \
  --host 0.0.0.0 \
  --port 8080 \
  --strategy fuzzy
```

**Console Output:**
```
🚀 TraceTap Mock Server starting...
   Host: 0.0.0.0:8080
   Captures loaded: 45
   Matching strategy: fuzzy
   Admin API: http://0.0.0.0:8080/__admin__/metrics
```

3. **Test the mock server:**
```bash
# Original request
curl http://localhost:8080/api/users/123

# Returns captured response
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com"
}

# Even works with different IDs (fuzzy matching)
curl http://localhost:8080/api/users/999
# Still returns a user response!
```

4. **Monitor with Admin API:**
```bash
# View metrics
curl http://localhost:8080/__admin__/metrics

{
  "total_requests": 15,
  "matched_requests": 14,
  "unmatched_requests": 1,
  "match_rate": 93.33,
  "uptime_seconds": 125.4
}

# List captured endpoints
curl http://localhost:8080/__admin__/captures

# Update configuration at runtime
curl -X POST http://localhost:8080/__admin__/config \
  -H "Content-Type: application/json" \
  -d '{"add_delay_ms": 100, "chaos_enabled": true}'
```

**Matching Strategies:**
- **exact**: Only exact URL matches
- **fuzzy** (default): Similarity scoring, works with different IDs
- **pattern**: Wildcard and regex patterns

**Configuration Options:**
```bash
# Add response delay
python tracetap-replay.py mock api_captures.json --delay 50

# Enable chaos engineering (10% failure rate)
python tracetap-replay.py mock api_captures.json \
  --chaos \
  --chaos-rate 0.1 \
  --chaos-status 503

# Custom fallback for unmatched requests
python tracetap-replay.py mock api_captures.json \
  --fallback-status 503 \
  --fallback-body '{"error": "Service unavailable"}'
```

**Intelligent Mock Server Features:**

The mock server includes several AI-powered and intelligent features for enhanced development and debugging:

**1. AI-Powered Semantic Matching** (`--ai`)
```bash
# Enable semantic matching using Claude Sonnet 4.5
python tracetap-replay.py mock api_captures.json \
  --strategy semantic \
  --ai \
  --api-key sk-ant-xxx

# Console output
🤖 AI features enabled
💾 Match caching enabled (max size: 1000)
```

Semantic matching understands request intent, not just URL patterns:
- Matches `/users/123` with `/users/999` because both are "get user" requests
- Works across different ID formats (UUID, numeric, MongoDB ObjectId)
- Ideal for dynamic APIs where IDs change frequently

**2. Request Recording** (`--record`)
```bash
# Record all incoming requests during mock operation
python tracetap-replay.py mock api_captures.json \
  --record \
  --record-limit 1000

# View recordings
curl http://localhost:8080/__admin__/recordings

{
  "total": 15,
  "limit": 1000,
  "recording_enabled": true,
  "recordings": [
    {
      "timestamp": "2024-01-15T10:30:00",
      "method": "GET",
      "url": "/api/users/123",
      "matched": true,
      "matched_url": "https://api.example.com/users/123",
      "response_status": 200
    }
  ]
}

# Export recordings in TraceTap format
curl http://localhost:8080/__admin__/recordings/export > new_captures.json

# Clear recordings
curl -X DELETE http://localhost:8080/__admin__/recordings
```

**Use Cases for Recording:**
- Debug what your application actually sends
- Capture new API interactions while developing
- Compare expected vs actual requests
- Regression testing with request replay

**3. Request Diff Tracking** (`--diff`)
```bash
# Track diffs for requests that don't match well
python tracetap-replay.py mock api_captures.json \
  --diff \
  --diff-threshold 0.8 \
  --diff-limit 100

# View diffs
curl http://localhost:8080/__admin__/diffs

{
  "diff_enabled": true,
  "threshold": 0.8,
  "total": 3,
  "diffs": [
    {
      "timestamp": "2024-01-15T10:30:00",
      "incoming_url": "/api/orders/new-endpoint",
      "best_match_url": "/api/orders/123",
      "match_score": 0.65,
      "diff": "Path changed: orders/123 -> orders/new-endpoint"
    }
  ]
}

# Get latest diff
curl http://localhost:8080/__admin__/diffs/latest
```

**Use Cases for Diff Tracking:**
- Identify API breaking changes
- Debug why requests don't match
- Find missing endpoints in captures
- Validate API contract compliance

**4. Match Caching** (Enabled by default)
```bash
# Caching is on by default for performance
python tracetap-replay.py mock api_captures.json

# Disable caching if needed
python tracetap-replay.py mock api_captures.json --no-cache

# Customize cache size
python tracetap-replay.py mock api_captures.json --cache-size 5000

# View cache statistics
curl http://localhost:8080/__admin__/cache

{
  "enabled": true,
  "max_size": 1000,
  "current_size": 234,
  "hits": 1520,
  "misses": 450,
  "hit_rate": 0.771
}

# Clear cache
curl -X DELETE http://localhost:8080/__admin__/cache
```

**Performance Impact:**
- 70%+ hit rate typical for polling/health checks
- Sub-millisecond response for cache hits
- FIFO eviction when cache is full

**5. Response Modes** (`--response-mode`)
```bash
# Static: Return captured responses as-is (default)
python tracetap-replay.py mock api_captures.json --response-mode static

# Template: Apply basic templating
python tracetap-replay.py mock api_captures.json --response-mode template

# Transform: Apply transformations to responses
python tracetap-replay.py mock api_captures.json --response-mode transform

# AI: Intelligent response generation
python tracetap-replay.py mock api_captures.json --response-mode ai --ai

# Intelligent: AI decides best approach
python tracetap-replay.py mock api_captures.json --response-mode intelligent --ai
```

**Complete Example - Production-Ready Mock Server:**
```bash
python tracetap-replay.py mock prod_captures.json \
  --strategy semantic \
  --ai \
  --api-key $ANTHROPIC_API_KEY \
  --record \
  --record-limit 10000 \
  --diff \
  --diff-threshold 0.7 \
  --response-mode intelligent \
  --delay 50 \
  --chaos \
  --chaos-rate 0.05 \
  --host 0.0.0.0 \
  --port 8080

# Console output
🎭 TraceTap Mock Server
🤖 AI features enabled
📹 Request recording enabled (limit: 10000)
🔍 Diff tracking enabled (threshold: 0.7, limit: 100)
💾 Match caching enabled (max size: 1000)

🚀 TraceTap Mock Server starting...
   Host: 0.0.0.0:8080
   Captures loaded: 450
   Matching strategy: semantic
   Admin API: http://0.0.0.0:8080/__admin__/metrics
```

**Admin API Endpoints Summary:**
```
GET    /__admin__/metrics       - Server metrics and statistics
GET    /__admin__/config        - Current configuration
POST   /__admin__/config        - Update configuration
GET    /__admin__/captures      - List all captures
POST   /__admin__/reset         - Reset metrics

GET    /__admin__/recordings    - View recorded requests
DELETE /__admin__/recordings    - Clear recordings
GET    /__admin__/recordings/export - Export as TraceTap JSON

GET    /__admin__/diffs         - View request diffs
DELETE /__admin__/diffs         - Clear diffs
GET    /__admin__/diffs/latest  - Get most recent diff

GET    /__admin__/cache         - Cache statistics
DELETE /__admin__/cache         - Clear cache
POST   /__admin__/replay        - Replay recorded requests
```

---

### Scenario 11: AI Variable Extraction

**Goal**: Automatically detect and extract dynamic values from captured traffic

**Use Case**: Identify variables for replay configuration, create reusable test templates

**Command:**
```bash
python tracetap-replay.py variables session_capture.json \
  --use-ai \
  --output detected_variables.json \
  --verbose
```

**Output:**
```
🔍 TraceTap Variable Extractor
📂 Loaded 50 captures
🤖 Using AI-powered extraction with Claude Sonnet 4.5

Analyzing traffic patterns...

✨ Detected Variables:

📍 user_id
   Type: integer
   Locations: url_path, response_body
   Examples: 123, 456, 789, 12345
   Pattern: \d+
   Description: User identifier in API paths

🔑 auth_token
   Type: jwt
   Locations: header (Authorization)
   Examples: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   Pattern: eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*
   Description: JWT authentication token in Bearer format

🆔 order_id
   Type: uuid
   Locations: url_path, request_body
   Examples: 550e8400-e29b-41d4-a716-446655440000
   Pattern: [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}
   Description: Order UUID identifier

⏰ timestamp
   Type: timestamp
   Locations: request_body, response_body
   Examples: 2024-01-15T10:30:00, 2024-01-16T14:22:35
   Pattern: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}
   Description: ISO 8601 timestamp

📊 Extracted 4 variables
💾 Saved to detected_variables.json
```

**Without AI (Regex-based):**
```bash
# Faster, pattern-based extraction
python tracetap-replay.py variables session_capture.json \
  --output variables.json
```

**Detected Variable Types:**
- Numeric IDs (`\d+`)
- UUIDs (`550e8400-e29b-41d4-a716-446655440000`)
- JWT tokens (`eyJhbGc...`)
- ISO timestamps (`2024-01-15T10:30:00`)
- Unix timestamps (`1640995200`)
- API keys (`sk_live_...`)

**Use Variables in Replay:**
```bash
# Load detected variables
cat detected_variables.json | jq '.[] | {(.name): .example_values[0]}'

# Replay with substitution
python tracetap-replay.py replay session_capture.json \
  --target http://localhost:8080 \
  --variables '{"user_id": "999", "auth_token": "test-token-123"}'
```

---

### Scenario 12: Generate YAML Test Scenarios

**Goal**: Create declarative, reusable test scenarios from captured traffic

**Use Case**: API integration testing, CI/CD pipeline tests, scenario-driven testing

**Steps:**

1. **Capture user workflow:**
```bash
python tracetap.py --listen 8080 --raw-log workflow.json \
  --session "User Registration Flow"
# ... perform: register → verify → login ...
# Ctrl+C
```

2. **Generate YAML scenario with AI:**
```bash
python tracetap-replay.py scenario workflow.json \
  --intent "Test user registration and email verification flow" \
  --name "User Registration Test" \
  --output test_scenario.yaml \
  --use-ai
```

**Generated YAML (`test_scenario.yaml`):**
```yaml
name: "User Registration Test"
description: "Test user registration and email verification flow"
environment: staging

variables:
  base_url: "https://api.example.com"
  test_email: "test+${timestamp}@example.com"

environments:
  staging:
    base_url: "https://staging-api.example.com"
  production:
    base_url: "https://api.example.com"

steps:
  - id: register
    name: "Register new user"
    request:
      method: POST
      url: "${base_url}/users"
      headers:
        Content-Type: "application/json"
      body: '{"email": "${test_email}", "password": "Test123!"}'
    expect:
      status: 201
      body_contains:
        - "id"
        - "email"
      response_time_ms: "< 500"
    extract:
      user_id: "$.id"
      verification_token: "$.verification_token"
    retry: 2
    timeout: 30

  - id: verify_email
    name: "Verify user email"
    request:
      method: POST
      url: "${base_url}/users/${step.register.user_id}/verify"
      body: '{"token": "${step.register.verification_token}"}'
    expect:
      status: 200
      body_contains:
        - "verified"
        - "true"
    retry: 1

  - id: login
    name: "Login with verified user"
    request:
      method: POST
      url: "${base_url}/auth/login"
      body: '{"email": "${test_email}", "password": "Test123!"}'
    expect:
      status: 200
      headers:
        Content-Type: "application/json"
    extract:
      access_token: "$.access_token"
```

3. **Run the scenario:**
```bash
python tracetap-replay.py replay workflow.json \
  --scenario test_scenario.yaml \
  --environment staging \
  --verbose
```

**Output:**
```
🎬 Running Scenario: User Registration Test
📍 Environment: staging

Step 1/3: Register new user
  POST https://staging-api.example.com/users
  ✅ Status: 201 (expected: 201)
  ✅ Body contains: id, email
  ✅ Response time: 245ms (< 500ms)
  📤 Extracted: user_id=12345, verification_token=abc...

Step 2/3: Verify user email
  POST https://staging-api.example.com/users/12345/verify
  ✅ Status: 200 (expected: 200)
  ✅ Body contains: verified, true

Step 3/3: Login with verified user
  POST https://staging-api.example.com/auth/login
  ✅ Status: 200 (expected: 200)
  ✅ Header: Content-Type=application/json
  📤 Extracted: access_token=eyJhbGc...

✅ Scenario completed: 3/3 steps passed
```

**YAML Features:**
- **Variable resolution**: `${var}`, `${env.VAR}`, `${step.id.var}`
- **Response extraction**: JSONPath (`$.data.id`) and Regex (`regex:pattern`)
- **Assertions**: Status codes, headers, body content, response time
- **Step dependencies**: Use extracted values from previous steps
- **Environments**: Switch between staging/production configurations
- **Retry logic**: Automatic retry on failure

---

### Scenario 13: Mock Server with Chaos Engineering

**Goal**: Test application resilience with simulated failures and delays

**Use Case**: Chaos testing, fault injection, latency simulation, reliability testing

**Steps:**

1. **Start mock server with chaos mode:**
```bash
python tracetap-replay.py mock api_captures.json \
  --port 8080 \
  --chaos \
  --chaos-rate 0.2 \
  --chaos-status 500 \
  --delay 100
```

**Console Output:**
```
🚀 TraceTap Mock Server starting...
   Host: 127.0.0.1:8080
   Captures loaded: 50
   Matching strategy: fuzzy
   Admin API: http://127.0.0.1:8080/__admin__/metrics
   ⚠️  Chaos mode enabled (20% failure rate)
```

2. **Test application behavior:**
```bash
# Some requests succeed with delay
curl http://localhost:8080/api/users/123
# 100ms delay + normal response

# Some requests fail (20% chance)
curl http://localhost:8080/api/products/456
# {"error": "Chaos engineering failure"}
# HTTP 500
```

3. **Dynamic configuration via Admin API:**
```bash
# Increase failure rate to 50%
curl -X POST http://localhost:8080/__admin__/config \
  -H "Content-Type: application/json" \
  -d '{"chaos_enabled": true, "chaos_failure_rate": 0.5}'

# Add random delay (100-500ms)
curl -X POST http://localhost:8080/__admin__/config \
  -H "Content-Type: application/json" \
  -d '{"add_delay_ms": 0, "random_delay_range": [100, 500]}'

# Disable chaos mode
curl -X POST http://localhost:8080/__admin__/config \
  -H "Content-Type: application/json" \
  -d '{"chaos_enabled": false}'
```

4. **Monitor metrics:**
```bash
curl http://localhost:8080/__admin__/metrics
```

**Output:**
```json
{
  "total_requests": 100,
  "matched_requests": 95,
  "unmatched_requests": 5,
  "chaos_failures": 18,
  "match_rate": 95.0,
  "uptime_seconds": 245.5,
  "start_time": "2025-12-08T10:30:00"
}
```

**Chaos Configuration Options:**

| Option | Description | Example |
|--------|-------------|---------|
| `--chaos` | Enable chaos engineering | Flag (no value) |
| `--chaos-rate` | Failure probability (0.0-1.0) | `0.1` = 10% failures |
| `--chaos-status` | HTTP status for failures | `500`, `503`, `504` |
| `--delay` | Fixed delay in milliseconds | `100` = 100ms delay |
| `--random-delay` | Random delay range | `100,500` = 100-500ms |

**Advanced: Custom Response Transformers**
```python
# Create custom mock server with transformers
from src.tracetap.mock import MockServer, MockConfig
from src.tracetap.mock.generator import add_timestamp, replace_ids

config = MockConfig(
    matching_strategy='fuzzy',
    chaos_enabled=True,
    chaos_failure_rate=0.15,
    add_delay_ms=50
)

server = MockServer('api_captures.json', config=config)

# Apply response transformers
from src.tracetap.mock.generator import ResponseGenerator

generator = ResponseGenerator(
    use_ai=False,
    default_transformers=[add_timestamp, replace_ids]
)

server.generator = generator
server.start()
```

**Use Cases:**
- **Latency Testing**: Simulate slow networks or overloaded services
- **Error Handling**: Verify application handles 500/503 errors gracefully
- **Retry Logic**: Test exponential backoff and retry mechanisms
- **Circuit Breakers**: Trigger circuit breaker patterns
- **Load Testing**: Combine with load testing tools for realistic scenarios

---

### Scenario 14: Generate Playwright Tests from Postman Collection

**Goal**: Convert Postman collection to automated Playwright API tests

**Use Case**: Automate API testing by generating TypeScript test suite from Postman collections or captured traffic

**Steps:**

1. **Capture or obtain Postman collection:**
```bash
# Option A: Capture traffic to Postman collection
python tracetap.py --listen 8080 --export my_api.json --session "API Testing"
# ... make API requests ...
# Ctrl+C

# Option B: Use existing Postman collection
# Export from Postman: File → Export → Collection v2.1
```

2. **Generate Playwright tests:**
```bash
python tracetap-playwright.py my_api.json --output tests/
```

**Console Output:**
```
==================================================
TraceTap Playwright Test Generator
==================================================

Input: my_api.json
Output: tests/
AI Conversion: Enabled

🔍 Parsing Postman collection...
✓ Found 12 requests
✓ Folder structure: 3 folders

🔄 Converting requests to Playwright tests...
📝 Converting test scripts...
   ✓ Converted 8 test scripts with AI
   ⚠  2 scripts marked for manual review
🔧 Generating fixtures...
   ✓ Generated 3 fixtures (baseUrl, authToken, userId)
📄 Generating TypeScript test file...

==================================================
✅ Generation Complete!
==================================================

Generated: tests/my-api.spec.ts
   Tests: 12
   Fixtures: 3
   Folders: 3

📖 Next Steps:
1. Install Playwright: npm install -D @playwright/test
2. Review generated tests and adjust as needed
3. Set environment variables (BASE_URL, AUTH_TOKEN, etc.)
4. Run tests: npx playwright test
```

3. **Review generated test file** (`tests/my-api.spec.ts`):

```typescript
/**
 * Playwright API Tests
 * Generated from Postman Collection: My API
 * Generated on: 2025-12-21 14:30:00
 */

import { test as base, expect } from '@playwright/test';

// Custom fixtures for authentication and variables
type CustomFixtures = {
  baseUrl: string;
  authToken: string;
  userId: string;
};

const test = base.extend<CustomFixtures>({
  baseUrl: async ({}, use) => {
    const url = process.env.BASE_URL || 'https://api.example.com';
    await use(url);
  },

  authToken: async ({ request, baseUrl }, use) => {
    // Option 1: Use environment variable
    if (process.env.AUTH_TOKEN) {
      await use(process.env.AUTH_TOKEN);
      return;
    }

    // Option 2: Perform login to get token
    const response = await request.post(`${baseUrl}/auth/login`, {
      data: { username: 'testuser', password: 'testpass' }
    });
    const data = await response.json();
    await use(data.token);
  },

  userId: async ({}, use) => {
    await use(process.env.USER_ID || '12345');
  }
});

// Main test suite
test.describe('My API', () => {

  test.describe('Authentication', () => {

    test('Login with valid credentials', async ({ request, baseUrl }) => {
      const response = await request.post(`${baseUrl}/auth/login`, {
        headers: { 'Content-Type': 'application/json' },
        data: {
          "username": "testuser",
          "password": "testpass"
        }
      });

      // Assertions converted from Postman test scripts
      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data.token).toBeTruthy();
      expect(data.token).toMatch(/^eyJ/); // JWT format

      // Extract token for use in subsequent tests
      const authToken = data.token;
    });

  });

  test.describe('Users', () => {

    test('Get user profile', async ({ request, baseUrl, authToken, userId }) => {
      const response = await request.get(`${baseUrl}/users/${userId}`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      expect(response.status()).toBe(200);

      const user = await response.json();
      expect(user.id).toBe(parseInt(userId));
      expect(user.email).toMatch(/^[^@]+@[^@]+$/);
    });

    test('Update user profile', async ({ request, baseUrl, authToken, userId }) => {
      const response = await request.put(`${baseUrl}/users/${userId}`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        data: {
          "name": "Updated Name",
          "email": "updated@example.com"
        }
      });

      expect(response.status()).toBe(200);
    });

  });

});
```

4. **Install Playwright (if not already installed):**
```bash
cd tests/
npm init -y
npm install -D @playwright/test
```

5. **Set environment variables:**
```bash
export BASE_URL=https://api.staging.com
export AUTH_TOKEN=your-test-token-here
export USER_ID=12345
```

**Or create `.env` file:**
```bash
BASE_URL=https://api.staging.com
AUTH_TOKEN=your-test-token-here
USER_ID=12345
```

6. **Run the tests:**
```bash
npx playwright test
```

**Output:**
```
Running 12 tests using 4 workers

  ✓  my-api.spec.ts:45:3 › My API › Authentication › Login (234ms)
  ✓  my-api.spec.ts:62:3 › My API › Users › Get user profile (145ms)
  ✓  my-api.spec.ts:78:3 › My API › Users › Update user profile (198ms)
  ✓  my-api.spec.ts:95:3 › My API › Products › List products (167ms)
  ...

  12 passed (1.2s)
```

7. **Run specific tests or with options:**
```bash
# Run only Authentication tests
npx playwright test --grep "Authentication"

# Run with verbose output
npx playwright test --reporter=list

# Generate HTML report
npx playwright test --reporter=html

# Run in headed mode (see browser for UI tests)
npx playwright test --headed

# Run with specific number of workers
npx playwright test --workers=1
```

**Advanced: Generate Playwright config template**
```bash
python tracetap-playwright.py --config-template > playwright.config.ts
```

**Generated Config:**
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',

  // API testing doesn't need browser
  use: {
    baseURL: process.env.BASE_URL || 'https://api.example.com',
    extraHTTPHeaders: {
      // Add any default headers here
    },
  },

  // Timeouts
  timeout: 30000,
  expect: {
    timeout: 5000,
  },

  // Reporters
  reporter: [
    ['html'],
    ['list'],
  ],

  // Run tests in parallel
  workers: process.env.CI ? 1 : undefined,
});
```

**Without AI (Pattern-Based Conversion):**
```bash
# Faster conversion using pattern matching instead of AI
python tracetap-playwright.py my_api.json --output tests/ --no-ai
```

**What Gets Generated:**

✅ **Complete TypeScript test file** with:
- Import statements for Playwright
- Custom fixtures for authentication and variables
- Test suites organized by folder structure
- Converted test assertions
- Variable extractions for test chaining
- Proper TypeScript formatting

✅ **AI-Powered Conversion**:
- Postman `pm.test()` → Playwright `expect()`
- `pm.response.to.have.status(200)` → `expect(response.status()).toBe(200)`
- `pm.expect(data).to.exist` → `expect(data).toBeTruthy()`
- `pm.collectionVariables.set()` → Variable extraction

✅ **Fixture Generation**:
- Base URL fixture from environment
- Authentication tokens (with login template)
- Custom variables used in requests

**Use Cases:**

1. **API Test Automation:**
   - Capture real API workflows
   - Generate automated regression tests
   - Run in CI/CD pipelines

2. **Postman to Code:**
   - Convert manual Postman tests to automated code
   - Version control your API tests
   - Share test suites across teams

3. **Documentation as Code:**
   - Tests serve as executable API documentation
   - Keep tests in sync with API changes
   - Validate API contracts automatically

4. **Integration Testing:**
   - Test API endpoints in isolation
   - Chain requests with variable extraction
   - Validate response schemas and data

**Limitations:**

- Requires Postman Collection v2.1 format
- Complex JavaScript in test scripts may need manual review
- Browser UI automation not supported (API tests only)
- Some authentication methods may require customization

**Complete Workflow Example:**

```bash
# 1. Capture API traffic
python tracetap.py --listen 8080 --export api_capture.json

# 2. Generate Playwright tests
python tracetap-playwright.py api_capture.json --output playwright-tests/

# 3. Setup Playwright
cd playwright-tests/
npm init -y
npm install -D @playwright/test

# 4. Configure environment
echo "BASE_URL=https://api.staging.com" > .env
echo "AUTH_TOKEN=staging-token" >> .env

# 5. Run tests
npx playwright test

# 6. View HTML report
npx playwright show-report
```

---

### Scenario 15: Update Existing Postman Collection

**Goal**: Update an existing Postman collection with data from new captures while preserving customizations

**Use Case**: Keep collections up-to-date with latest API changes while maintaining test scripts, descriptions, and authentication settings added by users

**Steps:**

1. **You have an existing Postman collection with customizations:**
```json
// existing_collection.json
{
  "info": { "name": "My API" },
  "item": [
    {
      "name": "Get User",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/users/123"
      },
      "event": [{
        "listen": "test",
        "script": {
          "exec": [
            "pm.test('Status is 200', function() {",
            "  pm.response.to.have.status(200);",
            "});"
          ]
        }
      }]
    }
  ]
}
```

2. **Capture new API traffic:**
```bash
python tracetap.py --listen 8080 --export new_captures.json
# ... make API requests with updated endpoints ...
# Ctrl+C
```

3. **Preview changes with dry run:**
```bash
python tracetap-update-collection.py existing_collection.json new_captures.json --dry-run
```

**Output:**
```
==================================================
TraceTap Collection Updater - Dry Run Mode
==================================================

📂 Existing collection: existing_collection.json
   Requests: 12
   Variables: 3

📥 New captures: new_captures.json
   Captured requests: 15

🔍 Analyzing changes...

==================================================
📊 Update Summary
==================================================

✨ New Requests (3):
   + POST /users          - Create new user
   + GET /users/456/posts - Get user posts
   + DELETE /users/789    - Delete user

🔄 Updated Requests (9):
   ~ GET /users/123       - URL parameters changed
   ~ POST /auth/login     - Request body updated
   ~ PUT /users/123       - New header: X-API-Version

📍 Unchanged (0):
   (all requests have updates)

⚠️  Requests not in captures (3):
   ! GET /old-endpoint    - Will be deprecated (add description)
   ! POST /legacy-api     - Will be deprecated (add description)

==================================================
Preserved Customizations:
==================================================

✓ Test scripts: 8 requests
✓ Descriptions: 5 requests
✓ Authentication: Bearer token configuration
✓ Variables: baseUrl, userId, authToken

==================================================
💡 Next Steps:
==================================================

To apply these changes, run without --dry-run:
   python tracetap-update-collection.py existing_collection.json new_captures.json

Backup will be created: existing_collection.backup.json
```

4. **Apply the update:**
```bash
python tracetap-update-collection.py existing_collection.json new_captures.json
```

**Output:**
```
==================================================
TraceTap Collection Updater
==================================================

📂 Loading existing collection...
   ✓ Loaded 12 requests from existing_collection.json

📥 Loading new captures...
   ✓ Loaded 15 requests from new_captures.json

🔍 Matching requests...
   ✓ Matched 9 existing requests
   ✓ Found 3 new requests
   ✓ Found 3 removed requests

💾 Creating backup...
   ✓ Saved backup to existing_collection.backup.json

🔄 Updating collection...
   ✓ Updated 9 requests
   ✓ Added 3 new requests
   ✓ Deprecated 3 removed requests
   ✓ Preserved 8 test scripts
   ✓ Preserved 5 descriptions
   ✓ Preserved authentication config

✅ Collection updated successfully!
   Output: existing_collection.json

Summary:
   Updated: 9 requests
   Added: 3 requests
   Deprecated: 3 requests
   Total: 15 requests
```

5. **Review the updated collection:**
```json
// existing_collection.json (after update)
{
  "info": { "name": "My API" },
  "item": [
    {
      "name": "Get User",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/users/123"  // Updated URL from captures
      },
      "event": [{
        "listen": "test",
        "script": {
          "exec": [
            "pm.test('Status is 200', function() {",
            "  pm.response.to.have.status(200);",
            "});"  // Test script PRESERVED
          ]
        }
      }]
    },
    {
      "name": "Create new user",  // NEW REQUEST
      "request": {
        "method": "POST",
        "url": "{{baseUrl}}/users"
      }
    },
    {
      "name": "Get old endpoint",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/old-endpoint"
      },
      "description": "⚠️ DEPRECATED: Not found in recent captures"  // Auto-added
    }
  ]
}
```

6. **Generate detailed report:**
```bash
python tracetap-update-collection.py existing_collection.json new_captures.json \
  --report update_report.json
```

**Report Contents:**
```json
{
  "timestamp": "2025-12-21T15:30:00",
  "existing_collection": "existing_collection.json",
  "new_captures": "new_captures.json",
  "statistics": {
    "existing_requests": 12,
    "captured_requests": 15,
    "matched": 9,
    "new": 3,
    "removed": 3,
    "updated": 9
  },
  "changes": [
    {
      "request": "GET /users/123",
      "action": "updated",
      "changes": ["url_parameters", "headers"],
      "preserved": ["test_script", "description"]
    }
  ],
  "preserved_customizations": {
    "test_scripts": 8,
    "descriptions": 5,
    "auth_config": true
  }
}
```

**Configuration Options:**

```bash
# Custom match threshold (default: 0.75)
python tracetap-update-collection.py existing.json captures.json \
  --match-threshold 0.85

# Handle new requests differently
python tracetap-update-collection.py existing.json captures.json \
  --new-requests ignore  # Options: add (default), prompt, ignore

# Handle removed requests differently
python tracetap-update-collection.py existing.json captures.json \
  --removed-requests keep  # Options: deprecate (default), archive, keep

# Don't create backup
python tracetap-update-collection.py existing.json captures.json \
  --no-backup

# Custom output file
python tracetap-update-collection.py existing.json captures.json \
  -o updated_collection.json
```

**What Gets Preserved:**

✅ **Always Preserved:**
- Test scripts (`pm.test()` blocks)
- Pre-request scripts
- Request descriptions
- Authentication settings
- Collection variables
- Folder structure

✅ **Updated from Captures:**
- Request URLs
- HTTP methods
- Headers
- Request bodies
- Query parameters

**Use Cases:**

1. **API Evolution Tracking:**
   - Capture latest API behavior
   - Update collection automatically
   - Maintain test suite integrity

2. **Team Collaboration:**
   - Developers update API
   - QA adds test scripts
   - Collection stays synchronized

3. **Documentation Maintenance:**
   - Keep descriptions and examples current
   - Track deprecated endpoints
   - Document API changes

4. **CI/CD Integration:**
   - Automated collection updates
   - Regression detection
   - API contract validation

**Matching Algorithm:**

The updater uses intelligent matching:
- **URL Pattern Matching**: Handles dynamic IDs (123 vs 456)
- **Similarity Scoring**: Fuzzy matching for changed endpoints
- **Confidence Threshold**: Adjustable (default: 0.75)

**Example Matches:**
- `GET /users/123` matches `GET /users/456` (different ID)
- `GET /api/v1/users` matches `GET /api/v2/users` (version change)
- `POST /login` matches `POST /auth/login` (path change, high similarity)

**Conflict Resolution:**

```bash
# If automatic matching is uncertain:
python tracetap-update-collection.py existing.json captures.json

# Console output:
⚠️  Uncertain matches found (confidence < 0.75):
   ? GET /users/profile vs GET /users/me (score: 0.65)

   Options:
   1. Accept match (merge requests)
   2. Keep separate (treat as different requests)
   3. Skip this request

   Choice [1/2/3]: _
```

**Complete Workflow:**

```bash
# 1. Initial capture
python tracetap.py --listen 8080 --export initial_collection.json

# 2. Add customizations in Postman (tests, descriptions, auth)

# 3. API evolves over time...

# 4. Capture new traffic
python tracetap.py --listen 8080 --export new_captures.json

# 5. Preview changes
python tracetap-update-collection.py initial_collection.json new_captures.json --dry-run

# 6. Apply update
python tracetap-update-collection.py initial_collection.json new_captures.json

# 7. Import updated collection to Postman
# All your tests and customizations are preserved!
```

**Limitations:**

- Requires valid Postman Collection v2.1 format
- Can't detect renamed endpoints automatically (relies on similarity)
- Complex folder reorganizations may need manual review
- Backup recommended (enabled by default)

---

## Command Reference

### Main Capture Tool: `tracetap.py`

```
Usage: python tracetap.py [OPTIONS]

Options:
  --listen PORT              Port to listen on (default: 8080)
  --export PATH              Export Postman collection to PATH
  --raw-log PATH             Export raw JSON log to PATH
  --export-openapi PATH      Export OpenAPI 3.0 spec to PATH
  --session NAME             Session name for collection (default: tracetap-session)
  --filter-host HOSTS        Comma-separated hosts (supports wildcards)
  --filter-regex PATTERN     Regex pattern for URL/host matching
  --quiet                    Suppress console output
  --verbose                  Show detailed filtering info

Examples:
  python tracetap.py --listen 8080 --export api.json
  python tracetap.py --listen 8080 --filter-host "*.example.com"
  python tracetap.py --listen 8080 --export api.json --raw-log raw.json --export-openapi spec.json
```

### AI Postman Generator: `tracetap-ai-postman.py`

```
Usage: python tracetap-ai-postman.py <raw_log.json> [OPTIONS]

Required:
  raw_log.json               Raw JSON log from tracetap.py --raw-log

Options:
  --output PATH              Output Postman collection path
  --flow PATH                YAML flow specification file
  --instructions TEXT        Custom AI instructions for organization
  --save-analysis PATH       Save AI analysis to file
  --api-key KEY              Anthropic API key (or set ANTHROPIC_API_KEY env)

Examples:
  python tracetap-ai-postman.py capture.json --output enhanced.json
  python tracetap-ai-postman.py capture.json --output api.json --instructions "Group by resource type"
  python tracetap-ai-postman.py capture.json --save-analysis analysis.json
```

### WireMock Generator: `tracetap2wiremock.py`

```
Usage: python tracetap2wiremock.py <raw_log.json> [OPTIONS]

Required:
  raw_log.json               Raw JSON log from tracetap.py --raw-log

Options:
  --output DIR               Output directory for WireMock mappings
  --flow FLOW.yaml           Optional flow specification

Examples:
  python tracetap2wiremock.py capture.json --output wiremock/mappings/
  python tracetap2wiremock.py capture.json --flow flow.yaml --output stubs/
```

### Playwright Test Generator: `tracetap-playwright.py`

```
Usage: python tracetap-playwright.py [collection.json] [OPTIONS]

Positional Arguments:
  collection                 Path to Postman Collection v2.1 JSON file

Output Options:
  --output, -o DIR          Output directory for test files (required)

AI Options:
  --use-ai                  Use AI for test script conversion (default: enabled)
  --no-ai                   Disable AI, use pattern matching only

Code Options:
  --no-comments             Omit comments in generated code

Utility Options:
  --config-template         Print Playwright config template and exit
  --verbose, -v             Verbose output
  --help, -h                Show help message

Environment Variables:
  ANTHROPIC_API_KEY         API key for Claude AI (required for --use-ai)
  BASE_URL                  Default base URL for API endpoints

Examples:
  # Basic usage with AI conversion
  python tracetap-playwright.py collection.json --output tests/

  # Without AI (pattern-based only, faster)
  python tracetap-playwright.py collection.json --output tests/ --no-ai

  # Generate without comments
  python tracetap-playwright.py collection.json --output tests/ --no-comments

  # Generate Playwright config template
  python tracetap-playwright.py --config-template > playwright.config.ts

  # Verbose output
  python tracetap-playwright.py collection.json --output tests/ --verbose

Complete Workflow:
  # 1. Capture traffic to Postman
  python tracetap.py --listen 8080 --export api.json

  # 2. Generate Playwright tests
  python tracetap-playwright.py api.json --output playwright-tests/

  # 3. Install Playwright and run tests
  cd playwright-tests/
  npm install -D @playwright/test
  npx playwright test

Input Requirements:
  - Postman Collection v2.1 format
  - Valid JSON structure
  - Supports nested folders

Output:
  - TypeScript test files (.spec.ts)
  - Custom fixtures for auth and variables
  - Playwright config template (optional)

Conversion Features:
  - Converts pm.test() to expect() assertions
  - Extracts variables from responses
  - Generates authentication fixtures
  - Preserves folder structure
  - AI-powered script conversion (optional)
```

### Collection Updater: `tracetap-update-collection.py`

```
Usage: python tracetap-update-collection.py <existing> <captures> [OPTIONS]

Positional Arguments:
  existing                   Path to existing Postman collection (JSON)
  captures                   Path to new capture log (JSON)

Output Options:
  -o, --output FILE          Output file (default: overwrite existing)
  --report FILE              Save update report to JSON file

Matching Options:
  --match-threshold FLOAT    Minimum confidence for auto-matching (0.0-1.0, default: 0.75)
  --new-requests MODE        How to handle new requests: add (default), prompt, ignore
  --removed-requests MODE    How to handle removed: deprecate (default), archive, keep

Preservation Options:
  --no-preserve-tests        Don't preserve test scripts (not recommended)
  --no-preserve-auth         Don't preserve authentication settings

Backup Options:
  --no-backup                Don't create backup before updating

Execution Options:
  --dry-run                  Show what would change without applying
  -v, --verbose              Verbose output
  -q, --quiet                Minimal output

Examples:
  # Basic update (creates backup automatically)
  python tracetap-update-collection.py existing.json captures.json

  # Dry run to preview changes
  python tracetap-update-collection.py existing.json captures.json --dry-run

  # Custom output file
  python tracetap-update-collection.py existing.json captures.json -o updated.json

  # Higher matching threshold (more strict)
  python tracetap-update-collection.py existing.json captures.json --match-threshold 0.85

  # Keep removed requests instead of deprecating
  python tracetap-update-collection.py existing.json captures.json --removed-requests keep

  # Generate detailed report
  python tracetap-update-collection.py existing.json captures.json --report report.json

Complete Workflow:
  # 1. Capture initial traffic
  python tracetap.py --listen 8080 --export initial.json

  # 2. (Add customizations in Postman: tests, descriptions, auth)

  # 3. Capture new traffic after API changes
  python tracetap.py --listen 8080 --export new.json

  # 4. Preview update
  python tracetap-update-collection.py initial.json new.json --dry-run

  # 5. Apply update
  python tracetap-update-collection.py initial.json new.json

Preserved Customizations:
  - Test scripts (pm.test() blocks)
  - Pre-request scripts
  - Request descriptions
  - Authentication settings
  - Collection variables
  - Folder structure

Updated from Captures:
  - Request URLs
  - HTTP methods
  - Headers
  - Request bodies
  - Query parameters
```

### Traffic Replay & Mock: `tracetap-replay.py`

```
Usage: python tracetap-replay.py <command> [OPTIONS]

Commands:
  replay                     Replay captured traffic to target server
  mock                       Start mock HTTP server
  variables                  Extract variables from captures
  scenario                   Generate YAML test scenario
  validate                   Validate captures file format

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REPLAY Command - Replay captured traffic

Usage: python tracetap-replay.py replay <log_file.json> [OPTIONS]

Required:
  log_file.json              Raw JSON log from tracetap.py --raw-log

Options:
  --target URL               Target base URL (e.g., http://localhost:8080)
  --workers N                Number of concurrent workers (default: 5)
  --variables JSON           JSON object with variable substitutions
  --scenario PATH            YAML scenario file for structured replay
  --environment ENV          Environment name from scenario (default: staging)
  --filter PATTERN           Filter requests by URL pattern
  --timeout SECONDS          Request timeout (default: 30)
  --no-verify                Disable SSL verification
  --output PATH              Save replay results to JSON file
  --verbose                  Show detailed output

Examples:
  # Basic replay
  python tracetap-replay.py replay capture.json --target http://localhost:8080

  # With variable substitution
  python tracetap-replay.py replay capture.json \
    --target http://staging-api.com \
    --variables '{"user_id": "123", "token": "abc"}'

  # Run YAML scenario
  python tracetap-replay.py replay capture.json \
    --scenario test_flow.yaml \
    --environment production \
    --verbose

  # Save detailed metrics
  python tracetap-replay.py replay capture.json \
    --target http://localhost:8080 \
    --output replay_results.json \
    --workers 10

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MOCK Command - Start mock HTTP server

Usage: python tracetap-replay.py mock <log_file.json> [OPTIONS]

Required:
  log_file.json              Raw JSON log from tracetap.py --raw-log

Options:
  --host HOST                Host to bind to (default: 127.0.0.1)
  --port PORT                Port to bind to (default: 8080)
  --strategy STRATEGY        Matching strategy: exact, fuzzy, pattern (default: fuzzy)
  --min-score SCORE          Minimum match score for fuzzy matching (default: 0.7)
  --delay MS                 Fixed delay in milliseconds
  --random-delay MIN,MAX     Random delay range (e.g., 100,500)
  --chaos                    Enable chaos engineering
  --chaos-rate RATE          Chaos failure rate 0.0-1.0 (default: 0.0)
  --chaos-status CODE        HTTP status for chaos failures (default: 500)
  --fallback-status CODE     Status for unmatched requests (default: 404)
  --fallback-body TEXT       Body for unmatched requests
  --no-admin                 Disable admin API
  --reload                   Enable auto-reload (development)
  --log-level LEVEL          Log level: debug, info, warning, error (default: info)

Examples:
  # Basic mock server
  python tracetap-replay.py mock api_captures.json

  # Custom port and strategy
  python tracetap-replay.py mock api_captures.json \
    --host 0.0.0.0 \
    --port 9090 \
    --strategy exact

  # With chaos engineering
  python tracetap-replay.py mock api_captures.json \
    --chaos \
    --chaos-rate 0.1 \
    --chaos-status 503 \
    --delay 50

  # Custom fallback response
  python tracetap-replay.py mock api_captures.json \
    --fallback-status 503 \
    --fallback-body '{"error": "Service temporarily unavailable"}'

Admin API Endpoints:
  GET  /__admin__/metrics      View server metrics
  GET  /__admin__/config       View current configuration
  POST /__admin__/config       Update configuration at runtime
  GET  /__admin__/captures     List all captured requests
  POST /__admin__/reset        Reset metrics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VARIABLES Command - Extract variables from traffic

Usage: python tracetap-replay.py variables <log_file.json> [OPTIONS]

Required:
  log_file.json              Raw JSON log from tracetap.py --raw-log

Options:
  --output PATH              Save extracted variables to JSON file
  --use-ai                   Use AI for intelligent extraction (requires API key)
  --api-key KEY              Anthropic API key (or set ANTHROPIC_API_KEY env)
  --verbose                  Show detailed extraction process

Examples:
  # AI-powered extraction
  python tracetap-replay.py variables capture.json \
    --use-ai \
    --output variables.json \
    --verbose

  # Regex-based extraction (faster, no API key needed)
  python tracetap-replay.py variables capture.json \
    --output variables.json

Detected Variable Types:
  - Numeric IDs (e.g., 123, 456789)
  - UUIDs (e.g., 550e8400-e29b-41d4-a716-446655440000)
  - JWT tokens (e.g., eyJhbGc...)
  - ISO timestamps (e.g., 2024-01-15T10:30:00)
  - Unix timestamps (e.g., 1640995200)
  - API keys (e.g., sk_live_...)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCENARIO Command - Generate YAML test scenario

Usage: python tracetap-replay.py scenario <log_file.json> [OPTIONS]

Required:
  log_file.json              Raw JSON log from tracetap.py --raw-log

Options:
  --output PATH              Save YAML scenario to file (default: scenario.yaml)
  --name NAME                Scenario name
  --intent TEXT              Describe what the scenario should test
  --use-ai                   Use AI for intelligent scenario generation
  --api-key KEY              Anthropic API key (or set ANTHROPIC_API_KEY env)

Examples:
  # AI-generated scenario
  python tracetap-replay.py scenario workflow.json \
    --name "User Registration Flow" \
    --intent "Test complete registration: signup → verify → login" \
    --use-ai \
    --output user_flow.yaml

  # Basic scenario (template-based)
  python tracetap-replay.py scenario api_calls.json \
    --output test_scenario.yaml

YAML Scenario Features:
  - Variable resolution: ${var}, ${env.VAR}, ${step.id.var}
  - Response extraction: JSONPath ($.data.id) and Regex (regex:pattern)
  - Assertions: status codes, headers, body content, response time
  - Step dependencies: chain requests using extracted values
  - Environment configs: staging, production, etc.
  - Retry logic: automatic retry on failure

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VALIDATE Command - Validate captures file

Usage: python tracetap-replay.py validate <log_file.json>

Required:
  log_file.json              Raw JSON log to validate

Examples:
  python tracetap-replay.py validate capture.json

Checks:
  - JSON format validity
  - Required fields present
  - Data type correctness
  - URL format validation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 For detailed documentation, examples, and API reference:
   See REPLAY.md in the project root directory
```

### Certificate Manager: `cert_manager.py`

```
Usage: python src/tracetap/scripts/cert_manager.py {install|verify|info|uninstall} [OPTIONS]

Commands:
  install                    Install mitmproxy CA certificate
  verify                     Verify certificate is installed
  info                       Show certificate information
  uninstall                  Remove certificate

Options:
  --verbose                  Show detailed output

Examples:
  python src/tracetap/scripts/cert_manager.py install
  python src/tracetap/scripts/cert_manager.py verify
  python src/tracetap/scripts/cert_manager.py info --verbose
```

---

## Troubleshooting

### Issue 1: "Certificate verification failed"

**Symptom**: SSL errors when making HTTPS requests through proxy

**Cause**: mitmproxy CA certificate not installed

**Solution:**
```bash
# Verify certificate status
python src/tracetap/scripts/cert_manager.py verify

# If not installed:
python src/tracetap/scripts/cert_manager.py install --verbose

# Or use curl with -k flag to skip verification (testing only)
curl -k https://api.example.com
```

### Issue 2: "No requests captured"

**Symptom**: TraceTap shows "No requests captured" after Ctrl+C

**Cause**: HTTP client not configured to use proxy, or filters too restrictive

**Solution:**

1. **Verify proxy configuration:**
```bash
echo $HTTP_PROXY
echo $HTTPS_PROXY
# Should show: http://localhost:8080
```

2. **Set proxy environment variables:**
```bash
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
```

3. **Check filters with verbose mode:**
```bash
python tracetap.py --listen 8080 --verbose
# Watch output to see if requests are being filtered
```

4. **Test without filters:**
```bash
python tracetap.py --listen 8080 --export test.json
# No --filter-host or --filter-regex means capture ALL
```

### Issue 3: "Permission denied" on certificate installation

**Symptom**: Certificate installation fails with permission error

**Cause**: Insufficient privileges for system certificate store

**Solution:**

**Linux:**
```bash
sudo bash src/tracetap/scripts/chrome-cert-manager.sh install
```

**macOS:**
```bash
# Script will prompt for password
bash src/tracetap/scripts/macos-cert-manager.sh install
```

**Windows:**
```powershell
# Run PowerShell as Administrator
# Right-click PowerShell → Run as Administrator
.\src\tracetap\scripts\windows-cert-manager.ps1 -Action install
```

### Issue 4: "ANTHROPIC_API_KEY not found"

**Symptom**: AI features fail with API key error

**Cause**: Environment variable not set

**Solution:**
```bash
# Set temporarily
export ANTHROPIC_API_KEY="your-api-key-here"

# Set permanently (Linux/macOS)
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $ANTHROPIC_API_KEY
```

**Get API Key**: https://console.anthropic.com/

### Issue 5: "Port already in use"

**Symptom**: `Address already in use` error on startup

**Cause**: Another process using port 8080

**Solution:**

1. **Use different port:**
```bash
python tracetap.py --listen 9090 --export api.json
```

2. **Find process using port:**
```bash
# Linux/macOS
lsof -i :8080

# Kill process
kill -9 <PID>
```

3. **Or kill all mitmproxy processes:**
```bash
pkill -9 mitmdump
```

### Issue 6: Verbose output too noisy

**Symptom**: Too much output cluttering console

**Solution:**
```bash
# Use quiet mode
python tracetap.py --listen 8080 --export api.json --quiet

# Or redirect output
python tracetap.py --listen 8080 --export api.json 2>/dev/null
```

### Issue 7: AI enhancement takes too long

**Symptom**: `tracetap-ai-postman.py` processing slowly

**Cause**: Large capture file (hundreds/thousands of requests)

**Solution**:

AI tool automatically samples large datasets:
- Always includes first 50 requests
- Samples from middle and end
- Limits to 200 requests max for efficiency

**Manual filtering before AI processing:**
```bash
# Capture with filters to reduce size
python tracetap.py --listen 8080 --raw-log capture.json \
  --filter-host "api.example.com"

# Or use jq to filter raw log before AI processing
cat large_capture.json | jq '.requests[:100]' > filtered.json
```

### Issue 8: OpenAPI spec missing parameters

**Symptom**: Generated OpenAPI spec doesn't show path parameters

**Cause**: URL doesn't match ID pattern (numeric, UUID, or 8+ char alphanumeric with digit)

**Solution**:

Supported patterns:
- Numeric: `/users/123` → `/users/{id}`
- UUID: `/users/550e8400-e29b-41d4-a716-446655440000` → `/users/{id}`
- Alphanumeric (8+ chars with digit): `/users/abc12345def` → `/users/{id}`

For custom patterns, manually edit the OpenAPI spec after generation.

---

## Quick Reference Card

### Common Workflows

```bash
# 1. Basic capture to Postman
python tracetap.py --listen 8080 --export api.json

# 2. Filter specific host
python tracetap.py --listen 8080 --export api.json --filter-host "api.example.com"

# 3. All export formats
python tracetap.py --listen 8080 --export api.json --raw-log raw.json --export-openapi spec.json

# 4. AI-enhanced collection
python tracetap.py --listen 8080 --raw-log capture.json
python tracetap-ai-postman.py capture.json --output enhanced.json

# 5. WireMock stubs
python tracetap.py --listen 8080 --raw-log prod.json
python tracetap2wiremock.py prod.json --output wiremock/mappings/

# 6. Traffic replay to staging
python tracetap.py --listen 8080 --raw-log prod.json
python tracetap-replay.py replay prod.json --target http://staging-api.com

# 7. Mock server (offline development)
python tracetap.py --listen 8080 --raw-log api.json
python tracetap-replay.py mock api.json --port 8080

# 8. AI variable extraction
python tracetap-replay.py variables capture.json --use-ai --output vars.json

# 9. Generate YAML test scenario
python tracetap-replay.py scenario workflow.json --use-ai --name "User Flow"

# 10. Mock with chaos engineering
python tracetap-replay.py mock api.json --chaos --chaos-rate 0.1 --delay 100

# 11. Generate Playwright tests from Postman
python tracetap.py --listen 8080 --export api.json
python tracetap-playwright.py api.json --output tests/

# 12. Update existing Postman collection
python tracetap-update-collection.py existing.json new.json --dry-run

# 13. Debug filtering
python tracetap.py --listen 8080 --verbose --filter-host "*.example.com"
```

### Proxy Configuration

```bash
# Set proxy (before making requests)
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Unset proxy
unset HTTP_PROXY
unset HTTPS_PROXY

# One-time proxy with curl
curl -x http://localhost:8080 -k https://api.example.com
```

### File Outputs

| Command | Output | Format |
|---------|--------|--------|
| `--export api.json` | Postman Collection v2.1 | JSON |
| `--raw-log raw.json` | Raw captured data | JSON |
| `--export-openapi spec.json` | OpenAPI 3.0 spec | JSON |

### Filtering Patterns

| Pattern | Matches | Example |
|---------|---------|---------|
| `api.example.com` | Exact host | Only api.example.com |
| `*.example.com` | Wildcard subdomain | api.example.com, auth.example.com |
| `example.com,github.com` | Multiple hosts | Both hosts |
| `/api/v[0-9]+/` | Regex pattern | /api/v1/, /api/v2/ |

---

## Additional Resources

- **Source Code**: `/home/terminatorbill/PycharmProjects/Tracetap/`
- **Tests**: `/home/terminatorbill/PycharmProjects/Tracetap/tests/`
- **License**: MIT

**Key Files:**

*Capture & Export:*
- `tracetap.py` - Main entry point (25 lines, wrapper to modular implementation)
- `src/tracetap/capture/tracetap_main.py` - Core capture implementation (247 lines)
- `tracetap-ai-postman.py` - AI Postman generator (1533 lines)
- `tracetap2wiremock.py` - WireMock stub generator (461 lines)
- `src/tracetap/capture/exporters.py` - Export implementations (551 lines)
- `src/tracetap/capture/filters.py` - Filtering logic (102 lines)

*Collection Updater:*
- `tracetap-update-collection.py` - Collection updater CLI (234 lines)
- `src/tracetap/update/updater.py` - Update orchestrator
- `src/tracetap/update/matcher.py` - Request matching logic
- `src/tracetap/update/merger.py` - Collection merging logic

*Replay & Mock:*
- `tracetap-replay.py` - CLI for replay and mock features (471 lines)
- `src/tracetap/replay/replayer.py` - Traffic replay engine (408 lines)
- `src/tracetap/replay/variables.py` - AI variable extraction (384 lines)
- `src/tracetap/replay/replay_config.py` - YAML scenario configuration (533 lines)
- `src/tracetap/mock/server.py` - FastAPI mock server (1299 lines)
- `src/tracetap/mock/matcher.py` - Request matching engine (931 lines)
- `src/tracetap/mock/generator.py` - Response generation (544 lines)

*Playwright Test Generation:*
- `tracetap-playwright.py` - Playwright test generator CLI
- `src/tracetap/playwright/playwright_generator.py` - Main orchestrator (256 lines)
- `src/tracetap/playwright/postman_parser.py` - Postman collection parser (343 lines)
- `src/tracetap/playwright/test_converter.py` - Request to test converter (299 lines)
- `src/tracetap/playwright/script_analyzer.py` - AI script conversion (311 lines)
- `src/tracetap/playwright/fixture_generator.py` - Fixture generation (213 lines)
- `src/tracetap/playwright/template_engine.py` - TypeScript code rendering (308 lines)

**Test Coverage**: 514 tests passing (178 capture + 336 replay/mock), comprehensive coverage

---

**Last Updated**: 2025-12-21
**Version**: Based on version2 branch
**Model**: Documentation powered by Claude Sonnet 4.5
