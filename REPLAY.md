# TraceTap Replay & Mock Server

Advanced traffic replay and mock server functionality for captured HTTP traffic.

## Overview

TraceTap Replay & Mock provides cutting-edge capabilities for replaying captured HTTP traffic and creating intelligent mock servers. Built with AI-powered features using Claude, it enables sophisticated API testing, development, and validation workflows.

## Features

### 🔄 Traffic Replay
- **Intelligent Replay**: Replay captured requests to any target server
- **Variable Substitution**: Dynamic variable replacement (IDs, tokens, timestamps)
- **Concurrent Execution**: Multi-threaded replay with configurable workers
- **Response Comparison**: Automatic comparison of original vs replayed responses
- **Performance Metrics**: Detailed timing and success rate tracking
- **Flexible Filtering**: Filter requests by method, URL patterns, or custom logic

### 🎭 Mock HTTP Server
- **FastAPI-Based**: High-performance async mock server
- **Intelligent Matching**: Multiple strategies (exact, fuzzy, pattern, semantic)
- **Request Scoring**: Similarity-based matching with configurable weights
- **Chaos Engineering**: Simulate failures, delays, and errors
- **Admin API**: Runtime configuration and metrics
- **AI-Enhanced Responses**: Optional Claude-powered response generation

### 🤖 AI-Powered Intelligence
- **Variable Extraction**: Auto-detect IDs, tokens, UUIDs, JWTs using Claude
- **Scenario Generation**: Generate YAML test scenarios from captures
- **Semantic Matching**: AI-powered request matching by intent
- **Smart Responses**: Context-aware mock response generation

### 📝 YAML Scenarios
- **Declarative Testing**: Define test flows in YAML
- **Variable Resolution**: `${variable}` syntax with nested support
- **Response Extraction**: JSONPath and regex extraction
- **Assertion Validation**: Status codes, headers, body, timing
- **Environment Support**: Multiple environment configurations

## Installation

```bash
# Install replay dependencies
pip install -r requirements-replay.txt

# For AI features, set your Anthropic API key
export ANTHROPIC_API_KEY='your-api-key'
```

## Quick Start

### 1. Replay Traffic

Replay captured traffic to a different server:

```bash
# Basic replay
python3 tracetap-replay.py replay session.json --target http://localhost:8080

# With verbose output
python3 tracetap-replay.py replay session.json --target http://localhost:8080 --verbose

# With variable substitution
python3 tracetap-replay.py replay session.json --target http://localhost:8080 \
  --variables user_id=12345 auth_token=abc123

# Filter by method
python3 tracetap-replay.py replay session.json --target http://localhost:8080 \
  --filter-method GET POST

# Save results
python3 tracetap-replay.py replay session.json --target http://localhost:8080 \
  --output results.json
```

### 2. Start Mock Server

Start a mock server serving captured responses:

```bash
# Basic mock server
python3 tracetap-replay.py mock session.json --port 8080

# With fuzzy matching (default)
python3 tracetap-replay.py mock session.json --port 8080 --strategy fuzzy

# With chaos engineering
python3 tracetap-replay.py mock session.json --port 8080 \
  --chaos --chaos-rate 0.1

# With added delay
python3 tracetap-replay.py mock session.json --port 8080 --delay 100

# Bind to all interfaces
python3 tracetap-replay.py mock session.json --host 0.0.0.0 --port 8080
```

Once running, the mock server provides:
- Main API: `http://localhost:8080/*` (serves mocked responses)
- Admin API: `http://localhost:8080/__admin__/metrics` (server metrics)
- Config API: `http://localhost:8080/__admin__/config` (runtime config)

### 3. Extract Variables

Use AI to extract variables from captures:

```bash
# Extract with Claude AI
python3 tracetap-replay.py variables session.json --ai

# Save to file
python3 tracetap-replay.py variables session.json --ai --output variables.json

# Without AI (regex fallback)
python3 tracetap-replay.py variables session.json
```

