"""
Export functionality for TraceTap.

Provides functions to export captured HTTP traffic to:
- Postman Collection v2.1 format
- Raw JSON log format
- OpenAPI 3.0 specification

without using ANY CLAUDE support
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set, Optional
from urllib.parse import urlparse, parse_qs
from collections import defaultdict


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
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"❌ Error creating directory {output_file.parent}: {e}", flush=True)
            raise

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(collection, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"❌ Error writing to {output_path}: {e}", flush=True)
            raise

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


class OpenAPIExporter:
    """
    Exports captured traffic to OpenAPI 3.0 specification format.
    """

    @staticmethod
    def export(records: List[Dict[str, Any]], session_name: str, output_path: str,
               title: Optional[str] = None, version: str = "1.0.0") -> None:
        """
        Export captured traffic as OpenAPI 3.0 specification.

        Analyzes captured HTTP traffic and generates an OpenAPI specification
        that documents the API endpoints, parameters, request/response schemas.

        Args:
            records: List of captured request/response records
            session_name: Name for the API (used if title not provided)
            output_path: Where to save the OpenAPI spec file
            title: Optional API title (defaults to session_name)
            version: API version (default: "1.0.0")
        """
        if not records:
            print("⚠️  No records to export", flush=True)
            return

        # Use session_name as title if not provided
        api_title = title or session_name

        # Group requests by endpoint
        endpoints = OpenAPIExporter._group_by_endpoint(records)

        # Build OpenAPI paths object
        paths = OpenAPIExporter._build_paths(endpoints)

        # Extract server URLs
        servers = OpenAPIExporter._extract_servers(records)

        # Build OpenAPI 3.0 specification
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": api_title,
                "version": version,
                "description": f"API specification generated from captured traffic\nSession: {session_name}\nCaptured: {datetime.now().isoformat()}",
            },
            "servers": servers,
            "paths": paths
        }

        # Write to file
        output_file = Path(output_path)
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"❌ Error creating directory {output_file.parent}: {e}", flush=True)
            raise

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"❌ Error writing to {output_path}: {e}", flush=True)
            raise

        endpoint_count = len(paths)
        print(f"✓ Exported OpenAPI 3.0 spec with {endpoint_count} endpoints → {output_path}", flush=True)

    @staticmethod
    def _group_by_endpoint(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group records by endpoint path (with path parameters normalized).

        Returns:
            Dict mapping endpoint paths to lists of records
        """
        grouped = defaultdict(list)

        for rec in records:
            # Normalize path to detect path parameters
            path = OpenAPIExporter._normalize_path(rec["url"])
            grouped[path].append(rec)

        return dict(grouped)

    @staticmethod
    def _normalize_path(url: str) -> str:
        """
        Normalize URL path by converting IDs and UUIDs to path parameters.

        Examples:
            /users/123 → /users/{id}
            /api/v1/posts/abc-123-def → /api/v1/posts/{id}
            /products/550e8400-e29b-41d4-a716-446655440000 → /products/{id}
        """
        parsed = urlparse(url)
        path = parsed.path

        # Pattern for numeric IDs
        path = re.sub(r'/\d+(/|$)', r'/{id}\1', path)

        # Pattern for UUIDs
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(/|$)',
            r'/{id}\1',
            path,
            flags=re.IGNORECASE
        )

        # Pattern for alphanumeric IDs (like abc123def, user_12345)
        # Must contain at least one digit and be 8+ chars to avoid matching normal path segments
        path = re.sub(r'/(?=[a-zA-Z0-9_-]{8,}(?:/|$))(?=.*\d)[a-zA-Z0-9_-]{8,}(/|$)', r'/{id}\1', path)

        return path

    @staticmethod
    def _build_paths(endpoints: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Build OpenAPI paths object from grouped endpoints.

        Returns:
            Dict representing OpenAPI paths
        """
        paths = {}

        for path, records in endpoints.items():
            # Group by HTTP method
            methods = defaultdict(list)
            for rec in records:
                methods[rec["method"].lower()].append(rec)

            # Build operations for this path
            operations = {}
            for method, method_records in methods.items():
                operations[method] = OpenAPIExporter._build_operation(method, method_records, path)

            paths[path] = operations

        return paths

    @staticmethod
    def _build_operation(method: str, records: List[Dict[str, Any]], normalized_path: str) -> Dict[str, Any]:
        """
        Build OpenAPI operation object for a specific HTTP method.

        Args:
            method: HTTP method (get, post, etc.)
            records: All captured records for this method
            normalized_path: The normalized path with {id} placeholders

        Returns:
            OpenAPI operation object
        """
        # Use first record as representative
        sample = records[0]

        operation = {
            "summary": f"{method.upper()} {sample['url']}",
            "responses": OpenAPIExporter._build_responses(records)
        }

        # Add parameters if present
        params = OpenAPIExporter._extract_parameters(sample, normalized_path)
        if params:
            operation["parameters"] = params

        # Add request body if present (for POST, PUT, PATCH)
        if method in ['post', 'put', 'patch'] and sample.get("req_body"):
            operation["requestBody"] = OpenAPIExporter._build_request_body(sample)

        return operation

    @staticmethod
    def _extract_parameters(record: Dict[str, Any], normalized_path: str) -> List[Dict[str, Any]]:
        """
        Extract query and path parameters from a record.

        Args:
            record: The captured request record
            normalized_path: The normalized path with {id} placeholders

        Returns:
            List of OpenAPI parameter objects
        """
        parameters = []

        # Extract query parameters
        parsed = urlparse(record["url"])
        if parsed.query:
            query_params = parse_qs(parsed.query)
            for name, values in query_params.items():
                parameters.append({
                    "name": name,
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                    "example": values[0] if values else ""
                })

        # Extract path parameters from normalized path
        if '{id}' in normalized_path:
            parameters.append({
                "name": "id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
                "description": "Resource identifier"
            })

        return parameters

    @staticmethod
    def _build_request_body(record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build OpenAPI requestBody object from captured request.

        Returns:
            OpenAPI requestBody object
        """
        body_str = record.get("req_body", "")

        # Try to parse as JSON
        try:
            body_data = json.loads(body_str)
            schema = OpenAPIExporter._infer_schema(body_data)

            return {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": schema,
                        "example": body_data
                    }
                }
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            # Fallback to plain text
            return {
                "required": True,
                "content": {
                    "text/plain": {
                        "schema": {"type": "string"},
                        "example": body_str
                    }
                }
            }

    @staticmethod
    def _build_responses(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build OpenAPI responses object from captured responses.

        Groups responses by status code and generates schemas.

        Returns:
            Dict mapping status codes to response objects
        """
        responses = {}

        # Group by status code
        by_status = defaultdict(list)
        for rec in records:
            status = str(rec.get("status", 200))
            by_status[status].append(rec)

        # Build response for each status code
        for status, status_records in by_status.items():
            sample = status_records[0]
            response_body = sample.get("response_body", "")

            # Try to parse as JSON
            try:
                response_data = json.loads(response_body) if response_body else None
                if response_data:
                    schema = OpenAPIExporter._infer_schema(response_data)
                    responses[status] = {
                        "description": f"Response for {status}",
                        "content": {
                            "application/json": {
                                "schema": schema,
                                "example": response_data
                            }
                        }
                    }
                else:
                    responses[status] = {
                        "description": f"Response for {status}"
                    }
            except (json.JSONDecodeError, TypeError, ValueError):
                # Non-JSON response
                responses[status] = {
                    "description": f"Response for {status}",
                    "content": {
                        "text/plain": {
                            "schema": {"type": "string"}
                        }
                    }
                }

        return responses

    @staticmethod
    def _infer_schema(data: Any) -> Dict[str, Any]:
        """
        Infer JSON schema from data.

        Analyzes the structure and types of data to generate a JSON schema.

        Args:
            data: The data to analyze (dict, list, or primitive)

        Returns:
            JSON schema object
        """
        if data is None:
            return {"type": "null"}

        if isinstance(data, bool):
            return {"type": "boolean"}

        if isinstance(data, int):
            return {"type": "integer"}

        if isinstance(data, float):
            return {"type": "number"}

        if isinstance(data, str):
            return {"type": "string"}

        if isinstance(data, list):
            if not data:
                return {"type": "array", "items": {}}

            # Infer schema from first item
            item_schema = OpenAPIExporter._infer_schema(data[0])
            return {"type": "array", "items": item_schema}

        if isinstance(data, dict):
            properties = {}
            required = []

            for key, value in data.items():
                properties[key] = OpenAPIExporter._infer_schema(value)
                # Consider field required if value is not None
                if value is not None:
                    required.append(key)

            schema = {
                "type": "object",
                "properties": properties
            }

            if required:
                schema["required"] = required

            return schema

        # Unknown type
        return {"type": "string"}

    @staticmethod
    def _extract_servers(records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract unique server URLs from captured records.

        Returns:
            List of OpenAPI server objects
        """
        servers_set: Set[str] = set()

        for rec in records:
            parsed = urlparse(rec["url"])
            server_url = f"{parsed.scheme}://{parsed.netloc}"
            servers_set.add(server_url)

        return [{"url": url} for url in sorted(servers_set)]
