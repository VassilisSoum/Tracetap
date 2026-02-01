# Troubleshooting Guide

Common issues and their solutions.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Capture Issues](#capture-issues)
- [SSL/HTTPS Issues](#ssihttps-issues)
- [Test Generation Issues](#test-generation-issues)
- [Replay & Mock Server Issues](#replay--mock-server-issues)
- [CI/CD Issues](#cicd-issues)
- [Performance Issues](#performance-issues)
- [Getting Help](#getting-help)

---

## Installation Issues

### ImportError: No module named mitmproxy

**Problem**: `ModuleNotFoundError: No module named 'mitmproxy'`

**Solution**:
```bash
# Install requirements
pip install -r requirements.txt

# Or install mitmproxy directly
pip install mitmproxy

# Verify installation
python -c "import mitmproxy; print(mitmproxy.__version__)"
```

### Python Version Too Old

**Problem**: `SyntaxError` or module compatibility issues

**Solution**:
```bash
# Check Python version
python --version

# You need Python 3.8 or higher
# If you have multiple Python versions:
python3.11 tracetap.py --help

# Or create virtual environment with correct version
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Permission Denied

**Problem**: `PermissionError: [Errno 13] Permission denied`

**Solution**:
```bash
# Make script executable
chmod +x tracetap.py

# Or run with python explicitly
python tracetap.py --help

# If it's a port permission issue, use higher port
python tracetap.py --listen 8080  # Instead of 80
```

### Virtual Environment Issues

**Problem**: Can't import modules even after installing

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows PowerShell

# Check which Python is running
which python
which pip

# Should point to venv directory

# Reinstall requirements
pip install -r requirements.txt
```

---

## Capture Issues

### No Requests Being Captured

**Problem**: Started TraceTap but no requests appear

**Solutions**:

1. **Check proxy is configured**:
```bash
# Should show your proxy
echo $HTTP_PROXY
echo $HTTPS_PROXY

# Set if not set
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
```

2. **Check application uses proxy**:
```bash
# Test with curl
curl -x http://localhost:8080 http://www.example.com

# You should see request in TraceTap output
```

3. **Check TraceTap is running**:
```bash
# In another terminal
curl http://localhost:8080

# Should get response from TraceTap
```

4. **Check port is correct**:
```bash
# Default is 8080, verify:
python tracetap.py --listen 8080 --export api.json
```

### Port Already in Use

**Problem**: `Address already in use: ('0.0.0.0', 8080)`

**Solutions**:

```bash
# Use different port
python tracetap.py --listen 8081 --export api.json

# Or find and kill existing process
lsof -ti:8080 | xargs kill -9

# On Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

### Requests Captured But Empty

**Problem**: Requests appear in output but `captured.json` is empty

**Solutions**:

1. **Let capture run longer**:
```bash
# TraceTap might not flush immediately
# Stop with Ctrl+C to flush to file
```

2. **Check file permissions**:
```bash
# Ensure write permission to directory
ls -la captured.json

# Or use different location
python tracetap.py --listen 8080 --export /tmp/api.json
```

3. **Check filters aren't too restrictive**:
```bash
# Run without filters first
python tracetap.py --listen 8080 --export api.json

# Then add filters
python tracetap.py --listen 8080 --filter-host "api.example.com" --export api.json
```

### Filter Captures Too Much or Too Little

**Problem**: Wrong requests being captured

**Solution**:
```bash
# Enable filter debugging
python tracetap.py --listen 8080 \
  --filter-host "api.example.com" \
  --filter-verbose \
  --export api.json

# Watch output to see which requests match
# [16:43:12] REQUEST: GET https://api.example.com/users
#            FILTER: api.example.com ✓ MATCH → CAPTURE
# [16:43:13] REQUEST: GET https://other.com/endpoint
#            FILTER: api.example.com ✗ no match → SKIP
```

---

## SSL/HTTPS Issues

### SSL Certificate Verification Failed

**Problem**: `ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]`

**Solution**:

1. **Install TraceTap's certificate**:
```bash
python tracetap.py --install-cert

# Choose where to install:
# 1. System-wide (recommended)
# 2. Browser-specific
# 3. Python-specific
```

2. **Or bypass verification (not recommended)**:
```bash
# curl
curl -k https://api.example.com

# Python requests
import requests
requests.get('https://api.example.com', verify=False)

# But this won't capture properly
```

3. **Check certificate is installed**:
```bash
# Verify HTTPS capture works
curl -k https://www.example.com

# You should see request in TraceTap
```

### Certificate Expired

**Problem**: Certificate warnings even after installation

**Solution**:
```bash
# Generate new certificate
python tracetap.py --renew-cert

# Reinstall
python tracetap.py --install-cert

# Restart your browser if needed
```

### Self-Signed Certificate Errors in Specific Browser

**Problem**: One browser shows certificate error, others work

**Solution**:
```bash
# Reinstall certificate for that browser
python tracetap.py --install-cert

# Then restart the browser

# Or browse in incognito/private mode (might bypass cert check)
```

### HTTPS Doesn't Work But HTTP Does

**Problem**: HTTP requests captured, HTTPS not captured

**Solution**:

1. **Install certificate**:
```bash
python tracetap.py --install-cert
```

2. **Check application uses proxy for HTTPS too**:
```bash
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080  # Important!
```

3. **Test with curl**:
```bash
curl -x http://localhost:8080 -k https://api.example.com

# -k ignores cert errors temporarily for testing
```

---

## Test Generation Issues

### Generated Tests Fail

**Problem**: Generated tests fail when run

**Solution**:

1. **Check base URL**:
```bash
# Open generated test file
cat tests/test_api_calls.py

# Check BASE_URL constant
BASE_URL = 'https://api.example.com'  # Should be correct

# Or set environment variable
export API_URL=https://api.example.com
pytest tests/
```

2. **Check API is running**:
```bash
# Is the API accessible?
curl https://api.example.com/users

# If not, tests will fail
```

3. **Review generated assertions**:
```bash
# Some assertions might be too strict
# Edit tests/test_api_calls.py and adjust:
# - Skip timing assertions if flaky
# - Skip body assertions if data changes
# - Focus on status codes
```

4. **Check for PII in captures**:
```bash
# If tests reference real user IDs:
# ID: 12345 might not exist anymore

# Either:
# - Update captures with new data
# - Parameterize tests with variable IDs
# - Use mock server instead
```

### Too Many Test Files Generated

**Problem**: Generates hundreds of test files

**Solution**:
```bash
# Limit generation
python tracetap-playwright.py captured.json \
  --class-name TestAPI \
  --test-file test_api \
  -o tests/

# Or filter captures first
python tracetap-playwright.py captured.json \
  --endpoint-filter "^/api/users" \
  -o tests/
```

### AI Features Not Working

**Problem**: `--ai-suggestions` flag fails

**Solution**:

1. **Check API key**:
```bash
echo $ANTHROPIC_API_KEY

# Should output your API key
# If empty:
export ANTHROPIC_API_KEY='sk-ant-...'
```

2. **Verify API key works**:
```bash
python -c "
import anthropic
client = anthropic.Anthropic()
msg = client.messages.create(
    model='claude-3-5-sonnet-20241022',
    max_tokens=10,
    messages=[{'role': 'user', 'content': 'test'}]
)
print('✓ API key works')
"
```

3. **Check network access**:
```bash
# Is Anthropic API accessible?
curl https://api.anthropic.com

# If behind proxy:
export HTTPS_PROXY=http://proxy.example.com:8080
```

---

## Replay & Mock Server Issues

### Port Already in Use for Mock Server

**Problem**: `Address already in use: ('0.0.0.0', 8080)`

**Solution**:
```bash
# Use different port
python tracetap-replay.py mock api.json --port 9090

# Or kill existing process
lsof -ti:8080 | xargs kill -9
```

### Replay Requests Fail

**Problem**: Replayed requests get different responses than captured

**Solution**:

1. **Check target URL**:
```bash
python tracetap-replay.py replay api.json \
  --target http://localhost:8080 \
  --verbose

# Should show each request being replayed
```

2. **Check authentication**:
```bash
# If original requests had auth headers
python tracetap-replay.py replay api.json \
  --target http://localhost:8080 \
  --variables auth_token=new_token
```

3. **Check data hasn't changed**:
```bash
# If replaying GET /users/123 but user 123 was deleted:
# You'll get 404

# Either:
# - Use mock server instead
# - Use variable substitution
# - Update test data
```

### Mock Server Doesn't Match Requests

**Problem**: Mock server returns "no matching stub found"

**Solution**:

1. **Check matching strategy**:
```bash
# Try different strategies
python tracetap-replay.py mock api.json \
  --port 8080 \
  --strategy exact  # Strict matching

# Or fuzzy (more lenient)
python tracetap-replay.py mock api.json \
  --port 8080 \
  --strategy fuzzy
```

2. **Debug matching**:
```bash
python tracetap-replay.py mock api.json \
  --port 8080 \
  --verbose

# Makes requests to mock and watch for matching
curl http://localhost:8080/api/users/123
```

3. **Check stubs are valid**:
```bash
# Verify stubs file is valid JSON
python -m json.tool wiremock-stubs.json > /dev/null

# If it fails, JSON is invalid
```

### Chaos Engineering Not Working

**Problem**: `--chaos` flag doesn't simulate failures

**Solution**:
```bash
# Enable chaos and set rate
python tracetap-replay.py mock api.json \
  --port 8080 \
  --chaos \
  --chaos-rate 0.5  # 50% failure rate

# Check admin endpoint for stats
curl http://localhost:8080/__admin__/metrics
```

---

## CI/CD Issues

### Tests Pass Locally But Fail in CI

**Problem**: Tests work on your machine, fail in CI

**Solutions**:

1. **Check API URL**:
```yaml
# .github/workflows/test.yml
- name: Run tests
  env:
    API_URL: https://api.example.com  # Or staging
  run: pytest tests/
```

2. **Check network access**:
```bash
# In CI, can the API be accessed?
curl https://api.example.com

# If behind VPN, might need special config
```

3. **Check environment variables**:
```yaml
- name: Run tests
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    API_URL: ${{ secrets.API_URL }}
  run: pytest tests/
```

4. **Check Python version**:
```yaml
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'  # Match your local version
```

### CI Timeout

**Problem**: Tests timeout in CI but not locally

**Solution**:
```yaml
# Increase timeout
- name: Run tests
  run: pytest tests/ --timeout=60

# Or configure in pytest.ini
[pytest]
timeout = 60
```

### Contract Verification Fails in CI

**Problem**: Contract passes locally, fails in CI

**Solutions**:

1. **Check API is accessible from CI**:
```bash
# Can CI reach the API?
curl https://api.example.com

# If it's private/VPN, might not be accessible from CI
```

2. **Check contract file exists**:
```yaml
- name: Verify contract
  run: |
    ls contract.json  # Ensure file exists
    python -m json.tool contract.json > /dev/null  # Valid JSON
```

3. **Use proper exit codes**:
```bash
python -c "
from src.tracetap.contract import ContractVerifier
import json, sys

with open('contract.json') as f:
    contract = json.load(f)

result = ContractVerifier(contract).verify(
    base_url='http://localhost:3000'
)

# Must exit with proper code
sys.exit(0 if result.passed else 1)
"
```

---

## Performance Issues

### Replay is Slow

**Problem**: Replaying traffic takes too long

**Solution**:

1. **Increase worker count**:
```bash
python tracetap-replay.py replay api.json \
  --target http://localhost:8080 \
  --workers 20  # Increase from default 5
```

2. **Increase timeout**:
```bash
python tracetap-replay.py replay api.json \
  --target http://localhost:8080 \
  --timeout 60  # Increased from default 30
```

3. **Filter requests**:
```bash
python tracetap-replay.py replay api.json \
  --target http://localhost:8080 \
  --filter-method GET  # Only GET requests

# Or custom filter
```

### Mock Server is Slow

**Problem**: Mock server responds slowly

**Solution**:

1. **Check matching strategy**:
```bash
# Fuzzy matching is slower
python tracetap-replay.py mock api.json \
  --port 8080 \
  --strategy exact  # Faster
```

2. **Reduce stubs**:
```bash
# If thousands of stubs, reduce with filtering
python tracetap2wiremock.py api.json \
  --endpoint-filter "^/api/important" \
  -o wiremock-stubs.json
```

3. **Monitor performance**:
```bash
# Check admin metrics
curl http://localhost:8080/__admin__/metrics

# Look for slow endpoints
```

### Test Generation is Slow

**Problem**: Generating tests takes minutes

**Solution**:

1. **Skip AI**:
```bash
# Don't use --ai-suggestions if not needed
python tracetap-playwright.py api.json -o tests/

# Not:
python tracetap-playwright.py api.json --ai-suggestions -o tests/
```

2. **Filter captures**:
```bash
python tracetap-playwright.py api.json \
  --endpoint-filter "^/api" \
  -o tests/
```

3. **Use simpler assertions**:
```bash
python tracetap-playwright.py api.json \
  --minimal-assertions \
  -o tests/
```

---

## Getting Help

### Check Logs

**Enable debug logging**:
```bash
# Capture with debug output
python tracetap.py --listen 8080 --debug --export api.json

# Run tests with verbose output
pytest tests/ -vv

# Replay with verbose output
python tracetap-replay.py replay api.json \
  --target http://localhost:8080 \
  --verbose
```

### Review Generated Code

**Look at what was generated**:
```bash
# Test files
cat tests/test_api_calls.py

# Collections
python -m json.tool postman.json | head -50

# Stubs
python -m json.tool wiremock-stubs.json | head -50
```

### Common Error Messages

#### `ModuleNotFoundError: No module named 'tracetap'`

```bash
# Python can't find tracetap
# Make sure you're in the right directory
cd /path/to/tracetap

# And requirements are installed
pip install -r requirements.txt
```

#### `Connection refused`

```bash
# Can't connect to API or mock server
# Check:
# 1. Is server running?
# 2. Correct port?
# 3. Correct hostname?

curl http://localhost:8080/health
```

#### `JSON decode error`

```bash
# Corrupted JSON file
# Validate:
python -m json.tool captured.json > /dev/null

# If fails, file is corrupted
# Recapture traffic
```

### Report Issues

If you've exhausted troubleshooting:

1. **Collect information**:
```bash
# Python version
python --version

# TraceTap version
cat src/tracetap/__init__.py | grep version

# Error output
python tracetap.py --debug --export api.json 2>&1 | head -100
```

2. **Share details on GitHub**:
- Your OS and Python version
- Exact command you're running
- Full error message/traceback
- Steps to reproduce

---

## Next Steps

- **[Getting Started](getting-started.md)** - Back to basics
- **[CLI Reference](api/cli-reference.md)** - Check command options
- **[Guides](guides/)** - Learn specific workflows