Example output:
```
🔍 TraceTap Variable Extraction
   Captures: 47

✓ Claude AI enabled for intelligent variable detection

📊 Found 5 variables:

  • user_id (integer)
    Locations: url_path, query_param
    Examples: 12345, 67890, 45678
    Description: User identifier in API paths
    Pattern: \d+

  • auth_token (jwt)
    Locations: header
    Examples: eyJhbGc...
    Description: JWT authentication token
    Pattern: eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*
```

### 4. Generate Test Scenarios

Generate YAML scenarios with AI:

```bash
# Generate with AI
python3 tracetap-replay.py scenario session.json --ai \
  --intent "User registration and verification flow" \
  --output test-scenario.yaml

# With custom name
python3 tracetap-replay.py scenario session.json --ai \
  --name "E2E User Flow" \
  --intent "Complete user registration, login, and profile update" \
  --output e2e-test.yaml
```

Example generated scenario:

```yaml
name: "User Registration Flow"
description: "Complete user signup and verification"
environment: staging

variables:
  base_url: "https://api.example.com"
  test_email: "test@example.com"

steps:
  - id: register
    name: "Register new user"
    request:
      method: POST
      url: "${base_url}/api/users"
      body: '{"email": "${test_email}"}'
    expect:
      status: 201
      body_contains: ["id", "email"]
    extract:
      user_id: "$.id"

  - id: verify
    name: "Verify email"
    request:
      method: POST
      url: "${base_url}/api/users/${user_id}/verify"
    expect:
      status: 200
```

## Python API

### Traffic Replay

```python
from tracetap.replay import TrafficReplayer

# Create replayer
replayer = TrafficReplayer('session.json')

# Replay to different server
result = replayer.replay(
    target_base_url='http://localhost:8080',
    variables={'user_id': '12345'},
    max_workers=10,
    verbose=True
)

# Check results
print(f"Success rate: {result.success_rate}%")
print(f"Avg response time: {result.avg_duration_ms}ms")

# Save results
replayer.save_result(result, 'replay-results.json')
```

### Variable Extraction

```python
from tracetap.replay import VariableExtractor

# Load captures
with open('session.json') as f:
    captures = json.load(f)['requests']

# Extract with AI
extractor = VariableExtractor(
    captures=captures,
    use_ai=True,
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

variables = extractor.extract_variables(verbose=True)

for var in variables:
    print(f"{var.name}: {var.type}")
    print(f"  Examples: {var.example_values}")
    print(f"  Locations: {var.locations}")
```

### Mock Server

```python
from tracetap.mock import MockServer, MockConfig

# Configure server
config = MockConfig(
    host='0.0.0.0',
    port=8080,
    matching_strategy='fuzzy',
    chaos_enabled=True,
    chaos_failure_rate=0.1
)

# Create and start server
server = MockServer('session.json', config=config)
server.start()  # Blocking

# Or get app for custom deployment
app = server.get_app()
# Use with: uvicorn app:app --host 0.0.0.0 --port 8080
```

### Request Matching

```python
from tracetap.mock import RequestMatcher

# Create matcher
matcher = RequestMatcher(
    captures=captures,
    strategy='fuzzy',
    min_score=0.7
)

# Find match
result = matcher.find_match(
    method='GET',
    url='https://api.example.com/users/123',
    headers={'Authorization': 'Bearer token'},
    body=None
)

if result.matched:
    print(f"Match found! Score: {result.score.total_score}")
    print(f"Matched URL: {result.capture['url']}")
```

### Response Generation

```python
from tracetap.mock import ResponseGenerator

# Create generator with AI
generator = ResponseGenerator(
    use_ai=True,
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

# Generate intelligent response
response = generator.generate_intelligent(
    capture=matched_capture,
    request_context={
        'method': 'GET',
        'url': 'https://api.example.com/users/123',
        'user_id': '123'
    },
    intent="Return user profile"
)

print(response['resp_body'])
```

## YAML Scenario Format

### Basic Structure

