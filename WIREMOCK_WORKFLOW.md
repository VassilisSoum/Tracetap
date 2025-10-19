# TraceTap → WireMock Workflow

Complete workflow for capturing real API traffic and creating WireMock stubs.

## Quick Start

### 1. Capture Traffic with TraceTap

```bash
# Start TraceTap proxy with raw log export
./tracetap-linux-x64 --listen 8080 \
  --raw-log captured_traffic.json \
  --filter-host "api.example.com"

# Configure your application to use the proxy
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Run your application/tests
# ... application makes API calls through proxy ...

# Stop TraceTap (Ctrl+C)
# captured_traffic.json is created
```

### 2. Convert to WireMock Stubs

```bash
# Convert the raw log to WireMock mappings
python tracetap2wiremock.py captured_traffic.json \
  --output wiremock/mappings/
```

### 3. Run WireMock

```bash
# Option A: Standalone JAR
java -jar wiremock-standalone.jar --port 8080 --root-dir wiremock/

# Option B: Docker
docker run -p 8080:8080 \
  -v $(pwd)/wiremock/mappings:/home/wiremock/mappings \
  wiremock/wiremock

# Your app can now use http://localhost:8080 instead of the real API
```

## Real-World Example

### Scenario: Mock a Payment API

```bash
# 1. Capture real payment API traffic
./tracetap-linux-x64 --listen 8080 \
  --raw-log payment_api.json \
  --filter-host "payments.stage.eu.whitehatgaming.com" \
  --session "Payment API Capture"

# 2. Make real payment requests through proxy
export HTTPS_PROXY=http://localhost:8080
curl -k https://payments.stage.eu.whitehatgaming.com/api/v1/transactions

# 3. Stop TraceTap and convert to WireMock
python tracetap2wiremock.py payment_api.json \
  --output payment_stubs/ \
  --priority 1

# 4. Run WireMock with captured stubs
docker run -p 9000:8080 \
  -v $(pwd)/payment_stubs:/home/wiremock/mappings \
  wiremock/wiremock

# 5. Point your app to the mock
# Change API base URL from:
#   https://payments.stage.eu.whitehatgaming.com
# To:
#   http://localhost:9000
```

## Advanced Usage

### Ignoring Dynamic Fields

Real APIs have dynamic fields (timestamps, IDs, tokens) that change with each request. Use an ignore configuration to exclude these from matching:

**1. Create ignore config:**
```bash
cat > ignore-config.json << 'EOF'
{
  "ignore_headers": ["Date", "X-Request-Id"],
  "ignore_query_params": ["timestamp", "nonce"],
  "ignore_json_fields": ["createdAt", "id", "token"],
  "ignore_delays": false
}
EOF
```

**2. Convert with config:**
```bash
python tracetap2wiremock.py payment_api.json \
  --output payment_stubs/ \
  --config ignore-config.json
```

**Why this is important:**
- ✅ Stubs match requests with different timestamps
- ✅ Stubs match requests with different IDs
- ✅ Remove sensitive data (tokens, API keys)
- ✅ More flexible, maintainable stubs

**See [WireMock Ignore Configuration Guide](WIREMOCK_IGNORE_CONFIG.md) for complete documentation.**

### Capture Multiple Sessions

```bash
# Capture different scenarios
./tracetap-linux-x64 --listen 8080 --raw-log success_cases.json
# ... test successful flows ...

./tracetap-linux-x64 --listen 8080 --raw-log error_cases.json
# ... test error flows ...

# Convert both
python tracetap2wiremock.py success_cases.json -o wiremock/mappings/ -p 5
python tracetap2wiremock.py error_cases.json -o wiremock/mappings/ -p 10
```

### Different Matching Strategies

```bash
# Exact URL matching (default) - matches query params too
python tracetap2wiremock.py captured.json -o stubs/ --matching url

# Path only - ignores query parameters
python tracetap2wiremock.py captured.json -o stubs/ --matching urlPath

# Pattern matching - uses regex
python tracetap2wiremock.py captured.json -o stubs/ --matching urlPattern
```

