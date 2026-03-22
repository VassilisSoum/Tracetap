"""
TraceTap Recording Addon for mitmproxy.

Simplified addon for capturing HTTP/HTTPS traffic during manual recording sessions.
Designed to work with RecordingSession and export in format compatible with
EventCorrelator.load_mitmproxy_traffic().

Key differences from main TraceTap addon:
- Simpler configuration (less features)
- Optimized for recording sessions
- Exports in NetworkRequest-compatible format
- Session-scoped (lifecycle managed by RecordingSession)
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from mitmproxy import http


class RecordCaptureAddon:
    """
    Mitmproxy addon for recording sessions.

    Captures HTTP/HTTPS traffic during a recording session and exports
    in a format compatible with EventCorrelator.
    """

    def __init__(self):
        """Initialize addon - called when module is loaded."""
        self.records: List[Dict[str, Any]] = []
        self.initialized: bool = False

        # Configuration (set via environment variables)
        self.output_path: str = ''
        self.session_name: str = 'recording-session'
        self.quiet: bool = True  # Default quiet for recordings

    def _lazy_init(self):
        """
        Lazy initialization - reads config from environment on first use.

        Configuration is passed via environment variables because they
        survive mitmproxy's module re-import behavior.
        """
        if self.initialized:
            return

        self.initialized = True

        # Read configuration from environment
        self.output_path = os.environ.get('TRACETAP_RECORD_OUTPUT', '')
        self.session_name = os.environ.get('TRACETAP_RECORD_SESSION', 'recording-session')
        self.quiet = os.environ.get('TRACETAP_RECORD_QUIET', 'true') == 'true'

        if not self.quiet:
            print(f"\n🎬 Recording traffic for session: {self.session_name}", flush=True)
            print(f"   Output: {self.output_path}\n", flush=True)

    def response(self, flow: http.HTTPFlow) -> None:
        """
        Called when a complete HTTP response is received.

        Args:
            flow: The HTTP flow containing request and response data
        """
        self._lazy_init()

        try:
            req = flow.request
            resp = flow.response

            # Calculate timestamp in milliseconds (Unix epoch)
            timestamp = int(datetime.now().timestamp() * 1000)

            # Calculate duration
            duration_ms = self._calc_duration(flow)

            # Build record in NetworkRequest-compatible format
            record = {
                "method": req.method,
                "url": req.pretty_url,
                "host": req.host,
                "path": req.path,
                "timestamp": timestamp,
                "request": {
                    "headers": dict(req.headers),
                    "body": self._safe_body(req.text, req.raw_content)
                },
                "response": {
                    "status": resp.status_code if resp else 0,
                    "headers": dict(resp.headers) if resp else {},
                    "body": self._safe_body(resp.text, resp.raw_content) if resp else ""
                },
                "duration": duration_ms
            }

            # Store the record
            self.records.append(record)

            # Log if not quiet
            if not self.quiet:
                print(f"📝 {req.method} {req.pretty_url} → {resp.status_code if resp else '?'}", flush=True)

        except Exception as e:
            print(f"Error recording request: {e}", file=sys.stderr, flush=True)

    def done(self):
        """
        Called when mitmproxy is shutting down.

        Exports captured data to JSON file.
        """
        if not self.output_path:
            print("\n⚠️  No output path configured, skipping export", flush=True)
            return

        if not self.records:
            print("\n⚠️  No requests captured during recording", flush=True)
            return

        # Export to JSON in NetworkRequest-compatible format
        try:
            output_file = Path(self.output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Format: {"requests": [...]}
            # This matches what load_mitmproxy_traffic() expects
            data = {
                "session": self.session_name,
                "captured_at": datetime.now().isoformat(),
                "total_requests": len(self.records),
                "requests": self.records
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            file_size = output_file.stat().st_size / 1024
            print(f"\n💾 Captured {len(self.records)} network requests ({file_size:.1f} KB)", flush=True)
            print(f"   Saved to: {self.output_path}", flush=True)

        except Exception as e:
            print(f"\n❌ Error exporting traffic: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()

    def _safe_body(self, text: str, raw: bytes, max_bytes: int = 64 * 1024) -> str:
        """
        Safely extract body text, limiting size.

        Args:
            text: Decoded text body
            raw: Raw bytes of body
            max_bytes: Maximum size to capture

        Returns:
            Body as string, or placeholder for binary data
        """
        try:
            if text:
                return text[:max_bytes]
            elif raw:
                return raw[:max_bytes].decode('utf-8', errors='replace')
            return ""
        except (UnicodeDecodeError, AttributeError, TypeError):
            return f"[binary data: {len(raw)} bytes]" if raw else ""

    def _calc_duration(self, flow: http.HTTPFlow) -> int:
        """
        Calculate request duration in milliseconds.

        Args:
            flow: The HTTP flow object

        Returns:
            Duration in milliseconds, or 0 if not available
        """
        try:
            if hasattr(flow, 'server_conn') and flow.server_conn and flow.server_conn.timestamp_end:
                duration = flow.server_conn.timestamp_end - flow.server_conn.timestamp_start
                return int(duration * 1000)
        except (AttributeError, TypeError):
            pass
        return 0


# Module-level addon list - mitmproxy looks for this
addons = [RecordCaptureAddon()]
