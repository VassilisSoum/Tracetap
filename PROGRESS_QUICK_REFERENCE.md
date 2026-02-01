# Progress Indicators - Quick Reference

## Three Components

### ProgressBar
For operations with known total count.

```python
from tracetap.common.progress import ProgressBar

progress = ProgressBar(100, label="Processing", width=30)
for i in range(100):
    # do work
    progress.update()  # increment by 1
    # or progress.update(5)  # increment by 5
    # or progress.set(i)  # set to exact value
progress.finish()
```

**Output:** `Processing [=====>    ] 50% (50/100) 1.2s ETA: 1.3s`

### Spinner
For indeterminate operations (no known total).

```python
from tracetap.common.progress import Spinner
import time

spinner = Spinner("Loading...", style='dots')
spinner.start()
for i in range(20):
    time.sleep(0.1)
    spinner.update()
spinner.stop(final_label="✓ Done")
```

**Output:** `⠋ Loading...` (animated) → `✓ Done`

**Styles:** `dots` `line` `arrow` `box` `simple`

### StatusLine
For workflow status messages.

```python
from tracetap.common.progress import StatusLine

status = StatusLine(verbose=True)
status.start("Starting...")
status.progress("Step 1 done")
status.progress("Step 2 done")
status.success("Complete")
# status.error("Failed")
# status.warning("Warning")
# status.info("Info message")
```

**Output:**
```
→ Starting...
  • Step 1 done
  • Step 2 done
✓ Complete
```

## In CLI Commands

```bash
# Shows progress automatically
python3 tracetap-replay.py create-contract session.json -o contract.yaml
python3 tracetap-replay.py verify-contract baseline.yaml current.yaml
```

## In Python Modules

```python
# Contract creator
from tracetap.contract.contract_creator import create_contract_from_traffic
create_contract_from_traffic('file.json', 'out.yaml', verbose=True)

# Contract verifier
from tracetap.contract.contract_verifier import verify_contracts
verify_contracts('baseline.yaml', 'current.yaml', verbose=True)
```

## Combined Example

```python
from tracetap.common.progress import ProgressBar, StatusLine

def process_items(items):
    status = StatusLine(verbose=True)
    status.start(f"Processing {len(items)} items...")

    progress = ProgressBar(len(items), label="Items", width=25)

    for item in items:
        # do work
        progress.update()

    progress.finish()
    status.success("All items processed")
```

## Configuration

All components respect `verbose` parameter:
- `verbose=True` - Show all messages
- `verbose=False` - Show only final messages

Example:
```python
status = StatusLine(verbose=False)  # Only final messages
status.start("...")  # Not shown
status.success("Done")  # Shown
```

## Time Format

- `< 60 seconds`: `1.2s`
- `< 60 minutes`: `1.5m`
- `>= 60 minutes`: `2.3h`

## Common Patterns

### Pattern 1: Simple Loop Progress
```python
progress = ProgressBar(100, label="Step")
for i in range(100):
    # work
    progress.update()
progress.finish()
```

### Pattern 2: Multi-Step Workflow
```python
status = StatusLine(verbose=True)

status.start("Step 1...")
# do work
status.progress("Step 1 done")

status.start("Step 2...")
# do work
status.success("All steps done")
```

### Pattern 3: Mixed Progress
```python
status = StatusLine(verbose=True)
status.start("Processing...")

progress = ProgressBar(50, label="Items")
for i in range(50):
    # work
    progress.update()
progress.finish()

status.success("Processing complete")
```

### Pattern 4: Error Handling
```python
status = StatusLine(verbose=True)
status.start("Processing...")
try:
    # do work
    status.success("Done")
except Exception as e:
    status.error(f"Failed: {e}")
```

## No Dependencies Required

- Pure Python (uses only `sys`, `time`)
- No pip packages needed
- Works in all terminal environments
- Compatible with CI/CD systems

## Demo

Run the demo script to see all features:
```bash
python3 demo_progress.py
```

## More Info

See `/PROGRESS_INDICATORS.md` for complete documentation.
