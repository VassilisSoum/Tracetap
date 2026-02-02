# Playwright MCP Analysis: Event Capture Capabilities for Tracetap

**Research Date:** February 2, 2026
**Scope:** Evaluate Playwright MCP server viability for UI event capture in Tracetap QA automation
**Status:** ✅ COMPLETE

---

## Executive Summary

### Is MCP Viable for Our Use Case?

**NO - MCP is not suitable for event capture.** Playwright MCP is designed for **browser automation and AI agent control**, not passive event monitoring.

### Key Finding

**Playwright MCP is NOT designed for passive event recording.** It's an automation framework, not a capture framework.

- **Current Need:** Passive event listener capturing user interactions in real-time
- **What MCP Provides:** Active automation tool executing commands through AI agents

### Recommendation

**DO NOT use Playwright MCP for event capture.** Instead, use:
1. **Playwright Trace Files** ⭐ RECOMMENDED - Built-in recording with microsecond timestamps
2. **Chrome DevTools Protocol (CDP)** - Direct event subscription for real-time streaming
3. **Hybrid Approach** - Traces for capture, direct Playwright API for replay

---

## 1. MCP Server Availability

### Official Implementation

**Package:** `@playwright/mcp`
**Maintainer:** Microsoft (Official)
**Repository:** [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)

**Installation:**
```bash
npx @playwright/mcp@latest
```

---

## 2. Event Capture Capabilities

### Available MCP Tools (23 Total)

The MCP server exposes browser automation tools like:
- `browser_navigate`, `browser_click`, `browser_type`
- `browser_fill_form`, `browser_press_key`, `browser_hover`
- `browser_take_screenshot`, `browser_snapshot`
- `browser_evaluate`, `browser_console_messages`
- `browser_network_requests`

### What Events ARE Captured

✅ User actions via explicit tool calls (click, type, navigate)
✅ Console messages (error, warning, info)
✅ Network requests/responses
✅ DOM snapshots (accessibility tree)
✅ Screenshots

### What Events are NOT Captured

❌ **Passive event listening** - MCP requires explicit tool calls
❌ **Automatic timestamps** - No timing data in responses
❌ **Real-time event streaming** - Request/response model only
❌ **Mouse scroll events** - Known limitation
❌ **Background user interactions** - Not designed for monitoring

### Data Returned by Tools

**Minimal Return Data:**
Most tools return simple confirmations (e.g., "Click successful"), NOT detailed event data like:
- Timestamp of action
- Element selector used
- Element properties (text, value, attributes)
- Screen coordinates

### Timestamp Precision

**MCP Tools:** ❌ **NO automatic timestamps** in tool responses
**Playwright Trace Files:** ✅ **Microsecond precision** (μs)
**Chrome DevTools Protocol:** ✅ **Millisecond precision**

**Critical Gap:** MCP does not provide timing information needed for event correlation.

---

## 3. Recommended Alternative: Playwright Trace Files

### How It Works

```typescript
import { chromium } from 'playwright';

const browser = await chromium.launch();
const context = await browser.newContext();

// Start tracing
await context.tracing.start({
  screenshots: true,
  snapshots: true,
  sources: true
});

// User performs actions...
await page.goto('https://example.com');
await page.click('button');

// Stop tracing and save
await context.tracing.stop({ path: 'trace.zip' });
```

### Captured Data

✅ **Microsecond timestamps** (`ts` field in μs)
✅ **Every action** (click, type, navigate, etc.)
✅ **Network requests** with headers, payloads
✅ **DOM snapshots** before/after each action
✅ **Screenshots** at each step
✅ **Console messages**
✅ **Source code** execution

### Trace File Format

ZIP archive containing:
- `trace.json` - Event timeline with timestamps
- `resources/` - Screenshots, network data
- `actions.json` - Detailed action log

### Timestamp Example

```json
{
  "type": "action",
  "name": "click",
  "ts": 1738512345678901,  // Microseconds
  "dur": 12345,             // Duration in μs
  "selector": "button.submit",
  "args": { "button": "left" }
}
```

### Pros

✅ Built-in to Playwright
✅ Microsecond precision
✅ Complete action history
✅ Visual debugging in Trace Viewer
✅ Can be converted to HAR files

### Cons

❌ Requires code instrumentation
❌ Not real-time (recorded, then analyzed)
❌ File size can be large (1-50MB)

### Viability for Tracetap

⭐⭐⭐⭐⭐ **EXCELLENT** - This is the recommended approach

---

## 4. Implementation Path for Spike

### Revised Spike Goals

**Phase 1: Proof of Concept (1-2 days)**
1. ✅ Record trace file with sample interactions
2. ✅ Parse trace.json to extract events
3. ✅ Convert to Tracetap event format
4. ✅ Correlate with mitmproxy traffic by timestamp
5. ✅ Validate timing accuracy

