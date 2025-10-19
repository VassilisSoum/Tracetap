#!/usr/bin/env python3
"""
TraceTap - HTTP/HTTPS traffic capture proxy with Postman export
Captures all HTTP/HTTPS traffic and exports to Postman Collection v2.1

Usage:
    tracetap --listen 8080 --export output.json --session my-session

Requirements:
    pip install mitmproxy
"""

import argparse
import json
import sys
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs

from mitmproxy import http
from mitmproxy.tools import main as mitmain

# ============================================================================
# ADDON CODE
# ============================================================================
# The addon code is stored as a string and written to a temporary file.
# This is necessary because PyInstaller bundles everything into a single
# executable, so we need to extract the addon code at runtime for mitmproxy
# to load it via the -s flag.
# ============================================================================

ADDON_CODE = '''
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs
from mitmproxy import http


class TraceTapAddon:
    """
    Mitmproxy addon that captures HTTP/HTTPS traffic.

    This class is instantiated by mitmproxy and receives callbacks for
    various events in the HTTP flow lifecycle. We primarily use the
    'response' and 'done' callbacks.
    """

    def __init__(self):
        """
        Initialize addon - called when module is loaded.

        Note: Don't do heavy initialization here because mitmproxy may
        re-import this module. Use lazy initialization instead.
        """
        # Storage for captured request/response records
        self.records: List[Dict[str, Any]] = []

        # Flag to ensure we only initialize once
        self.initialized = False

        # Configuration attributes (set via environment variables)
        self.export_path = ''           # Postman collection output path
        self.raw_log_path = ''          # Raw JSON log output path
        self.session_name = 'tracetap-session'  # Session identifier
        self.quiet = False              # Suppress console output
        self.verbose = False            # Show detailed filtering info

        # Filtering configuration
        self.filter_hosts = ''          # Comma-separated host list
        self.filter_regex = ''          # Regex pattern for URL matching
        self.host_filters = []          # Parsed list of hosts
        self.regex_pattern = None       # Compiled regex pattern

    def _lazy_init(self):
        """
        Lazy initialization - reads config from environment on first use.

        This pattern is necessary because mitmproxy may re-import the addon
        module, and we want to avoid duplicate initialization. Configuration
        is passed via environment variables because they survive the re-import.
        """
        if self.initialized:
            return

        self.initialized = True

        # Read configuration from environment variables
        # These are set by the main() function before starting mitmproxy
        self.export_path = os.environ.get('TRACETAP_EXPORT_PATH', '')
        self.raw_log_path = os.environ.get('TRACETAP_RAW_LOG_PATH', '')
        self.session_name = os.environ.get('TRACETAP_SESSION', 'tracetap-session')
        self.quiet = os.environ.get('TRACETAP_QUIET', 'false') == 'true'
        self.verbose = os.environ.get('TRACETAP_VERBOSE', 'false') == 'true'

        # Read filtering configuration
        self.filter_hosts = os.environ.get('TRACETAP_FILTER_HOSTS', '')
        self.filter_regex = os.environ.get('TRACETAP_FILTER_REGEX', '')

        # Parse host filters (comma-separated list)
        self.host_filters = [h.strip() for h in self.filter_hosts.split(',') if h.strip()]

        # Compile regex pattern if provided
        self.regex_pattern = None
        if self.filter_regex:
            import re
            try:
                self.regex_pattern = re.compile(self.filter_regex)
            except re.error as e:
                print(f"Invalid regex pattern: {e}", file=sys.stderr, flush=True)

        # Display active filters to user
        if self.host_filters or self.regex_pattern:
            print(f"\\n🔍 Filtering enabled:", flush=True)
            if self.host_filters:
                print(f"   Hosts ({len(self.host_filters)}): {self.host_filters}", flush=True)
            if self.regex_pattern:
                print(f"   Regex: {self.filter_regex}", flush=True)
            print("", flush=True)
        else:
            print(f"\\n⚠️  No filters active - capturing ALL traffic", flush=True)
            print("", flush=True)

    def response(self, flow: http.HTTPFlow) -> None:
        """
        Called when a complete HTTP response is received.

        This is the main capture point. We receive the complete HTTP flow
        (request + response) and decide whether to capture it based on
        configured filters.

        Args:
            flow: The HTTP flow containing request and response data
        """
        # Ensure we're initialized before processing
        self._lazy_init()

        try:
            req = flow.request
            resp = flow.response

            # Apply filtering logic - skip if this request shouldn't be captured
            should_capture = self._should_capture(req.host, req.pretty_url)
            if not should_capture:
                if self.verbose:
                    print(f"⏭️  Skipping: {req.method} {req.pretty_url}", flush=True)
                return

            # Build a record containing all relevant data
            record = {
                "time": datetime.now().isoformat(),        # When captured
                "method": req.method,                       # GET, POST, etc.
                "url": req.pretty_url,                      # Full URL
                "host": req.host,                           # Hostname only
                "proto": f"HTTP/{req.http_version}",       # HTTP/1.1, HTTP/2, etc.
                "req_headers": dict(req.headers),           # Request headers as dict
                "req_body": self._safe_body(req.text, req.raw_content),  # Request body
                "status": resp.status_code if resp else 0,  # HTTP status code
                "resp_headers": dict(resp.headers) if resp else {},  # Response headers
                "resp_body": self._safe_body(resp.text, resp.raw_content) if resp else "",  # Response body
                "duration_ms": self._calc_duration(flow)    # Request duration
            }

            # Store the record
            self.records.append(record)

            # Log capture in verbose mode
            if self.verbose:
                print(f"📝 Recorded ({len(self.records)} total): {record['method']} {record['url']}", flush=True)

            # Print to console (unless quiet mode)
            if not self.quiet:
                status_color = self._status_color(record["status"])
                print(f"{record['method']} {record['url']} → "
                      f"{status_color}{record['status']}\\033[0m "
                      f"({record['duration_ms']} ms)", flush=True)

        except Exception as e:
            # Log errors but don't crash - keep capturing other requests
            print(f"Error recording request: {e}", file=sys.stderr, flush=True)

    def _should_capture(self, host: str, url: str) -> bool:
        """
        Determine if a request should be captured based on filters.

        Filtering logic:
        - If no filters configured: capture everything
        - If any filter matches: capture (OR logic)
        - Supports exact host matching, wildcard matching, and regex

        Args:
            host: The request hostname (e.g., "api.example.com")
            url: The full URL (e.g., "https://api.example.com/users")

        Returns:
            True if request should be captured, False otherwise
        """
        # No filters = capture everything
        if not self.host_filters and not self.regex_pattern:
            return True

        captured = False
        match_reason = ""

        # Check host filters
        if self.host_filters:
            for filter_host in self.host_filters:
                # Exact match: filter_host == host
                if filter_host == host:
                    captured = True
                    match_reason = f"exact match: {filter_host}"
                    break

                # Wildcard match: *.example.com matches api.example.com, auth.example.com, etc.
                if filter_host.startswith('*.'):
                    domain = filter_host[2:]  # Remove "*.""

                    # Match subdomains (api.example.com matches *.example.com)
                    if host.endswith('.' + domain):
                        captured = True
                        match_reason = f"wildcard match: {filter_host}"
                        break

                    # Also match the domain itself (example.com matches *.example.com)
                    if host == domain:
                        captured = True
                        match_reason = f"wildcard match: {filter_host}"
                        break

        # Check regex filter (only if not already captured)
        if not captured and self.regex_pattern:
            # Try matching against both URL and host
            if self.regex_pattern.search(url) or self.regex_pattern.search(host):
                captured = True
                match_reason = f"regex match: {self.filter_regex}"

        # Log filtering decision in verbose mode
        if self.verbose:
            if captured:
                print(f"✅ [CAPTURE] {host} ({match_reason})", flush=True)
            else:
                print(f"🚫 [FILTER]  {host}", flush=True)

        return captured

    def done(self):
        """
        Called when mitmproxy shuts down (e.g., user presses Ctrl+C).

        This is where we export all captured data to files. We handle
        both raw JSON export and Postman collection export.
        """
        # Ensure initialization happened
        self._lazy_init()

        print(f"\\n\\nShutting down... {len(self.records)} records captured", flush=True)

        # Export raw log if configured
        if self.raw_log_path and self.records:
            try:
                self._export_raw_log()
            except Exception as e:
                print(f"✗ Raw log export error: {e}", file=sys.stderr, flush=True)

        # Export Postman collection if configured
        if not self.export_path:
            if self.records:
                print(f"✓ Captured {len(self.records)} requests (Postman export disabled)", flush=True)
            return

        if not self.records:
            print(f"⚠ No requests captured, skipping Postman export", flush=True)
            return

        try:
            self._export_collection()
        except Exception as e:
            print(f"✗ Postman export error: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()

    def _export_raw_log(self):
        """
        Export raw captured data as JSON.

        The raw log contains:
        - Session metadata (name, timestamp, filters)
        - Complete list of captured requests with all data

        This format is ideal for:
        - Debugging
        - Custom processing
        - Converting to other formats (e.g., WireMock stubs)
        """
        output_path = Path(self.raw_log_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build the log data structure
        log_data = {
            "session": self.session_name,
            "captured_at": datetime.now().isoformat(),
            "total_requests": len(self.records),
            "filters": {
                "hosts": self.host_filters,
                "regex": self.filter_regex if self.filter_regex else None
            },
            "requests": self.records
        }

        # Write to file with pretty formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        # Show file size for user feedback
        file_size = output_path.stat().st_size / 1024  # Convert to KB
        print(f"✓ Exported raw log ({file_size:.1f} KB) → {self.raw_log_path}", flush=True)

    def _export_collection(self):
        """
        Export records to Postman Collection v2.1 format.

        Converts captured HTTP traffic into a Postman collection that can be
        imported into Postman for replaying requests, testing, documentation, etc.

        Postman Collection format:
        - info: Metadata about the collection
        - item: Array of request items
        """
        items = []

        for rec in self.records:
            # Convert headers to Postman format (array of {key, value} objects)
            headers = [{"key": k, "value": v} for k, v in rec["req_headers"].items()]

            # Build request body if present
            body = None
            if rec["req_body"]:
                body = {"mode": "raw", "raw": rec["req_body"]}

            # Parse URL into Postman's URL object format
            parsed = urlparse(rec["url"])

            # Extract hostname (remove port if present)
            host = parsed.netloc.split(':')[0] if ':' in parsed.netloc else parsed.netloc
            host_parts = host.split('.')  # Split into array: ["api", "example", "com"]

            # Extract path segments (filter empty strings)
            path_parts = [p for p in parsed.path.split('/') if p]

            # Parse query parameters
            query = []
            if parsed.query:
                for key, values in parse_qs(parsed.query).items():
                    for value in values:
                        query.append({"key": key, "value": value})

            # Build URL object in Postman format
            url_obj = {
                "raw": rec["url"],           # Full URL
                "protocol": parsed.scheme,    # http or https
                "host": host_parts,           # Hostname as array
                "path": path_parts,           # Path as array
            }
            if query:
                url_obj["query"] = query

            # Build the complete item
            item = {
                "name": f"{rec['method']} {rec['url']}",  # Display name in Postman
                "request": {
                    "method": rec["method"],
                    "header": headers,
                    "url": url_obj,
                }
            }
            if body:
                item["request"]["body"] = body

            items.append(item)

        # Create the collection structure
        collection = {
            "info": {
                "name": f"{self.session_name} @ {datetime.now().isoformat()}",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": items
        }

        # Write to file
        output_path = Path(self.export_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)

        print(f"✓ Exported {len(self.records)} requests → {self.export_path}", flush=True)

    def _safe_body(self, text: str, raw: bytes, max_bytes: int = 64 * 1024) -> str:
        """
        Safely extract body text, limiting size to prevent memory issues.

        Handles both text and binary data gracefully:
        - If text is available, use it (already decoded)
        - Otherwise, try to decode raw bytes as UTF-8
        - If binary/non-UTF-8, return a placeholder

        Args:
            text: Decoded text body (may be empty)
            raw: Raw bytes of body
            max_bytes: Maximum size to capture (default 64KB)

        Returns:
            Body as string, or placeholder for binary data
        """
        try:
            if text:
                # Text is already decoded, just limit size
                return text[:max_bytes]
            elif raw:
                # Try to decode raw bytes as UTF-8
                return raw[:max_bytes].decode('utf-8', errors='replace')
            return ""
        except Exception:
            # Fallback for binary data or encoding errors
            return f"[binary data: {len(raw)} bytes]" if raw else ""

    def _calc_duration(self, flow: http.HTTPFlow) -> int:
        """
        Calculate request duration in milliseconds.

        Duration is measured from when the server connection started to when
        it completed. This includes:
        - DNS resolution
        - TCP handshake
        - TLS handshake (for HTTPS)
        - Request transmission
        - Server processing
        - Response transmission

        Args:
            flow: The HTTP flow object

        Returns:
            Duration in milliseconds, or 0 if not available
        """
        try:
            # Check if we have server connection timing data
            if hasattr(flow, 'server_conn') and flow.server_conn and flow.server_conn.timestamp_end:
                # Calculate duration in seconds, then convert to milliseconds
                duration = flow.server_conn.timestamp_end - flow.server_conn.timestamp_start
                return int(duration * 1000)
        except Exception:
            # If timing data is not available, return 0
            pass
        return 0

    def _status_color(self, status: int) -> str:
        """
        Get ANSI color code for HTTP status code.

        Color coding:
        - 2xx (Success): Green
        - 3xx (Redirect): Cyan
        - 4xx (Client Error): Yellow
        - 5xx (Server Error): Red

        Args:
            status: HTTP status code (200, 404, 500, etc.)

        Returns:
            ANSI escape code for color
        """
        if 200 <= status < 300:
            return "\\033[32m"  # Green
        elif 300 <= status < 400:
            return "\\033[36m"  # Cyan
        elif 400 <= status < 500:
            return "\\033[33m"  # Yellow
        elif 500 <= status < 600:
            return "\\033[31m"  # Red
        return ""


# Module-level addon list - mitmproxy looks for this
addons = [TraceTapAddon()]
'''


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

