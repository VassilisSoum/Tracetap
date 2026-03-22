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
# Open http://localhost:6080 in your browser (noVNC desktop)
# Run tracetap commands inside the container
```

Or for one-off commands without the desktop:

```bash
docker build -t tracetap:2.0.0 .
docker run --rm -e ANTHROPIC_API_KEY tracetap:2.0.0 tracetap doctor
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

## Quick Start: Test Against a Real Website

This walkthrough uses [https://the-internet.herokuapp.com/login](https://the-internet.herokuapp.com/login), a public demo site with a login form.

### Step 1: Record

```bash
tracetap record https://the-internet.herokuapp.com/login -n login-test
```

A Chromium browser opens. Do the following manually:
1. Type `tomsmith` in the username field
2. Type `SuperSecretPassword!` in the password field
3. Click the **Login** button
4. Wait for the dashboard to load

Then switch back to your terminal and press **ENTER** to stop recording.

You'll see output like:

```
Recording Complete
  Duration: 15.2s
  UI events: 4
  Network calls: 13
  Correlated events: 1
  Saved to: recordings/20260322_175740_aaab84a2
```

### Step 2: Generate tests

```bash
export ANTHROPIC_API_KEY=sk-ant-...
tracetap generate recordings/<session-id> -o tests/login.spec.ts \
  --base-url https://the-internet.herokuapp.com
```

Replace `<session-id>` with the directory name from step 1.

This calls Claude AI and produces a Playwright test file plus a `playwright.config.ts` with the base URL pre-configured.

### Step 3: Run the generated tests

```bash
npm install -D @playwright/test
npx playwright install chromium
npx playwright test tests/login.spec.ts
```

## Commands

### `tracetap record`

Record browser interactions and network traffic.

```bash
tracetap record <url> [options]
```

| Option | Description |
|--------|-------------|
| `-n, --name TEXT` | Session name (default: auto-generated) |
| `-o, --output TEXT` | Output directory (default: `./recordings`) |
| `--headless` | Run browser without visible window |
| `--proxy TEXT` | Route traffic through a proxy (e.g. `http://localhost:8888`) |
| `-v, --verbose` | Debug logging |

**Examples:**

```bash
# Record a login flow
tracetap record https://myapp.com/login -n login-flow

# Record with a custom output directory
tracetap record https://myapp.com -o ./test-sessions

# Record headless (no visible browser - useful in CI or Docker)
tracetap record https://myapp.com --headless -n ci-test

# Record through mitmproxy for HTTPS inspection
tracetap record https://myapp.com --proxy http://localhost:8888
```

**What gets captured:**
- Clicks (with CSS selector: `data-testid` > `id` > `name` > `aria-label` > text content)
- Text input (debounced, captures final value not keystrokes)
- Form submissions
- Select/dropdown changes
- Enter/Escape/Tab key presses
- All network requests and responses (method, URL, status, headers, body)
- Password fields are automatically redacted at capture time

**Output files** (in `recordings/<session-id>/`):

| File | Contents |
|------|----------|
| `events.json` | UI interactions with timestamps and selectors |
| `traffic.json` | Network requests/responses |
| `correlation.json` | UI events matched to their API calls |
| `metadata.json` | Session info (URL, duration, timestamps) |

### `tracetap generate`

Generate Playwright tests from a recorded session.

```bash
tracetap generate <session-dir> -o <output-file> [options]
```

| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output file path (required) |
| `-t, --template` | `basic` or `comprehensive` (default: `comprehensive`) |
| `-f, --format` | `typescript`, `javascript`, or `python` (default: `typescript`) |
| `--base-url TEXT` | Base URL for generated tests |
| `--api-key TEXT` | Anthropic API key (or set `ANTHROPIC_API_KEY` env var) |
| `--no-sanitize` | Disable PII redaction before sending to AI |
| `--min-confidence FLOAT` | Minimum correlation confidence (default: 0.5) |
| `-v, --verbose` | Debug logging |

**Examples:**

```bash
# Generate TypeScript tests (default)
tracetap generate recordings/my-session -o tests/login.spec.ts

# Generate Python tests
tracetap generate recordings/my-session -o tests/test_login.py --format python

# Use the basic template (shorter, simpler tests)
tracetap generate recordings/my-session -o tests/login.spec.ts --template basic

# Override the base URL (useful for different environments)
tracetap generate recordings/my-session -o tests/login.spec.ts \
  --base-url https://staging.myapp.com

# Lower confidence threshold to include more events
tracetap generate recordings/my-session -o tests/login.spec.ts --min-confidence 0.3
```

**What happens:**
1. Loads correlation data from the session directory
2. Sanitizes PII (emails, passwords, API keys) before sending to AI
3. Sends correlated events to Claude with the selected template
4. Validates the generated code (Python: compile check; TS/JS: structural check)
5. If validation fails, retries up to 2 times with error feedback
6. Writes the test file and a `playwright.config.ts` with the base URL

### `tracetap proxy`

Run a standalone HTTP/HTTPS proxy for API-only traffic capture (no browser).

```bash
tracetap proxy [options]
```

| Option | Description |
|--------|-------------|
| `-l, --listen INT` | Proxy port (default: 8080) |
| `--raw-log TEXT` | Path to write JSON traffic log |
| `--filter TEXT` | Only capture traffic to this host |
| `-v, --verbose` | Debug logging |

**Examples:**

```bash
# Start proxy on default port
tracetap proxy

# Capture traffic to a specific backend
tracetap proxy --listen 9090 --raw-log api-traffic.json --filter api.myapp.com

# Use with curl
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
curl https://api.myapp.com/users
```

**Use cases:**
- Capture API traffic from mobile apps or Postman
- Record traffic from automated scripts
- Inspect HTTPS traffic from any HTTP client

### `tracetap doctor`

Check that all prerequisites are installed and working.

```bash
tracetap doctor [options]
```

| Option | Description |
|--------|-------------|
| `--no-api-check` | Skip API key validation (avoids a small billable API call) |

**Checks performed:**
- Python version (>= 3.10)
- mitmproxy installed and version
- Playwright Python package installed
- Playwright Chromium browser downloaded
- mitmproxy CA certificate exists
- Certificate trusted by system
- Default proxy port (8080) available
- npm/npx available (for running generated tests)
- `ANTHROPIC_API_KEY` set and valid (makes a test API call unless `--no-api-check`)

## How Recording Works

TraceTap opens a single Chromium browser via Playwright and injects JavaScript event listeners into every page. These listeners capture real manual interactions (clicks, typing, form submits) with real timestamps from the browser's `Date.now()`.

Events are pushed from JavaScript to Python immediately via Playwright's `expose_function` mechanism. This means events survive page navigation - they're stored in Python memory, not the browser's JS context.

Network traffic (requests + responses) is captured via Playwright's built-in `page.on('request')` / `page.on('response')` events from the same browser instance. No second process, no proxy subprocess needed for recording.

After recording stops, TraceTap correlates UI events with network calls using a time-window algorithm: network requests that occur within a configurable window after a UI event are linked to it with a confidence score.

For standalone API capture (without browser), TraceTap uses mitmproxy as an HTTPS-intercepting proxy.

## Docker Usage

### Interactive mode (with noVNC desktop)

```bash
docker compose up -d
```

Open [http://localhost:6080](http://localhost:6080) in your browser. You'll see a desktop environment. Open a terminal inside it and run TraceTap commands. The recording browser opens inside this desktop, and you interact with it through your web browser.

Recordings are saved to `./recordings/` on your host via volume mount.

### One-off commands

```bash
# Check prerequisites
docker run --rm tracetap:2.0.0 tracetap doctor --no-api-check

# Generate tests from an existing session
docker run --rm \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -v $(pwd)/recordings:/app/recordings \
  tracetap:2.0.0 \
  tracetap generate /app/recordings/<session-id> -o /app/recordings/tests.spec.ts

# Headless recording (no desktop needed)
docker run --rm \
  -v $(pwd)/recordings:/app/recordings \
  tracetap:2.0.0 \
  tracetap record https://example.com --headless -n my-test
```

### Pass your API key

The `ANTHROPIC_API_KEY` must be passed to the container:

```bash
# Via docker compose (add to .env file or shell)
export ANTHROPIC_API_KEY=sk-ant-...
docker compose up -d

# Via docker run
docker run --rm -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" tracetap:2.0.0 tracetap generate ...
```

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required for generate) | Claude API key |
| `TRACETAP_CLAUDE_MODEL` | `claude-sonnet-4-6` | Model to use (falls back to older models if unavailable) |
| `TRACETAP_MAX_TOKENS` | `8192` | Max tokens per generation |
| `TRACETAP_MAX_GENERATION_RETRIES` | `2` | Retries on syntax validation failure |

## Project Status

v2.0.0 - ground-up rewrite focused on getting the core pipeline right.

**Working:**
- Browser interaction recording (clicks, typing, navigation, form submits)
- Network traffic capture (requests + responses from the same browser)
- Event correlation (timestamp-based matching of UI events to API calls)
- AI test generation with Claude (basic and comprehensive templates)
- PII sanitization before sending data to AI
- Syntax validation with retry loop (up to 3 attempts)
- Playwright config generation alongside tests
- Standalone proxy mode (mitmproxy-based)
- `tracetap doctor` prerequisite checker
- Docker with noVNC for cross-platform browser access

**Not yet implemented:**
- HTML reports
- Contract testing
- Mock server generation
- CI/CD pipeline

## Requirements

- Python 3.10+
- Playwright + Chromium browser
- mitmproxy (for standalone proxy mode)
- Anthropic API key (for test generation)
- Node.js/npm (for running generated Playwright tests)

Or just Docker.

## License

MIT
