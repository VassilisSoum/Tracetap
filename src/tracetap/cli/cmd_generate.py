"""
tracetap generate - Generate Playwright tests from a recorded session.

Reads a session directory (from tracetap record), sends correlated events
to Claude AI, generates Playwright test code, validates syntax, retries
on failure.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from tracetap.common.constants import MAX_GENERATION_RETRIES

console = Console()
logger = logging.getLogger(__name__)


@click.command()
@click.argument("session", type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--output", required=True, type=click.Path(), help="Output file path")
@click.option("-t", "--template", type=click.Choice(["basic", "comprehensive"]),
              default="comprehensive", help="Test template")
@click.option("-f", "--format", "output_format",
              type=click.Choice(["typescript", "javascript", "python"]),
              default="typescript", help="Output language")
@click.option("--base-url", default=None, help="Base URL for generated tests")
@click.option("--api-key", default=None, help="Anthropic API key (or set ANTHROPIC_API_KEY)")
@click.option("--no-sanitize", is_flag=True, help="Disable PII sanitization (not recommended)")
@click.option("--min-confidence", type=float, default=0.5, help="Minimum correlation confidence")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def generate(session, output, template, output_format, base_url, api_key,
             no_sanitize, min_confidence, verbose):
    """Generate Playwright tests from a recorded session.

    SESSION is the path to a recording directory (from tracetap record).

    \b
    Examples:
        tracetap generate recordings/20240101_120000_abc12345 -o tests/login.spec.ts
        tracetap generate recordings/my-session -o tests/flow.spec.ts --template basic
        tracetap generate recordings/my-session -o tests/flow.py --format python
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    # Resolve API key
    resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not resolved_key:
        console.print("[red]No API key found.[/red]")
        console.print("Set ANTHROPIC_API_KEY environment variable or use --api-key")
        sys.exit(1)

    asyncio.run(_generate_async(
        session_dir=Path(session),
        output_file=Path(output),
        template=template,
        output_format=output_format,
        base_url=base_url,
        api_key=resolved_key,
        sanitize_pii=not no_sanitize,
        min_confidence=min_confidence,
        verbose=verbose,
    ))


