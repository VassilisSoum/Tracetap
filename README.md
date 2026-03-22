# TraceTap

Record manual browser tests, capture API traffic, generate Playwright test code with AI.

## What It Does

1. **Record** - Opens a browser. You interact manually (click, type, navigate). TraceTap captures both your UI interactions and network traffic from a single browser.
2. **Correlate** - Matches UI events to API calls by timestamp proximity. Click a button that triggers a POST? TraceTap links them.
3. **Generate** - Sends correlated events to Claude AI. Gets back a runnable Playwright test file with assertions.

## Install

### Docker (recommended)

```bash
docker compose up -d
# Open http://localhost:6080 in your browser (noVNC)
# Run tracetap commands inside the container
```

### pip

```bash
pip install tracetap
playwright install chromium
```

Then verify your setup:

```bash
tracetap doctor
```

## Usage

### Record a session

```bash
tracetap record https://myapp.com -n login-flow
```

A browser opens. Interact with it normally. Press ENTER in the terminal when done.

Output: `recordings/<session-id>/` containing `events.json`, `traffic.json`, `correlation.json`, `metadata.json`.

### Generate tests

```bash
tracetap generate recordings/<session-id> -o tests/login.spec.ts
```

Requires `ANTHROPIC_API_KEY` environment variable.

Options:
- `--template basic|comprehensive` - Test detail level
- `--format typescript|javascript|python` - Output language
- `--base-url https://myapp.com` - Override base URL in tests
- `--no-sanitize` - Disable PII redaction (not recommended)

### Standalone proxy

Capture API traffic without a browser:

```bash
tracetap proxy --listen 8080 --raw-log api.json --filter localhost:3000
```

### Check prerequisites

```bash
tracetap doctor
```

Checks: Python version, mitmproxy, Playwright, browsers, certificates, API key, npm.

## How Recording Works

TraceTap injects JavaScript event listeners into the browser page to capture real manual interactions (clicks, typing, form submits) with real timestamps. Network traffic is captured via Playwright's built-in request/response events. Both streams share the same browser instance - no second process, no proxy needed for recording.

For standalone API capture (without browser), TraceTap uses mitmproxy as an HTTPS-intercepting proxy.

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | Claude API key for test generation |
| `TRACETAP_CLAUDE_MODEL` | `claude-sonnet-4-5-20250514` | Model to use |
| `TRACETAP_MAX_TOKENS` | `8192` | Max tokens per generation |
| `TRACETAP_MAX_GENERATION_RETRIES` | `2` | Retries on syntax validation failure |

## Project Status

This is v2.0.0 - a ground-up rewrite focused on getting the core pipeline right.

**Working:**
- Browser interaction recording (clicks, typing, navigation, form submits)
- Network traffic capture (requests + responses from the same browser)
- Event correlation (timestamp-based matching of UI events to API calls)
- AI test generation with Claude (basic and comprehensive templates)
- PII sanitization before sending data to AI
- Syntax validation with retry loop
- Standalone proxy mode
- `tracetap doctor` prerequisite checker

**Not yet implemented:**
- HTML reports
- Contract testing
- Mock server generation

## Requirements

- Python 3.10+
- Playwright + Chromium browser
- mitmproxy (for standalone proxy mode)
- Anthropic API key (for test generation)

## License

MIT
