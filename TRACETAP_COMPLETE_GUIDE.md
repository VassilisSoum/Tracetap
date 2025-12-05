# TraceTap Complete Guide

**The Complete Reference for HTTP/HTTPS Traffic Capture, AI-Powered API Documentation, and WireMock Stub Generation**

---

## Table of Contents

1. [What is TraceTap?](#what-is-tracetap)
2. [Features](#features)
3. [How TraceTap Works](#how-tracetap-works)
4. [Installation](#installation)
5. [Usage Scenarios](#usage-scenarios)
6. [Command Reference](#command-reference)
7. [Troubleshooting](#troubleshooting)

---

## What is TraceTap?

TraceTap is a comprehensive HTTP/HTTPS traffic capture proxy that records API interactions and exports them to multiple formats. It combines the power of mitmproxy for traffic interception with AI-powered analysis using Claude Sonnet 4.5 to generate intelligent API documentation, organized Postman collections, and WireMock stubs.

**Key Use Cases:**
- Document APIs by capturing live traffic
- Generate Postman collections from real user workflows
- Create WireMock stubs for testing and mocking
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
- **Operating System**: Linux, macOS, or Windows

### Step 1: Install Dependencies

```bash
# Navigate to TraceTap directory
cd /path/to/TraceTap

# Install core dependencies
pip install -r requirements.txt
```

**Required Packages:**
- `mitmproxy>=10.0.0,<11.0.0` - HTTP proxy framework
- `pyinstaller>=5.0.0` - Executable building
- `anthropic>=0.71.0` - Claude AI API client
- `PyYAML>=6.0` - YAML parsing for flow specs
- `typing-extensions>=4.3,<=4.11.0` - Type hints compatibility

### Step 2: Install Certificate (REQUIRED for HTTPS)

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

### Step 3: Set Up API Key (Optional - for AI Features)

If you want to use AI-powered features:

```bash
# Set environment variable
export ANTHROPIC_API_KEY="your-api-key-here"

# Or add to ~/.bashrc or ~/.zshrc for persistence
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**Get API Key:** Sign up at https://console.anthropic.com/

### Step 4: Verify Installation

```bash
# Test basic capture (should show help)
python tracetap.py --help

# Test AI tools (should show help)
python tracetap-ai-postman.py --help
python tracetap2wiremock.py --help
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

# 6. Debug filtering
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
- **Documentation**: `/home/terminatorbill/PycharmProjects/Tracetap/docs/`
- **License**: MIT

**Key Files:**
- `tracetap.py` - Main capture tool (714 lines)
- `tracetap-ai-postman.py` - AI Postman generator (1061 lines)
- `tracetap2wiremock.py` - WireMock stub generator (478 lines)
- `src/tracetap/capture/exporters.py` - Export implementations (551 lines)
- `src/tracetap/capture/filters.py` - Filtering logic (102 lines)

**Test Coverage**: 178 tests passing, 81% code coverage

---

**Last Updated**: 2025-12-06
**Version**: Based on latest main branch
**Model**: Documentation powered by Claude Sonnet 4.5
