# Getting Started with TraceTap

TraceTap is a powerful HTTP/HTTPS traffic capture tool that automatically generates clean, organized Postman collections using AI.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Basic Usage](#basic-usage)
- [Certificate Installation](#certificate-installation)
- [Configuration](#configuration)
- [AI Enhancement](#ai-enhancement)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Installation

### Prerequisites

- Python 3.8 or higher (for AI enhancement features)
- pip package manager (for AI enhancement)

### Option 1: Download Pre-built Executables

**Choose your platform:**

- **Linux (x64):** [tracetap-linux-x64](https://github.com/VassilisSoum/tracetap/releases/latest)
- **macOS (Intel):** [tracetap-macos-x64](https://github.com/VassilisSoum/tracetap/releases/latest)
- **macOS (Apple Silicon M1/M2/M3):** [tracetap-macos-arm64](https://github.com/VassilisSoum/tracetap/releases/latest)
- **Windows (x64):** [tracetap-windows-x64.exe](https://github.com/VassilisSoum/tracetap/releases/latest)

**Make executable (Linux/macOS):**
```bash
chmod +x tracetap-*
```

### Option 2: Install from Source

```bash
git clone https://github.com/VassilisSoum/tracetap.git
cd tracetap
pip install -r requirements.txt
```

### Install AI Enhancement Dependencies

```bash
pip install anthropic
```

---

## Quick Start

### 1. Install HTTPS Certificate

Before capturing HTTPS traffic, install TraceTap's certificate.

**Recommended Method (All Platforms):**
```bash
# Navigate to scripts directory
cd src/tracetap/scripts

# Install certificate
python3 cert_manager.py install

# Verify installation
python3 cert_manager.py verify
```

**Alternative: Platform-Specific Scripts**
```bash
# Linux
./src/tracetap/scripts/chrome-cert-manager.sh install

# macOS
./src/tracetap/scripts/macos-cert-manager.sh install

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass .\src\tracetap\scripts\windows-cert-manager.ps1 install
```

> **Note:** See [CERTIFICATE_INSTALLATION.md](./CERTIFICATE_INSTALLATION.md) for detailed instructions and troubleshooting.

### 2. Start Capturing Traffic

```bash
# Using pre-built executable (Linux example)
./tracetap-linux-x64 --listen 8080 --raw-log my_capture.json

# Or from source
python tracetap.py --listen 8080 --raw-log my_capture.json
```

You should see:
```
┌──────────────────────────────────────────────────┐
│ TraceTap HTTP/HTTPS Proxy                       │
├──────────────────────────────────────────────────┤
│ Listening: http://0.0.0.0:8080                  │
│ Raw Log:   my_capture.json                       │
│ Session:   tracetap-session                      │
└──────────────────────────────────────────────────┘

Configure your client:
  export HTTP_PROXY=http://localhost:8080
  export HTTPS_PROXY=http://localhost:8080

Press Ctrl+C to stop and export.
```

### 3. Configure Your Application

**Browser (FoxyProxy - Recommended):**
1. Install [FoxyProxy Standard](https://getfoxyproxy.org/)
2. Add new proxy:
   - Type: HTTP
   - Host: `localhost`
   - Port: `8080`
3. Enable the proxy

**Command Line:**
```bash
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

curl https://api.example.com/users
```

### 4. Browse Your Application

Use your application normally. TraceTap captures all traffic:

```
GET https://api.example.com/users → 200 (234 ms)
POST https://api.example.com/login → 201 (156 ms)
GET https://api.example.com/profile → 200 (89 ms)
```

### 5. Stop and Export

Press `Ctrl+C` to stop:

```
Shutting down... 25 records captured
✓ Exported raw log (15.3 KB) → my_capture.json
```

### 6. Enhance with AI (Optional)

```bash
# Set your Claude API key
export ANTHROPIC_API_KEY='sk-ant-your-key-here'

# Enhance the capture
python tracetap-ai-postman.py my_capture.json \
  --output enhanced_collection.json
```

### 7. Import to Postman

1. Open Postman
2. Click **Import**
3. Select `enhanced_collection.json`
4. Done! 🎉

---

## Basic Usage

### Capture Commands

**Capture all traffic:**
```bash
./tracetap-linux-x64 --listen 8080 --raw-log all_traffic.json
```

**Capture specific host:**
```bash
./tracetap-linux-x64 --listen 8080 \
  --filter-host "api.example.com" \
  --raw-log api_traffic.json
```

**Capture multiple hosts:**
```bash
./tracetap-linux-x64 --listen 8080 \
  --filter-host "api.example.com,auth.example.com" \
  --raw-log traffic.json
```

**Capture with wildcard:**
```bash
./tracetap-linux-x64 --listen 8080 \
  --filter-host "*.example.com" \
  --raw-log traffic.json
```

**Capture by URL pattern (regex):**
```bash
./tracetap-linux-x64 --listen 8080 \
  --filter-regex ".*\/api\/v[0-9]+\/.*" \
  --raw-log versioned_apis.json
```

**Quiet mode (less output):**
```bash
./tracetap-linux-x64 --listen 8080 --quiet --raw-log traffic.json
```

**Verbose mode (detailed filtering):**
```bash
./tracetap-linux-x64 --listen 8080 --verbose --raw-log traffic.json
```

**Export both raw and Postman:**
```bash
./tracetap-linux-x64 --listen 8080 \
  --raw-log captures.json \
  --export postman_collection.json
```

### Command-Line Options

```
Options:
  --listen PORT          Port to listen on (default: 8080)
  --export PATH          Export Postman collection to JSON file
  --raw-log PATH         Export raw captured data to JSON file
  --session NAME         Session name for exports (default: tracetap-session)
  --filter-host HOSTS    Capture only these hosts (comma-separated, supports wildcards)
  --filter-regex PATTERN Capture URLs matching regex pattern
  --quiet                Reduce output (only show errors)
  --verbose              Show detailed filtering information
  --help                 Show help message
```

---

## Certificate Installation

### Why Do I Need a Certificate?

To intercept HTTPS traffic, TraceTap acts as a "man-in-the-middle" proxy. It needs to decrypt HTTPS traffic, which requires installing a trusted certificate on your system.

### Quick Installation (All Platforms)

TraceTap now uses a simplified, unified certificate installer:

```bash
# Navigate to scripts directory
cd src/tracetap/scripts

# Install certificate
python3 cert_manager.py install

# Verify installation
python3 cert_manager.py verify

# Check certificate info
python3 cert_manager.py info

# Remove certificate (when done)
python3 cert_manager.py uninstall
```

**What it does:**
- Automatically detects your platform (Linux, macOS, Windows)
- Installs certificate to the appropriate trust store
- Provides clear error messages if something goes wrong
- Offers manual installation instructions as fallback

### Platform-Specific Notes

**macOS:**
- You'll be prompted for your password
- Certificate added to login keychain
- Works with Safari, Chrome, and system apps

**Windows:**
- Installs to Current User store (no admin required)
- For system-wide trust, run as Administrator
- Works with Chrome, Edge, and Windows apps

**Linux:**
- Requires sudo for system-wide installation
- Automatically detects your distribution
- Works with Chrome, Chromium, and system tools

**Firefox:**
- Uses its own certificate store on all platforms
- See [CERTIFICATE_INSTALLATION.md](./CERTIFICATE_INSTALLATION.md#firefox-on-linux) for Firefox setup

### Troubleshooting

If installation fails or you see certificate warnings:

1. **Verify certificate was generated:**
   ```bash
   ls ~/.mitmproxy/mitmproxy-ca-cert.pem
   ```

2. **Reinstall certificate:**
   ```bash
   python3 cert_manager.py uninstall
   python3 cert_manager.py install
   ```

3. **Check installation status:**
   ```bash
   python3 cert_manager.py verify
   ```

4. **Restart your browser** after installation

For detailed troubleshooting, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

**Chrome/Edge:**
- Uses system certificate store
- Automatic installation scripts handle this
- Restart browser after installation

---

## Configuration

### Environment Variables

TraceTap can be configured using environment variables:

```bash
# Claude API key for AI enhancement
export ANTHROPIC_API_KEY='sk-ant-your-key-here'

# Default session name
export TRACETAP_SESSION='my-project-api'

# Proxy settings for applications
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
```

### Proxy Configuration

#### Browser Manual Settings

**Chrome/Edge:**
1. Settings → System → Open proxy settings
2. Set HTTP and HTTPS proxy to `localhost:8080`

**Firefox:**
1. Preferences → Network Settings → Settings
2. Manual proxy: `localhost` port `8080`
3. Check "Use this proxy for HTTPS"

#### Command Line Tools

**curl/wget:**
```bash
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

curl https://api.example.com/users
wget https://api.example.com/data
```

---

## AI Enhancement

Transform raw captures into clean, organized Postman collections using Claude AI.

### Setup

**1. Get Claude API Key:**
- Visit https://console.anthropic.com/
- Sign up or log in
- Navigate to **API Keys**
- Create a new key (starts with `sk-ant-`)

**2. Set API Key:**
```bash
export ANTHROPIC_API_KEY='sk-ant-your-key-here'

# Make permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export ANTHROPIC_API_KEY="sk-ant-your-key-here"' >> ~/.bashrc
```

### Basic Enhancement

```bash
python tracetap-ai-postman.py capture.json \
  --output enhanced_collection.json
```

**What happens:**
- Removes noise (analytics, tracking, OPTIONS requests)
- Organizes into logical folders
- Generates clear request names
- Extracts variables (base URLs, tokens, IDs)
- Adds descriptions and test scenarios

### Custom Instructions

```bash
python tracetap-ai-postman.py capture.json \
  --output collection.json \
  --instructions "Focus on /api/v2 endpoints. Remove all /metrics calls. Group by resource type."
```

### Save Analysis

```bash
python tracetap-ai-postman.py capture.json \
  --output collection.json \
  --save-analysis analysis.json
```

Review `analysis.json` to see Claude's recommendations.

---

## Troubleshooting

### No Requests Captured

**Problem:** TraceTap shows 0 captured requests.

**Possible causes:**
- Proxy not configured
- Filters too restrictive
- Wrong port number

**Solutions:**
```bash
# Test proxy is working
curl -x http://localhost:8080 http://httpbin.org/get

# Try without filters
./tracetap-linux-x64 --listen 8080 --verbose

# Check FoxyProxy is enabled (if using browser extension)
```

---

### "Address already in use" Error

**Problem:** Port 8080 is already in use.

**Solution:**
```bash
# Find what's using the port
lsof -i :8080  # Linux/macOS
netstat -ano | findstr :8080  # Windows

# Use a different port
./tracetap-linux-x64 --listen 9000 --raw-log traffic.json
```

---

### Certificate Errors

**Problem:** "Your connection is not private" warning in browser.

**Solutions:**

**1. Verify certificate installation:**
```bash
cd src/tracetap/scripts
python3 cert_manager.py verify
```

**2. Check certificate info:**
```bash
python3 cert_manager.py info
```

**3. Reinstall certificate:**
```bash
python3 cert_manager.py uninstall
python3 cert_manager.py install
```

**4. Restart browser completely** (close all windows)

**5. For Firefox:**
- Firefox uses its own certificate store
- See [CERTIFICATE_INSTALLATION.md](./CERTIFICATE_INSTALLATION.md#firefox-on-linux) for Firefox-specific instructions

For more help, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

### AI Enhancement Fails

**Problem:** "Could not parse Claude's recommendations"

**Solutions:**

**1. Check API key:**
```bash
echo $ANTHROPIC_API_KEY
# Should show: sk-ant-...
```

**2. Review Claude's output:**
```bash
python tracetap-ai-postman.py capture.json \
  --save-analysis analysis.json
cat analysis.json
```

**3. Use smaller capture:**
```bash
# If capture is huge (>1000 requests), filter first
./tracetap-linux-x64 --filter-host "api.yourapp.com" --listen 8080
```

---

### Permission Denied (Linux/macOS)

**Problem:** `Permission denied` when running executable.

**Solution:**
```bash
chmod +x tracetap-*
./tracetap-linux-x64 --listen 8080
```

---

### macOS Blocks Unsigned Application

**Problem:** "Cannot be opened because the developer cannot be verified"

**Solution:**
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine tracetap-macos-*

# Or: System Preferences → Security & Privacy → "Open Anyway"
```

---

### Antivirus Blocks TraceTap (Windows)

**Problem:** Antivirus flags TraceTap as malicious.

**Why:** PyInstaller executables sometimes trigger false positives.

**Solutions:**
1. Add exception in your antivirus
2. Run from source: `python tracetap.py --listen 8080`
3. Build yourself: `python build_executables.py`

---

## Best Practices

### Capturing Traffic

**1. Use specific filters**
```bash
# Good: Focus on your API
./tracetap-linux-x64 --filter-host "api.myapp.com" --listen 8080

# Bad: Capture everything (noisy)
./tracetap-linux-x64 --listen 8080
```

**2. Use meaningful session names**
```bash
./tracetap-linux-x64 \
  --session "Payment Flow - QA Testing - October 2025" \
  --listen 8080
```

**3. Save both raw and Postman**
```bash
./tracetap-linux-x64 \
  --raw-log raw.json \
  --export postman.json \
  --listen 8080
```

**4. Use quiet mode in CI/CD**
```bash
./tracetap-linux-x64 --quiet --raw-log ci_capture.json --listen 8080
```

### AI Enhancement

**1. Provide custom instructions**
```bash
python tracetap-ai-postman.py capture.json \
  --instructions "Remove OPTIONS requests. Focus on REST API endpoints."
```

**2. Always save analysis for debugging**
```bash
python tracetap-ai-postman.py capture.json \
  --save-analysis analysis.json
```

### Security

**1. Remove certificate when done**
```bash
cd src/tracetap/scripts
python3 cert_manager.py uninstall
```

**2. Use for local development only**
- Never use TraceTap on production systems
- Don't install on shared/public computers
- Remove certificate from shared development machines

**3. Review captured data before sharing**
```bash
# Check for sensitive data
grep -i "password\|token\|secret\|api.key" capture.json

# Or use your editor's search
```

**4. Protect your captures**
- Raw logs may contain authentication tokens
- Don't commit capture files to Git
- Add to `.gitignore`: `*.json` (capture files)

---

## Analyzing Captured Data

### Using jq

```bash
# Count total requests
cat capture.json | jq '.total_requests'

# List all URLs
cat capture.json | jq '.requests[].url'

# Find errors (4xx, 5xx)
cat capture.json | jq '.requests[] | select(.status >= 400)'

# Group by status code
cat capture.json | jq '.requests[].status' | sort | uniq -c

# Calculate average response time
cat capture.json | jq '.requests[].duration_ms' | \
  awk '{sum+=$1} END {print sum/NR " ms"}'

# Extract all endpoints
cat capture.json | jq -r '.requests[] | .method + " " + .url' | sort | uniq

# Find slow requests (>1s)
cat capture.json | jq '.requests[] | select(.duration_ms > 1000)'

# Count requests per host
cat capture.json | jq '.requests[] | .host' | sort | uniq -c
```

---

## WireMock Integration

Create API mocks from captured traffic.

### 1. Capture Traffic

```bash
./tracetap-linux-x64 --listen 8080 \
  --filter-host "api.stripe.com" \
  --raw-log stripe_api.json
```

### 2. Convert to WireMock Stubs

```bash
python tracetap2wiremock.py stripe_api.json \
  --output wiremock/mappings/
```

### 3. Run WireMock

```bash
# Using Docker
docker run -p 8080:8080 \
  -v $(pwd)/wiremock/mappings:/home/wiremock/mappings \
  wiremock/wiremock

# Or standalone JAR
java -jar wiremock-standalone.jar --port 8080
```

### 4. Test Your App

Change your app's API URL from `https://api.stripe.com` to `http://localhost:8080` and test with mocks!

**See:** [WireMock Workflow Guide](WIREMOCK_WORKFLOW.md) for complete details.

---

## Next Steps

- **[Getting Started](getting-started.md)** - Complete walkthrough
- **[Examples](examples.md)** - Real-world workflow examples
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute

---

## Getting Help

**Need help?** Here's where to go:

- **GitHub Issues:** https://github.com/VassilisSoum/tracetap/issues
- **GitHub Discussions:** https://github.com/VassilisSoum/tracetap/discussions
- **Documentation:** https://github.com/VassilisSoum/tracetap/wiki

---