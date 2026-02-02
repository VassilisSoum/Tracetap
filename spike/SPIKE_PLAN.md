# UI Recording Validation Spike - Revised Plan

**Branch:** `spike/mcp-ui-recording`
**Duration:** 2 weeks
**Goal:** Validate feasibility of recording UI interactions + traffic → auto-generate Playwright tests

---

## 🔴 Critical Finding: MCP Not Suitable

**Research completed** (Task #26): Playwright MCP is designed for automation (active control), not event capture (passive monitoring).

**Impact:** Pivot from MCP approach to Playwright Trace Files approach.

---

## Revised Technical Approach

### OLD PLAN (Rejected)
```
MCP Server captures UI events → Correlate with mitmproxy traffic
```

**Problems:**
- ❌ No passive event monitoring
- ❌ No automatic timestamps
- ❌ Requires explicit tool calls
- ❌ Request/response model (not streaming)

### NEW PLAN (Recommended)
```
Playwright Trace Files capture UI events → Parse trace.json → Correlate with mitmproxy traffic
```

**Advantages:**
- ✅ Microsecond timestamp precision
- ✅ Complete event history with selectors
- ✅ Network requests included in trace
- ✅ Built-in to Playwright (no external dependencies)
- ✅ Visual debugging with Trace Viewer

---

## Revised Spike Tasks

### Task #26: ✅ Research Playwright MCP (COMPLETE)
**Status:** Done
**Output:** `spike/research/playwright-mcp-analysis.md`
**Finding:** Use Playwright Trace Files instead of MCP

### Task #27: Build Trace Recorder POC
**Goal:** Create a simple script that records user interactions as Playwright trace files

**Implementation:**
1. Launch Playwright browser with tracing enabled
2. Let user interact manually
3. Stop tracing on user signal (Enter key)
4. Save trace.zip

**Output:** `spike/poc/trace-recorder.ts`

**Acceptance Criteria:**
- [ ] Script launches browser
- [ ] User can interact manually
- [ ] Trace file is saved on completion
- [ ] trace.zip contains valid trace.json

### Task #28: Build Trace Parser POC
**Goal:** Parse trace.json and convert to Tracetap event format

**Implementation:**
1. Extract trace.zip
2. Parse trace.json
3. Filter relevant actions (click, type, navigate)
4. Convert μs timestamps to ms
5. Extract selectors and element data

**Output:** `spike/poc/trace-parser.ts`

**Acceptance Criteria:**
- [ ] Parses trace.json successfully
- [ ] Extracts UI events with timestamps
- [ ] Converts to Tracetap event format
- [ ] Outputs JSON event stream

### Task #29: Build Event Correlator POC
**Goal:** Correlate parsed UI events with mitmproxy traffic

**Implementation:**
1. Load UI events from trace parser
2. Load network traffic from mitmproxy JSON
3. Correlate by timestamp (±500ms window)
4. Build interaction graph (UI event → API calls)
5. Calculate correlation confidence

**Output:** `spike/poc/event-correlator.ts`

**Acceptance Criteria:**
- [ ] Links UI events to network requests
- [ ] Handles timing windows correctly
- [ ] Outputs correlated event pairs
- [ ] Calculates confidence scores

### Task #30: Test on Sample App & Document Results
**Goal:** Validate entire flow and make go/no-go decision

**Implementation:**
1. Use examples/ecommerce-api as test app
2. Record user session (login, add to cart, checkout)
3. Parse trace and mitmproxy data
4. Correlate events
5. Measure accuracy and edge cases

**Output:** `spike/RESULTS.md`

**Metrics:**
- Correlation accuracy (% of UI events correctly linked)
- Timestamp precision (average delta in ms)
- Edge cases identified
- Performance (time to process 10-minute session)

**Go/No-Go Decision:**
- ✅ GO: >80% correlation accuracy, <50ms average delta
- ❌ NO-GO: <70% correlation accuracy, >100ms average delta

---

## Implementation Plan

### Week 1: Core POC (Days 1-5)

**Day 1-2: Trace Recorder**
- Set up TypeScript project
- Implement trace recorder script
- Test with manual interactions
- Verify trace files

**Day 3-4: Trace Parser**
- Implement ZIP extraction
- Parse trace.json format
- Convert to Tracetap events
- Unit tests

**Day 5: Event Correlator**
- Implement timestamp correlation
- Build interaction graph
- Test with sample data

### Week 2: Validation & Documentation (Days 6-10)

**Day 6-7: Integration Testing**
- Run on examples/ecommerce-api
- Test multiple workflows
- Measure accuracy

**Day 8-9: Edge Case Testing**
- Delayed API calls (>500ms)
- Simultaneous requests
- Complex user flows
- Error scenarios

**Day 10: Documentation & Decision**
- Write RESULTS.md
- Calculate success metrics
- Make go/no-go recommendation
- Update main plan if GO

---

## Success Criteria

### Quantitative Metrics

| Metric | Target | Stretch |
|--------|--------|---------|
| Correlation accuracy | >80% | >90% |
| Average timestamp delta | <50ms | <20ms |
| Processing speed | <5s for 10min session | <2s |
| Event capture completeness | >95% | >99% |

### Qualitative Assessment

- [ ] Trace files capture all UI interactions
- [ ] Selectors are stable and reliable
- [ ] Network correlation feels accurate
- [ ] No major technical blockers identified
- [ ] Implementation path is clear

---

## Risk Assessment

### Low Risk (Resolved)

✅ **MCP viability** - Solved by using trace files instead
✅ **Timestamp precision** - Trace files provide μs precision
✅ **Event detail** - Trace files include complete event data

### Medium Risk (Mitigatable)

⚠️ **Delayed API calls** - Some requests happen >500ms after click
- Mitigation: Adaptive correlation windows, AI confidence scoring

⚠️ **Trace file size** - Large sessions create large files (1-50MB)
- Mitigation: Stream processing, compression, selective capture

⚠️ **Manual start/stop** - User must initiate tracing
- Mitigation: CLI wrapper, auto-start on page load

### High Risk (Monitor)

🔴 **Real-time feedback** - Trace files are post-recording only
- Impact: User doesn't see what's captured until after
- Mitigation: Progress indicators, live event count

---

## Deliverables

1. **spike/research/playwright-mcp-analysis.md** ✅ DONE
2. **spike/poc/trace-recorder.ts** - Week 1
3. **spike/poc/trace-parser.ts** - Week 1
4. **spike/poc/event-correlator.ts** - Week 1
5. **spike/RESULTS.md** - Week 2

---

## Decision Point

**End of Week 2:**

### IF GO (>80% accuracy, <50ms delta)
→ Proceed with full killer feature implementation (12 weeks)
→ Update architecture in main plan
→ Start Phase 1: Foundation

### IF NO-GO (<70% accuracy, >100ms delta)
→ Explore alternative approaches:
- Chrome DevTools Protocol (CDP) for real-time streaming
- Browser extension for passive capture
- Playwright Codegen integration
→ Run 1-week spike on best alternative

---

**Plan Version:** 2.0 (Revised)
**Last Updated:** February 2, 2026
**Status:** Ready to implement
