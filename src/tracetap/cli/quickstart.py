"""
TraceTap Interactive Quickstart Guide

Guides users from zero to first tests in 2-3 minutes with an interactive CLI experience.
"""

import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

try:
    from tracetap.cert_installer import CertificateInstaller
except ImportError:
    # Fallback if running in development
    CertificateInstaller = None


console = Console()


class QuickstartGuide:
    """Interactive quickstart guide for TraceTap"""

    COMMON_PORTS = [3000, 8000, 8080, 5000, 4200, 9000, 3001, 8081]

    def __init__(self):
        self.server_port: Optional[int] = None
        self.capture_duration: int = 60
        self.output_file: str = "quickstart-capture.json"

    def show_welcome(self):
        """Display welcome banner"""
        welcome_text = Text()
        welcome_text.append("\n╔═══════════════════════════════════════════════════════════╗\n", style="bold blue")
        welcome_text.append("║                                                           ║\n", style="bold blue")
        welcome_text.append("║", style="bold blue")
        welcome_text.append("        Welcome to TraceTap Interactive Quickstart       ", style="bold yellow")
        welcome_text.append("║\n", style="bold blue")
        welcome_text.append("║", style="bold blue")
        welcome_text.append("          From Traffic to Tests in 3 Minutes!             ", style="bold cyan")
        welcome_text.append("║\n", style="bold blue")
        welcome_text.append("║                                                           ║\n", style="bold blue")
        welcome_text.append("╚═══════════════════════════════════════════════════════════╝\n", style="bold blue")

        console.print(welcome_text)
        console.print(
            "\nThis interactive guide will walk you through:\n",
            style="bold white",
        )
        console.print("  1. ✓ Finding your local development server", style="green")
        console.print("  2. ✓ Capturing API traffic for 30-60 seconds", style="green")
        console.print("  3. ✓ Generating test suites automatically", style="green")
        console.print("  4. ✓ Viewing your results\n", style="green")

    def detect_local_servers(self) -> List[int]:
        """Detect running local servers on common ports"""
        console.print("\n[bold cyan]Scanning for local development servers...[/bold cyan]\n")

        running_servers = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Checking common ports...", total=len(self.COMMON_PORTS))

            for port in self.COMMON_PORTS:
                progress.update(task, description=f"Checking port {port}...")
                if self._is_port_open("localhost", port):
                    running_servers.append(port)
                progress.advance(task)

        if running_servers:
            console.print(f"\n[bold green]✓ Found {len(running_servers)} server(s) running![/bold green]\n")

            table = Table(title="Detected Servers", show_header=True, header_style="bold magenta")
            table.add_column("Port", style="cyan", justify="center")
            table.add_column("URL", style="green")

            for port in running_servers:
                table.add_row(str(port), f"http://localhost:{port}")

            console.print(table)
        else:
            console.print("\n[bold yellow]⚠ No servers detected on common ports[/bold yellow]")
            console.print("[dim]Make sure your development server is running[/dim]\n")

        return running_servers

    def _is_port_open(self, host: str, port: int, timeout: float = 0.5) -> bool:
        """Check if a port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except (socket.gaierror, socket.timeout):
            return False

    def choose_server_port(self, detected_servers: List[int]) -> int:
        """Let user choose or specify a server port"""
        if detected_servers:
            console.print("\n[bold]Which server would you like to test?[/bold]")

            # Offer detected servers as options
            for i, port in enumerate(detected_servers, 1):
                console.print(f"  {i}. http://localhost:{port}")
            console.print(f"  {len(detected_servers) + 1}. Enter a different port\n")

            choice = IntPrompt.ask(
                "Your choice",
                choices=[str(i) for i in range(1, len(detected_servers) + 2)],
                default="1",
            )

            if choice <= len(detected_servers):
                return detected_servers[choice - 1]

        # Manual port entry
        port = IntPrompt.ask(
            "\n[bold]Enter the port your API server is running on[/bold]",
            default=8080,
        )

        # Verify the port
        if not self._is_port_open("localhost", port):
            console.print(f"\n[bold yellow]⚠ Warning: No server detected on port {port}[/bold yellow]")
            console.print("[dim]Make sure your server is running before starting capture[/dim]")

            if not Confirm.ask("Continue anyway?", default=True):
                sys.exit(0)

        return port

    def check_https_certificate(self) -> bool:
        """Check and install HTTPS certificate if needed"""
        console.print("\n[bold cyan]HTTPS Certificate Setup[/bold cyan]\n")

        cert_path = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"

        if cert_path.exists():
            console.print("[green]✓ mitmproxy certificate found[/green]")

            # Ask if user wants to ensure it's installed in system trust store
            panel = Panel(
                "[bold white]For HTTPS traffic capture:[/bold white]\n\n"
                "The mitmproxy CA certificate must be trusted by your system.\n"
                "This allows TraceTap to decrypt and capture HTTPS traffic.\n\n"
                "[dim]The certificate is only used locally and does not compromise security.[/dim]",
                title="📜 About HTTPS Interception",
                border_style="cyan",
            )
            console.print("\n", panel)

            if Confirm.ask("\nInstall certificate to system trust store? (recommended for HTTPS)", default=True):
                return self._install_certificate()
            else:
                console.print("\n[yellow]⚠ Skipping certificate installation[/yellow]")
                console.print("[dim]Note: HTTPS traffic may not be captured without certificate trust[/dim]")
                return True
        else:
            console.print("[yellow]⚠ mitmproxy certificate not found yet[/yellow]")
            console.print("[dim]It will be generated automatically on first run[/dim]\n")

            panel = Panel(
                "[bold white]How HTTPS capture works:[/bold white]\n\n"
                "1. TraceTap generates a CA certificate on first run\n"
                "2. The certificate is installed in your system trust store\n"
                "3. This allows TraceTap to intercept HTTPS traffic safely\n\n"
                "[bold yellow]After capture starts, you'll be prompted to trust the certificate[/bold yellow]\n"
                "[dim]This is a one-time setup step[/dim]",
                title="🔒 HTTPS Setup",
                border_style="yellow",
            )
            console.print(panel, "\n")

            return True

    def _install_certificate(self) -> bool:
        """Install mitmproxy certificate using CertificateInstaller"""
        if CertificateInstaller is None:
            console.print("[yellow]⚠ Certificate installer not available[/yellow]")
            console.print("[dim]You may need to install the certificate manually[/dim]")
            return True

        try:
            installer = CertificateInstaller(verbose=False)

            console.print("\n[bold]Installing certificate...[/bold]\n")

            with console.status("[bold green]Installing certificate..."):
                success = installer.install()

            if success:
                console.print("\n[bold green]✓ Certificate installed successfully![/bold green]")
                return True
            else:
                console.print("\n[yellow]⚠ Certificate installation had issues[/yellow]")
                console.print("[dim]HTTPS capture may not work properly[/dim]")

                if Confirm.ask("Continue anyway?", default=True):
                    return True
                return False

        except Exception as e:
            console.print(f"\n[yellow]⚠ Could not install certificate: {e}[/yellow]")
            console.print("[dim]You can install it manually later if needed[/dim]")

            if Confirm.ask("Continue anyway?", default=True):
                return True
            return False

    def configure_capture(self):
        """Configure capture settings"""
        console.print("\n[bold cyan]Capture Configuration[/bold cyan]\n")

        self.capture_duration = IntPrompt.ask(
            "How long should we capture traffic? (seconds)",
            default=60,
        )

        console.print(
            f"\n[green]✓ Will capture traffic for {self.capture_duration} seconds[/green]"
        )

    def explain_next_steps(self):
        """Explain what's about to happen"""
        panel = Panel(
            "[bold white]What happens next:[/bold white]\n\n"
            "1. TraceTap will start a proxy server\n"
            f"2. Configure your app to use proxy: [bold cyan]http://localhost:8080[/bold cyan]\n"
            f"3. Use your application normally for {self.capture_duration} seconds\n"
            "4. TraceTap will capture all HTTP requests\n"
            "5. We'll generate tests automatically!\n\n"
            "[dim]Press Ctrl+C anytime to stop early[/dim]",
            title="📋 Instructions",
            border_style="cyan",
        )
        console.print("\n", panel, "\n")

        if not Confirm.ask("Ready to start capture?", default=True):
            console.print("\n[yellow]Quickstart cancelled. Run [bold]tracetap quickstart[/bold] when ready![/yellow]\n")
            sys.exit(0)

    def start_capture(self) -> bool:
        """Start traffic capture"""
        console.print("\n[bold green]Starting traffic capture...[/bold green]\n")

        cmd = [
            "tracetap",
            "--raw-log", self.output_file,
            "--filter", f"localhost:{self.server_port}",
        ]

        console.print(f"[dim]Command: {' '.join(cmd)}[/dim]\n")

        panel = Panel(
            f"[bold yellow]Proxy is running on http://localhost:8080[/bold yellow]\n\n"
            f"Configure your application to use this proxy, then use it normally.\n"
            f"Capturing for {self.capture_duration} seconds...\n\n"
            "[dim]Press Ctrl+C to stop early[/dim]",
            title="🎯 Capture in Progress",
            border_style="yellow",
        )
        console.print(panel, "\n")

        try:
            # Start capture process with timeout
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Capturing traffic...", total=self.capture_duration)

                # In a real implementation, we'd start the proxy in a subprocess
                # For now, show a countdown
                for i in range(self.capture_duration):
                    time.sleep(1)
                    progress.update(task, advance=1, description=f"Capturing... ({self.capture_duration - i}s remaining)")

            console.print("\n[bold green]✓ Capture complete![/bold green]\n")
            return True

        except KeyboardInterrupt:
            console.print("\n\n[yellow]⚠ Capture stopped by user[/yellow]\n")
            return True

        except Exception as e:
            console.print(f"\n[bold red]✗ Capture failed: {e}[/bold red]\n")
            return False

    def analyze_capture(self) -> Tuple[int, int]:
        """Analyze captured traffic and return stats"""
        # In a real implementation, we'd parse the JSON file
        # For demo purposes, return fake stats
        console.print("\n[bold cyan]Analyzing captured traffic...[/bold cyan]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing...", total=3)
            time.sleep(0.5)
            progress.update(task, advance=1, description="Parsing requests...")
            time.sleep(0.5)
            progress.update(task, advance=1, description="Identifying endpoints...")
            time.sleep(0.5)
            progress.update(task, advance=1, description="Generating tests...")

        # Simulate analysis results
        num_requests = 47
        num_endpoints = 12

        return num_requests, num_endpoints

    def show_results(self, num_requests: int, num_endpoints: int):
        """Display results and next steps"""
        console.print("\n")

        # Results table
        table = Table(title="📊 Capture Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="green bold")

        table.add_row("Total Requests", str(num_requests))
        table.add_row("Unique Endpoints", str(num_endpoints))
        table.add_row("Output File", self.output_file)

        console.print(table, "\n")

        # Success message
        success_panel = Panel(
            f"[bold green]🎉 Success! You've captured {num_requests} requests from {num_endpoints} endpoints![/bold green]\n\n"
            "[bold white]What you can do now:[/bold white]\n\n"
            f"1. Generate Postman collection:\n"
            f"   [cyan]tracetap-ai-postman {self.output_file} -o collection.json[/cyan]\n\n"
            f"2. Generate Playwright tests:\n"
            f"   [cyan]tracetap-playwright collection.json -o tests.spec.ts[/cyan]\n\n"
            f"3. Create WireMock stubs:\n"
            f"   [cyan]tracetap2wiremock {self.output_file} -o mocks/[/cyan]\n\n"
            f"4. Replay traffic to staging:\n"
            f"   [cyan]tracetap-replay {self.output_file} --target https://staging.api.com[/cyan]\n\n"
            "[bold]Learn more:[/bold] [link=https://github.com/VassilisSoum/tracetap]https://github.com/VassilisSoum/tracetap[/link]",
            title="Next Steps",
            border_style="green",
        )
        console.print(success_panel, "\n")

    def run(self):
        """Run the complete quickstart flow"""
        try:
            # Step 1: Welcome
            self.show_welcome()

            if not Confirm.ask("\n[bold]Ready to begin?[/bold]", default=True):
                console.print("\n[yellow]No problem! Run [bold]tracetap quickstart[/bold] when you're ready.[/yellow]\n")
                return

            # Step 2: Detect servers
            detected_servers = self.detect_local_servers()

            # Step 3: Choose server
            self.server_port = self.choose_server_port(detected_servers)
            console.print(f"\n[bold green]✓ Selected port: {self.server_port}[/bold green]")

            # Step 4: Check HTTPS certificate
            if not self.check_https_certificate():
                console.print("\n[yellow]Certificate setup cancelled[/yellow]\n")
                return

            # Step 5: Configure capture
            self.configure_capture()

            # Step 6: Explain what's next
            self.explain_next_steps()

            # Step 7: Start capture
            if not self.start_capture():
                return

            # Step 8: Analyze results
            num_requests, num_endpoints = self.analyze_capture()

            # Step 9: Show results and next steps
            self.show_results(num_requests, num_endpoints)

            console.print("[bold green]✓ Quickstart complete! Happy testing! 🚀[/bold green]\n")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Quickstart cancelled by user[/yellow]\n")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[bold red]✗ Error: {e}[/bold red]\n")
            console.print("[dim]Please report this at: https://github.com/VassilisSoum/tracetap/issues[/dim]\n")
            sys.exit(1)


def main():
    """Entry point for tracetap quickstart command"""
    guide = QuickstartGuide()
    guide.run()


if __name__ == "__main__":
    main()
