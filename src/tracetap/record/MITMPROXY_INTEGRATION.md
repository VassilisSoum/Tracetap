# mitmproxy Integration for TraceTap Recording

This document describes the integration between TraceTap's recording module and mitmproxy for network traffic capture.

## Overview

The recording session now automatically:
1. Starts mitmproxy proxy server in the background
2. Configures the browser to use the proxy
3. Captures all HTTP/HTTPS traffic during recording
4. Correlates captured traffic with UI events
5. Exports results in a unified format

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RecordingSession                         │
│  (Orchestrates entire recording workflow)                   │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             ▼                                ▼
    ┌────────────────┐                ┌──────────────┐
    │  TraceRecorder │                │  mitmproxy   │
    │  (Playwright)  │                │   Process    │
    └────────┬───────┘                └──────┬───────┘
             │                               │
             │ proxy=localhost:8888          │
             │◄──────────────────────────────┤
             │                               │
    ┌────────▼───────┐                ┌──────▼───────┐
    │   Browser      │                │ capture_addon│
    │  (Chromium)    │                │    (.py)     │
    └────────┬───────┘                └──────┬───────┘
             │                               │
             │  HTTP/HTTPS requests          │
             ├──────────────────────────────►│
             │                               │
             │  UI Events (trace.zip)        │  Network Traffic (traffic.json)
             ▼                               ▼
    ┌─────────────────────────────────────────────────────┐
    │              EventCorrelator                        │
    │  (Correlates UI events with network calls)          │
    └─────────────────────────────────────────────────────┘
```

## Components

### 1. RecordingSession (`session.py`)

The main orchestrator that manages the entire recording workflow.

**Key Methods:**
- `start(url)` - Starts mitmproxy, then starts browser recording
- `stop()` - Stops browser recording, then stops mitmproxy
- `analyze()` - Parses trace and correlates with network traffic
- `save_results()` - Saves all results to disk

**Lifecycle:**
```python
session = RecordingSession(
    session_name="checkout-flow",
    output_dir="recordings/",
    proxy_port=8888
)

# Start recording (launches mitmproxy + browser)
await session.start("https://shop.example.com")

# User interacts manually...

# Stop recording (stops browser + mitmproxy)
await session.stop()

# Analyze and correlate
result = await session.analyze()
session.save_results(result)
```

### 2. TraceRecorder (`recorder.py`)

Records UI interactions using Playwright tracing.

**Updates:**
- Added `proxy` parameter to `start_recording()`
- Browser context now configured with proxy server
- SSL errors ignored for mitmproxy interception

```python
await recorder.start_recording(
    url="https://example.com",
    proxy="http://localhost:8888"
)
```

### 3. RecordCaptureAddon (`capture_addon.py`)

Simplified mitmproxy addon for recording sessions.

**Features:**
- Captures all HTTP/HTTPS traffic
- Exports in NetworkRequest-compatible format
- Lifecycle managed by RecordingSession
- Configuration via environment variables

**Output Format:**
```json
{
  "session": "checkout-flow",
  "captured_at": "2024-01-15T10:30:00",
  "total_requests": 15,
  "requests": [
    {
      "method": "POST",
      "url": "https://api.example.com/checkout",
      "host": "api.example.com",
      "path": "/checkout",
      "timestamp": 1675234567890,
      "request": {
        "headers": {...},
        "body": "..."
      },
      "response": {
        "status": 200,
        "headers": {...},
        "body": "..."
      },
      "duration": 150
    }
  ]
}
```

## Configuration

### Environment Variables

The capture addon receives configuration via environment variables (set by RecordingSession):

- `TRACETAP_RECORD_OUTPUT` - Path to save traffic.json
- `TRACETAP_RECORD_SESSION` - Session name
- `TRACETAP_RECORD_QUIET` - Quiet mode (default: true)

### Proxy Port

Default proxy port is 8888. Can be customized:

```python
session = RecordingSession(
    session_name="my-session",
    proxy_port=9999  # Custom port
)
```

## mitmproxy Orchestration

### Starting mitmproxy

`RecordingSession._start_mitmproxy()`:
1. Validates capture addon exists
2. Sets environment variables for addon config
3. Launches mitmdump as subprocess
4. Waits 2 seconds for startup
5. Verifies process is running

**Command:**
```bash
mitmdump \
  --listen-host 0.0.0.0 \
  --listen-port 8888 \
  --set ssl_insecure=true \
  --set upstream_cert=false \
  --quiet \
  -s capture_addon.py
