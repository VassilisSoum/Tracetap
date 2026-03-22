# TraceTap Recording Module

Complete recording solution for capturing UI interactions and network traffic during manual testing sessions.

## Features

- **UI Recording**: Capture browser interactions using Playwright tracing
- **Network Capture**: Automatic mitmproxy integration for HTTP/HTTPS traffic
- **Event Correlation**: Link UI events with network calls using time-based correlation
- **Session Management**: Complete lifecycle management with persistence
- **High Precision**: Microsecond-accurate timestamps for reliable correlation

## Quick Start

```python
import asyncio
from tracetap.record import RecordingSession, RecorderOptions

async def record_session():
    # Create session
    session = RecordingSession(
        session_name="login-flow",
        output_dir="recordings/",
        recorder_options=RecorderOptions(headless=False)
    )

    # Start recording (launches mitmproxy + browser)
    await session.start("https://app.example.com")

    # User interacts manually...
    input("Press ENTER to stop recording...")

    # Stop recording
    await session.stop()

    # Analyze and correlate
    result = await session.analyze()
    session.save_results(result)

    print(f"✅ Session saved to: {result.metadata.output_dir}")
    print(f"   Correlation rate: {result.stats['correlation_rate']:.1%}")

asyncio.run(record_session())
```

## Components

### 1. RecordingSession

High-level API for complete recording workflows. Orchestrates all components.

**Key Methods:**
- `start(url)` - Start recording at URL
- `stop()` - Stop recording and save files
- `analyze()` - Parse events and correlate with network
- `save_results()` - Persist all results to disk
- `list_sessions()` - List all recorded sessions

### 2. TraceRecorder

Records UI interactions using Playwright tracing.

**Features:**
- Captures clicks, fills, navigation
- Screenshots and DOM snapshots
- Source maps for debugging
- Proxy support for network capture

### 3. TraceParser

Parses Playwright trace files to extract UI events.

**Extracted Events:**
- Click events with selectors
- Input/fill events with values
- Navigation events with URLs
- Timing information (microsecond precision)

### 4. EventCorrelator

Correlates UI events with network traffic.

**Correlation Method:**
- Time-window based (default ±500ms)
- Confidence scoring (0.0 - 1.0)
- One-to-many relationships
- Duplicate prevention

### 5. mitmproxy Integration

Automatic network traffic capture via mitmproxy proxy.

**Features:**
- Background proxy process
- SSL interception
- NetworkRequest-compatible export
- Graceful lifecycle management

See [MITMPROXY_INTEGRATION.md](./MITMPROXY_INTEGRATION.md) for details.

## Architecture

```
RecordingSession
├── TraceRecorder (Playwright)
│   └── Browser with Proxy
├── mitmproxy Process
│   └── RecordCaptureAddon
├── TraceParser
│   └── Extract UI Events
└── EventCorrelator
    └── Link Events + Network
```

## Output Files

Each recording session creates:

```
recordings/20240115_103000_a1b2c3d4/
├── metadata.json         # Session info (ID, duration, status)
├── trace.zip            # Playwright trace (view with playwright show-trace)
├── traffic.json         # Network traffic (mitmproxy capture)
├── events.json          # Parsed UI events
└── correlation.json     # Correlated events with confidence scores
```

## Configuration

### RecorderOptions

```python
RecorderOptions(
    headless=False,        # Show browser (True = background)
    screenshots=True,      # Capture screenshots
    snapshots=True,        # Capture DOM snapshots
    sources=True,          # Include source maps
    viewport_width=1280,   # Browser width
    viewport_height=720    # Browser height
)
```

### CorrelationOptions

```python
CorrelationOptions(
    window_ms=500,         # Time window for correlation (ms)
    min_confidence=0.5,    # Minimum confidence threshold
    include_orphans=False  # Include events with no network calls
)
```

## Examples

### Basic Recording

```python
from tracetap.record import RecordingSession

session = RecordingSession(session_name="checkout")
await session.start("https://shop.example.com")
# ... manual interaction ...
await session.stop()
result = await session.analyze()
session.save_results(result)
```

### Custom Configuration

```python
from tracetap.record import (
    RecordingSession,
    RecorderOptions,
    CorrelationOptions
)

session = RecordingSession(
    session_name="api-test",
    output_dir="my_recordings/",
    recorder_options=RecorderOptions(
        headless=True,
        screenshots=False
    ),
    proxy_port=9999  # Custom proxy port
)

await session.start("https://api.example.com")
await session.stop()

result = await session.analyze(
    correlation_options=CorrelationOptions(
        window_ms=1000,      # Longer window
        min_confidence=0.4,  # Lower threshold
        include_orphans=True # Include all events
    )
)
```

### Load Existing Session

```python
session = RecordingSession(output_dir="recordings/")
sessions = session.list_sessions()

for metadata in sessions:
    print(f"{metadata.session_id}: {metadata.session_name}")
    print(f"  URL: {metadata.url}")
    print(f"  Duration: {metadata.duration}s")

# Load specific session
result = session.load_session("20240115_103000_a1b2c3d4")
```

### View Correlation Results

```python
result = await session.analyze()

# Print statistics
stats = result.correlation_result.stats
print(f"Correlation Rate: {stats['correlation_rate']:.1%}")
print(f"Average Confidence: {stats['average_confidence']:.1%}")
print(f"Average Time Delta: {stats['average_time_delta']:.0f}ms")

# Iterate correlated events
for event in result.correlation_result.correlated_events:
    print(f"\n{event.sequence}. {event.ui_event.type}")
    print(f"   Confidence: {event.correlation.confidence:.1%}")
    print(f"   Network Calls: {len(event.network_calls)}")

    for nc in event.network_calls:
        print(f"     • {nc.method} {nc.path} → {nc.response_status}")
```

## Requirements

```bash
pip install playwright mitmproxy
playwright install chromium
```

**Python:** 3.9+

## Troubleshooting

### mitmproxy not found

```bash
pip install mitmproxy
```

### Playwright not installed

```bash
pip install playwright
playwright install chromium
```

### Port already in use

```python
session = RecordingSession(proxy_port=9999)  # Different port
```

### Low correlation rate

Try increasing the time window:

```python
result = await session.analyze(
    correlation_options=CorrelationOptions(window_ms=1000)
)
```

### SSL certificate errors

This is normal for mitmproxy SSL interception. The browser is configured to ignore SSL errors during recording.

## Testing

Run integration test:

```bash
cd src/tracetap/record
python test_integration.py https://example.com
```

Run example:

```bash
cd examples
python recording_session_example.py
```

## File Reference

| File | Purpose |
|------|---------|
| `session.py` | RecordingSession class - main orchestrator |
| `recorder.py` | TraceRecorder - Playwright integration |
| `parser.py` | TraceParser - Extract events from traces |
| `correlator.py` | EventCorrelator - Link events with network |
| `capture_addon.py` | mitmproxy addon for traffic capture |
| `test_integration.py` | Integration test script |
| `MITMPROXY_INTEGRATION.md` | Detailed integration docs |

## Related Modules

- [TraceTap Capture](../capture/) - Standalone mitmproxy traffic capture
- [TraceTap Replay](../replay/) - Replay captured sessions
- [TraceTap Generators](../generators/) - Generate tests from recordings

## License

See main TraceTap license.