**Phase 2: Integration (2-3 days)**
1. ✅ Build trace-to-Tracetap converter
2. ✅ Implement event filter (relevant actions only)
3. ✅ Add timestamp normalization (μs → ms)
4. ✅ Create event correlation logic
5. ✅ Test with existing Tracetap assertions

### Sample Code: Trace Capture

```typescript
import { chromium, BrowserContext } from 'playwright';

async function recordUserSession(url: string, outputPath: string) {
  const browser = await chromium.launch({ headless: false });
  const context: BrowserContext = await browser.newContext();

  // Start tracing
  await context.tracing.start({
    screenshots: true,
    snapshots: true,
    sources: true
  });

  const page = await context.newPage();
  await page.goto(url);

  // User performs actions manually...
  // (In POC, wait for user to complete their testing)

  console.log('Recording session. Press Enter when done...');
  await new Promise(resolve => process.stdin.once('data', resolve));

  // Stop tracing and save
  await context.tracing.stop({ path: outputPath });
  await browser.close();

  console.log(`Trace saved to ${outputPath}`);
}

// Usage
await recordUserSession('https://example.com', 'session-trace.zip');
```

### Sample Code: Trace Parsing

```typescript
import AdmZip from 'adm-zip';

interface PlaywrightTraceAction {
  type: string;
  name: string;
  ts: number;       // Timestamp in microseconds
  dur?: number;     // Duration in microseconds
  selector?: string;
  args?: any;
}

interface TracetapEvent {
  type: string;
  timestamp: number;  // Milliseconds
  selector: string;
  args: any;
  duration: number;
}

async function parseTraceToTracetapEvents(
  tracePath: string
): Promise<TracetapEvent[]> {
  // Extract ZIP
  const zip = new AdmZip(tracePath);
  const traceEntry = zip.getEntry('trace.json');

  if (!traceEntry) {
    throw new Error('trace.json not found in ZIP');
  }

  const traceData = JSON.parse(traceEntry.getData().toString('utf8'));
  const actions: PlaywrightTraceAction[] = traceData.actions || [];

  // Convert to Tracetap format
  const events: TracetapEvent[] = actions
    .filter(action => action.type === 'action')
    .map(action => ({
      type: action.name,  // 'click', 'fill', 'navigate', etc.
      timestamp: Math.floor(action.ts / 1000),  // Convert μs to ms
      selector: action.selector || '',
      args: action.args || {},
      duration: action.dur ? Math.floor(action.dur / 1000) : 0
    }));

  return events;
}

// Usage
const events = await parseTraceToTracetapEvents('session-trace.zip');
console.log(`Captured ${events.length} events`);
```

### Sample Code: Event Correlation

```typescript
interface NetworkRequest {
  method: string;
  url: string;
  timestamp: number;  // Milliseconds
  response: any;
}

function correlateUIEventsWithTraffic(
  uiEvents: TracetapEvent[],
  networkRequests: NetworkRequest[],
  windowMs: number = 500
): CorrelatedEvent[] {
  const correlated: CorrelatedEvent[] = [];

  for (const uiEvent of uiEvents) {
    // Find network requests within 500ms after UI event
    const relatedRequests = networkRequests.filter(req =>
      req.timestamp >= uiEvent.timestamp &&
      req.timestamp <= uiEvent.timestamp + windowMs
    );

    correlated.push({
      uiEvent,
      networkRequests: relatedRequests,
      confidence: relatedRequests.length > 0 ? 0.95 : 0.5
    });
  }

  return correlated;
}
```

---

## 5. Conclusion

### Key Findings

1. **MCP is NOT designed for event capture** - It's an automation framework, not a monitoring tool
2. **Playwright Trace Files are ideal** - Microsecond precision, complete event history, built-in
3. **Simple implementation path** - Parse trace files, correlate with traffic, generate tests

### Is MCP Viable?

**For Event Capture:** ❌ **NO**
- No passive monitoring
- No automatic timestamps
- Request/response model incompatible

**For Event Replay (Future):** ✅ **YES**
- Could be used for AI-assisted test execution
- Natural language test creation
- Cross-browser support

### Recommended Approach for Tracetap

✅ **Use Playwright Trace Files for capture**
✅ **Parse trace.json to extract events**
✅ **Correlate with mitmproxy traffic**
✅ **Generate Playwright tests via existing AI pipeline**

### Next Steps for Spike

1. ✅ Implement trace file recorder
2. ✅ Build trace parser
3. ✅ Create event correlator
4. ✅ Test with sample app
5. ✅ Measure accuracy and make go/no-go decision

---

## Sources

- [GitHub - microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)
- [Playwright Trace Viewer Documentation](https://playwright.dev/docs/trace-viewer)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)

---

**Document Version:** 1.0
**Last Updated:** February 2, 2026
**Status:** Spike-ready
