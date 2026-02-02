"""
TraceTap Record CLI Command

Interactive CLI for recording UI interactions with network traffic capture.
Provides command-line interface for the RecordingSession workflow.

Usage:
    tracetap record <url> [options]

Example:
    tracetap record https://example.com
    tracetap record https://example.com -n login-flow -o ./sessions
    tracetap record https://example.com --headless --window-ms 1000
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import recording modules
try:
    from tracetap.record.session import RecordingSession, SessionMetadata, SessionResult
    from tracetap.record.recorder import TraceRecorder, RecorderOptions
    from tracetap.record.correlator import (
        EventCorrelator,
        CorrelationOptions,
        load_mitmproxy_traffic,
    )
    from tracetap.record.parser import TraceParser
except ImportError as e:
    print(f"Error: Failed to import recording modules: {e}")
    print("Please ensure tracetap is properly installed.")
    sys.exit(1)


console = Console()
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI.

    Args:
        verbose: Enable verbose debug logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler()],
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="tracetap record",
        description="Record UI interactions with network traffic capture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  tracetap record https://example.com

  # With custom session name and output directory
  tracetap record https://example.com -n login-flow -o ./sessions

  # Headless mode with custom correlation window
  tracetap record https://example.com --headless --window-ms 1000

  # Full control over correlation parameters
  tracetap record https://example.com --window-ms 500 --min-confidence 0.7
        """,
    )

    # Required arguments
    parser.add_argument(
        "url",
        type=str,
        help="URL to record (e.g., https://example.com)",
    )

    # Optional arguments
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="./recordings",
        help="Output directory for session files (default: ./recordings)",
    )

    parser.add_argument(
        "-n",
        "--name",
        type=str,
        help="Session name (default: auto-generated)",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (default: False)",
    )

    parser.add_argument(
        "--proxy-port",
        type=int,
        default=8888,
        help="mitmproxy port (default: 8888)",
    )

    parser.add_argument(
        "--window-ms",
        type=int,
        default=500,
        help="Correlation time window in milliseconds (default: 500)",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Minimum correlation confidence threshold (default: 0.5)",
    )

    parser.add_argument(
        "--no-screenshots",
        action="store_true",
        default=False,
        help="Disable screenshots in trace",
    )

    parser.add_argument(
        "--no-snapshots",
        action="store_true",
        default=False,
        help="Disable DOM snapshots in trace",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose debug logging",
    )

    return parser.parse_args()


def validate_arguments(args: argparse.Namespace) -> None:
    """Validate command-line arguments.

    Args:
        args: Parsed arguments

    Raises:
        ValueError: If arguments are invalid
    """
    # Validate URL
    if not args.url.startswith(("http://", "https://")):
        raise ValueError(
            f"Invalid URL: {args.url}. URL must start with http:// or https://"
        )

    # Validate output directory
    output_path = Path(args.output)
    if output_path.exists() and not output_path.is_dir():
        raise ValueError(f"Output path exists but is not a directory: {args.output}")

    # Validate port
    if not (1 <= args.proxy_port <= 65535):
        raise ValueError(f"Invalid proxy port: {args.proxy_port}. Must be 1-65535")

    # Validate time window
    if args.window_ms < 0:
        raise ValueError(f"Invalid time window: {args.window_ms}. Must be >= 0")

    # Validate confidence threshold
    if not (0.0 <= args.min_confidence <= 1.0):
        raise ValueError(
            f"Invalid min confidence: {args.min_confidence}. Must be 0.0-1.0"
        )


def show_welcome(url: str, args: argparse.Namespace) -> None:
    """Display welcome banner with session information.

    Args:
        url: Target URL
        args: Command-line arguments
    """
    console.print("\n")
    panel = Panel(
        f"[bold cyan]TraceTap Recording Session[/bold cyan]\n\n"
        f"[bold]Target URL:[/bold] {url}\n"
        f"[bold]Session Name:[/bold] {args.name or 'auto-generated'}\n"
        f"[bold]Output Directory:[/bold] {args.output}\n"
        f"[bold]Headless Mode:[/bold] {args.headless}\n"
        f"[bold]Proxy Port:[/bold] {args.proxy_port}\n"
        f"[bold]Correlation Window:[/bold] {args.window_ms}ms\n"
        f"[bold]Min Confidence:[/bold] {args.min_confidence}\n\n"
        f"[dim]Browser will open. Interact with the application, then press ENTER to stop.[/dim]",
        title="🎬 Recording Configuration",
        border_style="cyan",
    )
    console.print(panel)
    console.print("\n")