### Priority-Based Stubs

WireMock uses priority to determine which stub matches first (lower = higher priority):

```bash
# High priority for specific cases
python tracetap2wiremock.py specific_errors.json -o stubs/ --priority 1

# Medium priority for normal flows
python tracetap2wiremock.py normal_flow.json -o stubs/ --priority 5

# Low priority for catch-all
python tracetap2wiremock.py fallback.json -o stubs/ --priority 10
```

## Generated Stub Format

TraceTap generates WireMock stubs like this:

```json
{
  "priority": 5,
  "request": {
    "method": "POST",
    "url": "/api/v1/transactions",
    "queryParameters": {
      "currency": {"equalTo": "USD"}
    },
    "bodyPatterns": [
      {
        "equalToJson": "{\"amount\": 100}",
        "ignoreArrayOrder": true,
        "ignoreExtraElements": true
      }
    ]
  },
  "response": {
    "status": 200,
    "headers": {
      "Content-Type": "application/json"
    },
    "jsonBody": {
      "transactionId": "tx_12345",
      "status": "completed"
    },
    "fixedDelayMilliseconds": 234
  }
}
```

## Benefits

### 1. **Realistic Test Data**
- Stubs use real API responses
- Includes actual headers, status codes, timing

### 2. **Fast Development**
- No need to manually write mock responses
- Capture once, reuse forever

### 3. **Regression Testing**
- Save production/staging responses
- Test against known good responses
- Detect API changes

### 4. **Offline Development**
- Work without network
- No rate limits
- Consistent responses

### 5. **CI/CD Integration**
- Fast, reliable tests
- No external dependencies
- Deterministic results

## Tips & Tricks

### Capture Only What You Need

```bash
# Use filters to capture specific endpoints
./tracetap-linux-x64 --listen 8080 \
  --raw-log api.json \
  --filter-regex "/api/v1/(users|transactions)"
```

### Update Stubs

```bash
# Capture new traffic
./tracetap-linux-x64 --listen 8080 --raw-log new_endpoints.json

# Add to existing stubs (different directory or merge manually)
python tracetap2wiremock.py new_endpoints.json -o wiremock/mappings/new/
```

### Debug Stubs

```bash
# WireMock verbose mode
java -jar wiremock-standalone.jar --port 8080 --verbose

# Check which stub matched
curl -v http://localhost:8080/__admin/requests
```

### Modify Responses

Edit generated stub files to:
- Change response data for edge cases
- Add different error scenarios
- Adjust timing/delays
- Add response templating

Example:
```json
{
  "response": {
    "status": 500,
    "jsonBody": {"error": "Internal Server Error"},
    "fixedDelayMilliseconds": 5000
  }
}
```

## Troubleshooting

### No stubs generated

Check that:
- Raw log file has requests: `jq '.total_requests' captured.json`
- Filters aren't too restrictive
- Output directory is writable

### Stubs not matching

- Check WireMock logs for match failures
- Try different matching modes (`--matching urlPath`)
- Verify request URL/method
- Check `__admin/requests` endpoint

### Response bodies too large

WireMock handles large bodies, but consider:
- Extracting to separate files
- Using response templating
- Reducing body size in stubs

## Integration with CI/CD

```yaml
# .github/workflows/test.yml
name: Tests with WireMock

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start WireMock
        run: |
          docker run -d -p 8080:8080 \
            -v $PWD/test/wiremock/mappings:/home/wiremock/mappings \
            --name wiremock \
            wiremock/wiremock
      
      - name: Run tests
        env:
          API_BASE_URL: http://localhost:8080
        run: npm test
      
      - name: Stop WireMock
        run: docker stop wiremock
```

## Next Steps

1. **Capture production traffic** (carefully!)
2. **Create stub library** for your APIs
3. **Version control stubs** alongside tests
4. **Document API contracts** from stubs
5. **Share stubs** across teams

Happy mocking! 🎭