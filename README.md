# TraceTap

> **HTTP/HTTPS Traffic Capture with AI-Powered Postman Export**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](docs/CONTRIBUTING.md)

TraceTap captures HTTP/HTTPS traffic and uses Claude AI to automatically generate clean, organized Postman collections. Perfect for API testing, documentation, debugging, and creating realistic mocks.

---

## ✨ Features

- 🔒 **HTTPS Support** - Intercept HTTPS traffic with automatic certificate installation
- 🤖 **AI-Powered Organization** - Claude AI cleans and organizes your captures into production-ready collections
- 🎯 **Smart Filtering** - Capture only what you need with host and regex filters
- 📦 **Multiple Export Formats** - Postman Collection v2.1, Raw JSON, WireMock stubs
- 🔄 **Incremental Updates** - Merge new captures with existing collections without losing work
- 🚀 **Zero Configuration** - Single executable, no Python required
- 🌐 **Cross-Platform** - Works on Linux, macOS, and Windows
- ⚡ **Real-Time Monitoring** - See captured traffic as it happens

---

## 🚀 Quick Start

### 1. Download

Choose your platform:
- [Linux (x64)](https://github.com/VassilisSoum/tracetap/releases/latest) • [macOS (Intel)](https://github.com/VassilisSoum/tracetap/releases/latest) • [macOS (Apple Silicon)](https://github.com/VassilisSoum/tracetap/releases/latest) • [Windows](https://github.com/VassilisSoum/tracetap/releases/latest)

### 2. Install Certificate (One-Time)

```bash
# Linux
./chrome-cert-manager.sh install

# macOS
./macos-cert-manager.sh install

# Windows
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 install
```

### 3. Start Capturing

```bash
# Basic capture
./tracetap-linux-x64 --listen 8080 --raw-log capture.json

# Configure your browser proxy to localhost:8080
# Browse your app - traffic is captured!
# Press Ctrl+C to stop
```

### 4. Enhance with AI (Optional)

```bash
export ANTHROPIC_API_KEY='sk-ant-your-key-here'

python tracetap-ai-postman.py capture.json \
  --output enhanced_collection.json
```

### 5. Import to Postman

Open Postman → Import → Select `enhanced_collection.json` → Done! 🎉

**[📖 Full Quick Start Guide](docs/quick-start.md)**

---

## 📊 Example: Before & After

### Before (Raw Capture)
```
📊 150 captured requests
  • Mixed with tracking pixels, analytics, OPTIONS requests
  • Hardcoded session tokens everywhere
  • No organization
```

### After (AI Enhanced)
```
✨ 45 relevant API requests

📁 Payment Configuration
   • Get Payment Options
   • Get Payment Method Deposit Limits
   • Get Downtime Configurations
   
📁 Deposit Management
   • Fetch Deposit Tiles
   • Generate PXP Session Token
   • Initiate Payment with Existing Method

🔧 8 Collection Variables
   • {{base_url}}: https:/example.com
   • {{session_token}}: AAABmfze...
   • {{payment_method}}: pxp_card_visa

📝 Clear descriptions and test scenarios for each request
```

---

## 🎯 Use Cases

### API Testing & Documentation
Capture real API traffic from your application and instantly generate Postman collections for testing and documentation.

```bash
./tracetap-linux-x64 --filter-host "api.myapp.com" --listen 8080 --raw-log api.json
python tracetap-ai-postman.py api.json --output api_collection.json
```

### Creating Test Mocks
Capture production API responses and convert them to WireMock stubs for offline development and testing.

```bash
./tracetap-linux-x64 --filter-host "api.stripe.com" --raw-log stripe.json
python tracetap2wiremock.py stripe.json --output wiremock/mappings/
```

### Debugging Integration Issues
See exactly what requests and responses are being sent during integration issues.

```bash
./tracetap-linux-x64 --verbose --filter-regex ".*\/api\/.*" --raw-log debug.json
cat debug.json | jq '.requests[] | select(.status >= 400)'
```

---

## 📖 Documentation

- **[Getting Started](docs/getting-started.md)** - Complete installation and configuration guide
- **[Contributing Guide](docs/CONTRIBUTING.md)** - How to contribute to TraceTap
- **[Examples](docs/examples.md)** - Real-world workflow examples

---

## 🔧 Advanced Usage

### Smart Filtering

```bash
# Capture specific host
./tracetap-linux-x64 --filter-host "api.example.com" --listen 8080

# Capture with wildcard
./tracetap-linux-x64 --filter-host "*.example.com" --listen 8080

# Capture by URL pattern
./tracetap-linux-x64 --filter-regex ".*\/api\/v[0-9]+\/.*" --listen 8080

# Combine filters (OR logic)
./tracetap-linux-x64 \
  --filter-host "api.example.com" \
  --filter-regex ".*\/v2\/.*" \
  --listen 8080
```

### AI Enhancement Options

```bash
# Custom instructions
python tracetap-ai-postman.py capture.json \
  --instructions "Focus on /api/v2 endpoints. Remove all /metrics calls." \
  --output collection.json

# Save analysis for review
python tracetap-ai-postman.py capture.json \
  --save-analysis analysis.json \
  --output collection.json
```

### WireMock Integration

```bash
# Capture traffic
./tracetap-linux-x64 --listen 8080 --raw-log api.json

# Convert to WireMock stubs
python tracetap2wiremock.py api.json --output wiremock/mappings/

# Run WireMock
docker run -p 8080:8080 \
  -v $(pwd)/wiremock/mappings:/home/wiremock/mappings \
  wiremock/wiremock
```

---

## 🛠️ Installation from Source

```bash
# Clone repository
git clone https://github.com/VassilisSoum/tracetap.git
cd tracetap

# Install dependencies
pip install -r requirements.txt

# Run from source
python tracetap.py --listen 8080

# For AI enhancement
pip install anthropic
export ANTHROPIC_API_KEY='sk-ant-your-key-here'
python tracetap-ai-postman.py capture.json --output collection.json
```

---

## 🗺️ Roadmap

**Current Version: 1.0.0**

- [x] HTTP/HTTPS traffic capture
- [x] Postman Collection export
- [x] Raw JSON logging
- [x] WireMock stub generation
- [x] AI-powered enhancement with Claude
- [x] Incremental collection merging
- [x] Smart filtering (host, regex)
- [ ] WebSocket support
- [ ] HTTP/2 and HTTP/3 support
- [ ] Request/response modification
- [ ] OpenAPI/Swagger export
- [ ] Web UI for browsing captures
- [ ] Environment generation (dev/staging/prod)
- [ ] Built-in request replay
- [ ] Performance metrics dashboard

---

## 🔐 Security & Privacy

⚠️ **Important:** TraceTap is designed for **local development and testing only**.

- All traffic stays on your machine - nothing is sent to external servers
- Captured data is stored locally in files you specify
- Remove the certificate when done: `./cert-manager.sh remove`
- Don't use on production systems or shared computers
- Review captured data before sharing (may contain tokens/passwords)

---

## 🤝 Contributing

Contributions are welcome! Whether it's:

- 🐛 Bug reports
- 💡 Feature requests  
- 📖 Documentation improvements
- 🔧 Code contributions

Please see our [Contributing Guide](docs/CONTRIBUTING.md) for details.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built on [mitmproxy](https://mitmproxy.org/) - an excellent open-source proxy
- AI enhancement powered by [Claude](https://www.anthropic.com/claude) (Anthropic)

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/VassilisSoum/tracetap/issues)
- **Discussions:** [GitHub Discussions](https://github.com/VassilisSoum/tracetap/discussions)
---

**Made with ❤️ for developers who need better API debugging tools**