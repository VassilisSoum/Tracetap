"""
TraceTap Test Generator CLI

Command-line interface for generating Playwright tests from recorded sessions.
Reads correlation data from a session directory and uses AI to synthesize tests.
"""

import argparse
import asyncio
import sys
import json
import os
from pathlib import Path
from typing import Optional
import logging

from ..generators import TestGenerator, GenerationOptions
from ..record.correlator import (
    CorrelationResult,
    CorrelatedEvent,
    CorrelationMetadata,
    CorrelationMethod,
    NetworkRequest,
)
from ..record.parser import TraceTapEvent, EventType
from ..common.errors import (
    APIKeyMissingError,
    InvalidSessionError,
    CorruptFileError,
    handle_common_errors,
)
from ..common.output import (
    console,
    success,
    error,
    warning,
    info,
    section_header,
    generation_progress,
    print_summary,
    print_next_steps,
    format_path,
    format_command,
)

# Import version
try:
    from tracetap import __version__
except ImportError:
    __version__ = "unknown"

logger = logging.getLogger(__name__)


def _sanitize_api_key(text: str, api_key: Optional[str]) -> str:
    """Sanitize API key from text for safe logging.

    Args:
        text: Text that may contain API key
        api_key: API key to redact (if None, returns text unchanged)

    Returns:
        Text with API key replaced by [REDACTED_API_KEY]
    """
    if not api_key or not text:
        return text
    return text.replace(api_key, '[REDACTED_API_KEY]')


def load_correlation_result(correlation_file: Path) -> CorrelationResult:
    """Load correlation result from JSON file.

    Args:
        correlation_file: Path to correlation.json

    Returns:
        CorrelationResult object

    Raises:
        ValueError: If correlation file is invalid
    """
    with open(correlation_file, "r") as f:
        data = json.load(f)

    # Reconstruct CorrelationResult from JSON
    correlated_events = []

    for event_data in data.get("correlated_events", []):
        # Reconstruct UI event
        ui_event_data = event_data["ui_event"]

        # Convert type string to EventType enum, fallback to CLICK if unknown
        event_type_str = ui_event_data.get("type", "click")
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            event_type = EventType.CLICK

        ui_event = TraceTapEvent(
            type=event_type,
            timestamp=ui_event_data.get("timestamp", 0),
            duration=ui_event_data.get("duration", 0),
            selector=ui_event_data.get("selector"),
            value=ui_event_data.get("value"),
            url=ui_event_data.get("url"),
        )

        # Reconstruct network calls
        network_calls = []
        for nc_data in event_data.get("network_calls", []):
            network_call = NetworkRequest(
                method=nc_data["method"],
                url=nc_data["url"],
                host=nc_data.get("host", ""),
                path=nc_data.get("path", ""),
                timestamp=nc_data.get("timestamp", 0),
                request_headers=nc_data.get("request_headers", {}),
                request_body=nc_data.get("request_body"),
                response_status=nc_data.get("response_status"),
                response_headers=nc_data.get("response_headers"),
                response_body=nc_data.get("response_body"),
                duration=nc_data.get("duration"),
            )
            network_calls.append(network_call)

        # Reconstruct correlation metadata
        corr_data = event_data["correlation"]
        correlation = CorrelationMetadata(
            confidence=corr_data["confidence"],
            time_delta=corr_data["time_delta"],
            method=CorrelationMethod(corr_data["method"]),
            reasoning=corr_data["reasoning"],
        )

        # Create CorrelatedEvent
        correlated_event = CorrelatedEvent(
            sequence=event_data["sequence"],
            ui_event=ui_event,
            network_calls=network_calls,
            correlation=correlation,
        )
        correlated_events.append(correlated_event)

    # Get stats
    stats = data.get("stats", {})

    return CorrelationResult(correlated_events=correlated_events, stats=stats)


