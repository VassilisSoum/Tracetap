"""
Export functionality for TraceTap.

Provides functions to export captured HTTP traffic to:
- Postman Collection v2.1 format
- Raw JSON log format

without using ANY CLAUDE support
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs


class PostmanExporter:
    """
    Exports captured traffic to Postman Collection v2.1 format.
    """
    
    @staticmethod
    def export(records: List[Dict[str, Any]], session_name: str, output_path: str) -> None:
        """
        Export records to Postman Collection v2.1 format.

        Converts captured HTTP traffic into a Postman collection that can be
        imported into Postman for replaying requests, testing, documentation, etc.

        Args:
            records: List of captured request/response records
            session_name: Name for the collection
            output_path: Where to save the collection file
        """
        items = []

        for rec in records:
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
                "name": f"{session_name} @ {datetime.now().isoformat()}",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": items
        }

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)

        print(f"✓ Exported {len(records)} requests → {output_path}", flush=True)


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
        output_file.parent.mkdir(parents=True, exist_ok=True)

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
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        # Show file size for user feedback
        file_size = output_file.stat().st_size / 1024  # Convert to KB
        print(f"✓ Exported raw log ({file_size:.1f} KB) → {output_path}", flush=True)