```yaml
name: "Scenario Name"
description: "What this scenario tests"
environment: default  # or staging, production, etc.

variables:
  base_url: "https://api.example.com"
  api_key: "your-api-key"

steps:
  - id: step1
    name: "Description"
    request:
      method: GET
      url: "${base_url}/endpoint"
      headers:
        Authorization: "Bearer ${api_key}"
    expect:
      status: 200
    extract:
      var_name: "$.response.field"
```

### Variable Types

```yaml
variables:
  # Simple variables
  base_url: "https://api.example.com"

  # Environment variables (access with ${env.VAR})
  api_key: "${env.API_KEY}"

  # Extracted from previous steps (access with ${step.id.var})
  user_id: "${step.register.user_id}"
```

### Request Configuration

```yaml
request:
  method: POST
  url: "${base_url}/users"
  headers:
    Content-Type: "application/json"
    Authorization: "Bearer ${auth_token}"
  body: |
    {
      "name": "${user_name}",
      "email": "${user_email}"
    }
```

### Response Extraction

```yaml
extract:
  # JSONPath extraction
  user_id: "$.id"
  user_email: "$.email"
  token: "$.auth.token"

  # Regex extraction
  session_id: "regex:session=([a-f0-9]+)"
```

### Assertions

```yaml
expect:
  # Status code
  status: 200

  # Or multiple acceptable codes
  status: [200, 201]

  # Headers
  headers:
    Content-Type: "application/json"

  # Body content
  body_contains:
    - "success"
    - "user_id"

  # Response time
  response_time_ms: "< 500"
```

### Multiple Environments

```yaml
environment: staging

environments:
  staging:
    base_url: "https://staging-api.example.com"
    api_key: "staging-key"

  production:
    base_url: "https://api.example.com"
    api_key: "production-key"
```

## Mock Server Matching Strategies

### Exact Matching

Full URL and method must match exactly:

```python
config = MockConfig(matching_strategy='exact')
```

- Pros: Predictable, no ambiguity
- Cons: Brittle, doesn't handle parameter variations

### Fuzzy Matching (Default)

Intelligent similarity scoring with configurable weights:

```python
config = MockConfig(matching_strategy='fuzzy')
```

Components:
- **Path similarity**: Recognizes ID patterns, handles path variations
- **Query parameters**: Optional matching with similarity scoring
- **Headers**: Matches important headers (auth, content-type)
- **Body**: JSON-aware body comparison

Scoring example:
- `/users/123` matches `/users/456` (different IDs, 80% score)
- `/users?limit=10` matches `/users?limit=20` (different param, 90% score)

### Pattern Matching

Wildcard and pattern support:

```python
config = MockConfig(matching_strategy='pattern')
```

Patterns:
- `/users/*` - matches `/users/123`, `/users/456`
- `/users/**` - matches `/users/123/posts/456`
- `/users/{id}` - named parameter

### Semantic Matching (AI-Powered)

AI understands request intent:

```python
matcher = RequestMatcher(captures, strategy='semantic', api_key='...')
```

Example:
- Request: `GET /api/v2/users/profile`
- Matches: `GET /api/v1/user/me` (different endpoint, same intent)

## Chaos Engineering

Simulate real-world failures:

```bash
# 10% failure rate, 500 errors
python3 tracetap-replay.py mock session.json --chaos --chaos-rate 0.1

# With added latency
python3 tracetap-replay.py mock session.json --chaos --chaos-rate 0.05 --delay 200
```

Python API:

```python
config = MockConfig(
    chaos_enabled=True,
    chaos_failure_rate=0.15,  # 15% failures
    chaos_error_status=503,   # Service Unavailable
    add_delay_ms=100          # 100ms delay
)
```

## Response Transformers

Add custom response transformations:

```python
from tracetap.mock import (
    ResponseGenerator,
    add_timestamp_transformer,
    cors_headers_transformer,
    pretty_json_transformer
)

generator = ResponseGenerator()

# Add transformers
generator.add_transformer(add_timestamp_transformer)
generator.add_transformer(cors_headers_transformer)
generator.add_transformer(pretty_json_transformer)

# Custom transformer
def add_version_transformer(response, context):
    body = json.loads(response['resp_body'])
    body['api_version'] = '2.0'
    response['resp_body'] = json.dumps(body)
    return response

generator.add_transformer(add_version_transformer)
```

