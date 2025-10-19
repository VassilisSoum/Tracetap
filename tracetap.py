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

# Addon code as a string - will be written to a temp file for mitmproxy
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
    """Mitmproxy addon that captures traffic"""

    def __init__(self):
        """Initialize addon - called when module is loaded"""
        self.records: List[Dict[str, Any]] = []
        self.initialized = False

        # Initialize all attributes with defaults
        self.export_path = ''
        self.raw_log_path = ''
        self.session_name = 'tracetap-session'
        self.quiet = False
        self.verbose = False
        self.filter_hosts = ''
        self.filter_regex = ''
        self.host_filters = []
        self.regex_pattern = None

    def _lazy_init(self):
        """Lazy initialization - reads config from environment on first use"""
        if self.initialized:
            return

        self.initialized = True

        # Read config from environment variables set by main
        self.export_path = os.environ.get('TRACETAP_EXPORT_PATH', '')
        self.raw_log_path = os.environ.get('TRACETAP_RAW_LOG_PATH', '')
        self.session_name = os.environ.get('TRACETAP_SESSION', 'tracetap-session')
        self.quiet = os.environ.get('TRACETAP_QUIET', 'false') == 'true'
        self.verbose = os.environ.get('TRACETAP_VERBOSE', 'false') == 'true'

        # Filtering options
        self.filter_hosts = os.environ.get('TRACETAP_FILTER_HOSTS', '')
        self.filter_regex = os.environ.get('TRACETAP_FILTER_REGEX', '')

        # Parse filters
        self.host_filters = [h.strip() for h in self.filter_hosts.split(',') if h.strip()]
        self.regex_pattern = None
        if self.filter_regex:
            import re
            try:
                self.regex_pattern = re.compile(self.filter_regex)
            except re.error as e:
                print(f"Invalid regex pattern: {e}", file=sys.stderr, flush=True)

        # Print filter info if any filters are active
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
        """Called when a response is received"""
        # Lazy initialization on first request
        self._lazy_init()

        try:
            req = flow.request
            resp = flow.response

            # Apply filters - RETURN EARLY if shouldn't capture
            should_capture = self._should_capture(req.host, req.pretty_url)
            if not should_capture:
                if self.verbose:
                    print(f"⏭️  Skipping: {req.method} {req.pretty_url}", flush=True)
                return

            # Build record
            record = {
                "time": datetime.now().isoformat(),
                "method": req.method,
                "url": req.pretty_url,
                "host": req.host,
                "proto": f"HTTP/{req.http_version}",
                "req_headers": dict(req.headers),
                "req_body": self._safe_body(req.text, req.raw_content),
                "status": resp.status_code if resp else 0,
                "resp_headers": dict(resp.headers) if resp else {},
                "resp_body": self._safe_body(resp.text, resp.raw_content) if resp else "",
                "duration_ms": self._calc_duration(flow)
            }

            self.records.append(record)

            if self.verbose:
                print(f"📝 Recorded ({len(self.records)} total): {record['method']} {record['url']}", flush=True)

            if not self.quiet:
                status_color = self._status_color(record["status"])
                print(f"{record['method']} {record['url']} → "
                      f"{status_color}{record['status']}\\033[0m "
                      f"({record['duration_ms']} ms)", flush=True)
        except Exception as e:
            print(f"Error recording request: {e}", file=sys.stderr, flush=True)

    def _should_capture(self, host: str, url: str) -> bool:
        """Check if request should be captured based on filters"""
        # If no filters, capture everything
        if not self.host_filters and not self.regex_pattern:
            return True

        captured = False
        match_reason = ""

        # Check host filters (exact match or wildcard)
        if self.host_filters:
            for filter_host in self.host_filters:
                # Exact match only
                if filter_host == host:
                    captured = True
                    match_reason = f"exact match: {filter_host}"
                    break

                # Wildcard match (*.whgstage.com matches platform.whgstage.com, stage.whgstage.com, etc.)
                if filter_host.startswith('*.'):
                    domain = filter_host[2:]  # Remove *.
                    # Must be a subdomain of the domain
                    if host.endswith('.' + domain):
                        captured = True
                        match_reason = f"wildcard match: {filter_host}"
                        break
                    # Also match the domain itself if specified as *.domain.com
                    if host == domain:
                        captured = True
                        match_reason = f"wildcard match: {filter_host}"
                        break

        # Check regex filter
        if not captured and self.regex_pattern:
            if self.regex_pattern.search(url) or self.regex_pattern.search(host):
                captured = True
                match_reason = f"regex match: {self.filter_regex}"

        # Log capture/filter decision in verbose mode
        if self.verbose:
            if captured:
                print(f"✅ [CAPTURE] {host} ({match_reason})", flush=True)
            else:
                print(f"🚫 [FILTER]  {host}", flush=True)

        return captured

    def done(self):
        """Called when mitmproxy shuts down - export here"""
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
        """Export raw captured data as JSON"""
        output_path = Path(self.raw_log_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

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

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        file_size = output_path.stat().st_size / 1024  # KB
        print(f"✓ Exported raw log ({file_size:.1f} KB) → {self.raw_log_path}", flush=True)

    def _export_collection(self):
        """Export records to Postman collection"""
        items = []

        for rec in self.records:
            # Build headers
            headers = [{"key": k, "value": v} for k, v in rec["req_headers"].items()]

            # Build body
            body = None
            if rec["req_body"]:
                body = {"mode": "raw", "raw": rec["req_body"]}

            # Parse URL
            parsed = urlparse(rec["url"])
            host = parsed.netloc.split(':')[0] if ':' in parsed.netloc else parsed.netloc
            host_parts = host.split('.')
            path_parts = [p for p in parsed.path.split('/') if p]

            query = []
            if parsed.query:
                for key, values in parse_qs(parsed.query).items():
                    for value in values:
                        query.append({"key": key, "value": value})

            url_obj = {
                "raw": rec["url"],
                "protocol": parsed.scheme,
                "host": host_parts,
                "path": path_parts,
            }
            if query:
                url_obj["query"] = query

            # Build item
            item = {
                "name": f"{rec['method']} {rec['url']}",
                "request": {
                    "method": rec["method"],
                    "header": headers,
                    "url": url_obj,
                }
            }
            if body:
                item["request"]["body"] = body

            items.append(item)

        # Create collection
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
        """Safely extract body text, limiting size"""
        try:
            if text:
                return text[:max_bytes]
            elif raw:
                return raw[:max_bytes].decode('utf-8', errors='replace')
            return ""
        except Exception:
            return f"[binary data: {len(raw)} bytes]" if raw else ""

    def _calc_duration(self, flow: http.HTTPFlow) -> int:
        """Calculate request duration in milliseconds"""
        try:
            if hasattr(flow, 'server_conn') and flow.server_conn and flow.server_conn.timestamp_end:
                duration = flow.server_conn.timestamp_end - flow.server_conn.timestamp_start
                return int(duration * 1000)
        except Exception:
            pass
        return 0

    def _status_color(self, status: int) -> str:
        """Get ANSI color code for status"""
        if 200 <= status < 300:
            return "\\033[32m"  # Green
        elif 300 <= status < 400:
            return "\\033[36m"  # Cyan
        elif 400 <= status < 500:
            return "\\033[33m"  # Yellow
        elif 500 <= status < 600:
            return "\\033[31m"  # Red
        return ""


addons = [TraceTapAddon()]
'''


def parse_args():
    """Parse command line arguments"""
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


def main():
    """Main entry point"""
    args = parse_args()

    # Pass config via environment variables (survives the re-import by mitmproxy)
    if args.export:
        os.environ['TRACETAP_EXPORT_PATH'] = args.export
    if args.raw_log:
        os.environ['TRACETAP_RAW_LOG_PATH'] = args.raw_log
    os.environ['TRACETAP_SESSION'] = args.session
    os.environ['TRACETAP_QUIET'] = 'true' if args.quiet else 'false'
    os.environ['TRACETAP_VERBOSE'] = 'true' if args.verbose else 'false'
    os.environ['TRACETAP_FILTER_HOSTS'] = args.filter_host
    os.environ['TRACETAP_FILTER_REGEX'] = args.filter_regex

    # Print startup message
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
    addon_file = None
    try:
        # Write addon to temporary file
        fd, addon_file = tempfile.mkstemp(suffix='.py', prefix='tracetap_')
        with os.fdopen(fd, 'w') as f:
            f.write(ADDON_CODE)

        # Run mitmproxy with our addon
        sys.argv = [
            'mitmdump',
            '--listen-host', '0.0.0.0',
            '--listen-port', str(args.listen),
            '--set', 'ssl_insecure=true',
            '--set', 'upstream_cert=false',
        ]

        if args.quiet:
            sys.argv.extend(['--quiet'])

        sys.argv.extend(['-s', addon_file])

        mitmain.mitmdump()

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        # Clean up temporary addon file
        if addon_file and os.path.exists(addon_file):
            try:
                os.unlink(addon_file)
            except:
                pass


if __name__ == '__main__':
    main()