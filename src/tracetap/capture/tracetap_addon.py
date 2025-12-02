"""
TraceTap Mitmproxy Addon

Main addon that integrates with mitmproxy to capture HTTP/HTTPS traffic.
Uses modular components for filtering, exporting, and utilities.
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any

from mitmproxy import http

# Import our modular components
from filters import RequestFilter
from exporters import PostmanExporter, RawLogExporter
from utils import safe_body, calc_duration, status_color


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

        # Filtering
        self.filter_hosts = ''          # Comma-separated host list
        self.filter_regex = ''          # Regex pattern for URL matching
        self.request_filter = None      # RequestFilter instance

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
        self.export_path = os.environ.get('TRACETAP_EXPORT_PATH', '')
        self.raw_log_path = os.environ.get('TRACETAP_RAW_LOG_PATH', '')
        self.session_name = os.environ.get('TRACETAP_SESSION', 'tracetap-session')
        self.quiet = os.environ.get('TRACETAP_QUIET', 'false') == 'true'
        self.verbose = os.environ.get('TRACETAP_VERBOSE', 'false') == 'true'

        # Read filtering configuration
        self.filter_hosts = os.environ.get('TRACETAP_FILTER_HOSTS', '')
        self.filter_regex = os.environ.get('TRACETAP_FILTER_REGEX', '')

        # Parse host filters
        host_filters = [h.strip() for h in self.filter_hosts.split(',') if h.strip()]

        # Initialize request filter
        self.request_filter = RequestFilter(host_filters, self.filter_regex)

        # Display active filters to user
        if host_filters or self.filter_regex:
            print(f"\n🔍 Filtering enabled:", flush=True)
            if host_filters:
                print(f"   Hosts ({len(host_filters)}): {host_filters}", flush=True)
            if self.filter_regex:
                print(f"   Regex: {self.filter_regex}", flush=True)
            print("", flush=True)
        else:
            print(f"\n⚠️  No filters active - capturing ALL traffic", flush=True)
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

            # Apply filtering logic
            should_capture = self.request_filter.should_capture(
                req.host, 
                req.pretty_url, 
                verbose=self.verbose
            )
            
            if not should_capture:
                if self.verbose:
                    print(f"⏭️  Skipping: {req.method} {req.pretty_url}", flush=True)
                return

            # Build a record containing all relevant data
            record = {
                "time": datetime.now().isoformat(),
                "method": req.method,
                "url": req.pretty_url,
                "host": req.host,
                "proto": f"HTTP/{req.http_version}",
                "req_headers": dict(req.headers),
                "req_body": safe_body(req.text, req.raw_content),
                "status": resp.status_code if resp else 0,
                "resp_headers": dict(resp.headers) if resp else {},
                "resp_body": safe_body(resp.text, resp.raw_content) if resp else "",
                "duration_ms": calc_duration(flow)
            }

            # Store the record
            self.records.append(record)

            # Log capture in verbose mode
            if self.verbose:
                print(f"📝 Recorded ({len(self.records)} total): {record['method']} {record['url']}", flush=True)

            # Print to console (unless quiet mode)
            if not self.quiet:
                color = status_color(record["status"])
                print(f"{record['method']} {record['url']} → "
                      f"{color}{record['status']}\033[0m "
                      f"({record['duration_ms']} ms)", flush=True)

        except Exception as e:
            # Log errors but don't crash
            print(f"Error recording request: {e}", file=sys.stderr, flush=True)

    def done(self):
        """
        Called when mitmproxy is shutting down.

        This is our cleanup hook where we export captured data to files.
        """
        if not self.records:
            print("\nNo requests captured.", flush=True)
            return

        print(f"\n📊 Captured {len(self.records)} requests", flush=True)

        # Export to Postman collection if requested
        if self.export_path:
            try:
                PostmanExporter.export(self.records, self.session_name, self.export_path)
            except Exception as e:
                print(f"Error exporting Postman collection: {e}", file=sys.stderr, flush=True)
                import traceback
                traceback.print_exc()

        # Export to raw log if requested
        if self.raw_log_path:
            try:
                host_filters = [h.strip() for h in self.filter_hosts.split(',') if h.strip()]
                RawLogExporter.export(
                    self.records, 
                    self.session_name, 
                    self.raw_log_path,
                    host_filters,
                    self.filter_regex
                )
            except Exception as e:
                print(f"Error exporting raw log: {e}", file=sys.stderr, flush=True)
                import traceback
                traceback.print_exc()


# Module-level addon list - mitmproxy looks for this
addons = [TraceTapAddon()]