## Admin API

When mock server is running:

```bash
# Get metrics
curl http://localhost:8080/__admin__/metrics

# Response:
{
  "total_requests": 150,
  "matched_requests": 145,
  "unmatched_requests": 5,
  "match_rate": 96.67,
  "uptime_seconds": 3600.5
}

# Update config at runtime
curl -X POST http://localhost:8080/__admin__/config \
  -H "Content-Type: application/json" \
  -d '{"chaos_enabled": true, "chaos_failure_rate": 0.2}'

# List all captures
curl http://localhost:8080/__admin__/captures

# Reset metrics
curl -X POST http://localhost:8080/__admin__/reset
```

## Examples

### Example 1: API Development

Develop against a mock of production API:

```bash
# 1. Capture production traffic
mitmproxy --mode reverse:https://api.production.com \
  -s src/tracetap/capture/tracetap_addon.py \
  --set tracetap_output=prod-api.json

# 2. Start local mock server
python3 tracetap-replay.py mock prod-api.json --port 8080

# 3. Point your app to localhost:8080
# Develop offline with realistic responses!
```

### Example 2: Integration Testing

Create automated integration tests:

```bash
# 1. Extract variables with AI
python3 tracetap-replay.py variables session.json --ai --output vars.json

# 2. Generate test scenario
python3 tracetap-replay.py scenario session.json --ai \
  --intent "Complete user registration flow" \
  --output test.yaml

# 3. Run scenario (replay with assertions)
python3 tracetap-replay.py replay-scenario test.yaml --target http://staging-api.com
```

### Example 3: Load Testing

Replay traffic with high concurrency:

```bash
# Replay with 50 concurrent workers
python3 tracetap-replay.py replay session.json \
  --target http://localhost:8080 \
  --workers 50 \
  --output load-test-results.json

# Analyze results
python3 -c "
import json
with open('load-test-results.json') as f:
    data = json.load(f)
print(f'Success rate: {data[\"success_rate\"]}%')
print(f'Avg response time: {data[\"avg_duration_ms\"]}ms')
print(f'Status match rate: {data[\"status_match_rate\"]}%')
"
```

## Architecture

```
tracetap/
├── replay/
│   ├── __init__.py
│   ├── replayer.py          # HTTP replay engine
│   ├── variables.py         # AI variable extraction
│   └── replay_config.py     # YAML scenario support
└── mock/
    ├── __init__.py
    ├── server.py            # FastAPI mock server
    ├── matcher.py           # Request matching engine
    └── generator.py         # AI response generation
```

## Performance

- **Replay**: 100+ requests/second with 10 workers
- **Mock Server**: 1000+ requests/second (FastAPI async)
- **Matching**: Sub-millisecond for fuzzy matching
- **AI Operations**: 2-5 seconds for Claude analysis

## Troubleshooting

### Import Errors

```bash
# Install replay dependencies
pip install -r requirements-replay.txt
```

### AI Features Not Working

```bash
# Set API key
export ANTHROPIC_API_KEY='your-key'

# Verify
python3 -c "import anthropic; print('OK')"
```

### Mock Server Port Already in Use

```bash
# Use different port
python3 tracetap-replay.py mock session.json --port 9090

# Or kill existing process
lsof -ti:8080 | xargs kill
```

### SSL Verification Errors

```bash
# Disable SSL verification for replay
python3 tracetap-replay.py replay session.json --no-verify-ssl --target https://...
```

## Contributing

Contributions welcome! Key areas:

- Additional matching strategies
- More response transformers
- Test scenario features
- Performance optimizations
- Documentation improvements

## License

Same as TraceTap main project.

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Anthropic Claude](https://www.anthropic.com/) - AI-powered intelligence
- [requests](https://requests.readthedocs.io/) - HTTP client
- [jsonpath-ng](https://github.com/h2non/jsonpath-ng) - JSONPath extraction