async def generate_tests_from_session(
    session_dir: Path,
    output_file: Path,
    template: str,
    output_format: str,
    confidence_threshold: float,
    api_key: Optional[str],
    base_url: Optional[str],
    verbose: bool,
    dry_run: bool = False,
    sanitize_pii: bool = True,
    add_performance: bool = False,
    organize: bool = False,
    variations_count: int = 0,
) -> int:
    """Generate tests from a recorded session.

    Args:
        session_dir: Path to session directory
        output_file: Output file path
        template: Template type
        output_format: Output format
        confidence_threshold: Minimum confidence
        api_key: Anthropic API key
        base_url: Base URL for tests
        verbose: Enable verbose logging
        dry_run: Show what would be done without actually generating
        sanitize_pii: Enable PII sanitization before sending to AI
        add_performance: Add performance/timing assertions to tests
        organize: Organize tests into logical directory structure
        variations_count: Number of test variations to generate (0=disabled)

    Returns:
        Exit code (0=success, 1=error)
    """
    # Load correlation result
    console.print()
    section_header("Loading Session")
    info(f"Loading session: {format_path(str(session_dir))}")

    correlation_file = session_dir / "correlation.json"

    if not correlation_file.exists():
        raise InvalidSessionError(
            str(session_dir),
            f"Missing correlation.json file"
        )

    try:
        correlation_result = load_correlation_result(correlation_file)
        event_count = len(correlation_result.correlated_events)
        correlation_rate = correlation_result.stats.get("correlation_rate", 0) * 100
        avg_confidence = correlation_result.stats.get("average_confidence", 0) * 100

        success(f"Loaded {event_count} correlated events")
        console.print(f"   • Correlation rate: [bold]{correlation_rate:.1f}%[/bold]")
        console.print(f"   • Average confidence: [bold]{avg_confidence:.1f}%[/bold]")

        if event_count == 0:
            warning("No correlated events found")
            info("Try re-recording with adjusted parameters:")
            console.print("   • Increase --window-ms to capture more events")
            console.print("   • Lower --min-confidence threshold")
            return 1
    except json.JSONDecodeError as e:
        raise CorruptFileError(
            str(correlation_file),
            f"Invalid JSON at line {e.lineno}: {e.msg}"
        )
    except Exception as e:
        error_msg = _sanitize_api_key(str(e), api_key)
        error(f"Error loading correlation data: {error_msg}")
        if verbose:
            import traceback
            import io
            tb_buffer = io.StringIO()
            traceback.print_exc(file=tb_buffer)
            tb_output = _sanitize_api_key(tb_buffer.getvalue(), api_key)
            console.print(tb_output, style="red dim")
        return 1

    # Dry-run mode
    if dry_run:
        console.print()
        section_header("Dry-run Mode - Configuration Check")
        console.print(f"  Session: {format_path(str(session_dir))}")
        console.print(f"  Output: {format_path(str(output_file.absolute()))}")
        console.print(f"  Template: [bold]{template}[/bold]")
        console.print(f"  Format: [bold]{output_format}[/bold]")
        console.print(f"  Confidence threshold: [bold]{confidence_threshold}[/bold]")
        if base_url:
            console.print(f"  Base URL: [bold]{base_url}[/bold]")
        console.print()
        success("Configuration is valid (no tests generated)")
        return 0

    # Check API key
    if not api_key and not os.getenv("ANTHROPIC_API_KEY"):
        raise APIKeyMissingError()

    # Initialize generator
    console.print()
    section_header("Initializing Generator")
    if not sanitize_pii:
        warning("PII sanitization is DISABLED - sensitive data will be sent to AI")
    else:
        info("PII sanitization enabled (default)")

    try:
        generator = TestGenerator(api_key=api_key, sanitize_pii=sanitize_pii)
        success("Generator initialized successfully")
    except Exception as e:
        # Sanitize API key from error message before logging
        error_msg = _sanitize_api_key(str(e), api_key)
        error(f"Failed to initialize generator: {error_msg}")
        if "api" in str(e).lower() or "key" in str(e).lower():
            raise APIKeyMissingError()
        if verbose:
            import traceback
            import io
            # Capture and sanitize traceback
            tb_buffer = io.StringIO()
            traceback.print_exc(file=tb_buffer)
            tb_output = _sanitize_api_key(tb_buffer.getvalue(), api_key)
            console.print(tb_output, style="red dim")
        return 1

    # Generate tests
    console.print()
    section_header("Generating Tests")
    info(f"Template: [bold]{template}[/bold]")
    info(f"Output format: [bold]{output_format}[/bold]")
    info(f"Confidence threshold: [bold]{confidence_threshold}[/bold]")

    # Extract performance thresholds if enabled
    performance_thresholds = None
    if add_performance:
        from ..generators.performance_analyzer import PerformanceAnalyzer

        perf_analyzer = PerformanceAnalyzer()
        performance_thresholds = perf_analyzer.extract_thresholds(
            correlation_result.correlated_events
        )
        if performance_thresholds:
            stats = perf_analyzer.get_statistics(performance_thresholds)
            info(f"Performance: [bold]{stats['count']}[/bold] thresholds extracted")
            console.print(f"   • Average duration: [bold]{stats['avg_duration_ms']}ms[/bold]")

    options = GenerationOptions(
        template=template,
        output_format=output_format,
        confidence_threshold=confidence_threshold,
        base_url=base_url,
        performance_thresholds=performance_thresholds,
    )

    # Generate test variations if requested
    variations = []
    if variations_count > 0:
        from ..generators.variation_generator import VariationGenerator

        var_gen = VariationGenerator(api_key=api_key)
        console.print()
        info(f"Generating [bold]{variations_count}[/bold] test variations...")

        with generation_progress("Creating variations...") as progress:
            task = progress.add_task("Creating variations...", total=None)
            variations = var_gen.generate_variations(
                correlation_result.correlated_events, count=variations_count
            )
            progress.update(task, description=f"Created {len(variations)} variations")

        success(f"Created {len(variations)} variations")
        for var in variations:
            console.print(f"   • Variation {var.variation_number}: {var.description}")
    else:
        # No variations - use original events
        from ..generators.variation_generator import TestVariation, VariationType

        variations = [
            TestVariation(
                variation_number=1,
                variation_type=VariationType.HAPPY_PATH,
                description="Original recording",
                modified_events=correlation_result.correlated_events,
                expected_outcome="success",
            )
        ]

    # Generate tests (organized or single file)
    if organize:
        from ..generators.file_organizer import FileOrganizer
        from ..record.correlator import CorrelationResult as CR

        total_files = 0
        total_lines = 0

        # Generate for each variation
        for variation in variations:
            organizer = FileOrganizer()
            file_specs = organizer.organize(
                variation.modified_events, output_file.parent
            )

            stats = organizer.get_statistics(file_specs)
            variation_suffix = (
                f"-variation-{variation.variation_number}"
                if variations_count > 0
                else ""
            )

            console.print()
            info(f"Organizing variation {variation.variation_number} into [bold]{len(file_specs)}[/bold] files:")
            console.print(f"   {variation.description}")
            console.print(f"   Features: {', '.join(stats['features'])}")

            with generation_progress(f"Generating organized tests...") as progress:
                task = progress.add_task(
                    f"Generating {len(file_specs)} test files...",
                    total=len(file_specs)
                )

                for spec in file_specs:
                    # Create CorrelationResult for this file's events
                    file_correlation_result = CR(
                        correlated_events=spec.events, stats=correlation_result.stats
                    )

                    try:
                        test_code = await generator.generate_tests(
                            file_correlation_result, options
                        )
                    except Exception as e:
                        error_msg = _sanitize_api_key(str(e), api_key)
                        error(f"Error generating {spec.relative_path}: {error_msg}")
                        if verbose:
                            import traceback
                            import io
                            tb_buffer = io.StringIO()
                            traceback.print_exc(file=tb_buffer)
                            tb_output = _sanitize_api_key(tb_buffer.getvalue(), api_key)
                            console.print(tb_output, style="red dim")
                        progress.update(task, advance=1)
                        continue

                    # Write to organized path with variation suffix
                    relative_dir = spec.relative_path.parent
                    filename = spec.relative_path.stem + variation_suffix + spec.relative_path.suffix
                    full_path = output_file.parent / relative_dir / filename
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(test_code)

                    lines = test_code.count("\n")
                    total_lines += lines
                    total_files += 1
                    progress.update(task, advance=1)

        # Print organized test summary
        console.print()
        print_summary(
            "Tests Generated Successfully",
            [
                ("Variations", str(len(variations))),
                ("Total files", str(total_files)),
                ("Total lines", str(total_lines)),
                ("Template", template),
            ],
        )

    else:
        # Single file output (original behavior) - iterate through variations
        from ..record.correlator import CorrelationResult as CR

        total_lines = 0
        files_written = []

        with generation_progress("Generating test files...") as progress:
            task = progress.add_task(
                f"Generating {len(variations)} test file(s)...",
                total=len(variations)
            )

            for variation in variations:
                # Create CorrelationResult for this variation's events
                var_correlation_result = CR(
                    correlated_events=variation.modified_events,
                    stats=correlation_result.stats,
                )

                try:
                    test_code = await generator.generate_tests(var_correlation_result, options)
                except Exception as e:
                    error_msg = _sanitize_api_key(str(e), api_key)
                    error(f"Error generating variation {variation.variation_number}: {error_msg}")
                    info("Troubleshooting:")
                    console.print("   • Check your API key is valid")
                    console.print("   • Check your network connection")
                    console.print("   • Try a simpler template (basic)")
                    if verbose:
                        import traceback
                        import io
                        tb_buffer = io.StringIO()
                        traceback.print_exc(file=tb_buffer)
                        tb_output = _sanitize_api_key(tb_buffer.getvalue(), api_key)
                        console.print(tb_output, style="red dim")
                    progress.update(task, advance=1)
                    continue

                # Determine output path (add variation suffix if multiple variations)
                if variations_count > 0:
                    var_output = (
                        output_file.parent
                        / f"{output_file.stem}-variation-{variation.variation_number}{output_file.suffix}"
                    )
                else:
                    var_output = output_file

                # Save to file
                var_output.parent.mkdir(parents=True, exist_ok=True)
                var_output.write_text(test_code)

                lines = test_code.count("\n")
                total_lines += lines
                files_written.append((var_output, lines, variation.description))
                progress.update(task, advance=1)

        # Display statistics
        console.print()
        if variations_count > 0:
            files_list = [
                (str(file_path), lines, desc)
                for file_path, lines, desc in files_written
            ]
            print_summary(
                "Tests Generated Successfully",
                [
                    ("Variations", str(len(files_written))),
                    ("Total lines", str(total_lines)),
                    ("Template", template),
                ],
                files=files_list,
            )
        else:
            print_summary(
                "Tests Generated Successfully",
                [
                    ("Output", format_path(str(output_file))),
                    ("Lines", str(total_lines)),
                    ("Template", template),
                ],
            )
    # Next steps
    if output_format in ["typescript", "javascript"]:
        steps = [
            f"Review the generated test: {format_command(f'cat {output_file}')}",
            f"Install Playwright (if needed): {format_command('npm install -D @playwright/test')}",
            f"Run tests: {format_command(f'npx playwright test {output_file}')}",
        ]
    else:
        steps = [
            f"Review the generated test: {format_command(f'cat {output_file}')}",
            f"Install pytest (if needed): {format_command('pip install pytest')}",
            f"Run tests: {format_command(f'pytest {output_file}')}",
        ]

    print_next_steps(steps)

    # Resources
    console.print("🔗 Resources:")
    console.print("   • Playwright docs: https://playwright.dev")
    console.print("   • TraceTap docs: https://github.com/VassilisSoum/tracetap")
    console.print()

    return 0


