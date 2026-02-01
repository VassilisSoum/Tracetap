# Progress Indicators for TraceTap CLI

## Overview

Progress indicators provide visual feedback for long-running CLI operations. They show:
- **Progress bars** with percentage, count, elapsed time, and ETA
- **Spinners** for indeterminate progress (animated)
- **Status messages** for workflow steps

All indicators are **text-based** with no external dependencies.

## Features

### Progress Bar
Displays numerical progress with visual indicators:

```
Analyzing [=====>    ] 50% (125/250) 1.2s ETA: 1.3s
Operations [=========>        ] 46% (23/50) 0.5s ETA: 0.6s
```

Features:
- Percentage completion
- Current/total count
- Elapsed time
- Estimated time remaining (ETA)
- Visual filled/empty bar
- Auto-completes with newline when done

### Spinner
Animated indicator for indeterminate progress:

```
⠋ Analyzing endpoints...
⠙ Analyzing endpoints...
⠹ Analyzing endpoints...
```

Spinner styles available:
- `dots` - Braille dots (default)
- `line` - Rotating line characters
- `arrow` - Rotating arrows
- `box` - Rotating box corners
- `simple` - Simple dots

### Status Line
Print structured status messages:

```
→ Starting analysis...
  • Processed 50 items
  • Found 5 patterns
✓ Analysis complete
✗ Error occurred
⚠ Warning message
ℹ Info message
```

## Usage

### In CLI Commands

The contract creation and verification commands now show progress:

```bash
# Contract creation shows progress
python3 tracetap-replay.py create-contract session.json -o contract.yaml

# Output:
# 📋 TraceTap Contract Creator
#    Input: session.json
#    Output: contract.yaml
#
# → Loading traffic from session.json...
# → Analyzing 125 requests...
# Analyzing [=====>    ] 50% (125/250) 1.2s ETA: 1.3s
#   • Found 50 unique endpoints
# → Generating OpenAPI operations...
# Operations [=========>    ] 46% (23/50) 0.5s ETA: 0.6s
# → Building OpenAPI specification...
#
# ✓ Contract created (125 requests analyzed)
#   • 50 endpoints documented
#   • Saved to contract.yaml
#   • OpenAPI 3.0 specification
```

```bash
# Contract verification shows comparison progress
python3 tracetap-replay.py verify-contract baseline.yaml current.yaml

# Output:
# 🔍 TraceTap Contract Verifier
#    Baseline: baseline.yaml
#    Current: current.yaml
#
# → Verifying contracts...
# → Loading baseline contract...
# → Loading current contract...
# → Comparing 50 endpoints...
# Endpoints [=========>     ] 46% (23/50) 0.5s ETA: 0.6s
#   • Detected 5 changes so far
# → Comparing schemas...
#
# ✓ Contracts are compatible - no breaking changes
#
# Changes detected:
#   • 5 total changes
#   • 0 breaking
#   • 0 warnings
#   • 5 info
```

### In Python Code

Import and use progress indicators:

```python
from tracetap.common.progress import ProgressBar, Spinner, StatusLine

# Progress bar
progress = ProgressBar(total=100, label="Processing", width=30)
for i in range(100):
    # Do work
    progress.update()
progress.finish()

# Spinner
spinner = Spinner("Analyzing endpoints...", style='dots')
spinner.start()
for i in range(20):
    time.sleep(0.1)
    spinner.update()
spinner.stop(final_label="✓ Analysis complete")

# Status line
status = StatusLine(verbose=True)
status.start("Starting workflow...")
status.progress("Step 1 complete")
status.progress("Step 2 complete")
status.success("Workflow complete")
```

## Implementation Details

### Progress Bar

**Location:** `/src/tracetap/common/progress.py`

**Methods:**
- `update(amount=1)` - Increment progress by amount
- `set(current)` - Set progress to exact value
- `finish()` - Mark as complete and print newline
- `print()` - Internal method to render bar

**Time Formatting:**
- `< 60s`: `1.2s`
- `< 1h`: `1.5m`
- `>= 1h`: `2.3h`

### Spinner

