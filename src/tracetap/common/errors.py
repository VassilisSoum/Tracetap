"""Enhanced error handling for TraceTap CLI.

Provides clear, actionable error messages for common failure scenarios.
"""

import sys
from pathlib import Path
from typing import Optional


class TraceTapError(Exception):
    """Base exception with enhanced error messages."""

    def __init__(
        self,
        message: str,
        suggestion: Optional[str] = None,
        docs_link: Optional[str] = None,
    ):
        self.message = message
        self.suggestion = suggestion
        self.docs_link = docs_link
        super().__init__(message)

    def print_error(self):
        """Print formatted error message with suggestions."""
        print(f"\n❌ Error: {self.message}\n", file=sys.stderr)

        if self.suggestion:
            print(f"💡 Suggestion: {self.suggestion}\n", file=sys.stderr)

        if self.docs_link:
            print(f"📖 Documentation: {self.docs_link}\n", file=sys.stderr)


class APIKeyMissingError(TraceTapError):
    """Raised when ANTHROPIC_API_KEY is not set."""

    def __init__(self):
        super().__init__(
            message="ANTHROPIC_API_KEY environment variable is not set",
            suggestion=(
                "Set your API key in one of these ways:\n"
                "   1. Export environment variable:\n"
                "      export ANTHROPIC_API_KEY='sk-ant-your-key-here'\n"
                "   2. Add to ~/.bashrc or ~/.zshrc:\n"
                "      echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> ~/.bashrc\n"
                "   3. Use --api-key flag:\n"
                "      tracetap-generate-tests --api-key sk-ant-..."
            ),
            docs_link="https://docs.anthropic.com/claude/reference/getting-started-with-the-api",
        )


class InvalidSessionError(TraceTapError):
    """Raised when session directory is invalid."""

    def __init__(self, session_path: str, reason: str):
        super().__init__(
            message=f"Invalid session directory: {session_path}",
            suggestion=(
                f"Reason: {reason}\n\n"
                "A valid session directory must contain:\n"
                "   • metadata.json - Session metadata\n"
                "   • correlation.json - Correlated events\n"
                "   • trace.zip - Playwright trace\n"
                "   • traffic.json - Network captures\n\n"
                "To create a new session:\n"
                "   tracetap-record https://your-site.com"
            ),
        )


class CorruptFileError(TraceTapError):
    """Raised when a required file is corrupt."""

    def __init__(self, file_path: str, error_detail: str):
        super().__init__(
            message=f"Corrupt or invalid file: {file_path}",
            suggestion=(
                f"File error: {error_detail}\n\n"
                "Possible fixes:\n"
                "   1. Re-record the session if the file is damaged\n"
                "   2. Check file permissions\n"
                "   3. Verify the session completed successfully\n\n"
                "To re-record:\n"
                "   tracetap-record https://your-site.com"
            ),
        )


class PortConflictError(TraceTapError):
    """Raised when mitmproxy port is already in use."""

    def __init__(self, port: int):
        super().__init__(
            message=f"Port {port} is already in use",
            suggestion=(
                f"Another process is using port {port} (default mitmproxy port).\n\n"
                "To fix:\n"
                "   1. Find and stop the process:\n"
                f"      lsof -ti:{port} | xargs kill\n"
                "   2. Or use a different port:\n"
                "      tracetap-record --proxy-port 8889 https://your-site.com"
            ),
        )


class CertificateError(TraceTapError):
    """Raised when HTTPS certificate setup fails."""

    def __init__(self):
        super().__init__(
            message="HTTPS certificate not installed or invalid",
            suggestion=(
                "TraceTap requires mitmproxy certificate for HTTPS interception.\n\n"
                "To install:\n"
                "   1. Run: tracetap-quickstart\n"
                "   2. Or manually:\n"
                "      • Visit http://mitm.it in browser during recording\n"
                "      • Download certificate for your OS\n"
                "      • Install and trust the certificate\n\n"
                "Note: You only need to do this once."
            ),
            docs_link="https://docs.mitmproxy.org/stable/concepts-certificates/",
        )


class BrowserLaunchError(TraceTapError):
    """Raised when Playwright browser fails to launch."""

    def __init__(self, browser_type: str, error_detail: str):
        super().__init__(
            message=f"Failed to launch {browser_type} browser",
            suggestion=(
                f"Browser error: {error_detail}\n\n"
                "To fix:\n"
                "   1. Install Playwright browsers:\n"
                "      playwright install chromium\n"
                "   2. Check system dependencies:\n"
                "      playwright install-deps\n"
                "   3. Try a different browser:\n"
                "      tracetap-record --browser firefox https://your-site.com"
            ),
            docs_link="https://playwright.dev/python/docs/browsers",
        )


class NetworkError(TraceTapError):
    """Raised when network request fails."""

    def __init__(self, url: str, error_detail: str):
        super().__init__(
            message=f"Network request failed: {url}",
            suggestion=(
                f"Error: {error_detail}\n\n"
                "Possible causes:\n"
                "   1. No internet connection\n"
                "   2. API service is down\n"
                "   3. Firewall blocking requests\n"
                "   4. Invalid API endpoint\n\n"
                "To diagnose:\n"
                "   • Check your internet connection\n"
                "   • Try accessing the URL in a browser\n"
                "   • Check API service status"
            ),
        )


def handle_common_errors(func):
    """Decorator to catch and format common errors."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TraceTapError as e:
            e.print_error()
            sys.exit(1)
        except FileNotFoundError as e:
            error = InvalidSessionError(
                str(e.filename) if hasattr(e, "filename") else "unknown",
                "File not found",
            )
            error.print_error()
            sys.exit(1)
        except PermissionError as e:
            error = TraceTapError(
                message=f"Permission denied: {e.filename if hasattr(e, 'filename') else 'unknown'}",
                suggestion=(
                    "Check file/directory permissions:\n"
                    f"   chmod -R u+rw {Path(e.filename).parent if hasattr(e, 'filename') else '.'}"
                ),
            )
            error.print_error()
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n⚠️  Operation cancelled by user", file=sys.stderr)
            sys.exit(130)

    return wrapper
