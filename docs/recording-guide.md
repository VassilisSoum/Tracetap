# Demo Recording Guide

This guide explains how to capture and optimize demo GIFs and screenshots for TraceTap documentation.

## Table of Contents

1. [Setup](#setup)
2. [Recording Tools](#recording-tools)
3. [Demo Scenarios](#demo-scenarios)
4. [GIF Optimization](#gif-optimization)
5. [Screenshot Capture](#screenshot-capture)
6. [Troubleshooting](#troubleshooting)

---

## Setup

### Install Recording Tools

#### Option 1: Using Homebrew (macOS)

```bash
# Install asciinema for terminal recording
brew install asciinema

# Install agg for converting asciinema to GIF
brew install agg

# Install ImageMagick for GIF optimization
brew install imagemagick

# Optional: Install gifski for high-quality GIF encoding
brew install gifski
```

#### Option 2: Using apt (Linux)

```bash
# Install asciinema
sudo apt-get install asciinema

# Install agg (build from source)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cargo install agg

# Install ImageMagick
sudo apt-get install imagemagick

# Optional: Install gifski
cargo install gifski
```

#### Option 3: Using Docker

```bash
# If you have all tools installed via Docker
docker build -t tracetap-recording -f docker/Dockerfile.recording .
```

### Verify Installation

```bash
# Check all required tools are available
./scripts/record-demos.sh --check-tools
```

---

## Recording Tools

### asciinema

Terminal session recorder that captures all terminal activity.

**Features:**
- Records terminal sessions with perfect clarity
- Outputs to `.cast` format (JSON-based)
- No performance impact during recording
- Preserves ANSI colors and formatting

**Basic usage:**
```bash
# Start recording
asciinema rec demo.cast

# Press Ctrl+D or type `exit` to stop recording

# Play back recording
asciinema play demo.cast

# Convert to GIF (using agg)
agg demo.cast demo.gif
```

### agg

Converts asciinema recordings to GIF format.

**Features:**
- Fast conversion from `.cast` to `.gif`
- Supports theme customization
- Frame rate and speed control
- Supports terminal background colors

**Basic usage:**
```bash
# Simple conversion
agg input.cast output.gif

# With custom theme and speed
agg input.cast output.gif --theme solarized-dark --speed 2
```

**Themes available:**
- `asciinema`
- `solarized-dark`
- `solarized-light`
- `dracula`
- `monokai`

### ImageMagick

Suite of command-line image tools for GIF optimization.

**Features:**
- Reduce color palette for smaller files
- Resize images
- Strip unnecessary metadata
- Lossy compression

**Basic usage:**
```bash
# Optimize GIF (reduce size)
convert input.gif -colors 128 -fuzz 10% output.gif

# Resize GIF
convert input.gif -resize 800x600 output.gif

# Combine optimizations
convert input.gif -colors 128 -fuzz 15% -resize 1200x -strip output.gif
```

### gifski

High-quality GIF encoder (optional, better quality than ImageMagick).

**Features:**
- Superior color quality
- Smaller file sizes than ImageMagick
- Lossy compression with high fidelity

**Basic usage:**
```bash
# Convert PNG frames to high-quality GIF
gifski -o output.gif frame*.png
```

---

## Demo Scenarios

### Run All Demos

```bash
# Run all recording scenarios automatically
./scripts/record-demos.sh --all

# This will generate:
# - assets/demo-gifs/quickstart.gif (60s)
# - assets/demo-gifs/regression.gif (30s)
# - assets/demo-gifs/ai-suggestions.gif (45s)
# - assets/demo-gifs/contract-testing.gif (40s)
# - assets/demo-gifs/html-report.gif (30s)
```

### Run Individual Demos

```bash
# Run specific demo scenario
./scripts/record-demos.sh --demo quickstart

# Available options:
# --demo quickstart      Install → capture → generate tests (60s)
# --demo regression      Snapshot regression generation (30s)
# --demo ai-suggestions  AI test suggestions workflow (45s)
# --demo contract        Contract verification (40s)
# --demo report          HTML report generation and viewing (30s)
```

### Demo Scenario Details

#### 1. Quickstart Demo (60s)

**File:** `scripts/demo-scenarios/quickstart.sh`

**Workflow:**
1. Show project structure
2. Run `tracetap --help`
3. Start TraceTap with mitmproxy
4. Show API capture (simulated with curl requests)
5. Generate test output
6. Show generated Postman collection

**Command:**
```bash
./scripts/record-demos.sh --demo quickstart
```

**Output:** `assets/demo-gifs/quickstart.gif` (< 2MB)

#### 2. Regression Demo (30s)

**File:** `scripts/demo-scenarios/regression.sh`

**Workflow:**
1. Show existing snapshot file
2. Run regression test with differences
3. Show HTML comparison output
4. Highlight key differences

**Command:**
```bash
./scripts/record-demos.sh --demo regression
```

**Output:** `assets/demo-gifs/regression.gif` (< 1MB)

#### 3. AI Suggestions Demo (45s)

**File:** `scripts/demo-scenarios/ai-suggestions.sh`

**Workflow:**
1. Show test file with potential improvements
2. Run AI analysis on test suite
3. Display AI suggestions
4. Show applied improvements

**Command:**
```bash
./scripts/record-demos.sh --demo ai-suggestions
```

**Output:** `assets/demo-gifs/ai-suggestions.gif` (< 2MB)

#### 4. Contract Testing Demo (40s)

**File:** `scripts/demo-scenarios/contract.sh`

**Workflow:**
1. Show contract specification
2. Run contract verification
3. Display passing/failing contracts
4. Show verification report

**Command:**
```bash
./scripts/record-demos.sh --demo contract
```

**Output:** `assets/demo-gifs/contract-testing.gif` (< 1.5MB)

#### 5. HTML Report Demo (30s)

**File:** `scripts/demo-scenarios/report.sh`

**Workflow:**
1. Run test suite
2. Generate HTML report
3. Open in browser (show file path)
4. Display report structure

**Command:**
```bash
./scripts/record-demos.sh --demo report
```

**Output:** `assets/demo-gifs/html-report.gif` (< 1.5MB)

---

## GIF Optimization

### Understanding File Sizes

| Format | Size | Quality | Use Case |
|--------|------|---------|----------|
| Unoptimized GIF | 20-50MB | Excellent | Initial capture |
| Optimized GIF | 1-5MB | Good | Documentation |
| WEBP (lossy) | 0.5-2MB | Good | Modern browsers |
| Heavily lossy GIF | 0.5-1MB | Fair | Bandwidth limited |

### Optimization Techniques

#### 1. Color Reduction

Reduce from 256 colors to 128 or fewer:

```bash
# Reduce colors to 128
convert input.gif -colors 128 output.gif

# Reduce colors with fuzz (allow color variations)
convert input.gif -colors 96 -fuzz 10% output.gif
```

**Impact:**
- 128 colors: ~30-40% size reduction
- 96 colors: ~40-50% size reduction
- 64 colors: ~50-60% size reduction (quality degrades)

#### 2. Frame Reduction

Remove duplicate/similar frames:

```bash
# Remove every other frame
convert input.gif -coalesce -deconstruct -layers OptimizeFrame output.gif

# With color reduction
convert input.gif -colors 128 -fuzz 15% \
  -coalesce -deconstruct -layers OptimizeFrame output.gif
```

**Impact:**
- 20-30% size reduction with minimal quality loss

#### 3. Resize/Scale Down

```bash
# Scale to 1200px wide (maintains aspect ratio)
convert input.gif -resize 1200x output.gif

# Scale to specific dimensions
convert input.gif -resize 1024x768 output.gif
```

**Impact:**
- 50% size reduction at 1200px width
- 40% size reduction at 1024x width

#### 4. Combined Optimization

```bash
# Recommended: color reduction + frame optimization + resize
convert input.gif \
  -colors 128 \
  -fuzz 10% \
  -coalesce -deconstruct -layers OptimizeFrame \
  -resize 1200x \
  -strip \
  output.gif

# Check file size
ls -lh output.gif
```

**Expected Results:**
- Input: 40MB → Output: 1.5-2.5MB (95% reduction)
- Quality: Good (minimal visual difference)

### Automated Optimization

The `record-demos.sh` script automatically optimizes GIFs:

```bash
# GIF optimization is automatic
./scripts/record-demos.sh --demo quickstart --optimize

# Optimization steps:
# 1. Color reduction (128 colors)
# 2. Frame optimization
# 3. Resize to 1200px width
# 4. Strip metadata
```

### Validation

Check final GIF size and quality:

```bash
# Show file info
identify -verbose output.gif | grep -E "Geometry|Colorspace|Colors"

# Show file size
du -h output.gif

# View the GIF
open output.gif  # macOS
xdg-open output.gif  # Linux
```

---

## Screenshot Capture

### Using asciinema for Static Frames

Capture a single frame from an asciinema recording:

```bash
# Record first
asciinema rec demo.cast

# Extract frame at 5 seconds
agg demo.cast --at 5s output.png
```

### Using scrot or maim

For taking actual screenshots:

```bash
# Install (macOS)
brew install scrot

# Install (Linux)
sudo apt-get install scrot maim

# Take screenshot
scrot ~/screenshot.png

# Take screenshot of specific window
scrot -w ~/screenshot.png

# Take screenshot with delay
scrot --delay 5 ~/screenshot.png
```

### Manual Screenshots

For complex UIs, manual screenshots work best:

**macOS:**
- Full screen: Cmd+Shift+3
- Selection: Cmd+Shift+4
- Window: Cmd+Shift+4, then Space

**Linux:**
- Full screen: Print key
- Selection: Shift+Print
- Using GNOME: Ctrl+Alt+Shift+R (for screen recording)

### Screenshot Optimization

```bash
# Reduce PNG size
pngquant 256 input.png -o output.png

# Or using ImageMagick
convert input.png -colors 256 output.png

# Reduce quality further if needed
convert input.png -quality 85 -strip output.png
```

---

## Workflow: Recording a New Demo

### Step 1: Prepare Environment

```bash
# Create clean terminal
# Set terminal to 80x24 or similar for consistency

# Install any required packages
# Ensure tool versions are consistent
```

### Step 2: Test the Workflow

```bash
# Run through the workflow manually
# Time yourself to ensure it fits target duration
# Identify clear stopping points
```

### Step 3: Create Scenario Script

Create a new file in `scripts/demo-scenarios/`:

```bash
#!/bin/bash
# Demo scenario: [name]
# Duration: [X seconds]
# Description: [what it demonstrates]

# Typing helper function
type_command() {
    local cmd="$1"
    local delay="${2:-0.05}"
    echo -n "$cmd"
    for ((i=0; i<${#cmd}; i++)); do
        sleep "$delay"
    done
    echo
}

# Start recording (handled by record-demos.sh)
# Your scenario here
```

### Step 4: Record

```bash
./scripts/record-demos.sh --demo [name] --record
```

### Step 5: Review

```bash
# Play back the GIF
open assets/demo-gifs/[name].gif

# Check file size
du -h assets/demo-gifs/[name].gif

# Should be < 5MB
```

### Step 6: Optimize if Needed

```bash
# Manual optimization
./scripts/record-demos.sh --demo [name] --optimize-more

# Or re-record with different settings
```

---

## Advanced Topics

### Custom Themes

Create custom color scheme for asciinema:

```bash
# Edit theme in convert command
agg input.cast output.gif --theme custom

# Or specify colors directly
agg input.cast output.gif \
  --foreground "#FFF" \
  --background "#000"
```

### Speed Control

Record at different speeds:

```bash
# Speed up playback by 2x (smaller file)
agg input.cast output.gif --speed 2

# Slow down for clarity (larger file)
agg input.cast output.gif --speed 0.5
```

### Frame Rate

Adjust animation frame rate:

```bash
# Lower frame rate (choppier, smaller)
convert input.gif -fuzz 20% -delay 10 -resize 1200x output.gif

# Higher frame rate (smoother, larger)
convert input.gif -fuzz 5% -delay 5 -resize 1200x output.gif
```

### Interactive Demos

For complex workflows, consider recording parts separately:

```bash
# Part 1: Setup
asciinema rec part1.cast

# Part 2: Main workflow
asciinema rec part2.cast

# Part 3: Results
asciinema rec part3.cast

# Combine GIFs
convert part1.gif part2.gif part3.gif -append combined.gif
```

---

## Troubleshooting

### Issue: asciinema recording shows no color

**Solution:**
```bash
# Ensure TERM is set correctly
export TERM=xterm-256color

# Then record
asciinema rec demo.cast
```

### Issue: GIF is too large (> 5MB)

**Solutions:**
```bash
# Reduce colors more aggressively
convert input.gif -colors 64 -fuzz 20% output.gif

# Resize smaller
convert input.gif -resize 960x output.gif

# Reduce frame rate
convert input.gif -delay 20 output.gif
```

### Issue: GIF appears choppy or has artifacts

**Solutions:**
```bash
# Reduce fuzz (less color merging)
convert input.gif -colors 128 -fuzz 5% output.gif

# Use gifski for better quality
gifski -o output.gif input.gif
```

### Issue: Terminal text is unreadable in GIF

**Solutions:**
```bash
# Record at higher resolution
# Resize less aggressively
convert input.gif -resize 1400x output.gif

# Use clearer font in terminal
# Increase font size (recommend 14pt+)
```

### Issue: agg not converting properly

**Solutions:**
```bash
# Check asciinema recording is valid
asciinema play input.cast

# Try with explicit theme
agg input.cast output.gif --theme solarized-dark

# Check for special characters
file input.cast
```

### Issue: Script fails during recording

**Solutions:**
```bash
# Check dependencies
./scripts/record-demos.sh --check-tools

# Run with verbose output
bash -x ./scripts/record-demos.sh --demo quickstart

# Check disk space
df -h

# Check terminal supports recording
asciinema rec --help
```

---

## Best Practices

1. **Clear Terminal Before Recording**
   ```bash
   clear
   ```

2. **Use Consistent Font and Size**
   - Recommend: Monospace 14pt or larger
   - Avoid: Proportional fonts, tiny sizes

3. **Slow Down for Clarity**
   - Use `type_command()` with delays (0.05-0.1s)
   - Pause before/after important sections

4. **Test Thoroughly**
   - Run scenario 2-3 times before recording
   - Time yourself to match target duration
   - Verify output is correct each time

5. **Optimize for Bandwidth**
   - Target < 5MB per GIF
   - Use color reduction for non-photo content
   - Remove silent pauses in recording

6. **Version Control**
   - Store `.cast` files for re-recording
   - Don't commit large GIF files (use .gitignore)
   - Document any manual edits

7. **Consistency**
   - Keep same terminal size across demos
   - Use same color scheme
   - Use same font
   - Match screen resolution

---

## File Locations

```
scripts/
├── record-demos.sh                 # Main recording script
└── demo-scenarios/
    ├── quickstart.sh              # Quickstart workflow
    ├── regression.sh              # Regression testing
    ├── ai-suggestions.sh          # AI analysis workflow
    ├── contract.sh                # Contract verification
    └── report.sh                  # HTML report generation

assets/
├── demo-gifs/
│   ├── quickstart.gif
│   ├── regression.gif
│   ├── ai-suggestions.gif
│   ├── contract-testing.gif
│   └── html-report.gif
└── screenshots/
    ├── dashboard.png
    ├── report-example.png
    └── ui-preview.png

docs/
└── recording-guide.md             # This file
```

---

## Quick Reference

```bash
# Check tools installed
./scripts/record-demos.sh --check-tools

# Record all demos
./scripts/record-demos.sh --all

# Record specific demo
./scripts/record-demos.sh --demo quickstart

# Optimize existing GIF
convert input.gif -colors 128 -fuzz 10% output.gif

# Extract static frame
agg input.cast -at 5s output.png

# Check file sizes
du -h assets/demo-gifs/

# Play GIF
open assets/demo-gifs/quickstart.gif  # macOS
xdg-open assets/demo-gifs/quickstart.gif  # Linux
```

---

## Getting Help

- asciinema help: `asciinema --help`
- agg help: `agg --help`
- ImageMagick help: `convert --help` or `man convert`
- ffmpeg help: `ffmpeg -h`

For issues with the recording scripts:
```bash
./scripts/record-demos.sh --help
```

---

**Last Updated:** 2024
**Version:** 1.0
