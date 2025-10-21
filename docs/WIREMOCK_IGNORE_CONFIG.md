# WireMock Ignore Configuration Guide

When converting TraceTap captures to WireMock stubs, you often need to ignore dynamic fields that change with each request (timestamps, IDs, tokens, etc.). This guide explains how to configure what fields to ignore in matching.

## Quick Start

```bash
# 1. Create config file
cat > ignore-config.json << 'EOF'
{
  "ignore_headers": ["Date", "X-Request-Id"],
  "ignore_query_params": ["timestamp"],
  "ignore_json_fields": ["createdAt", "id"]
}
EOF

# 2. Convert with config
python tracetap2wiremock.py captures.json \
  --output stubs/ \
  --config ignore-config.json
```

## Configuration Options

### `ignore_headers` (Array of Strings)

HTTP headers to exclude from request matching.

```json
{
  "ignore_headers": [
    "Date",
    "X-Request-Id",
    "X-Correlation-Id",
    "Authorization",
    "Cookie"
  ]
}
```

**Use case:** Headers that are dynamic or contain sensitive data.

**Example:**
```json
// Without config - Won't match if Date header differs
{
  "request": {
    "headers": {
      "Date": {"equalTo": "Mon, 20 Oct 2025 10:00:00 GMT"}
    }
  }
}

// With config - Date header ignored
{
  "request": {
    "headers": {}  // Date not included
  }
}
```

### `ignore_query_params` (Array of Strings)

Query string parameters to exclude from URL matching.

```json
{
  "ignore_query_params": [
    "timestamp",
    "nonce",
    "_",
    "cache_buster"
  ]
}
```

**Use case:** Cache busters, timestamps, random tokens in URLs.

**Example:**
```json
// Without config
{
  "request": {
    "url": "/api/users",
    "queryParameters": {
      "timestamp": {"equalTo": "1729420800"}
    }
  }
}

// With config - timestamp ignored
{
  "request": {
    "url": "/api/users"
    // queryParameters omitted
  }
}
```

### `ignore_json_fields` (Array of Strings)

JSON fields to exclude from request body matching.

```json
{
  "ignore_json_fields": [
    "timestamp",
    "createdAt",
    "id",
    "uuid",
    "requestId",
    "token"
  ]
}
```

**Use case:** Auto-generated IDs, timestamps, tokens in request bodies.

**Example:**
```json
// Original request body
{
  "userId": 123,
  "action": "login",
  "timestamp": 1729420800,
  "requestId": "abc-123"
}

// With config - timestamp and requestId ignored
{
  "request": {
    "bodyPatterns": [{
      "equalToJson": {
        "userId": 123,
        "action": "login"
      }
    }]
  }
}
```

### `ignore_response_json_fields` (Array of Strings)

JSON fields to exclude from response body.

```json
{
  "ignore_response_json_fields": [
    "timestamp",
    "serverTime",
    "processingTime"
  ]
}
```

**Use case:** Server-generated timestamps, processing times.

**Note:** Response fields are removed from the stub, not matched against.

### `match_headers` (Boolean, default: false)

Whether to include request headers in matching criteria.

```json
{
  "match_headers": true,
  "ignore_headers": ["Date", "User-Agent"]
}
```

**Use case:** 
- `false` (default): Only match URL, method, and body
- `true`: Also match headers (useful for API key validation, content-type enforcement)

**Example with `match_headers: true`:**
```json
{
  "request": {
    "method": "POST",
    "url": "/api/users",
    "headers": {
      "Content-Type": {"equalTo": "application/json"},
      "X-API-Key": {"equalTo": "secret-key"}
    }
  }
}
```

### `ignore_request_body` (Boolean, default: false)

Ignore request body entirely in matching.

```json
{
  "ignore_request_body": true
}
```

**Use case:** Match any request to an endpoint regardless of body content.

**Example:**
```json
// With ignore_request_body: true
{
  "request": {
    "method": "POST",
    "url": "/api/users"
    // No bodyPatterns - matches any body
  }
}
```

### `ignore_delays` (Boolean, default: false)

Don't include response delays in stubs.

```json
{
  "ignore_delays": true
}
```

**Use case:** Speed up tests by removing realistic delays.

**Example:**
```json
// Without config - includes actual timing
{
  "response": {
    "status": 200,
    "fixedDelayMilliseconds": 1234
  }
}

// With ignore_delays: true
{
  "response": {
    "status": 200
    // No delay
  }
}
```

