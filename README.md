# TraceTap

> **HTTP/HTTPS Traffic Capture Proxy with Postman & WireMock Export**

TraceTap is a powerful tool for capturing HTTP/HTTPS traffic and automatically converting it into Postman collections or WireMock stubs. Perfect for API testing, debugging, offline development, and creating realistic mock services.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## ✨ Features

- 🔒 **HTTPS Support** - Intercept HTTPS traffic with automatic certificate installation
- 🎯 **Smart Filtering** - Capture only what you need with host and regex filters
- 📦 **Multiple Export Formats**
  - Postman Collection v2.1 (ready to import)
  - Raw JSON logs (complete request/response data)
  - WireMock stubs (automatic stub generation)
- 🚀 **Zero Configuration** - Single executable, no Python required
- 🌐 **Cross-Platform** - Works on Linux, macOS, and Windows
- ⚡ **Real-Time Monitoring** - See captured traffic as it happens
- 🎭 **Perfect for Testing** - Create realistic mocks from production traffic

## 🚀 Quick Start

### 1. Download

**Choose your platform:**

- **Linux (x64):** `tracetap-linux-x64`
- **macOS (Intel):** `tracetap-macos-x64`
- **macOS (Apple Silicon M1/M2/M3):** `tracetap-macos-arm64`
- **Windows (x64):** `tracetap-windows-x64.exe`

