"""
tracetap doctor - Check prerequisites and system configuration.

Verifies that all dependencies are installed, configured, and working:
- Python version
- mitmproxy
- Playwright + browsers
- HTTPS certificate
- ANTHROPIC_API_KEY
- npm/npx (for running generated tests)
"""

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


class Check:
    """Result of a single prerequisite check."""
    def __init__(self, name, status, detail="", fix=""):
        self.name = name
        self.status = status  # 'ok', 'warn', 'fail'
        self.detail = detail
        self.fix = fix


def check_python_version() -> Check:
    v = sys.version_info
    version_str = f"{v.major}.{v.minor}.{v.micro}"
    if v >= (3, 10):
        return Check("Python", "ok", f"v{version_str}")
    return Check("Python", "fail", f"v{version_str} (need >=3.10)",
                 "Install Python 3.10+: https://python.org/downloads")


def check_mitmproxy() -> Check:
    try:
        result = subprocess.run(
            ["mitmdump", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            return Check("mitmproxy", "ok", version)
        return Check("mitmproxy", "fail", "installed but errored",
                     "Reinstall: pip install mitmproxy>=10.0.0")
    except FileNotFoundError:
        return Check("mitmproxy", "fail", "not found",
                     "Install: pip install mitmproxy>=10.0.0")
    except Exception as e:
        return Check("mitmproxy", "fail", str(e))


def check_playwright() -> Check:
    try:
        import playwright
        version = getattr(playwright, "__version__", "unknown")
        return Check("Playwright (pip)", "ok", f"v{version}")
    except ImportError:
        return Check("Playwright (pip)", "fail", "not installed",
                     "Install: pip install playwright")


def check_playwright_browsers() -> Check:
    try:
        result = subprocess.run(
            ["playwright", "install", "--dry-run"],
            capture_output=True, text=True, timeout=15
        )
        # Check if chromium is installed by trying to find it
        from pathlib import Path
        import json

        # Playwright stores browsers in a known location
        browsers_path = Path.home() / ".cache" / "ms-playwright"
        if not browsers_path.exists():
            browsers_path = Path.home() / "Library" / "Caches" / "ms-playwright"

        if browsers_path.exists():
            chromium_dirs = list(browsers_path.glob("chromium-*"))
            if chromium_dirs:
                return Check("Playwright browsers", "ok", f"chromium found in {browsers_path}")

        return Check("Playwright browsers", "warn", "chromium may not be installed",
                     "Install: playwright install chromium")
    except FileNotFoundError:
        return Check("Playwright browsers", "warn", "playwright CLI not in PATH",
                     "Install: playwright install chromium")
    except Exception as e:
        return Check("Playwright browsers", "warn", str(e),
                     "Install: playwright install chromium")


def check_mitmproxy_cert() -> Check:
    cert_path = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"
    if cert_path.exists():
        return Check("mitmproxy CA cert", "ok", str(cert_path))
    return Check("mitmproxy CA cert", "warn",
                 "not found (generated on first proxy run)",
                 "Run: mitmdump --set listen_port=0 --set connection_strategy=lazy -q &; sleep 2; kill %1")


def check_cert_trusted() -> Check:
    """Check if mitmproxy cert is in system trust store."""
    cert_path = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"
    if not cert_path.exists():
        return Check("Cert trusted", "warn", "cert not yet generated")

    # Try to verify using openssl
    try:
        result = subprocess.run(
            ["openssl", "verify", str(cert_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return Check("Cert trusted", "ok", "verified by openssl")
        # Self-signed certs fail openssl verify, which is expected
        # Check if it's in system store instead
        return Check("Cert trusted", "warn",
                     "cert exists but may not be in system trust store",
                     "Install cert: tracetap doctor will add install instructions")
    except FileNotFoundError:
        return Check("Cert trusted", "warn", "openssl not found, cannot verify")
    except Exception:
        return Check("Cert trusted", "warn", "could not verify")


def check_anthropic_key() -> Check:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return Check("ANTHROPIC_API_KEY", "fail", "not set",
                     "Set: export ANTHROPIC_API_KEY=sk-ant-...")
    if not key.startswith("sk-ant-"):
        return Check("ANTHROPIC_API_KEY", "warn", "set but format looks wrong (expected sk-ant-...)")

    # Quick API validation
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Reply with just 'ok'"}],
        )
        return Check("ANTHROPIC_API_KEY", "ok", "set and verified (API call succeeded)")
    except ImportError:
        return Check("ANTHROPIC_API_KEY", "warn", "set but anthropic package not installed")
    except Exception as e:
        err = str(e)
        if "api_key" in err.lower() or "auth" in err.lower():
            return Check("ANTHROPIC_API_KEY", "fail", "set but invalid",
                         "Check your key at: https://console.anthropic.com/account/keys")
        return Check("ANTHROPIC_API_KEY", "warn", f"set but validation failed: {err[:80]}")


def check_proxy_port(port=8080) -> Check:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        if result == 0:
            return Check(f"Port {port}", "warn", "already in use",
                         f"Free the port or use --proxy-port to pick another")
        return Check(f"Port {port}", "ok", "available")
    except Exception:
        return Check(f"Port {port}", "ok", "available (check inconclusive)")


def check_npm() -> Check:
    npx = shutil.which("npx")
    if npx:
        try:
            result = subprocess.run(["npx", "--version"], capture_output=True, text=True, timeout=10)
            return Check("npx", "ok", f"v{result.stdout.strip()}")
        except Exception:
            return Check("npx", "ok", "found in PATH")
    return Check("npx", "warn", "not found (needed to run generated Playwright tests)",
                 "Install Node.js: https://nodejs.org")


@click.command()
@click.option("--no-api-check", is_flag=True, help="Skip API key validation (avoids API call)")
def doctor(no_api_check):
    """Check prerequisites and system configuration.

    Verifies all dependencies needed for TraceTap to work:
    Python, mitmproxy, Playwright, browsers, certificates, API key, npm.

    \b
    Examples:
        tracetap doctor
        tracetap doctor --no-api-check
    """
    console.print("\n[bold]TraceTap Doctor[/bold] - checking prerequisites...\n")

    checks = [
        check_python_version(),
        check_mitmproxy(),
        check_playwright(),
        check_playwright_browsers(),
        check_mitmproxy_cert(),
        check_cert_trusted(),
        check_proxy_port(),
        check_npm(),
    ]

    if not no_api_check:
        checks.append(check_anthropic_key())
    else:
        checks.append(Check("ANTHROPIC_API_KEY", "warn", "skipped (--no-api-check)"))

    # Display results
    table = Table(show_header=True, header_style="bold")
    table.add_column("Check", style="white", min_width=22)
    table.add_column("Status", justify="center", min_width=6)
    table.add_column("Details", style="dim")

    ok_count = 0
    warn_count = 0
    fail_count = 0

    for check in checks:
        if check.status == "ok":
            status = "[green]OK[/green]"
            ok_count += 1
        elif check.status == "warn":
            status = "[yellow]WARN[/yellow]"
            warn_count += 1
        else:
            status = "[red]FAIL[/red]"
            fail_count += 1

        table.add_row(check.name, status, check.detail)

    console.print(table)

    # Show fixes for failures and warnings
    fixes_needed = [c for c in checks if c.status in ("fail", "warn") and c.fix]
    if fixes_needed:
        console.print(f"\n[bold]Fixes needed:[/bold]")
        for check in fixes_needed:
            icon = "[red]x[/red]" if check.status == "fail" else "[yellow]![/yellow]"
            console.print(f"  {icon} {check.name}: {check.fix}")

    # Summary
    console.print()
    if fail_count == 0 and warn_count == 0:
        console.print("[bold green]All checks passed. TraceTap is ready to use.[/bold green]\n")
    elif fail_count == 0:
        console.print(f"[bold yellow]{warn_count} warning(s), but TraceTap should work.[/bold yellow]\n")
    else:
        console.print(f"[bold red]{fail_count} check(s) failed. Fix these before using TraceTap.[/bold red]\n")
        sys.exit(1)
