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
tracetap capture --port 8080 --raw-log my-session.json
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

### Workflow 1: Capture and Generate Tests

**Use case:** Document new API and create tests

```bash
# Terminal 1: Start capture
tracetap capture \
  --port 8080 \
  --session-name "user-feature" \
  --raw-log user-feature.json

# Terminal 2: Use your application
# Click through the user feature manually
# Or run your existing tests

# Back to Terminal 1: Stop with Ctrl+C

# Generate Playwright tests with AI
tracetap-playwright user-feature.json \
  --ai-suggestions \
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
  --raw-log debug-session.json

# Reproduce the issue
# Watch real-time output in terminal

# Review captured traffic
cat debug-session.json | jq '.requests[] | {method, url, status: .response.status}'

# Extract just the failing requests
cat debug-session.json | jq '.requests[] | select(.response.status >= 400)'
```

**Result:** Complete request/response details for debugging.

### Workflow 3: API Contract Validation

**Use case:** Ensure your changes don't break existing API

```bash
# Capture baseline (first time)
tracetap capture --port 8080 --raw-log baseline.json
# Use the app...
# Ctrl+C

# Generate baseline contract
tracetap contract create baseline.json \
  --output contracts/baseline.yaml

# Later, after making changes:
tracetap capture --port 8080 --raw-log current.json
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
  --raw-log "captures/$FEATURE_NAME.json" \
  --verbose &

CAPTURE_PID=$!
echo "Capture started (PID: $CAPTURE_PID)"

echo "Develop your feature... Press Enter when done"
read

# Stop capture
kill $CAPTURE_PID

echo "Generating tests with AI..."
tracetap-playwright "captures/$FEATURE_NAME.json" \
  --ai-suggestions \
  --output "tests/$FEATURE_NAME.spec.ts"

echo "Complete! Check:"
echo "  - Captures: captures/$FEATURE_NAME.json"
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
tracetap capture --port 8080 --raw-log test-data/scenarios/happy-path.json
# ... test happy path ...

# Capture error cases
tracetap capture --port 8080 --raw-log test-data/scenarios/error-cases.json
# ... trigger errors ...

# Capture edge cases
tracetap capture --port 8080 --raw-log test-data/scenarios/edge-cases.json
# ... test edge cases ...

# Generate test suite with AI
for scenario in test-data/scenarios/*.json; do
  name=$(basename "$scenario" .json)
  tracetap-playwright "$scenario" \
    --ai-suggestions \
    --output "tests/regression/$name.spec.ts"
done

echo "Run tests with: npx playwright test tests/regression/"
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
  --raw-log auth-debug.json

# Extract auth headers
cat auth-debug.json | jq '.requests[] | {url, auth: .headers.Authorization}'

# Check for token patterns
cat auth-debug.json | jq -r '.requests[].headers.Authorization' | sort -u
```

### Debug Slow API Calls

```bash
# Capture with timing
tracetap capture --port 8080 --raw-log timing.json

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
  tracetap capture --port 8080 --raw-log "runs/run-$i.json" &
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
tracetap capture --port 8080 --raw-log output.json

# Good
tracetap capture \
  --session-name "user-auth-flow-2024-01-15" \
  --raw-log captures/user-auth.json
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

# Quick test generation
alias tttest='tracetap-playwright'

# Capture with AI processing
alias ttai='tracetap capture --port 8080 && tracetap-playwright'
```

Usage:
```bash
ttcap --raw-log session.json
tttest session.json --ai-suggestions --output tests/
```

### Tip 4: Organize Captures

```bash
# Create organized structure
mkdir -p captures/{features,bugs,exploration}

# Save to appropriate location
tracetap capture --raw-log captures/features/user-registration.json
tracetap capture --raw-log captures/bugs/issue-123.json
tracetap capture --raw-log captures/exploration/new-api.json
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
  --raw-log $TRACETAP_OUTPUT_DIR/session.json
```

### Tip 6: Combine with Git

```bash
# Capture before committing
git add .
tracetap capture --port 8080 --raw-log pre-commit-api.json &
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
  "tracetap-playwright captures/latest.json --ai-suggestions --output tests/api.spec.ts"
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
tracetap capture --port 8080 --raw-log part1.json
# Ctrl+C after 5 minutes
tracetap capture --port 8080 --raw-log part2.json
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
# Check request type
cat capture.json | jq '.requests[] | select(.response.body == null) | .url'
```

---

## Quick Reference

### Essential Commands

```bash
# Start capture
tracetap capture --port 8080 --raw-log session.json

# Verbose capture
tracetap capture --port 8080 --verbose

# Generate tests with AI
tracetap-playwright capture.json --ai-suggestions --output tests/

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