**Methods:**
- `start()` - Begin animation
- `update(label=None)` - Advance to next frame
- `stop(final_label=None)` - Stop and optionally show final message

**Styles:**
- Configurable via `style` parameter
- Easy to add new styles in `SPINNERS` dict

### Status Line

**Methods:**
- `start(message)` - Print start message
- `progress(message)` - Print intermediate progress
- `success(message)` - Print success with ✓
- `error(message)` - Print error with ✗
- `warning(message)` - Print warning with ⚠
- `info(message)` - Print info with ℹ

**Verbose Mode:**
- `StatusLine(verbose=True)` - Show all messages
- `StatusLine(verbose=False)` - Show only success/error/final messages

## Integration Points

### Contract Creator
- Shows progress while analyzing requests
- Displays endpoint grouping progress
- Shows generation progress for operations
- Final summary with endpoint count

**File:** `/src/tracetap/contract/contract_creator.py`

Methods enhanced:
- `create_contract(requests, verbose=False)`
- `save_contract(requests, output_file, verbose=False)`
- `create_contract_from_traffic(..., verbose=True)`

### Contract Verifier
- Shows loading progress for both contracts
- Displays endpoint comparison progress
- Shows schema comparison
- Provides change summary with counts

**File:** `/src/tracetap/contract/contract_verifier.py`

Methods enhanced:
- `verify(baseline_contract, current_contract, verbose=False)`
- `verify_files(baseline_file, current_file, verbose=False)`
- `verify_contracts(..., verbose=True)`

## Examples

### Command Line Usage

```bash
# Create contract with progress indicators
python3 tracetap-replay.py create-contract large-session.json -o contract.yaml

# Verify contracts with progress
python3 tracetap-replay.py verify-contract baseline.yaml current.yaml -o report.txt
```

### Python Module Usage

```python
from tracetap.contract.contract_creator import create_contract_from_traffic

# Function automatically shows progress when verbose=True
success = create_contract_from_traffic(
    json_file='session.json',
    output_file='contract.yaml',
    verbose=True  # Enables progress indicators
)
```

### Custom Progress in New Features

```python
from tracetap.common.progress import ProgressBar, StatusLine

def my_long_operation(items):
    status = StatusLine(verbose=True)
    status.start(f"Processing {len(items)} items...")

    progress = ProgressBar(len(items), label="Items", width=25)

    for item in items:
        # Process item
        progress.update()

    progress.finish()
    status.success("All items processed")
```

## Design Decisions

1. **No External Dependencies**
   - Pure Python using `sys.stdout`
   - Works in all terminal environments
   - Minimal overhead

2. **Text-Based Only**
   - No color codes or special terminal features
   - Compatible with CI/CD systems
   - Easy to redirect/log

3. **Verbose Mode**
   - `verbose=True` shows all progress
   - `verbose=False` shows only final results
   - Controlled per component

4. **Time Formatting**
   - Shows elapsed time and ETA
   - Automatically scales (seconds, minutes, hours)
   - Helps estimate remaining work

5. **Non-Intrusive**
   - Progress bars clear themselves
   - Spinners replace themselves on same line
   - Final messages remain for clarity

## Performance

- Minimal CPU overhead from progress updates
- No threading required
- Works with sequential processing
- Suitable for CLI operations lasting 1s-10min+

## Testing

Demo script available:
```bash
python3 demo_progress.py
```

Shows:
- Progress bar in action
- Spinner animation
- Status line messages
- Multiple concurrent operations

## Future Enhancements

Possible improvements:
- Color support for terminal types
- Multi-line progress for parallel operations
- Rate limiting to reduce updates
- Network bandwidth indicators
- Memory usage indicators

## Troubleshooting

### Progress bar not showing
- Check terminal supports ANSI escape sequences
- Verify `verbose=True` is set
- Check output isn't redirected to file

### Spinner animation looks wrong
- Some terminals don't support Unicode characters
- Try different `style` (e.g., 'line' or 'simple')
- Use simpler style for compatibility

### ETA incorrect
- ETA is estimated from current rate
- May be inaccurate if operation speed varies
- Becomes more accurate as progress advances
