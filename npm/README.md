# TraceTap npm Package

Node.js/JavaScript wrapper for TraceTap - the HTTP/HTTPS traffic capture proxy with AI-powered testing tools.

This package allows JavaScript/TypeScript teams to use TraceTap without worrying about Python installation or setup.

## Quick Start

### Installation

```bash
# Global installation (recommended)
npm install -g tracetap

# Or use npx (no installation required)
npx tracetap-quickstart
```

### Usage

```bash
# Interactive quickstart guide
npx tracetap-quickstart

# Capture traffic
npx tracetap --listen 8080 --export collection.json

# Generate Playwright tests
npx tracetap-playwright collection.json -o tests.spec.ts

# Run mock server
npx tracetap-replay capture.json --mock-server --mock-port 9000

# Replay to staging
npx tracetap-replay capture.json --target https://staging.example.com
```

## What is TraceTap?

TraceTap is a comprehensive HTTP/HTTPS traffic capture proxy that:

- 📡 Captures API traffic in real-time
- 🎭 Creates Playwright test suites
- 🎪 Runs intelligent mock servers
- 🔄 Replays traffic to different environments
- 📊 Generates beautiful HTML reports

Perfect for QA engineers, developers, and testers who want to:
- Document APIs from real traffic
- Generate tests automatically
- Create mocks for offline development
- Debug integration issues

## Available Commands

After installation, these commands are available:

| Command | Description |
|---------|-------------|
| `tracetap` | Main capture proxy |
| `tracetap-quickstart` | Interactive onboarding (start here!) |
| `tracetap-replay` | Replay & mock server |
| `tracetap-playwright` | Playwright test generator |

## Requirements

- **Node.js**: 14.0.0 or higher
- **Python**: 3.8 or higher (automatically checked during installation)
- **Operating System**: macOS, Linux, or Windows

The package will automatically:
1. Check for Python installation
2. Install TraceTap via pip if not already installed
3. Make all commands available

## Examples

### Capture API Traffic

```bash
# Start proxy on port 8080
npx tracetap --listen 8080 --raw-log capture.json

# Configure your app to use proxy: http://localhost:8080
# Use your application normally
# Press Ctrl+C when done
```

### Generate Tests from Traffic

```bash
# Generate Playwright tests from capture
npx tracetap-playwright capture.json -o tests/api.spec.ts

# Run the tests
npx playwright test tests/api.spec.ts
```

### Run Mock Server

```bash
# Start intelligent mock server
npx tracetap-replay capture.json \
  --mock-server \
  --mock-port 9000 \
  --mock-mode intelligent

# Access mock API at: http://localhost:9000
```

### CI/CD Integration

```yaml
# .github/workflows/api-tests.yml
name: API Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      # Install TraceTap
      - run: npm install -g tracetap

      # Generate and run tests
      - run: |
          tracetap-playwright collection.json -o tests.spec.ts
          npx playwright test
```

## How It Works

This npm package is a lightweight wrapper that:

1. Checks for Python 3.8+ on your system
2. Installs the TraceTap Python package via pip
3. Provides convenient `npx` commands that proxy to Python CLI
4. Handles cross-platform compatibility (Windows/macOS/Linux)

The actual TraceTap functionality runs in Python, but you don't need to know Python to use it!

## Troubleshooting

### Python Not Found

If you see "Python not found":

1. Install Python from https://python.org (version 3.8 or higher)
2. Make sure Python is in your PATH
3. On Windows, check "Add Python to PATH" during installation
4. Verify with: `python --version` or `python3 --version`

### TraceTap Not Installing

If automatic pip installation fails:

```bash
# Install manually
python3 -m pip install tracetap

# Or use the one-line installer
curl -sSL https://get.tracetap.io | bash
```

### Command Not Found

If `npx tracetap` doesn't work:

```bash
# Try global installation
npm install -g tracetap

# Then use without npx
tracetap-quickstart
```

### Permission Errors

On macOS/Linux, if you see permission errors:

```bash
# Install for current user only
npm install -g tracetap --user
```

## Development

### Testing the Package

```bash
cd npm/
npm test
```

### Publishing

```bash
# Login to npm
npm login

# Publish
npm publish
```

## Documentation

- [Main Documentation](https://github.com/VassilisSoum/tracetap#readme)
- [Replay & Mock Server](https://github.com/VassilisSoum/tracetap/blob/master/REPLAY.md)
- [Docker Guide](https://github.com/VassilisSoum/tracetap/blob/master/docker/README.md)

## Support

- **Issues**: https://github.com/VassilisSoum/tracetap/issues
- **Discussions**: https://github.com/VassilisSoum/tracetap/discussions

## License

MIT © Vassilis Soumakis
