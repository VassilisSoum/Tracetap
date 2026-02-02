# TraceTap Record CLI Usage

This document describes how to use the `tracetap record` command for capturing UI interactions with network traffic.

## Installation

After installing tracetap with the record feature:

```bash
pip install -e .
playwright install chromium  # Install browser binaries
```

## Basic Usage

### Record a Session

```bash
# Basic usage - opens browser for manual interaction
tracetap record https://example.com

# With custom session name
tracetap record https://example.com -n login-flow

# With custom output directory
tracetap record https://example.com -o ./my-recordings

# Headless mode (no visible browser)
tracetap record https://example.com --headless
```

### Advanced Options

```bash
# Custom correlation window (time between UI event and network call)
tracetap record https://example.com --window-ms 1000

# Minimum confidence threshold for correlations
tracetap record https://example.com --min-confidence 0.7

# Custom mitmproxy port
tracetap record https://example.com --proxy-port 8888

# Disable screenshots in trace (smaller file size)
tracetap record https://example.com --no-screenshots

# Disable DOM snapshots (smaller file size)
tracetap record https://example.com --no-snapshots

# Enable verbose logging
tracetap record https://example.com -v
```

## Command-Line Arguments

### Required Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `url` | URL to record | `https://example.com` |

### Optional Arguments

| Flag | Description | Default |
|------|-------------|---------|
| `-o, --output DIR` | Output directory for session files | `./recordings` |
| `-n, --name NAME` | Session name | auto-generated |
| `--headless` | Run browser in headless mode | `False` |
| `--proxy-port PORT` | mitmproxy port | `8888` |
| `--window-ms MS` | Correlation time window (ms) | `500` |
| `--min-confidence N` | Minimum correlation confidence | `0.5` |
| `--no-screenshots` | Disable screenshots in trace | disabled |
| `--no-snapshots` | Disable DOM snapshots in trace | disabled |
| `-v, --verbose` | Enable verbose debug logging | disabled |

## Workflow

### 1. Start Recording

```bash
tracetap record https://app.example.com -n checkout-test
```

**Output:**
```
╔════════════════════════════════════════════════╗
║         TraceTap Recording Session            ║
║                                               ║
║ Target URL: https://app.example.com          ║
║ Session Name: checkout-test                   ║
║ Output Directory: ./recordings                ║
║ Headless Mode: False                          ║
║ Proxy Port: 8888                              ║
║ Correlation Window: 500ms                     ║
║ Min Confidence: 0.5                           ║
║                                               ║
║ Browser will open. Interact with the         ║
║ application, then press ENTER to stop.       ║
╚════════════════════════════════════════════════╝

Starting recording session...

✓ Recording started
  Session ID: 20260202_143052_a8b9c7d2
  Browser opened at: https://app.example.com

Interact with the application in the browser.
Press ENTER in this terminal when you're done...
```

### 2. User Interaction

At this point:
- A Chromium browser window opens
- Navigate to the target URL
- Perform your test actions (click, type, navigate)
- All UI events and network traffic are captured
- Press ENTER in the terminal when done

### 3. Stop Recording and Analysis

After pressing ENTER:

```
Stopping recording...

✓ Recording stopped
  Duration: 45.3s
  Trace file: ./recordings/20260202_143052_a8b9c7d2/trace.zip

Analyzing session...

✓ Analysis complete

📊 Parse Results:
   UI Events: 23
   Event Types: click, navigate, fill

📊 Correlation Statistics:
   Total UI Events: 23
   Total Network Calls: 15
   Correlated UI Events: 18
   Correlated Network Calls: 14
   Correlation Rate: 78.3%
   Average Confidence: 82.5%
   Average Time Delta: 127.3ms

🎯 Quality Assessment:
   ✅ GOOD - Acceptable correlation quality

⏱️  Correlation Timeline (first 10):
   1. [14:30:53.245] click    [data-testid="login-btn"]
      └─ 1 call(s), 89% confidence, +45ms
         1. POST /api/auth/login (200)

   2. [14:30:58.891] navigate https://app.example.com/dashboard
      └─ 2 call(s), 92% confidence, +103ms
         1. GET /api/user/profile (200)
         2. GET /api/notifications (200)
   ...

Saving results...

✓ Session saved successfully!
   Location: ./recordings/20260202_143052_a8b9c7d2
   Metadata: ./recordings/20260202_143052_a8b9c7d2/metadata.json

╔════════════════════════════════════════════════╗
║                 Next Steps                     ║
║                                               ║
║ 1. Generate Playwright tests from session:    ║
║    tracetap-generate ./recordings/...         ║
║                                               ║
║ 2. Replay the trace file in Playwright:       ║
║    playwright show-trace trace.zip            ║
║                                               ║
║ 3. Analyze correlations in detail:            ║
║    cat correlation.json                       ║
║                                               ║
║ Learn more: github.com/VassilisSoum/tracetap ║
╚════════════════════════════════════════════════╝
```