## Common Configuration Patterns

### API Testing (Strict Matching)

```json
{
  "ignore_headers": [
    "Date",
    "User-Agent",
    "X-Request-Id"
  ],
  "ignore_json_fields": [
    "timestamp",
    "requestId"
  ],
  "match_headers": false,
  "ignore_delays": true
}
```

**Use for:** Fast, deterministic tests that ignore timing and trace IDs.

### Authentication Testing

```json
{
  "ignore_headers": [
    "Date",
    "X-Request-Id"
  ],
  "ignore_json_fields": [
    "timestamp"
  ],
  "match_headers": true,
  "ignore_delays": false
}
```

**Use for:** Testing auth flows where headers matter but timing is realistic.

### Loose Matching (Development)

```json
{
  "ignore_headers": ["*"],
  "ignore_query_params": ["timestamp", "nonce", "_"],
  "ignore_json_fields": [
    "timestamp",
    "createdAt",
    "updatedAt",
    "id",
    "uuid",
    "requestId",
    "correlationId",
    "traceId"
  ],
  "match_headers": false,
  "ignore_delays": true
}
```

**Use for:** Quick prototyping where exact matching isn't critical.

### Production Capture (Security Conscious)

```json
{
  "ignore_headers": [
    "Authorization",
    "Cookie",
    "Set-Cookie",
    "X-API-Key",
    "X-Auth-Token"
  ],
  "ignore_json_fields": [
    "token",
    "accessToken",
    "refreshToken",
    "password",
    "secret",
    "apiKey"
  ],
  "ignore_response_json_fields": [
    "token",
    "accessToken",
    "refreshToken"
  ]
}
```

**Use for:** Removing sensitive data from stubs.

## Advanced Usage

### Field Path Matching

For nested JSON fields, use dot notation:

```json
{
  "ignore_json_fields": [
    "user.id",
    "user.createdAt",
    "metadata.timestamp",
    "data.items[].id"
  ]
}
```

**Note:** Currently only top-level field names are supported. Nested path support is planned.

### Pattern Matching (Planned)

Future feature for ignoring fields by pattern:

```json
{
  "ignore_patterns": [
    ".*_id$",
    ".*Timestamp$",
    "^temp.*"
  ]
}
```

## Real-World Examples

### Example 1: Payment API

**Scenario:** Capture payment API with dynamic transaction IDs and timestamps.

**Config:**
```json
{
  "ignore_headers": [
    "Date",
    "X-Request-Id",
    "X-Idempotency-Key"
  ],
  "ignore_query_params": [
    "timestamp"
  ],
  "ignore_json_fields": [
    "transactionId",
    "timestamp",
    "requestId",
    "idempotencyKey"
  ],
  "ignore_response_json_fields": [
    "transactionId",
    "processedAt",
    "serverTimestamp"
  ],
  "ignore_delays": false
}
```

**Usage:**
```bash
python tracetap2wiremock.py payment_api.json \
  --output payment_stubs/ \
  --config payment-ignore.json
```

### Example 2: User Management API

**Scenario:** CRUD operations with auto-generated UUIDs.

**Config:**
```json
{
  "ignore_headers": [
    "Date",
    "X-Correlation-Id"
  ],
  "ignore_json_fields": [
    "id",
    "uuid",
    "createdAt",
    "updatedAt",
    "lastModified"
  ],
  "ignore_response_json_fields": [
    "id",
    "uuid",
    "createdAt"
  ],
  "match_headers": false,
  "ignore_delays": true
}
```

### Example 3: Third-Party Integration

**Scenario:** OAuth flow with tokens and nonces.

**Config:**
```json
{
  "ignore_headers": [
    "Authorization",
    "Date",
    "X-Request-Id"
  ],
  "ignore_query_params": [
    "state",
    "nonce",
    "code_challenge"
  ],
  "ignore_json_fields": [
    "token",
    "accessToken",
    "refreshToken",
    "nonce",
    "state"
  ],
  "ignore_response_json_fields": [
    "access_token",
    "refresh_token",
    "expires_in",
    "issued_at"
  ],
  "ignore_delays": true
}
```

## Workflow

### 1. Capture Traffic

```bash
./tracetap-linux-x64 --listen 8080 \
  --raw-log api_traffic.json \
  --filter-host "api.example.com"
```

### 2. Analyze Captured Data

