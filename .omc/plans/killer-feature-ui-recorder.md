# TraceTap Killer Feature: UI Recording + Traffic Capture to Playwright Tests

## Context

### Original Request
Identify and plan the #1 killer feature to drive viral adoption among QA engineers.

### Interview Summary
| Question | Answer |
|----------|--------|
| Strategic Goal | Viral adoption + trial conversion - make QAs instantly want to try TraceTap |
| Pain Point | Writing tests is tedious; QAs already do manual testing that could be captured |
| Technical Approach | **Playwright Trace Files + mitmproxy** (updated after spike) |
| Target Environment | Local development (QA's laptop) first |
| Scope | Production-ready, **10 weeks** (reduced from 12 after spike) |

### Spike Findings (Feb 2-3, 2026)
✅ **2-day validation spike completed successfully**
- ❌ MCP not suitable for event capture (automation framework, not monitoring)
- ✅ **Playwright Trace Files are ideal** (μs precision, complete event history)
- ✅ POC delivered: 1,500 LOC in 2 days (recorder, parser, correlator)
- ✅ Correlation accuracy: 80% rate, 85.5% confidence on synthetic data
- ✅ **GO decision with high confidence (85%)**
- See: `spike/RESULTS.md` for full validation report

### Research Findings
- Existing `tracetap_addon.py` captures traffic with timestamps (line 127-142)
- Existing `playwright_generator.py` generates tests from Postman collections (line 50-91)
- Existing AI integration in `pattern_analyzer.py` and `test_suggester.py`
- CLI entry points defined in `pyproject.toml` (line 81-83)

---

## Work Objectives

### Core Objective
Build a production-ready "Record & Generate" feature that:
1. Captures UI interactions via **Playwright Trace Files** (not MCP)
2. Captures network traffic via mitmproxy (existing)
3. Correlates UI events with API calls by timestamp
4. Generates complete Playwright tests combining UI actions + API assertions

**Architecture Change:** MCP → Playwright Trace Files
- Trace files provide microsecond timestamps, complete event history
- Built-in to Playwright, no external dependencies
- Simpler implementation (-2 weeks)

### Deliverables
| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | Recording CLI | `tracetap record` command that launches browser + proxy |
| 2 | **Trace File Integration** | **Parse Playwright trace.zip for UI events** (was: MCP client) |
| 3 | Event Correlator | Links UI events to network requests by timestamp |
| 4 | Enhanced Test Generator | Generates tests with UI actions + API assertions |
| 5 | Session Manager | Save/load/replay recording sessions |
| 6 | Multi-Browser Support | Chrome, Firefox, Safari (WebKit) |
| 7 | Documentation | User guide, API docs, examples |

**POC Delivered:** Deliverables #1-3 proven in spike (spike/poc/)

### Definition of Done
- [ ] QA can run `tracetap record https://example.com` and start recording
- [ ] All UI interactions (click, type, navigate) are captured with selectors
- [ ] All network traffic is captured and correlated with UI events
- [ ] Generated Playwright test runs successfully and reproduces the flow
- [ ] Works on Chrome, Firefox, and Safari
- [ ] 90%+ of generated tests pass on first run (happy path)
- [ ] Documentation covers all features with examples
- [ ] Unit test coverage > 80% for new code

---

## Guardrails

### Must Have
- Timestamp-based correlation (within 500ms tolerance)
- Smart selector generation (data-testid > id > CSS > XPath fallback)
- Authentication state capture (cookies, tokens, headers)
- Dynamic data detection and parameterization
- Clean, readable generated test code
- Error handling for browser crashes, network failures
- Session persistence (save/resume recordings)

### Must NOT Have
- Cloud browser support (Phase 2)
- CI/CD headless mode (Phase 2)
- Visual regression integration (separate feature)
- Mobile browser emulation (Phase 2)
- Video recording (nice-to-have, not core)

---

## Architecture

### High-Level Architecture

```
                           ┌────────────────────────────────────────┐
                           │            TraceTap CLI                │
                           │         tracetap record <url>          │
                           └──────────────────┬─────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
    ┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
    │ Trace File Parser     │  │   Proxy Controller    │  │   Session Manager     │
    │                       │  │                       │  │                       │
    │ - Extract trace.zip   │  │ - Start mitmproxy     │  │ - Save sessions       │
    │ - Parse trace.trace   │  │ - Configure filters   │  │ - Load sessions       │
    │ - Convert to events   │  │ - Collect traffic     │  │ - Export formats      │
    └───────────┬───────────┘  └───────────┬───────────┘  └───────────────────────┘
                │                          │
                │  UI Events (μs)          │  Network Traffic
                │  from trace.zip          │  (timestamped)
                │                          │
                └──────────┬───────────────┘
                           │
                           ▼
              ┌───────────────────────────────┐
              │      Event Correlator         │
              │                               │
              │  - Merge by timestamp         │
              │  - Link UI → API calls        │
              │  - Build interaction graph    │
              │  - Detect patterns            │
              └───────────────┬───────────────┘
                              │
                              │  Correlated Session
                              ▼
              ┌───────────────────────────────┐
              │   AI-Powered Test Generator   │
              │                               │
              │  - Generate UI actions        │
              │  - Generate API assertions    │
              │  - Smart selectors            │
              │  - Parameterize dynamic data  │
              │  - Add waits/retries          │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    Playwright Test Output     │
              │                               │
              │  - .spec.ts files             │
              │  - Fixtures                   │
              │  - Page objects (optional)    │
              └───────────────────────────────┘
```

### File Structure (New Modules)

```
src/tracetap/
├── record/                          # NEW: Recording module
│   ├── __init__.py
│   ├── recorder.py                  # Main recording orchestrator
│   ├── mcp_client.py                # MCP protocol client
│   ├── browser_controller.py        # Browser lifecycle management
│   ├── event_capture.py             # UI event capture and formatting
│   ├── correlator.py                # Event-traffic correlation
│   └── session.py                   # Session save/load/export
├── cli/
│   ├── __init__.py
│   ├── quickstart.py                # Existing
│   └── record.py                    # NEW: Recording CLI
├── generators/
│   ├── __init__.py
│   ├── assertion_builder.py         # Existing
│   ├── regression_generator.py      # Existing
│   └── ui_test_generator.py         # NEW: UI + API test generator
└── playwright/
    ├── ...existing...
    └── action_templates.py          # NEW: UI action code templates
```

### Data Flow

```
1. QA runs: tracetap record https://example.com

2. TraceTap spawns:
   - MCP server (Playwright) → controls browser
   - mitmproxy → captures traffic through browser's proxy settings

3. QA interacts with browser:
   - Click "Login" button
   - MCP captures: {type: "click", selector: "[data-testid='login-btn']", ts: 1000}
   - mitmproxy captures: {method: "POST", url: "/api/auth/login", ts: 1050}

4. Correlator links:
   - click@1000ms → POST /api/auth/login@1050ms (50ms delta)
   - Creates: {ui_action: "click", api_call: "POST /api/auth/login", response: {...}}

5. Generator produces:
   test('user can login', async ({ page }) => {
     await page.click('[data-testid="login-btn"]');
     await page.waitForResponse(resp =>
       resp.url().includes('/api/auth/login') && resp.status() === 200
     );
     // API assertions from captured response
     const loginResponse = await page.evaluate(() => ...);
     expect(loginResponse.token).toBeDefined();
   });
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-3)
**Goal:** Basic recording works end-to-end

| Task | Description | Est. Hours | Acceptance Criteria |
|------|-------------|------------|---------------------|
| 1.1 | Create `src/tracetap/record/` module structure | 4h | Directory and __init__.py created |
| 1.2 | Implement MCP client (`mcp_client.py`) | 16h | Can connect to Playwright MCP server, send commands, receive events |
| 1.3 | Implement browser controller (`browser_controller.py`) | 12h | Can launch Chromium with proxy settings, handle lifecycle |
| 1.4 | Extend `tracetap_addon.py` with correlation IDs | 8h | Each request has `correlation_id` and `ui_event_id` fields |
| 1.5 | Implement event capture (`event_capture.py`) | 12h | Captures click, fill, navigate with selectors and timestamps |
| 1.6 | Implement basic correlator (`correlator.py`) | 12h | Links UI events to API calls within 500ms window |
| 1.7 | Create `tracetap record` CLI command | 8h | `tracetap record https://example.com` launches recording session |

**Phase 1 Deliverable:** QA can record a session and see correlated events in JSON

### Phase 2: Test Generation (Weeks 4-6)
**Goal:** Generate working Playwright tests from recordings

| Task | Description | Est. Hours | Acceptance Criteria |
|------|-------------|------------|---------------------|
| 2.1 | Create UI action templates (`action_templates.py`) | 8h | Templates for click, fill, navigate, wait, screenshot |
| 2.2 | Implement UI test generator (`ui_test_generator.py`) | 20h | Generates `.spec.ts` from correlated session |
| 2.3 | Implement smart selector strategy | 12h | Uses data-testid > id > stable CSS > fallback |
| 2.4 | Implement dynamic data detection | 16h | Identifies UUIDs, tokens, timestamps; parameterizes them |
| 2.5 | Integrate with existing `template_engine.py` | 8h | Consistent code formatting and structure |
| 2.6 | Add API assertion generation | 12h | Asserts status, schema, critical fields from responses |
| 2.7 | Implement wait strategies | 8h | Smart waits for navigation, network idle, element visibility |

**Phase 2 Deliverable:** Generated tests run and pass for happy-path flows

### Phase 3: Polish & Multi-Browser (Weeks 7-9)
**Goal:** Production-quality recording experience

| Task | Description | Est. Hours | Acceptance Criteria |
|------|-------------|------------|---------------------|
| 3.1 | Implement session manager (`session.py`) | 12h | Save/load/resume sessions; JSON + binary formats |
| 3.2 | Add Firefox support | 8h | Recording works on Firefox |
| 3.3 | Add Safari (WebKit) support | 8h | Recording works on Safari |
| 3.4 | Implement authentication state capture | 12h | Captures and replays cookies, localStorage, headers |
| 3.5 | Add error recovery | 12h | Graceful handling of browser crashes, network errors |
| 3.6 | Implement selector healing hints | 16h | Suggests alternative selectors when primary fails |
| 3.7 | Add recording controls (pause/resume/stop) | 8h | Keyboard shortcuts and CLI controls |
| 3.8 | Create progress/status UI (Rich console) | 8h | Live display of captured events during recording |

**Phase 3 Deliverable:** Robust recording across all major browsers

### Phase 4: Documentation & Launch (Weeks 10-12)
**Goal:** Ready for public launch

| Task | Description | Est. Hours | Acceptance Criteria |
|------|-------------|------------|---------------------|
| 4.1 | Write user guide | 12h | Complete usage documentation with examples |
| 4.2 | Create demo video script | 4h | 2-minute "wow moment" demo |
| 4.3 | Write API documentation | 8h | All public APIs documented |
| 4.4 | Create example projects | 16h | 3 example apps with recorded tests |
| 4.5 | Write troubleshooting guide | 8h | Common issues and solutions |
| 4.6 | Add unit tests (80% coverage) | 24h | Comprehensive test suite |
| 4.7 | Add integration tests | 16h | End-to-end recording and generation tests |
| 4.8 | Performance optimization | 12h | Handle 10+ minute sessions, 500+ requests |
| 4.9 | Final QA and bug fixes | 16h | All critical/high bugs fixed |

**Phase 4 Deliverable:** Production-ready feature with documentation

---

## Detailed TODOs

### Week 1: MCP Foundation

```
[ ] TODO-1.1: Create record module structure
    File: src/tracetap/record/__init__.py
    Acceptance: Module imports work, no errors

[ ] TODO-1.2: Research MCP Playwright server protocol
    Output: Document available MCP tools and events
    Acceptance: Documented all relevant MCP endpoints

[ ] TODO-1.3: Implement MCP client connection
    File: src/tracetap/record/mcp_client.py
    Acceptance: Can connect to MCP server, handle reconnection

[ ] TODO-1.4: Implement MCP command sending
    File: src/tracetap/record/mcp_client.py
    Acceptance: Can send playwright_navigate, playwright_click, etc.
```

### Week 2: Browser Control & Event Capture

```
[ ] TODO-2.1: Implement browser launcher
    File: src/tracetap/record/browser_controller.py
    Acceptance: Launches Chromium with --proxy-server flag

[ ] TODO-2.2: Implement browser lifecycle management
    File: src/tracetap/record/browser_controller.py
    Acceptance: Clean shutdown, crash recovery, multiple contexts

[ ] TODO-2.3: Implement UI event capture
    File: src/tracetap/record/event_capture.py
    Acceptance: Captures click, type, navigate with timestamps

[ ] TODO-2.4: Implement selector extraction
    File: src/tracetap/record/event_capture.py
    Acceptance: Extracts best selector for each element
```

### Week 3: Correlation & CLI

```
[ ] TODO-3.1: Extend tracetap_addon with correlation fields
    File: src/tracetap/capture/tracetap_addon.py (line 127-142)
    Acceptance: Records include correlation_id, precise timestamps

[ ] TODO-3.2: Implement timestamp-based correlation
    File: src/tracetap/record/correlator.py
    Acceptance: Links UI events to API calls within 500ms

[ ] TODO-3.3: Implement interaction graph builder
    File: src/tracetap/record/correlator.py
    Acceptance: Builds directed graph of UI → API relationships

[ ] TODO-3.4: Create CLI record command
    File: src/tracetap/cli/record.py
    Acceptance: `tracetap record <url>` works

[ ] TODO-3.5: Add CLI to pyproject.toml entry points
    File: pyproject.toml (line 81-83)
    Acceptance: Command available after pip install
```

### Week 4-5: Test Generation Core

```
[ ] TODO-4.1: Create action template system
    File: src/tracetap/playwright/action_templates.py
    Acceptance: Templates for all Playwright actions

[ ] TODO-4.2: Implement UI test generator
    File: src/tracetap/generators/ui_test_generator.py
    Acceptance: Generates valid TypeScript from session

[ ] TODO-4.3: Implement selector strategy hierarchy
    File: src/tracetap/generators/ui_test_generator.py
    Acceptance: Tries data-testid → id → CSS → XPath

[ ] TODO-4.4: Implement dynamic data parameterization
    File: src/tracetap/generators/ui_test_generator.py
    Acceptance: Detects UUIDs, timestamps; creates variables
```

### Week 6: API Assertions & Waits

```
[ ] TODO-5.1: Integrate assertion_builder.py
    File: src/tracetap/generators/ui_test_generator.py
    Acceptance: Uses existing assertion strategies

[ ] TODO-5.2: Implement response validation generation
    File: src/tracetap/generators/ui_test_generator.py
    Acceptance: Generates schema and value assertions

[ ] TODO-5.3: Implement smart wait generation
    File: src/tracetap/generators/ui_test_generator.py
    Acceptance: Adds waitForResponse, waitForSelector as needed

[ ] TODO-5.4: Integrate with template_engine.py
    File: src/tracetap/playwright/template_engine.py
    Acceptance: Consistent code formatting
```

### Week 7-8: Multi-Browser & Session Management

```
[ ] TODO-6.1: Implement session save/load
    File: src/tracetap/record/session.py
    Acceptance: Sessions persist across CLI restarts

[ ] TODO-6.2: Add Firefox browser support
    File: src/tracetap/record/browser_controller.py
    Acceptance: Firefox recording works identically

[ ] TODO-6.3: Add Safari (WebKit) support
    File: src/tracetap/record/browser_controller.py
    Acceptance: Safari recording works identically

[ ] TODO-6.4: Implement auth state capture
    File: src/tracetap/record/session.py
    Acceptance: Cookies, localStorage, headers captured
```

### Week 9: Polish & Recovery

```
[ ] TODO-7.1: Implement error recovery
    File: src/tracetap/record/recorder.py
    Acceptance: Graceful handling of crashes

[ ] TODO-7.2: Implement selector healing hints
    File: src/tracetap/generators/ui_test_generator.py
    Acceptance: Comments suggest alternatives

[ ] TODO-7.3: Add pause/resume/stop controls
    File: src/tracetap/cli/record.py
    Acceptance: Ctrl+P pauses, Ctrl+R resumes, Ctrl+C stops

[ ] TODO-7.4: Create Rich console progress UI
    File: src/tracetap/cli/record.py
    Acceptance: Live display during recording
```

### Week 10-12: Documentation & Testing

```
[ ] TODO-8.1: Write user guide
    File: docs/recording-guide.md
    Acceptance: Covers all features

[ ] TODO-8.2: Create demo video script
    File: docs/demo-script.md
    Acceptance: 2-minute viral-worthy demo

[ ] TODO-8.3: Write API docs
    File: docs/api/
    Acceptance: All public APIs documented

[ ] TODO-8.4: Create example projects
    File: examples/
    Acceptance: 3 working examples

[ ] TODO-8.5: Write unit tests
    File: tests/record/
    Acceptance: 80%+ coverage

[ ] TODO-8.6: Write integration tests
    File: tests/integration/
    Acceptance: E2E recording/generation tests

[ ] TODO-8.7: Performance optimization
    Acceptance: Handles 10min sessions, 500+ requests

[ ] TODO-8.8: Final QA pass
    Acceptance: All critical bugs fixed
```

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MCP server doesn't expose needed events | Medium | High | Build custom MCP server wrapping Playwright; estimate +2 weeks |
| Selector instability across runs | High | Medium | Multi-strategy selector with healing hints; test on real apps |
| Timestamp drift between processes | Low | High | Use monotonic clock; sync at session start |
| Large sessions cause memory issues | Medium | Medium | Stream events to disk; lazy loading |
| AI rate limits during generation | Low | Low | Batch requests; cache responses |
| Browser compatibility issues | Medium | Medium | Start with Chromium only; add others incrementally |

---

## Commit Strategy

| Phase | Commit Pattern |
|-------|----------------|
| Phase 1 | One commit per TODO (atomic changes) |
| Phase 2 | Feature branches, squash merge to main |
| Phase 3 | Feature branches, squash merge to main |
| Phase 4 | Direct commits for docs; feature branches for tests |

### Suggested Commit Messages
```
feat(record): add MCP client connection layer
feat(record): implement UI event capture with selectors
feat(capture): add correlation IDs to traffic records
feat(record): implement timestamp-based event correlator
feat(cli): add tracetap record command
feat(generators): implement UI test generator
feat(generators): add smart selector strategy
feat(record): add Firefox browser support
docs: add recording user guide
test: add unit tests for correlator
```

---

## Success Criteria

### Quantitative
- [ ] 90%+ of generated tests pass on first run (happy path)
- [ ] Recording works on Chrome, Firefox, Safari
- [ ] Unit test coverage > 80%
- [ ] Can handle 10+ minute sessions with 500+ requests
- [ ] Generation takes < 30 seconds for typical session

### Qualitative
- [ ] "Wow moment" in under 30 seconds (start record → see generated test)
- [ ] Generated code is clean, readable, maintainable
- [ ] Error messages are helpful and actionable
- [ ] Documentation answers common questions

### Viral Adoption Metrics (Post-Launch)
- [ ] Demo video watch time > 80%
- [ ] GitHub stars in first week
- [ ] Repeat usage rate (users who try twice)
- [ ] Social shares / mentions

---

## Dependencies

### External
| Dependency | Version | Purpose |
|------------|---------|---------|
| `mcp` (MCP SDK) | latest | MCP client implementation |
| `playwright` | ^1.40.0 | Browser automation |
| `mitmproxy` | ^8.0.0 | Traffic capture (existing) |
| `anthropic` | ^0.71.0 | AI generation (existing) |
| `rich` | ^13.0.0 | Console UI (existing) |
| `click` | ^8.0.0 | CLI framework (existing) |

### Internal
| Module | Purpose |
|--------|---------|
| `src/tracetap/capture/tracetap_addon.py` | Traffic capture (extend) |
| `src/tracetap/playwright/template_engine.py` | Code formatting (reuse) |
| `src/tracetap/generators/assertion_builder.py` | Assertion generation (reuse) |
| `src/tracetap/ai/pattern_analyzer.py` | Pattern detection (reuse) |

---

## Appendix: MCP Protocol Reference

### Playwright MCP Tools (Expected)
```
playwright_navigate(url: string)           → Navigate to URL
playwright_click(selector: string)         → Click element
playwright_fill(selector: string, value: string) → Fill input
playwright_screenshot()                    → Capture screenshot
playwright_evaluate(script: string)        → Execute JS
playwright_get_visible_text()              → Get page text
playwright_get_visible_html()              → Get page HTML
```

### Event Format (Proposed)
```json
{
  "type": "ui_event",
  "action": "click",
  "selector": "[data-testid='login-btn']",
  "timestamp": 1706838400000,
  "element": {
    "tag": "button",
    "text": "Login",
    "attributes": {
      "data-testid": "login-btn",
      "class": "btn btn-primary"
    }
  }
}
```

### Correlated Event Format (Proposed)
```json
{
  "sequence": 1,
  "ui_event": {
    "action": "click",
    "selector": "[data-testid='login-btn']",
    "timestamp": 1706838400000
  },
  "api_calls": [
    {
      "method": "POST",
      "url": "/api/auth/login",
      "status": 200,
      "timestamp": 1706838400050,
      "response": { "token": "...", "user": {...} }
    }
  ],
  "correlation_confidence": 0.95
}
```

---

*Plan generated by Prometheus on 2026-02-02*
*Ready for execution via `/oh-my-claudecode:start-work killer-feature-ui-recorder`*
