# Building TraceTap Executables

## Prerequisites

- Python 3.7 or higher
- pip

## Quick Build

```bash
# Install dependencies
pip install -r requirements.txt

# Build for your current platform
python build_executables.py

# Find executable in release/ directory
ls -l release/
```

## Platform-Specific Instructions

### Linux (Ubuntu/Debian)

```bash
# Install Python if needed
sudo apt update
sudo apt install python3 python3-pip

# Install dependencies
pip3 install -r requirements.txt

# Build
python3 build_executables.py

# Result: release/tracetap-linux-x64
```

### macOS

```bash
# Install Python if needed (using Homebrew)
brew install python

# Install dependencies
pip3 install -r requirements.txt

# Build
python3 build_executables.py

# Result: release/tracetap-macos-x64 or tracetap-macos-arm64
```

### Windows

```powershell
# Install Python from python.org if needed

# Install dependencies
pip install -r requirements.txt

# Build
python build_executables.py

# Result: release\tracetap-windows-x64.exe
```

## Manual PyInstaller Build

If the build script doesn't work, you can use PyInstaller directly:

```bash
pyinstaller --onefile --name tracetap --clean --strip tracetap.py
```

The executable will be in `dist/tracetap` (or `dist/tracetap.exe` on Windows).

## Troubleshooting

### "Module not found" errors

Make sure all dependencies are installed:
```bash
pip install mitmproxy pyinstaller
```

### Executable too large

The executable includes Python and all dependencies (~40-60MB). This is normal for PyInstaller bundles.

### Antivirus warnings

Some antivirus software flags PyInstaller executables. This is a false positive. You can:
- Exclude the release directory from scans
- Sign the executable (requires a code signing certificate)
- Build from source yourself

### macOS "cannot be opened" error

```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine tracetap-macos-*

# Or allow in System Preferences > Security & Privacy
```

## Testing Your Build

```bash
# Test the executable
./release/tracetap-* --help

# Run a simple test
./release/tracetap-* --listen 9999 --export test.json

# In another terminal
export HTTP_PROXY=http://localhost:9999
curl -k http://httpbin.org/get

# Stop with Ctrl+C and check test.json
```

## Reducing Executable Size

To create smaller executables:

1. **Use UPX compression** (adds startup time):
```bash
pyinstaller --onefile --upx-dir=/path/to/upx tracetap.py
```

2. **Exclude unused modules** (requires testing):
```bash
pyinstaller --onefile --exclude-module pytest --exclude-module IPython tracetap.py
```

## Cross-Platform Build (Advanced)

To build for all platforms, use Docker or VMs:

```bash
# Linux executable from Docker
docker run -v $(pwd):/app python:3.11-slim bash -c \
  "cd /app && pip install -r requirements.txt && python build_executables.py"
```

For official releases, use GitHub Actions (see `.github/workflows/release.yml`).