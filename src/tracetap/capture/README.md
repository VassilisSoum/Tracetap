# TraceTap - HTTP/HTTPS Traffic Capture Proxy

TraceTap is a powerful HTTP/HTTPS proxy that captures all traffic passing through it and exports the data to Postman Collections or raw JSON logs.

## Features

- 🔍 **Capture all HTTP/HTTPS traffic** passing through the proxy
- 📦 **Export to Postman Collection v2.1** format for easy API testing
- 📝 **Raw JSON logging** for custom processing
- 🎯 **Smart filtering** by host (with wildcards) or regex patterns
- 🔐 **HTTPS support** with automatic SSL certificate handling
- 🎨 **Color-coded console output** for easy monitoring
- ⚡ **Real-time capture** with minimal performance impact

## Installation

### Requirements

- Python 3.7 or higher
- mitmproxy

### Install Dependencies

```bash
pip install mitmproxy
```

### Benefits of Modular Architecture

- **🔧 Easy Maintenance**: Each module has a single, clear responsibility
- **🧪 Testable**: Components can be unit tested independently
- **📖 Readable**: Smaller files are easier to understand and navigate
- **🔄 Reusable**: Modules can be used in other projects
- **🚀 Extensible**: Add new exporters or filters without touching core logic

## Quick Start

### 1. Basic Usage

Start the proxy on port 8080:

```bash
python tracetap_main.py --listen 8080
```

### 2. Configure Your HTTP Client

Set your HTTP client to use the proxy:

```bash
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Make requests
curl -k https://api.example.com
```

### 3. Stop and Export

Press `Ctrl+C` to stop the proxy and export captured data.

## Usage Examples

### Export to Postman Collection

```bash
python tracetap_main.py --listen 8080 --export api_captures.json
```

### Export Raw JSON Log

```bash
python tracetap_main.py --listen 8080 --raw-log traffic_log.json
```

### Export Both Formats

```bash
python tracetap_main.py --listen 8080 --export api.json --raw-log raw.json
```

### Capture with Session Name

```bash
python tracetap_main.py --listen 8080 --export api.json --session "API Testing"
```

## Filtering Traffic

### Filter by Specific Host

```bash
python tracetap_main.py --listen 8080 --filter-host "api.example.com"
```

### Filter Multiple Hosts

```bash
python tracetap_main.py --listen 8080 --filter-host "example.com,api.github.com"
```

### Use Wildcard Matching

Capture all subdomains:

```bash
python tracetap_main.py --listen 8080 --filter-host "*.example.com"
```

This will capture:
- `api.example.com`
- `auth.example.com`
- `www.example.com`
- etc.

### Filter by Regex Pattern

```bash
# Match specific API versions
python tracetap_main.py --listen 8080 --filter-regex "/api/v[0-9]+/"

# Match all .com API subdomains
python tracetap_main.py --listen 8080 --filter-regex "api\..*\.com"
```

### Combine Filters (OR Logic)

Filters use OR logic - traffic is captured if ANY filter matches:

```bash
python tracetap_main.py --listen 8080 \
  --filter-host "example.com" \
  --filter-regex ".*\.api\..*"
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--listen PORT` | Port to listen on | 8080 |
| `--export PATH` | Export Postman collection to path | None |
| `--raw-log PATH` | Export raw JSON log to path | None |
| `--session NAME` | Session name for exported collection | tracetap-session |
| `--quiet` | Reduce logging output | False |
| `--verbose` | Show filtered requests (verbose mode) | False |
| `--filter-host HOSTS` | Comma-separated list of hosts to capture | All hosts |
| `--filter-regex PATTERN` | Regex pattern for URL matching | None |

## Output Formats

### Postman Collection (--export)

Exports captured traffic as a Postman Collection v2.1 file that can be imported directly into Postman for:
- Replaying requests
- API testing
- Documentation
- Sharing with team members

### Raw JSON Log (--raw-log)

Exports captured traffic as a JSON array containing detailed information for each request:

```json
[
  {
    "time": "2025-10-27T10:30:45.123456",
    "method": "GET",
    "url": "https://api.example.com/users",
    "host": "api.example.com",
    "proto": "HTTP/1.1",
    "req_headers": {...},
    "req_body": "",
    "status": 200,
    "resp_headers": {...},
    "resp_body": "{...}",
    "duration_ms": 145
  }
]
```

## Advanced Usage

### Using with Different HTTP Clients

#### cURL
```bash
curl -k -x http://localhost:8080 https://api.example.com
```

#### Python Requests
```python
import requests

proxies = {
    'http': 'http://localhost:8080',
    'https': 'http://localhost:8080'
}

response = requests.get('https://api.example.com', proxies=proxies, verify=False)
```

#### Node.js
```javascript
const axios = require('axios');

axios.get('https://api.example.com', {
  proxy: {
    host: 'localhost',
    port: 8080
  }
});
```

### Quiet Mode

Reduce console output:

```bash
python tracetap_main.py --listen 8080 --quiet
```

### Verbose Mode

See all filtered requests (useful for debugging filters):

```bash
python tracetap_main.py --listen 8080 --verbose --filter-host "api.example.com"
```

## SSL/HTTPS Considerations

TraceTap automatically handles HTTPS traffic by:
1. Generating SSL certificates on-the-fly
2. Acting as a man-in-the-middle proxy
3. Re-encrypting traffic to the destination

**Note:** For HTTPS capture to work, you may need to:
- Use the `-k` flag with cURL (skip certificate verification)
- Set `verify=False` in Python requests
- Configure your client to trust the mitmproxy CA certificate

### Installing mitmproxy CA Certificate (Optional)

For production use without certificate warnings:

```bash
# The CA cert is generated by mitmproxy at:
~/.mitmproxy/mitmproxy-ca-cert.pem

# Add it to your system's trusted certificates
# (instructions vary by OS)
```

## Troubleshooting

### Port Already in Use

If port 8080 is already taken, use a different port:

```bash
python tracetap_main.py --listen 8888
```

### No Traffic Being Captured

1. Verify proxy settings are configured correctly
2. Check if filters are too restrictive (try without filters first)
3. Use `--verbose` to see which requests are being filtered out

### SSL/Certificate Errors

- Use `-k` with cURL or `verify=False` in code
- Install the mitmproxy CA certificate
- Ensure `ssl_insecure=true` is set (default in TraceTap)

## How It Works

1. **Proxy Setup**: TraceTap starts mitmproxy listening on the specified port
2. **Traffic Interception**: All HTTP/HTTPS requests are intercepted
3. **Filtering**: Requests are checked against configured filters
4. **Capture**: Matching requests and responses are stored in memory
5. **Export**: On shutdown (Ctrl+C), data is exported to specified formats

## Contributing

Feel free to submit issues, feature requests, or pull requests!

## License

This project is provided as-is for educational and testing purposes.

## Credits

Built on top of [mitmproxy](https://mitmproxy.org/) - a powerful and flexible proxy tool.