async def record_session(url: str, args: argparse.Namespace) -> Optional[SessionResult]:
    """Execute the recording workflow.

    Args:
        url: Target URL to record
        args: Command-line arguments

    Returns:
        Session result if successful, None otherwise
    """
    try:
        # Create recorder options
        recorder_options = RecorderOptions(
            headless=args.headless,
            screenshots=not args.no_screenshots,
            snapshots=not args.no_snapshots,
        )

        # Create recording session
        session = RecordingSession(
            session_name=args.name or f"session-{Path(args.output).name}",
            output_dir=args.output,
            recorder_options=recorder_options,
            proxy_port=args.proxy_port,
        )

        console.print("[bold green]Starting recording session...[/bold green]\n")

        # Start recording (session manages proxy internally)
        metadata = await session.start(url)
        console.print(
            f"[green]✓ Recording started[/green]\n"
            f"  Session ID: {metadata.session_id}\n"
            f"  Browser opened at: {url}\n"
        )

        console.print(
            "[bold yellow]Interact with the application in the browser.[/bold yellow]"
        )
        console.print(
            "[bold yellow]Press ENTER in this terminal when you're done...[/bold yellow]\n"
        )

        # Wait for user to complete interactions
        await session.recorder.wait_for_user_completion()

        # Stop recording
        console.print("\n[bold cyan]Stopping recording...[/bold cyan]\n")
        metadata = await session.stop()

        console.print(
            f"[green]✓ Recording stopped[/green]\n"
            f"  Duration: {metadata.duration:.1f}s\n"
            f"  Trace file: {metadata.trace_file}\n"
        )

        # Analyze (parse and correlate)
        console.print("[bold cyan]Analyzing session...[/bold cyan]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Parsing trace file...", total=None)

            correlation_options = CorrelationOptions(
                window_ms=args.window_ms,
                min_confidence=args.min_confidence,
            )

            # Note: network_traffic_path would be provided if mitmproxy integration is active
            # For now, we parse the trace file only
            result = await session.analyze(
                network_traffic_path=None,  # TODO: Add mitmproxy integration
                correlation_options=correlation_options,
            )

            progress.update(task, completed=True, description="Analysis complete!")

        console.print("[green]✓ Analysis complete[/green]\n")

        # Display results
        if result.parse_result:
            console.print("[bold cyan]📊 Parse Results:[/bold cyan]")
            console.print(
                f"   UI Events: {result.parse_result.stats.get('total_events', 0)}"
            )
            console.print(
                f"   Event Types: {', '.join(result.parse_result.stats.get('event_types', {}).keys())}"
            )
            console.print()

        if result.correlation_result:
            # Display correlation statistics
            session.correlator.print_summary(result.correlation_result)
            console.print()

            # Display correlation timeline
            session.correlator.print_timeline(result.correlation_result, limit=10)
            console.print()

        # Save results
        console.print("[bold cyan]Saving results...[/bold cyan]")
        session.save_results(result)

        console.print(
            f"[bold green]✓ Session saved successfully![/bold green]\n"
            f"   Location: {metadata.output_dir}\n"
            f"   Metadata: {metadata.output_dir / 'metadata.json'}\n"
        )

        return result

    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠ Recording cancelled by user[/yellow]\n")
        return None

    except Exception as e:
        console.print(f"\n[bold red]✗ Recording failed: {e}[/bold red]\n")
        logger.exception("Recording error details:")
        return None


def show_next_steps(result: SessionResult) -> None:
    """Display next steps and suggestions.

    Args:
        result: Session result with metadata
    """
    console.print("\n")
    panel = Panel(
        f"[bold white]What you can do now:[/bold white]\n\n"
        f"1. Generate Playwright tests from this session:\n"
        f"   [cyan]tracetap-generate {result.metadata.output_dir}[/cyan]\n\n"
        f"2. Replay the trace file in Playwright:\n"
        f"   [cyan]playwright show-trace {result.metadata.trace_file}[/cyan]\n\n"
        f"3. Analyze correlations in detail:\n"
        f"   [cyan]cat {result.metadata.output_dir / 'correlation.json'}[/cyan]\n\n"
        f"[bold]Learn more:[/bold] https://github.com/VassilisSoum/tracetap",
        title="🎯 Next Steps",
        border_style="green",
    )
    console.print(panel)
    console.print("\n")


async def main_async() -> int:
    """Async main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Parse arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(verbose=args.verbose)

    try:
        # Validate arguments
        validate_arguments(args)

        # Show welcome
        show_welcome(args.url, args)

        # Record session
        result = await record_session(args.url, args)

        if result is None:
            return 1

        # Show next steps
        show_next_steps(result)

        return 0

    except ValueError as e:
        console.print(f"[bold red]Error: {e}[/bold red]\n")
        return 1

    except Exception as e:
        console.print(f"[bold red]Unexpected error: {e}[/bold red]\n")
        logger.exception("Error details:")
        return 1


def main() -> None:
    """Synchronous main entry point for CLI command."""
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
