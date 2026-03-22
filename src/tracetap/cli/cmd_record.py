"""
tracetap record - Record browser interactions and network traffic.

Opens a browser, lets user interact manually, captures clicks/typing/navigation
and API calls, correlates them, saves session data for test generation.
"""

import asyncio
import logging
import sys

import click
from rich.console import Console
from rich.panel import Panel

console = Console()
logger = logging.getLogger(__name__)


@click.command()
@click.argument("url")
@click.option("-n", "--name", default=None, help="Session name (default: auto-generated)")
@click.option("-o", "--output", default="./recordings", help="Output directory for session files")
@click.option("--headless", is_flag=True, default=False, help="Run browser in headless mode")
@click.option("--proxy", default=None, help="Optional proxy URL (e.g. http://localhost:8888)")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Enable debug logging")
def record(url, name, output, headless, proxy, verbose):
    """Record browser interactions at URL.

    Opens a headed Chromium browser. Interact manually - clicks, typing,
    navigation are all captured along with network traffic.

    Press ENTER in the terminal to stop recording.

    \b
    Examples:
        tracetap record https://example.com
        tracetap record https://myapp.com -n login-flow -o ./sessions
        tracetap record https://myapp.com --proxy http://localhost:8888
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    # Validate URL
    if not url.startswith(("http://", "https://")):
        raise click.BadParameter(
            f"URL must start with http:// or https:// (got: {url})",
            param_hint="'URL'",
        )

    asyncio.run(_record_async(url, name, output, headless, proxy))


async def _record_async(url, name, output, headless, proxy):
    """Async recording workflow."""
    from tracetap.record.session import RecordingSession
    from tracetap.record.interaction_recorder import RecorderOptions

    session_name = name or f"session"

    # Show config
    console.print()
    console.print(Panel(
        f"[bold]URL:[/bold] {url}\n"
        f"[bold]Session:[/bold] {session_name}\n"
        f"[bold]Output:[/bold] {output}\n"
        f"[bold]Headless:[/bold] {headless}\n"
        + (f"[bold]Proxy:[/bold] {proxy}\n" if proxy else "")
        + "\n[dim]Browser will open. Interact with the app, then press ENTER to stop.[/dim]",
        title="TraceTap Recording",
        border_style="cyan",
    ))

    recorder_options = RecorderOptions(headless=headless)

    session = RecordingSession(
        session_name=session_name,
        output_dir=output,
        recorder_options=recorder_options,
        proxy=proxy,
    )

    try:
        # Start
        metadata = await session.start(url)
        console.print(f"\n[green]Recording started[/green] (session: {metadata.session_id})")
        console.print("[yellow]Press ENTER to stop recording...[/yellow]\n")

        # Wait for user
        await session.wait_for_user()

        # Stop and correlate
        console.print("\n[cyan]Stopping and analyzing...[/cyan]")
        result = await session.stop()

        # Save
        session_dir = session.save(result)

        # Summary
        ui_count = len(result.ui_events)
        net_count = len(result.network_calls)
        corr_count = (
            len(result.correlation_result.correlated_events)
            if result.correlation_result
            else 0
        )
        duration = result.metadata.duration or 0

        console.print()
        console.print(Panel(
            f"[bold]Duration:[/bold] {duration:.1f}s\n"
            f"[bold]UI events:[/bold] {ui_count}\n"
            f"[bold]Network calls:[/bold] {net_count}\n"
            f"[bold]Correlated events:[/bold] {corr_count}\n"
            f"[bold]Saved to:[/bold] {session_dir}\n\n"
            f"[bold]Next step:[/bold]\n"
            f"  tracetap generate {session_dir} -o tests/generated.spec.ts",
            title="Recording Complete",
            border_style="green",
        ))

    except KeyboardInterrupt:
        console.print("\n[yellow]Recording cancelled.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Recording failed: {e}[/red]")
        logger.exception("Recording error:")
        sys.exit(1)
