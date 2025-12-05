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

  # Export OpenAPI 3.0 specification
  %(prog)s --listen 8080 --export-openapi openapi.json
  %(prog)s --listen 8080 --export api.json --export-openapi openapi.json

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

    parser.add_argument(
        '--export-openapi',
        type=str,
        default='',
        metavar='PATH',
        dest='export_openapi',
        help='Export OpenAPI 3.0 specification to this path on shutdown'
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
    3. Load addon code from tracetap_addon.py
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
    if args.export_openapi:
        os.environ['TRACETAP_OPENAPI_PATH'] = args.export_openapi
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
    if args.export_openapi:
        openapi_display = args.export_openapi if len(args.export_openapi) <= 38 else args.export_openapi[:35] + "..."
        print(f"│ OpenAPI:   {openapi_display:<38} │")
    print(f"│ Session:   {args.session:<38} │")
    print(f"└{'─' * 50}┘")
    print()
    print("Configure your client:")
    print(f"  export HTTP_PROXY=http://localhost:{args.listen}")
    print(f"  export HTTPS_PROXY=http://localhost:{args.listen}")
    print()
    print("Press Ctrl+C to stop and export.\n", flush=True)

    # Find the addon file
    # First check if tracetap_addon.py exists in the same directory
    addon_file = None
    script_dir = Path(__file__).parent
    addon_path = script_dir / 'tracetap_addon.py'
    
    if not addon_path.exists():
        print(f"Error: Cannot find tracetap_addon.py in {script_dir}")
        print("Make sure tracetap_addon.py is in the same directory as this script.")
        sys.exit(1)

    try:
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
        sys.argv.extend(['-s', str(addon_path)])

        # Start mitmproxy
        # This blocks until user presses Ctrl+C
        mitmain.mitmdump()

    except (KeyboardInterrupt, SystemExit):
        # Normal shutdown via Ctrl+C
        pass


if __name__ == '__main__':
    main()
