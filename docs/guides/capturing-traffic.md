# Capturing Traffic with TraceTap

Complete guide to capturing HTTP/HTTPS traffic from your applications.

## Table of Contents

- [Overview](#overview)
- [Basic Capture](#basic-capture)
- [Filtering](#filtering)
- [Certificate Management](#certificate-management)
- [Export Formats](#export-formats)
- [Advanced Options](#advanced-options)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

TraceTap captures HTTP/HTTPS traffic by running as a proxy. Your application sends requests through TraceTap, which records them before passing them to the destination.

### How It Works

```
Your App
  │
  ├─ HTTP Request ──→ TraceTap Proxy (port 8080)
  │                      │
  │                  [Record Request]
  │                      │
  │                  [Forward to Server]
  │                      ▼
  │                   Real Server
  │
  ├─ HTTP Response ←─ TraceTap Proxy
  │                      │
  │                  [Record Response]
  │                      │
  └─ Data Saved to: captured.json
```

---

## Basic Capture

### Step 1: Start TraceTap

```bash
# Start the proxy on port 8080
python tracetap.py --listen 8080 --export captured.json
```

Output:
```
[16:42:31] TraceTap HTTP Proxy started on port 8080
[16:42:31] Ready to capture traffic...
```

### Step 2: Configure Your Application

Point your app to use the TraceTap proxy:

**Bash/Shell:**
```bash
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
```

**Python:**
```python
import requests

proxies = {
    'http': 'http://localhost:8080',
    'https': 'http://localhost:8080'
}

response = requests.get('https://api.example.com', proxies=proxies)
```

**Node.js:**
```javascript
const HttpProxyAgent = require('http-proxy-agent');
const HttpsProxyAgent = require('https-proxy-agent');

const httpAgent = new HttpProxyAgent('http://localhost:8080');
const httpsAgent = new HttpsProxyAgent('http://localhost:8080');

const response = await fetch('https://api.example.com', {
  agent: { http: httpAgent, https: httpsAgent }
});
```

**cURL:**
```bash
curl -x http://localhost:8080 -k https://api.example.com
```

### Step 3: Make Requests

Exercise your application:

```bash
# Example API calls
curl -k https://api.github.com/users/github
curl -k https://api.example.com/endpoint
# ... do your workflow
```

Watch TraceTap show captured requests:

```
[16:43:12] → GET https://api.github.com/users/github
[16:43:12] ← 200 OK (142ms)
[16:43:15] → POST https://api.example.com/endpoint
[16:43:15] ← 201 Created (89ms)
```

### Step 4: Stop and Export

Press `Ctrl+C` in the TraceTap terminal:

```
[16:44:00] Stopping proxy...
[16:44:01] ✓ Exported 5 requests to captured.json
```

The `captured.json` file now contains all captured requests and responses.

---

## Filtering

Capture only specific traffic to reduce noise.

### Filter by Host

Capture requests to specific hosts:

```bash
# Single host
python tracetap.py --listen 8080 \
  --filter-host api.example.com \
  --export api.json

# Multiple hosts (OR logic - captures if ANY matches)
python tracetap.py --listen 8080 \
  --filter-host api.example.com \
  --filter-host api.github.com \
  --filter-host *.internal.com \
  --export api.json
```

### Wildcard Matching

Use `*` to match domain patterns:

```bash
# Match all subdomains
--filter-host "*.example.com"
# Matches: api.example.com, web.example.com, test.example.com

# Match deep subdomains
--filter-host "*.api.example.com"
# Matches: v1.api.example.com, v2.api.example.com

# Match prefix
--filter-host "api-*"
# Matches: api-v1.com, api-staging.com
```

### Regex Filtering

Use regular expressions for complex patterns:

```bash
# Match API versioning patterns
python tracetap.py --listen 8080 \
  --filter-regex "api\..*\.com" \
  --export api.json

# Match path patterns
python tracetap.py --listen 8080 \
  --filter-regex "/api/v[0-9]+" \
  --export api.json

# Multiple regex patterns (OR logic)
python tracetap.py --listen 8080 \
  --filter-regex "api\..*\.com" \
  --filter-regex "/api/.*" \
  --export api.json
```

### Combining Filters

Mix host and regex filters (OR logic):

```bash
# Captures if EITHER filter matches
python tracetap.py --listen 8080 \
  --filter-host "api.example.com" \
  --filter-regex ".*\.internal\..*" \
  --export api.json
```

### Debug Filtering

See which requests are captured/filtered:

```bash
python tracetap.py --listen 8080 \
  --filter-host "api.example.com" \
  --filter-verbose \
  --export api.json
```

Output:
```
[16:43:12] REQUEST: GET https://api.example.com/users
           FILTER: api.example.com ✓ MATCH → CAPTURE
[16:43:13] REQUEST: GET https://other.com/endpoint
           FILTER: api.example.com ✗ no match
           FILTER: other.com ✗ no match → SKIP
```

---

## Certificate Management

HTTPS requires certificate handling.

### The Problem

By default, browsers trust only certificates signed by known Certificate Authorities (CAs). When TraceTap acts as a proxy, it intercepts HTTPS, which requires installing TraceTap's certificate.

### Install Certificate (One-Time Setup)

```bash
# Install TraceTap's CA certificate
python tracetap.py --install-cert

# Choose where to install:
# 1. System-wide (recommended)
# 2. Browser-specific
# 3. Python-specific
```

**Linux:**
```bash
# System-wide
sudo cp ~/.tracetap/ca-cert.pem /usr/local/share/ca-certificates/
sudo update-ca-certificates

# Or for Python
export REQUESTS_CA_BUNDLE="$HOME/.tracetap/ca-cert.pem"
```

**macOS:**
```bash
# System Keychain
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  ~/.tracetap/ca-cert.pem
```

**Windows:**
```cmd
# Import to Windows certificate store
certutil -addstore -f "Root" "%USERPROFILE%\.tracetap\ca-cert.pem"
```

### Verify Certificate Installation

```bash
# Test HTTPS capture
curl -k https://www.example.com

# Check TraceTap output - should show the request
# If you see SSL errors, certificate isn't installed
```

### Bypass Certificate Verification (Insecure)

For testing only:

```bash
# Python
curl -k https://api.example.com  # -k ignores cert errors

# cURL environment
export CURL_CA_BUNDLE=""
curl https://api.example.com

# Python requests
import requests
requests.packages.urllib3.disable_warnings()
response = requests.get('https://api.example.com', verify=False)
```

### Generate New Certificate

If certificate expires:

```bash
python tracetap.py --renew-cert

# This generates a new CA certificate
# Re-install it following the steps above
```

---

## Export Formats

Choose how to export captured traffic.

### Format 1: Postman Collection (Default)

The default export format. Ready to import into Postman.

```bash
python tracetap.py --listen 8080 --export api.json
```

Features:
- ✅ Import directly into Postman
- ✅ Preserves request/response structure
- ✅ Organized by folders
- ✅ Ready for manual testing

### Format 2: Raw JSON Log

Complete raw data with metadata.

```bash
python tracetap.py --listen 8080 --raw-log captures.json
```

Structure:
```json
{
  "session_name": "API Capture",
  "timestamp": "2024-02-01T16:42:00Z",
  "filter_config": {
    "hosts": ["api.example.com"],
    "regexes": []
  },
  "requests": [
    {
      "method": "GET",
      "url": "https://api.example.com/users/123",
      "headers": {...},
      "body": null,
      "response": {
        "status": 200,
        "headers": {...},
        "body": "...",
        "duration_ms": 145
      }
    }
  ]
}
```

Best for:
- Processing with scripts
- Custom analysis
- Archival

### Format 3: OpenAPI 3.0 Specification

Auto-generate API documentation.

```bash
python tracetap.py --listen 8080 --export-openapi openapi.json
```

Result: Complete OpenAPI spec you can use with tools like:
- SwaggerUI (interactive API docs)
- Code generators
- API contract validation

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Captured API",
    "version": "1.0.0"
  },
  "servers": [
    {"url": "https://api.example.com"}
  ],
  "paths": {
    "/users/{id}": {
      "get": {
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": {"type": "integer"}
          }
        ],
        "responses": {
          "200": {
            "description": "User found",
            "content": {
              "application/json": {
                "schema": {...}
              }
            }
          }
        }
      }
    }
  }
}
```

### Combine Formats

Export to multiple formats simultaneously:

```bash
python tracetap.py --listen 8080 \
  --export postman.json \
  --raw-log raw.json \
  --export-openapi openapi.json
```

---

## Advanced Options

### Custom Session Name

```bash
python tracetap.py --listen 8080 \
  --session "User Registration Flow" \
  --export api.json
```

### Quiet Mode

Suppress console output:

```bash
python tracetap.py --listen 8080 --quiet --export api.json
```

### Debug Mode

Verbose output for troubleshooting:

```bash
python tracetap.py --listen 8080 --debug --export api.json
```

Output includes:
- All requests/responses
- Header details
- Timing information
- Filter decisions

### Listen on Specific Interface

By default listens on localhost. To accept connections from other machines:

```bash
# Listen on all interfaces
python tracetap.py --listen 0.0.0.0:8080 --export api.json

# Listen on specific IP
python tracetap.py --listen 192.168.1.10:8080 --export api.json
```

### Custom CA Certificate

Use existing certificate:

```bash
python tracetap.py --listen 8080 \
  --cert-file /path/to/cert.pem \
  --key-file /path/to/key.pem \
  --export api.json
```

### SOCKS Proxy

Forward through existing SOCKS proxy:

```bash
python tracetap.py --listen 8080 \
  --socks-server socks.example.com:1080 \
  --export api.json
```

---

## Troubleshooting

### HTTPS Connections Fail

**Problem**: `ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]`

**Solution**:
```bash
# Install certificate
python tracetap.py --install-cert

# Or use curl with -k flag (insecure)
curl -k https://api.example.com

# Or set Python to ignore certs (not recommended)
export REQUESTS_CA_BUNDLE=""
```

### Requests Not Being Captured

**Problem**: No requests showing in TraceTap output

**Solutions**:

1. **Check proxy is configured:**
```bash
echo $HTTP_PROXY
echo $HTTPS_PROXY
# Should show: http://localhost:8080
```

2. **Check application uses proxy:**
```bash
# For curl
curl -x http://localhost:8080 https://api.example.com

# For Python requests
import requests
proxies = {'https': 'http://localhost:8080'}
requests.get('https://api.example.com', proxies=proxies)
```

3. **Check filter configuration:**
```bash
python tracetap.py --listen 8080 --filter-verbose --export api.json
# Check if requests match your filters
```

4. **Check TraceTap is running:**
```bash
# In another terminal
curl http://localhost:8080

# Should get a response from TraceTap
```

### Port Already in Use

**Problem**: `Address already in use: ('0.0.0.0', 8080)`

**Solution**:
```bash
# Use different port
python tracetap.py --listen 8081 --export api.json

# Or kill existing process
lsof -ti:8080 | xargs kill -9
```

### Filtering Captures Too Much or Too Little

**Problem**: Unexpected requests being captured

**Solution**:
```bash
# Enable filter debugging
python tracetap.py --listen 8080 \
  --filter-host "api.example.com" \
  --filter-verbose \
  --export api.json

# Watch output to see which requests match
```

### Certificate Errors in Specific Browser

**Problem**: Browser shows certificate warning

**Solution**:
```bash
# Reinstall certificate for that browser
# Then restart the browser

# Or browse in incognito mode (doesn't use proxy)
```

---

## Best Practices

### 1. Capture Complete Workflows

Don't just capture random requests. Capture a complete user flow:

```bash
# Good: Workflow from start to finish
GET /api/users           # List users
POST /api/users          # Create new user
GET /api/users/123       # Verify created
PUT /api/users/123       # Update user
DELETE /api/users/123    # Delete user

# Not ideal: Random requests without context
GET /api/users/999999    # What is this for?
POST /api/config         # Why needed?
```

### 2. Include Error Cases

Capture both success and failure paths:

```bash
# Success case
curl -k https://api.example.com/users/123

# Error cases
curl -k https://api.example.com/users/999999        # Not found
curl -k https://api.example.com/users/abc           # Invalid ID
curl -k https://api.example.com/users               # Missing auth header

# Edge cases
curl -k https://api.example.com/users?limit=9999    # Large limit
curl -k https://api.example.com/users?offset=0      # Empty result
```

### 3. Use Meaningful Session Names

```bash
# Good
--session "User Registration and Login Flow"
--session "Payment Processing - Happy Path"
--session "Error Scenarios"

# Not helpful
--session "test"
--session "api1"
--session "capture1"
```

### 4. Keep Captures Focused

Use filtering to avoid noise:

```bash
# Good: Only capture API traffic
python tracetap.py --listen 8080 \
  --filter-host "api.example.com" \
  --export api.json

# Not ideal: Captures everything (CDN, ads, analytics)
python tracetap.py --listen 8080 \
  --export everything.json
```

### 5. Organize Multiple Captures

Create separate captures for different scenarios:

```bash
# Capture 1: Happy path
python tracetap.py --listen 8080 \
  --session "User Registration" \
  --export user-registration.json

# Capture 2: Error cases
python tracetap.py --listen 8080 \
  --session "Error Cases" \
  --export error-cases.json

# Capture 3: Edge cases
python tracetap.py --listen 8080 \
  --session "Edge Cases" \
  --export edge-cases.json

# Later, generate tests from each
python tracetap-playwright.py user-registration.json -o tests/registration/
python tracetap-playwright.py error-cases.json -o tests/errors/
python tracetap-playwright.py edge-cases.json -o tests/edge/
```

### 6. Capture on Staging/Test Environment First

```bash
# ✓ Good: Test on staging first
# Configure to use staging API
API_URL=https://staging-api.example.com

# Capture there
python tracetap.py --listen 8080 --export captures.json

# Then use captures for all analysis, testing, contracts, etc.

# ✗ Avoid: Capturing production directly
# (Risk of capturing production data)
```

### 7. Secure Captured Files

Captures contain sensitive data:

```bash
# Don't commit to version control
echo "*.json" >> .gitignore

# Store securely if needed
chmod 600 captured.json

# Remove PII before sharing
# (Manually edit or use anonymization tool)
```

---

## Next Steps

- **[Generating Tests](generating-tests.md)** - Create tests from captured traffic
- **[Regression Testing](../features/regression-testing.md)** - Use captures as regression baseline
- **[CI/CD Integration](ci-cd-integration.md)** - Automate capture and testing
