"""
tracetap proxy - Run standalone HTTP/HTTPS proxy for API traffic capture.

Uses mitmproxy to capture traffic without opening a browser.
Useful for API-only testing or when configuring an external client.
"""

import logging
import sys

import click
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


@click.command()
@click.option("-l", "--listen", default=8080, type=int, help="Proxy listen port")
@click.option("--raw-log", default=None, help="Path to write raw JSON log of all requests")
@click.option("--filter", "host_filter", default=None,
              help="Only capture traffic to this host (e.g. localhost:3000)")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def proxy(listen, raw_log, host_filter, verbose):
    """Run a standalone HTTP/HTTPS proxy for API traffic capture.

    Starts mitmproxy on the specified port. Configure your application
    or browser to use this proxy, then all HTTP/HTTPS traffic will be
    captured and logged.

    \b
    Examples:
        tracetap proxy
        tracetap proxy --listen 9090 --raw-log api-traffic.json
        tracetap proxy --filter localhost:3000 --raw-log api.json
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    try:
        from tracetap.capture.tracetap_addon import TraceTapAddon
        from tracetap.capture.tracetap_main import run_proxy
    except ImportError as e:
        console.print(f"[red]Failed to import proxy modules: {e}[/red]")
        console.print("Ensure mitmproxy is installed: pip install mitmproxy")
        sys.exit(1)

    console.print(f"\nStarting proxy on port [bold]{listen}[/bold]")
    if raw_log:
        console.print(f"Logging to: [bold]{raw_log}[/bold]")
    if host_filter:
        console.print(f"Filtering: [bold]{host_filter}[/bold]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

    try:
        run_proxy(
            listen_port=listen,
            raw_log_file=raw_log,
            host_filter=host_filter,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Proxy stopped.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Proxy error: {e}[/red]")
        logger.exception("Proxy error:")
        sys.exit(1)
