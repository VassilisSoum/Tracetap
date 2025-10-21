# TraceTap Examples

Real-world examples showing how to use TraceTap in various scenarios.

## Table of Contents

- [Basic Capture](#basic-capture)
- [API Testing Workflow](#api-testing-workflow)
- [WireMock Setup](#wiremock-setup)
- [Debugging Integration Issues](#debugging-integration-issues)

---

## Basic Capture

**Scenario:** Capture traffic from a specific API and export to Postman.

**Use Case:** Quick API documentation, one-off captures.

**Commands:**

```bash
# Start TraceTap with host filter
./tracetap-linux-x64 --listen 8080 \
  --filter-host "api.example.com" \
  --raw-log captures/basic.json \
  --export collections/basic_postman.json

# Configure proxy in your terminal
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Make API calls
curl https://api.example.com/users
curl https://api.example.com/products
```

**Result:** Two files created - raw capture and Postman collection ready to import.

---

## API Testing Workflow

**Scenario:** Capture traffic, enhance with AI, create organized collection.

**Use Case:** Comprehensive API documentation, team collaboration.

**Step 1: Capture traffic**
```bash
./tracetap-linux-x64 --listen 8080 \
  --filter-host "api.myapp.com" \
  --raw-log captures/ecommerce.json \
  --session "E-commerce API Testing"
```

**Step 2: Use your application** (configure browser proxy to localhost:8080, then browse normally)

**Step 3: Enhance with AI**
```bash
python tracetap-ai-postman.py captures/ecommerce.json \
  --output collections/ecommerce_enhanced.json \
  --instructions "Group by: Authentication, Products, Cart, Checkout. Extract user_id and cart_id as variables." \
  --save-analysis analysis.json
```

**Result:** Organized Postman collection with folders, clean names, variables, and descriptions.

---

## WireMock Setup

**Scenario:** Capture production API responses and create local mocks.

**Use Case:** Offline development, testing without hitting production.

**Step 1: Capture production traffic**
```bash
./tracetap-linux-x64 --listen 8080 \
  --filter-host "api.stripe.com" \
  --raw-log captures/stripe_prod.json
```

**Step 2: Convert to WireMock stubs**
```bash
python tracetap2wiremock.py captures/stripe_prod.json \
  --output wiremock/mappings/
```

**Step 3: Start WireMock**
```bash
docker run -p 8081:8080 \
  -v $(pwd)/wiremock/mappings:/home/wiremock/mappings \
  wiremock/wiremock
```

**Step 4: Update your app to use mocks**
Change API base URL from `https://api.stripe.com` to `http://localhost:8081`

**Result:** Local mock server with real production responses, no internet needed.

---

**Result:** Automatic API documentation generated with every CI build.

---

## Debugging Integration Issues

**Scenario:** Debug problems with third-party API integration.

**Use Case:** See exact requests/responses, identify issues quickly.

**Capture with verbose logging**
```bash
./tracetap-linux-x64 --listen 8080 \
  --filter-host "api.thirdparty.com" \
  --verbose \
  --raw-log debug_capture.json
```

**Run problematic code**
Configure your app to use proxy, then run the code that's failing.

**Inspect the capture**

View all requests:
```bash
cat debug_capture.json | jq '.requests[] | {method, url, status, duration_ms}'
```

Find failed requests:
```bash
cat debug_capture.json | jq '.requests[] | select(.status >= 400)'
```

Check specific endpoint:
```bash
cat debug_capture.json | jq '.requests[] | select(.url | contains("/payment"))'
```

View request/response headers:
```bash
cat debug_capture.json | jq '.requests[0] | {req_headers, resp_headers}'
```

**Result:** Complete visibility into API communication, exact error responses captured.

---

## Quick Reference

| Use Case | Key Command |
|----------|-------------|
| Basic capture | `--listen 8080 --raw-log file.json` |
| Filter by host | `--filter-host "api.example.com"` |
| Filter by pattern | `--filter-regex ".*\/api\/.*"` |
| AI enhancement | `python tracetap-ai-postman.py file.json --output enhanced.json` |
| WireMock stubs | `python tracetap2wiremock.py file.json --output mappings/` |
| Quiet mode | `--quiet` |
| Verbose mode | `--verbose` |

---

## Tips

**Reduce noise:** Always use filters to capture only relevant traffic
```bash
--filter-host "api.yourapp.com"
```

**Save both formats:** Keep raw capture for flexibility
```bash
--raw-log raw.json --export postman.json
```

**Use meaningful sessions:** Help identify captures later
```bash
--session "Checkout Flow - Bug Investigation - 2025-10-21"
```

**Analyze before enhancing:** Check what was captured
```bash
cat capture.json | jq '.total_requests'
cat capture.json | jq '.requests[].url' | sort | uniq
```

---

## Next Steps

- **[Getting Started](getting-started.md)** - Full installation guide