## Output Files

After recording, the following files are created in the output directory:

```
recordings/
└── 20260202_143052_a8b9c7d2/
    ├── trace.zip              # Playwright trace file
    ├── events.json            # Parsed UI events
    ├── correlation.json       # Correlated events with network calls
    ├── traffic.json           # Raw network traffic from mitmproxy
    └── metadata.json          # Session metadata
```

### File Contents

#### metadata.json
```json
{
  "session_id": "20260202_143052_a8b9c7d2",
  "session_name": "checkout-test",
  "url": "https://app.example.com",
  "start_time": "2026-02-02T14:30:52.123456",
  "end_time": "2026-02-02T14:31:37.456789",
  "duration": 45.333,
  "output_dir": "./recordings/20260202_143052_a8b9c7d2",
  "trace_file": "./recordings/20260202_143052_a8b9c7d2/trace.zip",
  "events_file": "./recordings/20260202_143052_a8b9c7d2/events.json",
  "correlation_file": "./recordings/20260202_143052_a8b9c7d2/correlation.json",
  "traffic_path": "./recordings/20260202_143052_a8b9c7d2/traffic.json",
  "status": "completed"
}
```

#### events.json
```json
{
  "events": [
    {
      "type": "click",
      "timestamp": 1706880653245,
      "selector": "[data-testid='login-btn']",
      "url": "https://app.example.com/login",
      "metadata": {
        "tag": "button",
        "text": "Login"
      }
    }
  ],
  "stats": {
    "total_events": 23,
    "event_types": {
      "click": 15,
      "navigate": 5,
      "fill": 3
    }
  }
}
```

#### correlation.json
```json
{
  "correlated_events": [
    {
      "sequence": 1,
      "ui_event": { /* event details */ },
      "network_calls": [
        {
          "method": "POST",
          "url": "/api/auth/login",
          "timestamp": 1706880653290,
          "response_status": 200
        }
      ],
      "correlation": {
        "confidence": 0.89,
        "time_delta": 45.0,
        "method": "exact",
        "reasoning": "click triggered 1 call(s) [POST] to /api/auth/login after 45ms"
      }
    }
  ],
  "stats": {
    "total_ui_events": 23,
    "total_network_calls": 15,
    "correlated_ui_events": 18,
    "correlated_network_calls": 14,
    "average_confidence": 0.825,
    "average_time_delta": 127.3,
    "correlation_rate": 0.783
  }
}
```

## Common Use Cases

### 1. Login Flow Recording

```bash
tracetap record https://app.example.com/login -n login-flow

# In browser:
# 1. Enter username and password
# 2. Click login button
# 3. Wait for redirect to dashboard
# 4. Press ENTER in terminal
```

### 2. E-commerce Checkout

```bash
tracetap record https://shop.example.com -n checkout-flow -o ./e2e-tests

# In browser:
# 1. Browse products
# 2. Add items to cart
# 3. Proceed to checkout
# 4. Fill shipping info
# 5. Complete payment
# 6. Press ENTER in terminal
```

### 3. API-Heavy Dashboard

```bash
tracetap record https://dashboard.example.com --window-ms 1000 -n dashboard-init

# Longer window to capture delayed API calls
```

### 4. Headless Recording (CI/CD)

```bash
tracetap record https://example.com --headless -n ci-test

# Note: Requires programmatic interaction or pre-recorded script
# Not suitable for manual testing
```

## Troubleshooting

### Browser Doesn't Open

```bash
# Check if Chromium is installed
playwright install chromium

# Check if port 8888 is available
lsof -i :8888
```

### No Network Traffic Captured

- Ensure mitmproxy is running on the correct port
- Check browser proxy settings are correct
- Verify HTTPS certificate is trusted

### Low Correlation Rate

- Increase correlation window: `--window-ms 1000`
- Lower confidence threshold: `--min-confidence 0.4`
- Check if timestamps are accurate

### Large Trace Files

- Disable screenshots: `--no-screenshots`
- Disable snapshots: `--no-snapshots`
- Record shorter sessions

## Integration with Test Generation

After recording, use the session to generate Playwright tests:

```bash
# Generate tests from recorded session
tracetap-generate recordings/20260202_143052_a8b9c7d2 -o tests/checkout.spec.ts

# Run generated tests
npx playwright test tests/checkout.spec.ts
```

## Tips for Best Results

1. **Clear Session State**: Start with a clean browser session (no cookies/cache)
2. **Stable Selectors**: Use `data-testid` attributes for better selector generation
3. **Wait for Completion**: Let each action complete before starting the next
4. **Moderate Speed**: Don't rush through actions too quickly
5. **Short Sessions**: Keep recordings under 5 minutes for better performance
6. **Meaningful Names**: Use descriptive session names for easy identification

## Standalone Script

You can also use the standalone script:

```bash
./tracetap-record.py https://example.com -n my-test
```

This is useful for development or when tracetap isn't installed system-wide.