@handle_common_errors
def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="tracetap-generate-tests",
        description="Generate Playwright tests from TraceTap recording sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic: Generate from session directory
  tracetap-generate-tests recordings/my-session -o tests/generated.spec.ts

  # Use comprehensive template with details
  tracetap-generate-tests recordings/my-session -o tests/full.spec.ts \\
    --template comprehensive --base-url https://myapp.com

  # Generate Python tests
  tracetap-generate-tests recordings/my-session -o tests/test_flow.py \\
    --format python

  # Higher confidence threshold for stricter correlation
  tracetap-generate-tests recordings/my-session -o tests/strict.spec.ts \\
    --min-confidence 0.8

  # Dry-run to check configuration
  tracetap-generate-tests recordings/my-session -o tests/output.spec.ts \\
    --dry-run

Troubleshooting:
  ❓ No correlation file?    → Run 'tracetap record' first
  ❓ Low event count?        → Re-record with different --window-ms
  ❓ API key error?          → Set ANTHROPIC_API_KEY environment variable
  ❓ Want to preview output? → Use --dry-run first
        """,
    )

    # Version flag
    parser.add_argument(
        "--version",
        action="version",
        version=f"TraceTap Generate Tests v{__version__}",
    )

    parser.add_argument(
        "session", type=Path, help="Path to recorded session directory (from tracetap record)"
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output file path for generated tests",
    )

    parser.add_argument(
        "-t",
        "--template",
        choices=["basic", "comprehensive", "regression"],
        default="comprehensive",
        help="Test template: basic (simple), comprehensive (detailed), regression (thorough)",
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=["typescript", "javascript", "python"],
        default="typescript",
        help="Output format (default: typescript)",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        metavar="THRESHOLD",
        help="Minimum correlation confidence (0.0-1.0, default: 0.5)",
    )

    parser.add_argument(
        "--base-url",
        type=str,
        help="Base URL for the application under test (optional)",
    )

    parser.add_argument(
        "--api-key", type=str, help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    )

    parser.add_argument(
        "--no-sanitize",
        action="store_true",
        help="Disable PII sanitization (NOT RECOMMENDED - sends raw data to AI)",
    )

    parser.add_argument(
        "--performance",
        action="store_true",
        help="Add performance/timing assertions to generated tests",
    )

    parser.add_argument(
        "--organize",
        action="store_true",
        help="Organize tests into logical directory structure by endpoint/feature",
    )

    parser.add_argument(
        "--variations",
        type=int,
        default=0,
        metavar="N",
        help="Generate N test variations (1=happy path, 2-N=edge cases/errors)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually generating tests",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose debug output"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG, format="%(levelname)s: %(message)s"
        )
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    # Validation
    if not args.session.exists():
        raise InvalidSessionError(str(args.session), "Directory does not exist")

    if not args.session.is_dir():
        raise InvalidSessionError(str(args.session), "Path is not a directory")

    if args.min_confidence < 0 or args.min_confidence > 1:
        from ..common.errors import TraceTapError
        raise TraceTapError(
            message="--min-confidence must be between 0.0 and 1.0",
            suggestion="Try: --min-confidence 0.5 (default) or 0.8 (stricter)"
        )

    # Check for API key (not needed for dry-run)
    api_key = args.api_key
    if not args.dry_run:
        if not api_key:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise APIKeyMissingError()

    # Run generation
    try:
        return asyncio.run(
            generate_tests_from_session(
                session_dir=args.session,
                output_file=args.output,
                template=args.template,
                output_format=args.format,
                confidence_threshold=args.min_confidence,
                api_key=api_key,
                base_url=args.base_url,
                verbose=args.verbose,
                dry_run=args.dry_run,
                sanitize_pii=not args.no_sanitize,  # Default: sanitize ON
                add_performance=args.performance,
                organize=args.organize,
                variations_count=args.variations,
            )
        )
    except KeyboardInterrupt:
        console.print("\n")
        warning("Operation interrupted by user")
        return 130
    except Exception as e:
        # Sanitize API key from error (use args.api_key or env var)
        api_key_to_sanitize = getattr(args, 'api_key', None) or os.environ.get("ANTHROPIC_API_KEY")
        error_msg = _sanitize_api_key(str(e), api_key_to_sanitize)
        error(f"Unexpected error: {error_msg}")
        info("Enable verbose mode for more details: -v")
        if args.verbose:
            import traceback
            import io
            tb_buffer = io.StringIO()
            traceback.print_exc(file=tb_buffer)
            tb_output = _sanitize_api_key(tb_buffer.getvalue(), api_key_to_sanitize)
            console.print(tb_output, style="red dim")
        return 1


if __name__ == "__main__":
    sys.exit(main())
