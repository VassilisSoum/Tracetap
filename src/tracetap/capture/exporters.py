"""
Export functionality for TraceTap.

Provides raw JSON log format export for captured HTTP traffic.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


class RawLogExporter:
    """
    Exports captured traffic to raw JSON format.
    """

    @staticmethod
    def export(records: List[Dict[str, Any]], session_name: str, output_path: str,
               host_filters: List[str], regex_filter: str) -> None:
        """
        Export raw captured data as JSON.

        The raw log contains:
        - Session metadata (name, timestamp, filters)
        - Complete list of captured requests with all data

        This format is ideal for:
        - Debugging
        - Custom processing
        - Converting to other formats (e.g., WireMock stubs)

        Args:
            records: List of captured request/response records
            session_name: Name for the session
            output_path: Where to save the log file
            host_filters: List of host filters that were active
            regex_filter: Regex filter that was active (if any)
        """
        output_file = Path(output_path)
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"❌ Error creating directory {output_file.parent}: {e}", flush=True)
            raise

        # Build the log data structure
        log_data = {
            "session": session_name,
            "captured_at": datetime.now().isoformat(),
            "total_requests": len(records),
            "filters": {
                "hosts": host_filters,
                "regex": regex_filter if regex_filter else None
            },
            "requests": records
        }

        # Write to file with pretty formatting
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"❌ Error writing to {output_path}: {e}", flush=True)
            raise

        # Show file size for user feedback
        file_size = output_file.stat().st_size / 1024  # Convert to KB
        print(f"✓ Exported raw log ({file_size:.1f} KB) → {output_path}", flush=True)
