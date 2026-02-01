# Local Development Workflow

Quick start guide and daily development workflows for using TraceTap during local development.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Common Workflows](#common-workflows)
3. [Development Patterns](#development-patterns)
4. [Debugging Workflow](#debugging-workflow)
5. [Tips and Best Practices](#tips-and-best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 5-Minute Setup

```bash
# 1. Install TraceTap
pip install tracetap

# 2. Install certificate (one-time)
tracetap cert install

# 3. Start capturing
tracetap capture --port 8080 --export my-session.json
```

In another terminal:
```bash
# 4. Configure your app to use proxy
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# 5. Run your app
npm start
```

**That's it!** All HTTP/HTTPS traffic is now being captured.

---

## Common Workflows

### Workflow 1: Capture → Generate → Test

**Use case:** Document new API and create tests

```bash
# Terminal 1: Start capture
tracetap capture \
  --port 8080 \
  --session-name "user-feature" \
  --export user-feature.json

# Terminal 2: Use your application
# Click through the user feature manually
# Or run your existing tests

# Back to Terminal 1: Stop with Ctrl+C

# Generate Postman collection
tracetap-ai-postman user-feature.json \
  --output user-api-collection.json \
  --ai

# Generate Playwright tests
tracetap-playwright user-feature.json \
  --output tests/user-feature.spec.ts

# Run the tests
npx playwright test tests/user-feature.spec.ts
```

**Result:** Complete API documentation + automated tests in minutes.

### Workflow 2: Debug API Issues

**Use case:** Understand what's happening with a failing API call

```bash
# Start verbose capture
tracetap capture \
  --port 8080 \
  --verbose \
  --debug \
  --export debug-session.json

# Reproduce the issue
# Watch real-time output in terminal

# Review captured traffic
cat debug-session.json | jq '.requests[] | {method, url, status: .response.status}'

# Extract just the failing requests
cat debug-session.json | jq '.requests[] | select(.response.status >= 400)'
```

**Result:** Complete request/response details for debugging.

### Workflow 3: Mock External APIs

**Use case:** Develop offline or against unstable APIs

```bash
# Step 1: Capture real API responses (once)
tracetap capture \
  --port 8080 \
  --filter api.production.com \
  --export prod-api-baseline.json

# Stop after capturing sufficient traffic

# Step 2: Start mock server
tracetap-replay.py mock prod-api-baseline.json \
  --port 8080

# Step 3: Point your app to localhost:8080
# Develop offline with realistic responses!
```

**Result:** Work without internet or against flaky external services.

### Workflow 4: API Contract Validation

**Use case:** Ensure your changes don't break existing API

```bash
# Capture baseline (first time)
tracetap capture --port 8080 --export baseline.json
# Use the app...
# Ctrl+C

# Generate baseline contract
tracetap contract create baseline.json \
  --output contracts/baseline.yaml

# Later, after making changes:
tracetap capture --port 8080 --export current.json
# Test the changes...
# Ctrl+C

# Generate current contract
tracetap contract create current.json \
  --output contracts/current.yaml

# Compare
tracetap contract verify \
  --baseline contracts/baseline.yaml \
  --current contracts/current.yaml

# Review output for breaking changes
```

**Result:** Catch breaking changes before pushing to production.

### Workflow 5: Update Existing Collections

**Use case:** Keep Postman collections in sync with API changes

```bash
# Capture new traffic
tracetap capture --port 8080 --export new-endpoints.json

# Update existing collection
tracetap-update-collection.py \
  existing-collection.json \
  new-endpoints.json \
  --output updated-collection.json \
  --merge-strategy smart

# Import into Postman
# File → Import → updated-collection.json
```

**Result:** Collection stays up-to-date with minimal effort.

---

## Development Patterns

### Pattern 1: Feature Development

```bash
#!/bin/bash
# dev-flow.sh

FEATURE_NAME=$1

echo "Starting development session: $FEATURE_NAME"

# Start capture
tracetap capture \
  --port 8080 \
  --session-name "$FEATURE_NAME" \
  --export "captures/$FEATURE_NAME.json" \
  --verbose &

CAPTURE_PID=$!
echo "Capture started (PID: $CAPTURE_PID)"

echo "Develop your feature... Press Enter when done"
read

# Stop capture
kill $CAPTURE_PID

echo "Generating documentation..."
tracetap-ai-postman "captures/$FEATURE_NAME.json" \
  --output "docs/$FEATURE_NAME-api.json" \
  --ai

echo "Generating tests..."
tracetap-playwright "captures/$FEATURE_NAME.json" \
  --output "tests/$FEATURE_NAME.spec.ts"

echo "✓ Complete! Check:"
echo "  - Docs: docs/$FEATURE_NAME-api.json"
echo "  - Tests: tests/$FEATURE_NAME.spec.ts"
```

Usage:
```bash
chmod +x dev-flow.sh
./dev-flow.sh user-registration
```

### Pattern 2: API Exploration

```bash
# Quick exploration of unknown API
tracetap capture \
  --port 8080 \
  --filter api.example.com \
  --verbose

# In another terminal, interact with the API
curl -x http://localhost:8080 https://api.example.com/users

# Watch the output to understand the API structure
```

### Pattern 3: Regression Testing Setup

```bash
# Create test data directory
mkdir -p test-data/scenarios

# Capture happy path
tracetap capture --port 8080 --export test-data/scenarios/happy-path.json
# ... test happy path ...

# Capture error cases
tracetap capture --port 8080 --export test-data/scenarios/error-cases.json
# ... trigger errors ...

# Capture edge cases
tracetap capture --port 8080 --export test-data/scenarios/edge-cases.json
# ... test edge cases ...

# Generate test suite
for scenario in test-data/scenarios/*.json; do
  name=$(basename "$scenario" .json)
  tracetap-playwright "$scenario" --output "tests/regression/$name.spec.ts"
done

echo "Run tests with: npx playwright test tests/regression/"
```

### Pattern 4: Environment Comparison

```bash
# Capture from staging
HTTP_PROXY=http://localhost:8080 \
  curl https://staging-api.example.com/users > /dev/null 2>&1 &
tracetap capture --port 8080 --export staging-traffic.json

# Replay to production (read-only endpoints only!)
tracetap-replay.py replay staging-traffic.json \
  --target https://api.example.com \
  --filter-method GET \
  --output comparison.json

# Check differences
cat comparison.json | jq '.requests[] | select(.response_matches == false)'
```

---

## Debugging Workflow

### Debug API Request/Response

```bash
# Capture with full details
tracetap capture \
  --port 8080 \
  --verbose \
  --raw-log debug.json

# Reproduce issue

# Analyze specific request
cat debug.json | jq '.requests[] | select(.url | contains("/problematic-endpoint"))'

# Check headers
cat debug.json | jq '.requests[0].headers'

# Check request body
cat debug.json | jq -r '.requests[0].body'

# Check response
cat debug.json | jq '.requests[0].response'
```

### Debug Authentication Issues

```bash
# Capture with header logging
tracetap capture \
  --port 8080 \
  --verbose \
  --export auth-debug.json

# Extract auth headers
cat auth-debug.json | jq '.requests[] | {url, auth: .headers.Authorization}'

# Check for token patterns
cat auth-debug.json | jq -r '.requests[].headers.Authorization' | sort -u
```

### Debug Slow API Calls

```bash
# Capture with timing
tracetap capture --port 8080 --export timing.json

# Find slow requests (>1000ms)
cat timing.json | jq '.requests[] | select(.duration_ms > 1000) | {url, duration_ms}'

# Sort by duration
cat timing.json | jq -r '.requests[] | [.duration_ms, .url] | @csv' | sort -rn
```

### Debug Intermittent Failures

```bash
# Capture multiple runs
for i in {1..10}; do
  echo "Run $i"
  tracetap capture --port 8080 --export "runs/run-$i.json" &
  PID=$!
  npm test
  kill $PID
  sleep 2
done

# Find failed requests
for f in runs/*.json; do
  echo "=== $f ==="
  cat "$f" | jq '.requests[] | select(.response.status >= 400) | {url, status: .response.status}'
done
```

---

## Tips and Best Practices

### Tip 1: Use Session Names

Always name your sessions for easy identification:

```bash
# Bad
tracetap capture --port 8080 --export output.json

# Good
tracetap capture \
  --session-name "user-auth-flow-2024-01-15" \
  --export captures/user-auth.json
```

### Tip 2: Filter Aggressively

Capture only what you need:

```bash
# Capture specific host
tracetap capture --filter api.myapp.com

# Capture specific endpoints
tracetap capture --filter-regex "^/api/v1/(users|products)"

# Multiple filters (OR logic)
tracetap capture --filter api.myapp.com --filter cdn.myapp.com
```

### Tip 3: Use Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
# Quick capture
alias ttcap='tracetap capture --port 8080 --verbose'

# Quick mock
alias ttmock='tracetap-replay.py mock'

# Quick test generation
alias tttest='tracetap-playwright'

# Capture with AI processing
alias ttai='tracetap capture --port 8080 && tracetap-ai-postman'
```

Usage:
```bash
ttcap --export session.json
tttest session.json --output tests/
```

### Tip 4: Organize Captures

```bash
# Create organized structure
mkdir -p captures/{features,bugs,exploration}

# Save to appropriate location
tracetap capture --export captures/features/user-registration.json
tracetap capture --export captures/bugs/issue-123.json
tracetap capture --export captures/exploration/new-api.json
```

### Tip 5: Use Environment Variables

```bash
# .env.local
TRACETAP_PORT=8080
TRACETAP_OUTPUT_DIR=./captures
ANTHROPIC_API_KEY=sk-...

# Load in your workflow
source .env.local

tracetap capture \
  --port $TRACETAP_PORT \
  --export $TRACETAP_OUTPUT_DIR/session.json
```

### Tip 6: Combine with Git

```bash
# Capture before committing
git add .
tracetap capture --port 8080 --export pre-commit-api.json &
PID=$!
npm test
kill $PID

# Generate contract
tracetap contract create pre-commit-api.json --output contract.yaml

# Commit with contract
git add contract.yaml
git commit -m "feat: add user feature

API Contract: contract.yaml"
```

### Tip 7: Use Watch Mode

```bash
# Auto-regenerate tests on capture changes
npm install -g nodemon

nodemon --watch captures/ --ext json --exec \
  "tracetap-playwright captures/latest.json --output tests/api.spec.ts"
```

### Tip 8: Quick Postman Import

```bash
# Generate and open in Postman in one command
tracetap-ai-postman capture.json --output collection.json && \
  open "https://www.postman.com/import" && \
  echo "Import: $PWD/collection.json"
```

---

## Troubleshooting

### Issue 1: No Traffic Captured

**Symptoms:** Capture runs but no requests recorded

**Checklist:**
```bash
# 1. Verify proxy is running
lsof -i :8080

# 2. Check proxy environment variables
echo $HTTP_PROXY
echo $HTTPS_PROXY

# 3. Test proxy manually
curl -x http://localhost:8080 http://example.com

# 4. Check if app uses proxy
# Some apps ignore env vars, configure directly
```

**Solution for Node.js:**
```javascript
// Set proxy in code
const axios = require('axios');
axios.defaults.proxy = {
  host: 'localhost',
  port: 8080
};
```

### Issue 2: Certificate Errors

**Symptoms:** `SSL_ERROR_UNKNOWN_CA_ALERT`, `CERT_AUTHORITY_INVALID`

**Solution:**
```bash
# Reinstall certificate
tracetap cert install --force

# Verify
tracetap cert verify

# If still fails, add to app config
NODE_TLS_REJECT_UNAUTHORIZED=0 npm start  # Node.js
```

### Issue 3: Large Captures

**Symptoms:** Capture files too large, slow to process

**Solution:**
```bash
# Use focused filtering
tracetap capture \
  --filter api.myapp.com \
  --filter-regex "^/api/v1" \
  --exclude-headers "Cookie,Set-Cookie" \
  --max-body-size 1000

# Split by time
tracetap capture --port 8080 --export part1.json
# Ctrl+C after 5 minutes
tracetap capture --port 8080 --export part2.json
```

### Issue 4: Port Already in Use

**Symptoms:** `Error: Address already in use`

**Solution:**
```bash
# Find process using port
lsof -i :8080

# Kill it
kill -9 <PID>

# Or use different port
tracetap capture --port 8081
export HTTP_PROXY=http://localhost:8081
```

### Issue 5: Missing Responses

**Symptoms:** Requests captured but responses empty

**Possible causes:**
- App timeout before response
- Non-HTTP traffic
- Websockets (not supported)

**Solution:**
```bash
# Increase timeout (if applicable in your app)
# Or check request type
cat capture.json | jq '.requests[] | select(.response.body == null) | .url'
```

---

## Quick Reference

### Essential Commands

```bash
# Start capture
tracetap capture --port 8080 --export session.json

# Verbose capture
tracetap capture --port 8080 --verbose

# Generate Postman
tracetap-ai-postman capture.json --output collection.json --ai

# Generate tests
tracetap-playwright capture.json --output tests/

# Start mock server
tracetap-replay.py mock capture.json --port 8080

# Create contract
tracetap contract create capture.json --output contract.yaml

# Verify contract
tracetap contract verify --baseline old.yaml --current new.yaml
```

### Proxy Configuration

```bash
# Bash/Zsh
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# PowerShell
$env:HTTP_PROXY="http://localhost:8080"
$env:HTTPS_PROXY="http://localhost:8080"

# Node.js
process.env.HTTP_PROXY = 'http://localhost:8080'

# Python requests
proxies = {'http': 'http://localhost:8080', 'https': 'http://localhost:8080'}
requests.get(url, proxies=proxies)

# curl
curl -x http://localhost:8080 https://api.example.com
```

### File Organization

```bash
project/
├── captures/           # Raw traffic captures
│   ├── features/
│   ├── bugs/
│   └── exploration/
├── contracts/          # API contracts
│   ├── baseline.yaml
│   └── current.yaml
├── tests/             # Generated tests
│   ├── api/
│   └── regression/
└── docs/              # API documentation
    └── collections/
```

---

## Related Documentation

- [Playwright Integration](./playwright-integration.md) - Detailed Playwright workflows
- [CI/CD Integration](./ci-cd-integration.md) - Automate in pipelines
- [Contract-First](./contract-first.md) - Contract-based development
- [TraceTap README](../../README.md) - Complete feature reference

---

**Next Steps:**
1. Try the [5-minute quick start](#quick-start)
2. Explore [common workflows](#common-workflows)
3. Set up your own [development patterns](#development-patterns)
