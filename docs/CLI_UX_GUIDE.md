# TraceTap CLI UX Guide

Quick reference for using the enhanced error handling and output utilities.

## Error Handling

### Using Custom Exceptions

```python
from tracetap.common.errors import (
    APIKeyMissingError,
    InvalidSessionError,
    CorruptFileError,
    TraceTapError,
)

# Raise specific errors with helpful messages
if not api_key:
    raise APIKeyMissingError()

if not session_path.exists():
    raise InvalidSessionError(str(session_path), "Directory does not exist")

try:
    data = json.loads(file_content)
except json.JSONDecodeError as e:
    raise CorruptFileError(str(file_path), f"Invalid JSON at line {e.lineno}")

# Custom error with suggestion
raise TraceTapError(
    message="Something went wrong",
    suggestion="Try doing X, Y, and Z",
    docs_link="https://example.com/docs"
)
```

### Using Error Handler Decorator

```python
from tracetap.common.errors import handle_common_errors

@handle_common_errors
def main():
    """Main function with automatic error handling."""
    # Any TraceTapError will be caught and formatted
    # FileNotFoundError, PermissionError, KeyboardInterrupt handled too
    ...
```

## Progress Indicators

### Indeterminate Progress (Spinning)

Use for operations where you can't track progress (AI generation, network requests):

```python
from tracetap.common.output import generation_progress

with generation_progress("Generating tests...") as progress:
    task = progress.add_task("Generating tests...", total=None)
    result = await some_long_operation()
    progress.update(task, description="Tests generated!")
```

### Determinate Progress (Bar)

Use for countable operations (processing files, correlating events):

```python
from tracetap.common.output import correlation_progress

with correlation_progress(total_events) as progress:
    task = progress.add_task("Correlating events...", total=total_events)
    for i, event in enumerate(events):
        # ... process event ...
        progress.update(task, advance=1)
```

### Live Recording Status

Use for real-time status updates:

```python
from tracetap.common.output import recording_progress

with recording_progress() as counter:
    for event in capture_events():
        counter['count'] += 1
        # Status automatically updates with elapsed time and count
```

## Color-Coded Output

### Basic Messages

```python
from tracetap.common.output import success, error, warning, info

success("Tests generated successfully!")
error("Failed to load session")
warning("PII sanitization disabled")
info("Loading session from /path/to/session")
```

### Section Headers

```python
from tracetap.common.output import section_header

section_header("Loading Session")
# Output:
# ╭──────────────────────────────────────────╮
# │ Loading Session                          │
# ╰──────────────────────────────────────────╯
```

### Formatted Summaries

```python
from tracetap.common.output import print_summary

print_summary(
    "Tests Generated Successfully",
    stats=[
        ("Variations", "3"),
        ("Total lines", "450"),
        ("Template", "comprehensive")
    ],
    files=[
        ("tests/login.spec.ts", 150, "Happy path"),
        ("tests/edge.spec.ts", 200, "Edge cases"),
    ]
)
```

### Next Steps Guide

```python
from tracetap.common.output import print_next_steps, format_command

steps = [
    f"Review the test: {format_command('cat tests/output.spec.ts')}",
    f"Install Playwright: {format_command('npm install -D @playwright/test')}",
    f"Run tests: {format_command('npx playwright test')}",
]
print_next_steps(steps)
```

### Path and Command Formatting

```python
from tracetap.common.output import format_path, format_command, info

info(f"Output: {format_path('/path/to/file.ts')}")
# Output: ℹ️  Output: /path/to/file.ts (in magenta)

info(f"Run: {format_command('tracetap-record https://...')}")
# Output: ℹ️  Run: tracetap-record https://... (in bold white)
```

## Complete Example

Here's a complete example showing all features:

```python
import asyncio
from pathlib import Path
from tracetap.common.errors import (
    handle_common_errors,
    APIKeyMissingError,
    InvalidSessionError,
)
from tracetap.common.output import (
    console,
    section_header,
    success,
    error,
    info,
    generation_progress,
    print_summary,
    print_next_steps,
    format_path,
    format_command,
)

@handle_common_errors
async def process_session(session_path: Path, api_key: str):
    """Process a recording session with enhanced UX."""

    # Validation with helpful errors
    if not api_key:
        raise APIKeyMissingError()

    if not session_path.exists():
        raise InvalidSessionError(str(session_path), "Directory not found")

    # Section header
    console.print()
    section_header("Loading Session")
    info(f"Session: {format_path(str(session_path))}")

    # Load with feedback
    session_data = load_session(session_path)
    success(f"Loaded {len(session_data.events)} events")

    # Generate with progress
    console.print()
    section_header("Generating Tests")

    with generation_progress("Generating tests...") as progress:
        task = progress.add_task("Calling AI...", total=None)
        result = await generate_tests(session_data, api_key)
        progress.update(task, description="Complete!")

    # Summary
    print_summary(
        "Generation Complete",
        [
            ("Lines", str(result.line_count)),
            ("Template", result.template),
        ]
    )

    # Next steps
    steps = [
        f"Review: {format_command(f'cat {result.output_path}')}",
        f"Run: {format_command('npx playwright test')}",
    ]
    print_next_steps(steps)

    return 0

if __name__ == "__main__":
    asyncio.run(process_session(Path("session"), "sk-ant-..."))
```

## Color Scheme Reference

| Type | Color | Icon | Use For |
|------|-------|------|---------|
| Success | Green | ✅ | Completed operations |
| Error | Red | ❌ | Failures and errors |
| Warning | Yellow | ⚠️ | Warnings and cautions |
| Info | Cyan | ℹ️ | Informational messages |
| Path | Magenta | 📁 | File and directory paths |
| Command | Bold White | 💻 | Shell commands |
| Section | Cyan | ─ | Section dividers |

## Tips

1. **Always use exceptions for errors**: Don't print error messages directly - raise exceptions instead
2. **Use progress indicators for long operations**: Users appreciate knowing something is happening
3. **Be consistent with colors**: Use the standard color scheme throughout
4. **Format paths and commands**: Always use `format_path()` and `format_command()` for consistency
5. **Provide next steps**: After completion, tell users what to do next
6. **Keep it simple**: Don't over-format - clarity is more important than decoration
