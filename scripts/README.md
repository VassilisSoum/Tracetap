# Demo Recording Scripts

Automated scripts for capturing and optimizing demo GIFs and screenshots for TraceTap documentation.

## Quick Start

### Check if all tools are installed

```bash
./record-demos.sh --check-tools
```

### Record all demos

```bash
./record-demos.sh --all
```

This will generate 5 demo GIFs in `assets/demo-gifs/`:
- `quickstart.gif` (60s) - Complete quickstart workflow
- `regression.gif` (30s) - Regression testing demo
- `ai-suggestions.gif` (45s) - AI test improvement workflow
- `contract-testing.gif` (40s) - Contract verification
- `html-report.gif` (30s) - HTML report generation

### Record a specific demo

```bash
./record-demos.sh --demo quickstart
```

Available demos: `quickstart`, `regression`, `ai-suggestions`, `contract`, `report`

## Files

### Main Recording Script

**`record-demos.sh`** (558 lines)
- Orchestrates all recording scenarios
- Handles asciinema recording and agg conversion
- Optimizes GIF file sizes automatically
- Provides tool checking and validation
- Generates statistics on output

### Demo Scenarios

Located in `demo-scenarios/`:

1. **`quickstart.sh`** (212 lines, 60s)
   - Shows complete TraceTap workflow
   - Install → capture → generate tests
   - Demonstrates key features

2. **`regression.sh`** (167 lines, 30s)
   - Snapshot regression testing
   - Shows comparison workflow
   - Highlights differences in API responses

3. **`ai-suggestions.sh`** (221 lines, 45s)
   - AI-powered test analysis
   - Shows improvement suggestions
   - Demonstrates quality metrics

4. **`contract.sh`** (204 lines, 40s)
   - API contract verification
   - Consumer compatibility checking
   - Contract testing workflow

5. **`report.sh`** (195 lines, 30s)
   - HTML report generation
   - Test result visualization
   - Coverage metrics display

### Documentation

**`../docs/recording-guide.md`** (786 lines)
- Complete setup instructions
- Tool documentation
- GIF optimization techniques
- Screenshot capture guide
- Workflow examples
- Troubleshooting guide

## Features

### Automated Recording

```bash
# Record with automatic optimization
./record-demos.sh --demo quickstart

# Record without optimization (faster)
./record-demos.sh --demo quickstart --skip-optimization

# Record with aggressive optimization (smaller files)
./record-demos.sh --demo quickstart --optimize-more
```

### Tool Support

- **asciinema** - Terminal recording
- **agg** - asciinema to GIF conversion
- **ImageMagick** - GIF optimization
- **gifski** - High-quality GIF encoding (optional)

### GIF Optimization

Automatic optimization reduces file sizes:
- Color reduction (256 → 128 colors)
- Frame optimization
- Resize to 1200px width
- Metadata stripping

**Typical results:** 40MB → 1.5-2.5MB (95% reduction)

## Installation

### macOS

```bash
brew install asciinema agg imagemagick
```

### Linux

```bash
sudo apt-get install asciinema imagemagick
cargo install agg  # requires Rust
```

### Docker

```bash
# Build container with all tools
docker build -t tracetap-recording -f docker/Dockerfile.recording .
```

## Usage Examples

### Record and optimize

```bash
./record-demos.sh --demo regression
# Output: assets/demo-gifs/regression.gif (< 1MB)
```

### Record all with statistics

```bash
./record-demos.sh --all
# Shows summary of all generated GIFs
```

### Apply more aggressive optimization

```bash
./record-demos.sh --demo contract --optimize-more
# For smaller file sizes (quality trade-off)
```

### Check tool installation

```bash
./record-demos.sh --check-tools
# Verifies all required tools are available
```

## Directory Structure

```
scripts/
├── record-demos.sh              # Main orchestration script
├── README.md                    # This file
└── demo-scenarios/
    ├── quickstart.sh           # Quickstart demo (60s)
    ├── regression.sh           # Regression demo (30s)
    ├── ai-suggestions.sh       # AI suggestions demo (45s)
    ├── contract.sh             # Contract testing demo (40s)
    └── report.sh               # HTML report demo (30s)

assets/
├── demo-gifs/                  # Generated GIF output
│   ├── .gitkeep
│   ├── quickstart.gif
│   ├── regression.gif
│   ├── ai-suggestions.gif
│   ├── contract-testing.gif
│   └── html-report.gif
└── screenshots/                # Screenshot storage
    └── .gitkeep

docs/
└── recording-guide.md          # Comprehensive recording guide
```

## Output

Generated GIFs are stored in `assets/demo-gifs/` with target sizes:

| Demo | Duration | Target Size | Actual |
|------|----------|------------|--------|
| quickstart | 60s | < 2MB | ~1.8MB |
| regression | 30s | < 1MB | ~0.8MB |
| ai-suggestions | 45s | < 2MB | ~1.5MB |
| contract-testing | 40s | < 1.5MB | ~1.2MB |
| html-report | 30s | < 1.5MB | ~1.0MB |

## Advanced Usage

### Custom Recording Settings

Edit environment variables in `record-demos.sh`:

```bash
TERMINAL_WIDTH=120        # Terminal columns
TERMINAL_HEIGHT=30        # Terminal rows
DELAY_BETWEEN_CHARS=0.02  # Typing delay (seconds)
PAUSE_AFTER_COMMAND=0.5   # Command pause (seconds)
```

### Manual Optimization

```bash
# Optimize a GIF manually
convert input.gif -colors 128 -fuzz 10% output.gif

# More aggressive
convert input.gif -colors 96 -fuzz 15% -resize 960x output.gif
```

### Extract Frame from Recording

```bash
# Get frame at specific time
agg demo.cast --at 5s output.png

# Extract multiple frames
agg demo.cast --at 0s frame0.png
agg demo.cast --at 2s frame2.png
```

## Tips

1. **Clear Terminal Before Recording**
   ```bash
   clear
   ```

2. **Use Consistent Font**
   - Recommend: 14pt monospace
   - Avoid: Proportional fonts

3. **Test Workflow First**
   - Run through scenario 2-3 times
   - Time yourself for target duration
   - Verify output matches expectations

4. **Check File Sizes**
   ```bash
   du -h assets/demo-gifs/
   ```

5. **Play Back GIFs**
   ```bash
   open assets/demo-gifs/quickstart.gif  # macOS
   xdg-open assets/demo-gifs/quickstart.gif  # Linux
   ```

## Troubleshooting

### Tools not found

```bash
./record-demos.sh --check-tools
```

Install missing tools per the output.

### GIF too large

```bash
./record-demos.sh --demo quickstart --optimize-more
```

### Recording looks choppy

- Ensure TERM=xterm-256color
- Use agg with `--speed 0.5` for slower playback
- Check terminal colors are working

### Text unreadable in GIF

- Record at higher terminal resolution
- Increase font size (14pt+)
- Resize GIF less aggressively

## Reference

- **asciinema:** https://asciinema.org/
- **agg:** https://github.com/asciinema/agg
- **ImageMagick:** https://imagemagick.org/
- **gifski:** https://github.com/ImageOptim/gifski

For detailed guidance, see `docs/recording-guide.md`.

## Help

```bash
./record-demos.sh --help
```

## Version

Created: February 2024
Last Updated: February 2024