```bash
# Look at a sample request
cat api_traffic.json | jq '.requests[0]'

# Identify dynamic fields
cat api_traffic.json | jq '.requests[].req_headers.Date' | sort -u
cat api_traffic.json | jq '.requests[].req_body | fromjson | .timestamp' | sort -u
```

### 3. Create Ignore Config

Based on analysis, create `ignore-config.json`:

```json
{
  "ignore_headers": ["Date", "X-Request-Id"],
  "ignore_json_fields": ["timestamp", "id"]
}
```

### 4. Convert with Config

```bash
python tracetap2wiremock.py api_traffic.json \
  --output stubs/ \
  --config ignore-config.json \
  --priority 5
```

### 5. Test Stubs

```bash
# Start WireMock
docker run -p 8080:8080 \
  -v $(pwd)/stubs:/home/wiremock/mappings \
  wiremock/wiremock

# Test with different timestamps - should still match!
curl -X POST http://localhost:8080/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John", "timestamp": 9999999999}'

curl -X POST http://localhost:8080/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John", "timestamp": 1111111111}'

# Both should return the same mocked response
```

## Troubleshooting

### Stubs Not Matching

**Problem:** Requests don't match stubs even with ignore config.

**Solutions:**
1. Check WireMock logs: `docker logs <container>`
2. Use WireMock admin API to see mismatches:
   ```bash
   curl http://localhost:8080/__admin/requests/unmatched
   ```
3. Verify config is loaded:
   ```bash
   python tracetap2wiremock.py ... --config ignore-config.json
   # Check output for "Loaded ignore configuration"
   ```

### Too Many Fields Ignored

**Problem:** Stubs match too broadly, returning wrong responses.

**Solution:** Be more selective in ignore config:
```json
{
  "ignore_json_fields": [
    "timestamp"  // Only ignore this
    // Don't ignore everything!
  ]
}
```

### Config Not Applied

**Problem:** Fields still appearing in stubs.

**Check:**
1. Config file path is correct
2. JSON is valid: `python -m json.tool ignore-config.json`
3. Field names match exactly (case-sensitive for JSON fields)
4. Headers are case-insensitive

### Performance Issues

**Problem:** Stub matching is slow.

**Solution:** Use more specific matching:
```json
{
  "match_headers": false,  // Faster
  "ignore_request_body": false  // Keep body matching
}
```

## Best Practices

### 1. Start Minimal

Begin with a small ignore list:
```json
{
  "ignore_headers": ["Date"],
  "ignore_json_fields": ["timestamp"]
}
```

Add more as needed based on test failures.

### 2. Document Your Config

Add comments explaining why fields are ignored:
```json
{
  "_comment": "Payment API - Ignoring transaction IDs",
  "ignore_json_fields": [
    "transactionId"  // Generated by payment gateway
  ]
}
```

### 3. Use Different Configs for Different APIs

```bash
# Payment API
python tracetap2wiremock.py payment.json \
  --config payment-ignore.json \
  --output payment-stubs/

# User API  
python tracetap2wiremock.py users.json \
  --config users-ignore.json \
  --output user-stubs/
```

### 4. Version Control Your Configs

```bash
git add ignore-configs/
git commit -m "Add WireMock ignore configs for all APIs"
```

### 5. Test Both With and Without Delays

```bash
# With delays (realistic)
python tracetap2wiremock.py api.json \
  --output stubs-realistic/ \
  --config config.json

# Without delays (fast tests)
python tracetap2wiremock.py api.json \
  --output stubs-fast/ \
  --config config-no-delays.json
```

Where `config-no-delays.json`:
```json
{
  "ignore_delays": true,
  // ... other config
}
```

## Reference

### Complete Configuration Schema

```json
{
  "ignore_headers": ["string"],
  "ignore_query_params": ["string"],
  "ignore_json_fields": ["string"],
  "ignore_response_json_fields": ["string"],
  "match_headers": false,
  "ignore_request_body": false,
  "ignore_delays": false
}
```

### Command-Line Reference

```bash
python tracetap2wiremock.py INPUT_FILE \
  --output OUTPUT_DIR \
  [--config CONFIG_FILE] \
  [--priority PRIORITY] \
  [--matching {url|urlPath|urlPattern|urlPathPattern}]
```

## See Also

- [WireMock Request Matching Documentation](https://wiremock.org/docs/request-matching/)
- [TraceTap README](../README.md)
- [WireMock Workflow Guide](WIREMOCK_WORKFLOW.md)

---

**Questions?** Open an issue on GitHub or check the discussions forum.