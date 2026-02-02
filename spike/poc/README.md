# TraceTap Spike POC - Trace Recorder

Proof-of-concept implementation for recording UI interactions using Playwright trace files.

## Setup

```bash
cd spike/poc
npm install
```

## Usage

### 1. Record a Session

```bash
# Record interactions on any website
npx ts-node trace-recorder.ts https://example.com my-session.zip

# Or use the npm script
npm run record https://example.com my-session.zip
```

**Workflow:**
1. Browser opens with the target URL
2. Interact manually (click, type, navigate)
3. Press ENTER in terminal when done
4. Trace file saved to `my-session.zip`

### 2. View Trace Visually

```bash
# Open Playwright Trace Viewer
npx playwright show-trace my-session.zip
```

This shows:
- Timeline of all actions
- Screenshots at each step
- Network requests
- Console logs
- DOM snapshots

### 3. Parse Trace Events (Coming in Task #28)

```bash
npm run parse my-session.zip
```

## What Gets Captured

The trace file contains:
- ✅ **UI Events** with microsecond timestamps
  - Clicks (with selectors)
  - Keyboard input
  - Navigation
  - Form interactions
- ✅ **Network Requests**
  - Method, URL, headers
  - Request/response bodies
  - Timing data
- ✅ **DOM Snapshots** before/after each action
- ✅ **Screenshots** at each step
- ✅ **Console Messages** (logs, errors, warnings)

## Example Session

```bash
# Test with a real website
npx ts-node trace-recorder.ts https://www.google.com google-search.zip

# Actions to perform:
# 1. Type "playwright testing" in search box
# 2. Click "Google Search" button
# 3. Press ENTER in terminal

# View the trace
npx playwright show-trace google-search.zip
```

## Trace File Format

The `trace.zip` contains:
- `trace.json` - Main event timeline with timestamps
- `trace.network` - Network request/response data
- `resources/` - Screenshots and snapshots
- `actions.json` - Detailed action log

## Next Steps

1. **Task #27** ✅ Build trace recorder → YOU ARE HERE
2. **Task #28** - Build trace parser (extract events from trace.json)
3. **Task #29** - Build event correlator (link UI events to network traffic)
4. **Task #30** - Test on sample app and measure accuracy

## Troubleshooting

**Browser doesn't open:**
```bash
# Install Playwright browsers
npx playwright install chromium
```

**"Module not found" error:**
```bash
npm install
```

**Trace file is empty:**
- Make sure you performed some actions before pressing ENTER
- Check that tracing started before page navigation

## Technical Details

**Timestamp Precision:** Microseconds (μs)
**Event Types Captured:** click, fill, navigate, press, select, check, etc.
**Browser:** Chromium (Chrome-based)
**File Size:** Typically 1-10MB for a 2-minute session