async def _generate_async(
    session_dir, output_file, template, output_format,
    base_url, api_key, sanitize_pii, min_confidence, verbose,
):
    """Async test generation workflow with retry loop."""
    from tracetap.generators import TestGenerator, GenerationOptions
    from tracetap.record.correlator import CorrelationResult

    # Load correlation data
    correlation_file = session_dir / "correlation.json"
    events_file = session_dir / "events.json"
    traffic_file = session_dir / "traffic.json"
    metadata_file = session_dir / "metadata.json"

    if not correlation_file.exists():
        # Try to build from raw events + traffic if correlation wasn't saved
        if events_file.exists() and traffic_file.exists():
            console.print("[yellow]No correlation.json found, re-correlating from raw data...[/yellow]")
            correlation_result = _correlate_from_raw(events_file, traffic_file)
        else:
            console.print(f"[red]Session directory missing required files.[/red]")
            console.print(f"Expected: correlation.json (or events.json + traffic.json)")
            console.print(f"In: {session_dir}")
            sys.exit(1)
    else:
        correlation_result = _load_correlation(correlation_file)

    if not correlation_result or len(correlation_result.correlated_events) == 0:
        console.print("[red]No correlated events found in session.[/red]")
        console.print("The recording may not have captured any meaningful interactions.")
        sys.exit(1)

    event_count = len(correlation_result.correlated_events)
    console.print(f"\nLoaded [bold]{event_count}[/bold] correlated events from session.")

    # Detect base URL from metadata if not provided
    if not base_url and metadata_file.exists():
        with open(metadata_file) as f:
            meta = json.load(f)
            base_url = meta.get("url")

    # Initialize generator
    if not sanitize_pii:
        console.print("[yellow]PII sanitization DISABLED - raw data will be sent to AI[/yellow]")

    generator = TestGenerator(api_key=api_key, sanitize_pii=sanitize_pii)

    options = GenerationOptions(
        template=template,
        output_format=output_format,
        confidence_threshold=min_confidence,
        base_url=base_url,
    )

    # Generate with retry loop
    console.print(f"\nGenerating [bold]{output_format}[/bold] tests (template: {template})...")

    test_code = None
    last_error = None

    for attempt in range(1, MAX_GENERATION_RETRIES + 2):  # +2 because range is exclusive and first attempt = 1
        try:
            if attempt > 1:
                console.print(f"[yellow]Retry {attempt - 1}/{MAX_GENERATION_RETRIES}...[/yellow]")

            test_code = await generator.generate_tests(correlation_result, options)

            # Validate syntax
            validation_errors = _validate_test_syntax(test_code, output_format)
            if validation_errors:
                console.print(f"[yellow]Syntax validation failed: {validation_errors}[/yellow]")
                if attempt <= MAX_GENERATION_RETRIES:
                    # Feed errors back to generator for retry
                    options = GenerationOptions(
                        template=template,
                        output_format=output_format,
                        confidence_threshold=min_confidence,
                        base_url=base_url,
                        retry_context=f"Previous attempt had syntax errors: {validation_errors}. Fix these issues.",
                    )
                    continue
                else:
                    console.print("[yellow]Max retries reached. Saving best attempt.[/yellow]")
            else:
                break  # Validation passed

        except Exception as e:
            last_error = str(e)
            # Redact API key from error messages
            if api_key and api_key in last_error:
                last_error = last_error.replace(api_key, "[REDACTED]")
            console.print(f"[red]Generation error: {last_error}[/red]")

            if attempt > MAX_GENERATION_RETRIES:
                console.print("[red]Max retries exceeded. Generation failed.[/red]")
                sys.exit(1)

    if not test_code:
        console.print("[red]Failed to generate tests.[/red]")
        sys.exit(1)

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(test_code)

    # Generate playwright config alongside tests
    if output_format in ("typescript", "javascript") and base_url:
        _write_playwright_config(output_file.parent, base_url)

    lines = test_code.count("\n")

    console.print()
    console.print(Panel(
        f"[bold]Output:[/bold] {output_file}\n"
        f"[bold]Lines:[/bold] {lines}\n"
        f"[bold]Template:[/bold] {template}\n"
        f"[bold]Format:[/bold] {output_format}\n"
        + (f"[bold]Base URL:[/bold] {base_url}\n" if base_url else "")
        + f"\n[bold]Run the tests:[/bold]\n"
        + (f"  npx playwright test {output_file}" if output_format != "python"
           else f"  pytest {output_file}"),
        title="Tests Generated",
        border_style="green",
    ))


def _load_correlation(correlation_file: Path):
    """Load CorrelationResult from JSON."""
    from tracetap.record.correlator import (
        CorrelationResult, CorrelatedEvent, CorrelationMetadata,
        CorrelationMethod, NetworkRequest,
    )
    from tracetap.record.parser import TraceTapEvent, EventType

    with open(correlation_file) as f:
        data = json.load(f)

    correlated_events = []
    for evt in data.get("correlated_events", []):
        ui_data = evt["ui_event"]
        try:
            event_type = EventType(ui_data.get("type", "click"))
        except ValueError:
            event_type = EventType.CLICK

        ui_event = TraceTapEvent(
            type=event_type,
            timestamp=ui_data.get("timestamp", 0),
            duration=ui_data.get("duration", 0),
            selector=ui_data.get("selector"),
            value=ui_data.get("value"),
            url=ui_data.get("url"),
        )

        network_calls = []
        for nc in evt.get("network_calls", []):
            network_calls.append(NetworkRequest(
                method=nc["method"],
                url=nc["url"],
                host=nc.get("host", ""),
                path=nc.get("path", ""),
                timestamp=nc.get("timestamp", 0),
                request_headers=nc.get("request_headers", {}),
                request_body=nc.get("request_body"),
                response_status=nc.get("response_status"),
                response_headers=nc.get("response_headers", {}),
                response_body=nc.get("response_body"),
                duration=nc.get("duration"),
            ))

        corr_data = evt["correlation"]
        correlation = CorrelationMetadata(
            confidence=corr_data["confidence"],
            time_delta=corr_data["time_delta"],
            method=CorrelationMethod(corr_data["method"]),
            reasoning=corr_data["reasoning"],
        )

        correlated_events.append(CorrelatedEvent(
            sequence=evt["sequence"],
            ui_event=ui_event,
            network_calls=network_calls,
            correlation=correlation,
        ))

    return CorrelationResult(
        correlated_events=correlated_events,
        stats=data.get("stats", {}),
    )