def parse_args():
    """
    Parse command-line arguments.

    Returns:
        Namespace object with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="TraceTap - HTTP/HTTPS proxy with Postman export",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --listen 8080
  %(prog)s --listen 8080 --export captures.json
  %(prog)s --listen 8080 --export captures.json --session "API Testing"
  %(prog)s --listen 8080 --quiet

  # Export both Postman collection and raw log
  %(prog)s --listen 8080 --export api.json --raw-log raw_data.json

  # Only raw log (no Postman export)
  %(prog)s --listen 8080 --raw-log captured_traffic.json

  # Capture only specific hosts
  %(prog)s --listen 8080 --export api.json --filter-host "api.example.com"
  %(prog)s --listen 8080 --filter-host "example.com,api.github.com"
  %(prog)s --listen 8080 --filter-host "*.example.com"

  # Capture using regex
  %(prog)s --listen 8080 --filter-regex "api\..*\.com"
  %(prog)s --listen 8080 --filter-regex "/api/v[0-9]+/"

  # Combine filters (OR logic - captures if ANY filter matches)
  %(prog)s --listen 8080 --filter-host "example.com" --filter-regex ".*\.api\..*"

After starting, configure your HTTP client:
  export HTTP_PROXY=http://localhost:8080
  export HTTPS_PROXY=http://localhost:8080
  curl -k https://api.example.com

Press Ctrl+C to stop and export.
        """
    )

    parser.add_argument(
        '--listen',
        type=int,
        default=8080,
        metavar='PORT',
        help='Port to listen on (default: 8080)'
    )

    parser.add_argument(
        '--export',
        type=str,
        default='',
        metavar='PATH',
        help='Export Postman collection to this path on shutdown'
    )

    parser.add_argument(
        '--raw-log',
        type=str,
        default='',
        metavar='PATH',
        dest='raw_log',
        help='Export raw captured data (JSON) to this path on shutdown'
    )

    parser.add_argument(
        '--session',
        type=str,
        default='tracetap-session',
        metavar='NAME',
        help='Session name for exported collection (default: tracetap-session)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce logging output'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show filtered requests (verbose mode)'
    )

    parser.add_argument(
        '--filter-host',
        type=str,
        default='',
        metavar='HOSTS',
        dest='filter_host',
        help='Capture only requests to these hosts (comma-separated). Supports wildcards: example.com,*.api.com'
    )

    parser.add_argument(
        '--filter-regex',
        type=str,
        default='',
        metavar='PATTERN',
        dest='filter_regex',
        help='Capture only requests matching this regex pattern (applied to URL and host)'
    )

    return parser.parse_args()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """
    Main entry point for TraceTap.

    Flow:
    1. Parse command-line arguments
    2. Pass configuration via environment variables
    3. Write addon code to temporary file
    4. Start mitmproxy with the addon
    5. Clean up on exit
    """
    args = parse_args()

    # Pass configuration via environment variables
    # This is necessary because mitmproxy re-imports the addon module,
    # and environment variables survive that re-import
    if args.export:
        os.environ['TRACETAP_EXPORT_PATH'] = args.export
    if args.raw_log:
        os.environ['TRACETAP_RAW_LOG_PATH'] = args.raw_log
    os.environ['TRACETAP_SESSION'] = args.session
    os.environ['TRACETAP_QUIET'] = 'true' if args.quiet else 'false'
    os.environ['TRACETAP_VERBOSE'] = 'true' if args.verbose else 'false'
    os.environ['TRACETAP_FILTER_HOSTS'] = args.filter_host
    os.environ['TRACETAP_FILTER_REGEX'] = args.filter_regex

    # Print startup banner
    print(f"┌{'─' * 50}┐")
    print(f"│ TraceTap HTTP/HTTPS Proxy                       │")
    print(f"├{'─' * 50}┤")
    print(f"│ Listening: http://0.0.0.0:{args.listen:<28} │")
    if args.export:
        export_display = args.export if len(args.export) <= 38 else args.export[:35] + "..."
        print(f"│ Export:    {export_display:<38} │")
    if args.raw_log:
        raw_display = args.raw_log if len(args.raw_log) <= 38 else args.raw_log[:35] + "..."
        print(f"│ Raw Log:   {raw_display:<38} │")
    print(f"│ Session:   {args.session:<38} │")
    print(f"└{'─' * 50}┘")
    print()
    print("Configure your client:")
    print(f"  export HTTP_PROXY=http://localhost:{args.listen}")
    print(f"  export HTTPS_PROXY=http://localhost:{args.listen}")
    print()
    print("Press Ctrl+C to stop and export.\n", flush=True)

    # Create a temporary file with the addon code
    # This is necessary for PyInstaller compatibility
    addon_file = None
    try:
        # Write addon code to a temporary file
        # mitmproxy will load it via the -s flag
        fd, addon_file = tempfile.mkstemp(suffix='.py', prefix='tracetap_')
        with os.fdopen(fd, 'w') as f:
            f.write(ADDON_CODE)

        # Build mitmproxy command-line arguments
        sys.argv = [
            'mitmdump',  # mitmproxy command-line tool
            '--listen-host', '0.0.0.0',  # Listen on all interfaces
            '--listen-port', str(args.listen),  # Port number
            '--set', 'ssl_insecure=true',  # Allow insecure SSL (self-signed certs, etc.)
            '--set', 'upstream_cert=false',  # Don't verify upstream certificates
        ]

        # Add quiet flag if requested
        if args.quiet:
            sys.argv.extend(['--quiet'])

        # Add our addon script
        sys.argv.extend(['-s', addon_file])

        # Start mitmproxy
        # This blocks until user presses Ctrl+C
        mitmain.mitmdump()

    except (KeyboardInterrupt, SystemExit):
        # Normal shutdown via Ctrl+C
        pass
    finally:
        # Clean up temporary addon file
        if addon_file and os.path.exists(addon_file):
            try:
                os.unlink(addon_file)
            except:
                # Ignore cleanup errors
                pass


if __name__ == '__main__':
    main()