```

### Stopping mitmproxy

`RecordingSession._stop_mitmproxy()`:
1. Sends SIGTERM for graceful shutdown
2. Waits up to 5 seconds
3. Forces SIGKILL if needed
4. Addon's `done()` callback exports traffic.json

## File Organization

Each recording session creates a directory structure:

```
recordings/
└── 20240115_103000_a1b2c3d4/
    ├── metadata.json         # Session metadata
    ├── trace.zip            # Playwright trace
    ├── traffic.json         # Captured network traffic
    ├── events.json          # Parsed UI events
    └── correlation.json     # Correlated events
```

## Correlation

`EventCorrelator` links UI events with network calls:

```python
correlator = EventCorrelator(CorrelationOptions(window_ms=500))
result = correlator.correlate(ui_events, network_calls)
```

**Correlation Logic:**
- Time-window based (default ±500ms)
- Confidence scoring
- Prevents duplicate correlations
- One-to-many relationships (1 click → N API calls)

**Output:**
```json
{
  "correlated_events": [
    {
      "sequence": 1,
      "ui_event": {
        "type": "click",
        "selector": "button.checkout"
      },
      "network_calls": [
        {
          "method": "POST",
          "url": "https://api.example.com/checkout",
          "timestamp": 1675234567890
        }
      ],
      "correlation": {
        "confidence": 0.85,
        "time_delta": 120,
        "method": "window"
      }
    }
  ],
  "stats": {
    "correlation_rate": 0.87,
    "average_confidence": 0.75
  }
}
```

## Requirements

### Python Dependencies

```
playwright>=1.40.0
mitmproxy>=10.0.0
```

Install:
```bash
pip install playwright mitmproxy
playwright install chromium
```

### System Requirements

- Python 3.9+
- Chromium browser (installed by Playwright)
- Network access (for proxy)

## Troubleshooting

### mitmproxy fails to start

**Error:** `mitmproxy not found`

**Solution:**
```bash
pip install mitmproxy
```

### SSL Certificate Errors

The integration uses `ssl_insecure=true` and `ignore_https_errors=true` to handle mitmproxy's SSL interception. This is normal for local testing.

### Port Already in Use

**Error:** `Address already in use`

**Solution:** Change proxy port:
```python
session = RecordingSession(proxy_port=9999)
```

### No Network Traffic Captured

**Possible causes:**
1. Browser not using proxy (check browser logs)
2. mitmproxy crashed (check process status)
3. Firewall blocking proxy connection

**Debug:** Check mitmproxy process logs:
```python
# In RecordingSession._start_mitmproxy(), remove:
stdout=subprocess.PIPE
stderr=subprocess.PIPE

# This will show mitmproxy output in console
```

### Correlation Rate Low

**Possible causes:**
1. Time window too narrow (increase `window_ms`)
2. Network timing varies significantly
3. Many UI events don't trigger network calls

**Solution:**
```python
result = await session.analyze(
    correlation_options=CorrelationOptions(
        window_ms=1000,  # Increase window
        include_orphans=True  # Include events with no network calls
    )
)
```

## Testing

Run the integration test:

```bash
cd src/tracetap/record
python test_integration.py https://example.com
```

This will:
1. Start recording session
2. Launch browser with proxy
3. Wait for manual interaction
4. Stop and analyze
5. Show results

## Comparison with Main TraceTap Addon

| Feature | RecordCaptureAddon | TraceTapAddon (main) |
|---------|-------------------|---------------------|
| Purpose | Recording sessions | General traffic capture |
| Lifecycle | Managed by RecordingSession | Standalone CLI tool |
| Configuration | Environment variables | Command-line arguments |
| Export Format | NetworkRequest-compatible | Multiple formats (Postman, OpenAPI, Raw) |
| Filtering | None (captures all) | Host and regex filters |
| Output | Single traffic.json | Multiple export options |
| Complexity | Simplified | Full-featured |

## Future Enhancements

1. **Smart Filtering**: Automatically filter out assets (images, CSS, fonts)
2. **Request Grouping**: Group related requests (e.g., GraphQL batches)
3. **Response Mocking**: Generate WireMock stubs from captured traffic
4. **Replay Mode**: Replay network traffic without hitting real APIs
5. **Diff Mode**: Compare network traffic between recording sessions

## References

- [mitmproxy Documentation](https://docs.mitmproxy.org/)
- [Playwright Tracing](https://playwright.dev/docs/trace-viewer)
- [TraceTap Main Addon](../capture/tracetap_addon.py)
- [EventCorrelator](./correlator.py)