def _correlate_from_raw(events_file: Path, traffic_file: Path):
    """Re-correlate from raw events.json + traffic.json."""
    from tracetap.record.correlator import EventCorrelator, CorrelationOptions, NetworkRequest
    from tracetap.record.parser import TraceTapEvent, EventType
    from urllib.parse import urlparse

    with open(events_file) as f:
        events_data = json.load(f)

    with open(traffic_file) as f:
        traffic_data = json.load(f)

    ui_events = []
    for evt in events_data.get("events", []):
        try:
            event_type = EventType(evt.get("type", "click"))
        except ValueError:
            event_type = EventType.CLICK

        ui_events.append(TraceTapEvent(
            type=event_type,
            timestamp=evt.get("timestamp", 0),
            duration=0,
            selector=evt.get("selector"),
            value=evt.get("value"),
            url=evt.get("url"),
        ))

    network_requests = []
    for nc in traffic_data.get("requests", []):
        parsed = urlparse(nc.get("url", ""))
        network_requests.append(NetworkRequest(
            method=nc.get("method", "GET"),
            url=nc.get("url", ""),
            host=parsed.netloc,
            path=parsed.path,
            timestamp=nc.get("timestamp", 0),
            request_headers=nc.get("request_headers", {}),
            request_body=nc.get("request_body"),
            response_status=nc.get("response_status"),
            response_headers=nc.get("response_headers", {}),
            response_body=nc.get("response_body"),
            duration=nc.get("duration"),
        ))

    correlator = EventCorrelator(CorrelationOptions())
    return correlator.correlate(ui_events, network_requests)


def _validate_test_syntax(code: str, output_format: str) -> str:
    """Validate generated test code syntax.

    Returns empty string if valid, error description if invalid.
    """
    if not code or len(code.strip()) < 50:
        return "Generated code is empty or too short"

    if output_format == "python":
        try:
            compile(code, "<generated_test>", "exec")
            return ""
        except SyntaxError as e:
            return f"Python syntax error at line {e.lineno}: {e.msg}"

    # For TypeScript/JavaScript, check structural validity
    errors = []
    if "import" not in code and "require" not in code:
        errors.append("missing import statements")
    if "test(" not in code and "it(" not in code and "describe(" not in code:
        errors.append("missing test function definitions")

    # Check for common AI generation artifacts
    if "```" in code:
        errors.append("contains markdown code fence (```)")

    return "; ".join(errors)


def _write_playwright_config(output_dir: Path, base_url: str):
    """Write a playwright.config.ts alongside generated tests."""
    config_path = output_dir / "playwright.config.ts"
    if config_path.exists():
        return  # Don't overwrite existing config

    config = f'''import {{ defineConfig }} from '@playwright/test';

// Generated by TraceTap - base URL from recording: {base_url}
export default defineConfig({{
  testDir: '.',
  use: {{
    baseURL: '{base_url}',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  }},
  retries: 1,
}});
'''
    config_path.write_text(config)
    console.print(f"[dim]Wrote playwright.config.ts with baseURL: {base_url}[/dim]")