Download from [Releases](https://github.com/yourusername/tracetap/releases/latest)

### 2. Install Certificate (One-Time Setup)

TraceTap needs to install a trusted certificate to intercept HTTPS traffic.

**Linux:**
```bash
chmod +x chrome-cert-manager.sh
./chrome-cert-manager.sh install
```

**macOS:**
```bash
chmod +x macos-cert-manager.sh
./macos-cert-manager.sh install
```

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 install
```

See [Certificate Installation Guide](CERTIFICATE_INSTALLATION.md) for detailed instructions.

### 3. Start Capturing

**Linux/macOS:**
```bash
chmod +x tracetap-*
./tracetap-linux-x64 --listen 8080 --raw-log captures.json --export postman.json
```

**Windows:**
```powershell
.\tracetap-windows-x64.exe --listen 8080 --raw-log captures.json --export postman.json
```

### 4. Configure Your Browser

**Option A: FoxyProxy (Recommended)**
1. Install [FoxyProxy Standard](https://getfoxyproxy.org/)
2. Add proxy: HTTP, `localhost`, port `8080`
3. Enable the proxy

**Option B: Manual Proxy Settings**
- Set HTTP/HTTPS proxy to `localhost:8080`
- Applies to: Chrome, Firefox, Edge, Safari, etc.

### 5. Browse & Capture

Visit any website. TraceTap captures all traffic in real-time:

```
GET https://api.example.com/users → 200 (234 ms)
POST https://api.example.com/login → 201 (156 ms)
```

Press `Ctrl+C` to stop and export.

## 📖 Usage

### Basic Usage

```bash
# Capture all traffic
./tracetap-linux-x64 --listen 8080 --raw-log all_traffic.json

# Capture specific host
./tracetap-linux-x64 --listen 8080 \
  --filter-host "api.example.com" \
  --export postman.json

# Capture multiple hosts
./tracetap-linux-x64 --listen 8080 \
  --filter-host "api.example.com,auth.example.com,cdn.example.com" \
  --raw-log captures.json

# Capture with wildcard
./tracetap-linux-x64 --listen 8080 \
  --filter-host "*.example.com"

# Capture by URL pattern
./tracetap-linux-x64 --listen 8080 \
  --filter-regex ".*\/api\/v[0-9]+\/.*"
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

### Examples

**API Testing:**
```bash
./tracetap-linux-x64 --listen 8080 \
  --filter-host "api.stripe.com" \
  --export stripe_api.json \
  --raw-log stripe_raw.json \
  --session "Stripe Integration Test"
```

**Multiple Services:**
```bash
./tracetap-linux-x64 --listen 8080 \
  --filter-host "*.amazonaws.com,*.cloudfront.net" \
  --raw-log aws_services.json
```

**Development Debugging:**
```bash
./tracetap-linux-x64 --listen 8080 \
  --filter-regex "localhost.*\/api\/" \
  --verbose
```

## 🎭 WireMock Integration

Convert captured traffic to WireMock stubs for mocking APIs:

### 1. Capture Traffic

```bash
./tracetap-linux-x64 --listen 8080 \
  --raw-log payment_api.json \
  --filter-host "api.stripe.com"
```

### 2. Convert to WireMock Stubs

```bash
python tracetap2wiremock.py payment_api.json \
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

Change your app's API URL from `https://api.stripe.com` to `http://localhost:8080` and your app now uses mocks created from real traffic!

See [WireMock Workflow Guide](WIREMOCK_WORKFLOW.md) for complete details.

## 📊 Output Formats

### Postman Collection (--export)

Ready to import into Postman:

```json
{
  "info": {
    "name": "API Testing @ 2024-10-19T10:30:00",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "GET https://api.example.com/users",
      "request": {
        "method": "GET",
        "header": [...],
        "url": {...}
      }
    }
  ]
}
```

### Raw Log (--raw-log)

Complete capture data with metadata:

```json
{
  "session": "my-session",
  "captured_at": "2024-10-19T10:30:00",
  "total_requests": 15,
  "filters": {
    "hosts": ["api.example.com"],
    "regex": null
  },
  "requests": [
    {
      "time": "2024-10-19T10:30:05",
      "method": "GET",
      "url": "https://api.example.com/users",
      "req_headers": {...},
      "req_body": "",
      "status": 200,
      "resp_headers": {...},
      "resp_body": "{...}",
      "duration_ms": 234
    }
  ]
}
```

## 🔧 Advanced Usage

### Filtering

**Exact host matching:**
```bash
--filter-host "api.example.com"
```

**Wildcard matching:**
```bash
--filter-host "*.example.com"  # Matches api.example.com, auth.example.com, etc.
```

**Multiple hosts:**
```bash
--filter-host "api.example.com,auth.example.com"
```

**Regex patterns:**
```bash
--filter-regex ".*\/api\/v[0-9]+\/.*"  # Match versioned API endpoints
--filter-regex "example\.com.*\/users"  # Match user endpoints
```

**Combine filters (OR logic):**
```bash
--filter-host "api.example.com" --filter-regex ".*\/v2\/.*"
# Captures if host matches OR regex matches
```

### Analyzing Captured Data

Use `jq` to analyze raw logs:

```bash
# Count total requests
cat captures.json | jq '.total_requests'

# List all URLs
cat captures.json | jq '.requests[].url'

# Find errors
cat captures.json | jq '.requests[] | select(.status >= 400)'

# Group by status code
cat captures.json | jq '.requests[].status' | sort | uniq -c

# Calculate average response time
cat captures.json | jq '.requests[].duration_ms' | awk '{sum+=$1} END {print sum/NR}'

# Extract all endpoints
cat captures.json | jq -r '.requests[] | .method + " " + .url' | sort | uniq
```

## 🛠️ Building from Source

### Requirements

- Python 3.8 or higher
- pip

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/tracetap.git
cd tracetap

# Install dependencies
pip install -r requirements.txt

# Run from source
python tracetap.py --listen 8080
```

### Building Executables

```bash
# Build for current platform
python build_executables.py

# Output in release/ directory
ls release/
```

See [BUILD.md](BUILD.md) for detailed build instructions.

## 📚 Documentation

- **[Quick Start Guide](QUICK_START.md)** - Complete setup walkthrough
- **[Certificate Installation](CERTIFICATE_INSTALLATION.md)** - Detailed cert setup for all platforms
- **[WireMock Workflow](WIREMOCK_WORKFLOW.md)** - End-to-end WireMock integration
- **[Platform Comparison](PLATFORM_COMPARISON.md)** - Platform-specific differences
- **[Build Instructions](BUILD.md)** - How to build from source

## 🔐 Security & Privacy

### ⚠️ Important Security Notes

- **For Local Development Only** - TraceTap is designed for testing and debugging in local environments
- **Man-in-the-Middle** - TraceTap acts as a MITM proxy to intercept HTTPS traffic
- **Certificate Trust** - Installing the certificate allows TraceTap to decrypt HTTPS
- **Sensitive Data** - Captured logs may contain authentication tokens, passwords, and sensitive data

### Best Practices

✅ **DO:**
- Use for local development and testing
- Remove certificate when done: `./cert-manager-* remove`
- Review captured data before sharing
- Use filters to capture only what you need
- Keep your `~/.mitmproxy/` directory secure

❌ **DON'T:**
- Use on production systems
- Install on shared/public computers
- Share your CA certificate or `~/.mitmproxy/` directory
- Capture traffic containing real credentials
- Leave the certificate installed permanently

### Data Privacy

- All traffic stays on your machine
- No data is sent to external servers
- Captured data is stored locally in files you specify
- You control what is captured via filters

## 🤝 Use Cases

### 1. API Testing & Documentation
```bash
# Capture all API calls from your application
./tracetap-linux-x64 --listen 8080 --export api_docs.json
# Import into Postman to document your API
```

### 2. Creating Test Mocks
```bash
# Capture production API responses
./tracetap-linux-x64 --listen 8080 --raw-log prod_api.json
# Convert to WireMock stubs
python tracetap2wiremock.py prod_api.json -o stubs/
# Use in tests without hitting production
```

### 3. Debugging Integration Issues
```bash
# Capture with verbose logging
./tracetap-linux-x64 --listen 8080 --verbose --raw-log debug.json
# Inspect exact headers, bodies, timing
```

### 4. Offline Development
```bash
# Capture all third-party API calls once
./tracetap-linux-x64 --listen 8080 --raw-log third_party.json
# Generate WireMock stubs
python tracetap2wiremock.py third_party.json -o mocks/
# Develop offline with mocks
```

### 5. Performance Analysis
```bash
# Capture timing data
./tracetap-linux-x64 --listen 8080 --raw-log timing.json
# Analyze response times
cat timing.json | jq '.requests[] | {url: .url, ms: .duration_ms}'
```

### 6. Regression Testing
```bash
# Capture expected responses from staging
./tracetap-linux-x64 --listen 8080 --raw-log expected.json
# Compare against new API versions
# Use in automated tests
```

## 🐛 Troubleshooting

### Certificate Warnings in Browser

**Problem:** Browser shows "Your connection is not private"

**Solution:**
```bash
# Check certificate status
./chrome-cert-manager.sh status  # Linux
./macos-cert-manager.sh status   # macOS
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 status  # Windows

# Reinstall if needed
./chrome-cert-manager.sh remove
./chrome-cert-manager.sh install
```

### No Traffic Captured

**Problem:** TraceTap shows no captured requests

**Possible causes:**
1. **Proxy not enabled** - Check FoxyProxy or browser proxy settings
2. **Filters too restrictive** - Try without filters first
3. **Wrong port** - Ensure browser proxy matches `--listen` port

**Debug:**
```bash
# Try without filters
./tracetap-linux-x64 --listen 8080 --verbose

# Test proxy is working
curl -x http://localhost:8080 http://httpbin.org/get
```

### Port Already in Use

**Problem:** `Error: Address already in use`

**Solution:**
```bash
# Find process using port 8080
lsof -i :8080  # Linux/macOS
netstat -ano | findstr :8080  # Windows

# Use different port
./tracetap-linux-x64 --listen 9000
```

### Permission Denied (Linux/macOS)

**Problem:** `Permission denied` when running executable

**Solution:**
```bash
chmod +x tracetap-*
./tracetap-linux-x64 --listen 8080
```

### Antivirus Blocking (Windows)

**Problem:** Antivirus flags TraceTap executable

**Why:** PyInstaller executables sometimes trigger false positives

**Solution:**
1. Add exception in antivirus
2. Run from source: `python tracetap.py`
3. Build yourself: `python build_executables.py`

### macOS "Cannot be opened" Error

**Problem:** macOS blocks unsigned application

**Solution:**
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine tracetap-macos-*

# Or: System Preferences → Security & Privacy → "Open Anyway"
```

## 🤔 FAQ

**Q: Do I need Python installed?**  
A: No, the executables are standalone and don't require Python.

**Q: Can I use this in production?**  
A: No, TraceTap is for local development and testing only.

**Q: Does TraceTap store my data?**  
A: Only in the files you specify (`--export`, `--raw-log`). Nothing is sent externally.

**Q: Can I capture WebSocket traffic?**  
A: Not currently. TraceTap focuses on HTTP/HTTPS only.

**Q: Does it work with mobile apps?**  
A: Yes! Configure your phone's proxy to point to your computer's IP and port.

**Q: Can I run multiple instances?**  
A: Yes, use different ports: `--listen 8080`, `--listen 8081`, etc.

**Q: How do I capture curl/wget traffic?**  
A: Set proxy environment variables:
```bash
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
curl https://api.example.com
```

**Q: Is this similar to Charles Proxy or Fiddler?**  
A: Yes, but TraceTap is free, open-source, and has built-in Postman/WireMock export.

## 🗺️ Roadmap

- [ ] WebSocket support
- [ ] HTTP/2 and HTTP/3 support
- [ ] Request/response modification
- [ ] Built-in request replay
- [ ] OpenAPI/Swagger export
- [ ] Web UI for browsing captures
- [ ] Request scripting/automation
- [ ] Performance metrics dashboard

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built on top of [mitmproxy](https://mitmproxy.org/) - a fantastic open-source proxy.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/yourusername/tracetap.git
cd tracetap
pip install -r requirements.txt
python tracetap.py --listen 8080
```

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/tracetap/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/tracetap/discussions)
- **Documentation:** [Wiki](https://github.com/yourusername/tracetap/wiki)

## ⭐ Star History

If you find TraceTap useful, please consider starring the repository!

---

**Made with ❤️ for developers who need better API debugging tools**