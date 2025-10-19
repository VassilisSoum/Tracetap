#!/usr/bin/env python3
"""
TraceTap to WireMock Converter
Converts TraceTap raw log JSON to WireMock stub mappings

WireMock is a popular HTTP mock server that matches incoming requests against
configured "stubs" and returns predefined responses. This tool automatically
generates WireMock stubs from captured HTTP traffic.

Usage:
    python tracetap2wiremock.py raw_capture.json --output wiremock/mappings/
    python tracetap2wiremock.py raw_capture.json --output stubs/ --priority 1
    python tracetap2wiremock.py raw_capture.json --output stubs/ --config ignore-config.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Set
from urllib.parse import urlparse, parse_qs
import hashlib


# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

def load_ignore_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration for fields to ignore in matching.

    The ignore configuration allows excluding dynamic fields (timestamps, IDs,
    tokens) from strict matching, making stubs more flexible and reusable.

    Args:
        config_path: Path to JSON configuration file

    Returns:
        Dictionary with ignore configuration

    Raises:
        SystemExit: If file not found or invalid JSON
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"✗ Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)


# ============================================================================
# FIELD FILTERING
# ============================================================================

def should_ignore_field(field_path: str, ignore_config: Dict[str, Any]) -> bool:
    """
    Check if a field should be ignored based on configuration.

    Supports both exact field name matching and pattern-based matching.

    Args:
        field_path: Field path (e.g., "user.id" or "timestamp")
        ignore_config: Configuration dictionary

    Returns:
        True if field should be ignored, False otherwise
    """
    if not ignore_config:
        return False

    # Check exact field name matches
    if 'ignore_fields' in ignore_config:
        if field_path in ignore_config['ignore_fields']:
            return True

    # Check pattern-based matches (substring matching)
    if 'ignore_patterns' in ignore_config:
        for pattern in ignore_config['ignore_patterns']:
            if pattern in field_path:
                return True

    return False


def should_ignore_header(header_name: str, ignore_config: Dict[str, Any]) -> bool:
    """
    Check if a header should be ignored.

    Headers are matched case-insensitively (per HTTP spec).

    Args:
        header_name: HTTP header name (e.g., "Content-Type")
        ignore_config: Configuration dictionary

    Returns:
        True if header should be ignored, False otherwise
    """
    if not ignore_config:
        return False

    header_lower = header_name.lower()

    if 'ignore_headers' in ignore_config:
        for ignored in ignore_config['ignore_headers']:
            if header_lower == ignored.lower():
                return True

    return False


def should_ignore_query_param(param_name: str, ignore_config: Dict[str, Any]) -> bool:
    """
    Check if a query parameter should be ignored.

    Useful for ignoring cache busters, timestamps, nonces, etc.

    Args:
        param_name: Query parameter name (e.g., "timestamp")
        ignore_config: Configuration dictionary

    Returns:
        True if parameter should be ignored, False otherwise
    """
    if not ignore_config:
        return False

    if 'ignore_query_params' in ignore_config:
        if param_name in ignore_config['ignore_query_params']:
            return True

    return False


# ============================================================================
# DYNAMIC PATH SEGMENT DETECTION
# ============================================================================

def detect_dynamic_path_segment(segment: str) -> bool:
    """
    Detect if a path segment looks like a dynamic parameter.

    Uses heuristics to identify common patterns:
    - UUIDs (36 chars with 4 dashes)
    - Long random strings (>20 chars)
    - Base64-like tokens (>30 chars with specific character set)
    - Numeric IDs (>5 digits)

    Examples of detected segments:
    - "550e8400-e29b-41d4-a716-446655440000" (UUID)
    - "AAABmfxJYJQrIFm0A908RAAAAAAAEyf0NsTP1QRNtcMo-NeKGBZPIw" (token)
    - "1234567890" (numeric ID)

    Args:
        segment: URL path segment

    Returns:
        True if segment appears to be dynamic, False otherwise
    """
    if not segment:
        return False

    # UUIDs: 8-4-4-4-12 hex characters with dashes
    # Example: 550e8400-e29b-41d4-a716-446655440000
    if len(segment) == 36 and segment.count('-') == 4:
        return True

    # Long random strings (>20 chars, alphanumeric with dashes/underscores)
    # Example: abc123_def456_ghi789_jkl012
    if len(segment) > 20 and segment.replace('-', '').replace('_', '').isalnum():
        return True

    # Base64-like strings (>30 chars, URL-safe base64 character set)
    # Example: AAABmfxJYJQrIFm0A908RAAAAAAAEyf0NsTP1QRNtcMo-NeKGBZPIw
    if len(segment) > 30 and all(
            c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_='
            for c in segment):
        return True

    # Numeric IDs (all digits, length > 5)
    # Example: 1234567890
    if segment.isdigit() and len(segment) > 5:
        return True

    return False


def should_ignore_path_segment(segment: str, index: int, ignore_config: Dict[str, Any]) -> bool:
    """
    Check if a path segment should be converted to a pattern.

    Supports three modes:
    1. Explicit position-based: {"position": 5}
    2. Keyword-based: {"contains": "session"}
    3. Auto-detection: auto_detect_path_params: true

    Args:
        segment: URL path segment
        index: Position in the path (0-indexed)
        ignore_config: Configuration dictionary

    Returns:
        True if segment should be patternized, False otherwise
    """
    if not ignore_config:
        return False

    # Check explicit ignore list
    if 'ignore_path_segments' in ignore_config:
        for pattern in ignore_config['ignore_path_segments']:
            if isinstance(pattern, dict):
                # Position-based: {"position": 4}
                # Example: /api/v1/users/{id}/profile - position 3 is the {id}
                if pattern.get('position') == index:
                    return True

                # Keyword-based: {"contains": "session"}
                # Example: /api/session/ABC123 - contains "session"
                if 'contains' in pattern and pattern['contains'] in segment:
                    return True
            elif isinstance(pattern, str) and pattern == segment:
                # Exact string match
                return True

    # Auto-detect dynamic segments if enabled
    if ignore_config.get('auto_detect_path_params', False):
        return detect_dynamic_path_segment(segment)

    return False


def convert_path_to_pattern(path: str, ignore_config: Dict[str, Any]) -> str:
    """
    Convert path with dynamic segments to regex pattern.

    Replaces dynamic segments with regex patterns while preserving static
    segments. This allows WireMock to match URLs with varying dynamic values.

    Example:
        Input:  /api/v1/users/550e8400-e29b-41d4-a716-446655440000/profile
        Output: /api/v1/users/[A-Za-z0-9._-]+/profile

    This pattern will match any UUID in the user ID position.

    Args:
        path: URL path (e.g., "/api/v1/users/123/profile")
        ignore_config: Configuration dictionary

    Returns:
        Path with dynamic segments replaced by patterns
    """
    if not ignore_config:
        return path

    # Only process if we have segment rules or auto-detect enabled
    if not (ignore_config.get('ignore_path_segments') or
            ignore_config.get('auto_detect_path_params')):
        return path

    # Split path into segments (filter out empty strings from leading/trailing slashes)
    segments = [s for s in path.split('/') if s]
    pattern_segments = []

    for idx, segment in enumerate(segments):
        if should_ignore_path_segment(segment, idx, ignore_config):
            # Replace with regex pattern for URL-safe characters
            # [A-Za-z0-9._-]+ matches:
            # - Letters (uppercase and lowercase)
            # - Numbers
            # - Period, underscore, hyphen (common in URLs)
            pattern_segments.append('[A-Za-z0-9._-]+')
        else:
            # Keep static segment, escape regex metacharacters
            # Only escape '.' since we're in a URL path context
            pattern_segments.append(segment.replace('.', r'\.'))

    # Reconstruct path with leading slash
    return '/' + '/'.join(pattern_segments)


def filter_json_body(body_obj: Any, ignore_config: Dict[str, Any], path: str = "") -> Any:
    """
    Recursively filter JSON body to remove ignored fields.

    This function walks through nested JSON structures (dicts and lists)
    and removes fields that should be ignored according to the configuration.

    Example:
        Input:  {"user": {"id": 123, "name": "John"}, "timestamp": 1234567890}
        Config: ignore_json_fields: ["timestamp", "id"]
        Output: {"user": {"name": "John"}}

    Args:
        body_obj: JSON object (dict, list, or primitive)
        ignore_config: Configuration dictionary
        path: Current field path (used for nested field matching)

    Returns:
        Filtered JSON object with ignored fields removed
    """
    if not ignore_config or not ignore_config.get('ignore_json_fields'):
        return body_obj

    if isinstance(body_obj, dict):
        filtered = {}
        for key, value in body_obj.items():
            # Build field path for nested fields (e.g., "user.id")
            field_path = f"{path}.{key}" if path else key

            # Only include field if it's not in the ignore list
            if not should_ignore_field(field_path,
                                       {'ignore_fields': ignore_config.get('ignore_json_fields', [])}):
                # Recursively filter nested objects
                filtered[key] = filter_json_body(value, ignore_config, field_path)

        return filtered

    elif isinstance(body_obj, list):
        # Recursively filter each item in the list
        return [filter_json_body(item, ignore_config, path) for item in body_obj]

    else:
        # Primitive value - return as-is
        return body_obj


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def sanitize_filename(text: str, max_length: int = 100) -> str:
    """
    Create a safe filename from text.

    Removes special characters, replaces spaces, and truncates to max length.

    Args:
        text: Input text
        max_length: Maximum filename length

    Returns:
        Sanitized filename
    """
    # Replace unsafe characters with underscores
    safe = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in text)
    # Normalize whitespace
    safe = ' '.join(safe.split())
    # Replace spaces with underscores
    safe = safe.replace(' ', '_')
    # Truncate if too long
    if len(safe) > max_length:
        safe = safe[:max_length]
    return safe.lower()


def parse_content_type(headers: Dict[str, str]) -> str:
    """
    Extract content type from headers.

    Strips charset and other parameters to get just the media type.

    Args:
        headers: HTTP headers dictionary

    Returns:
        Content type (e.g., "application/json")
    """
    for key, value in headers.items():
        if key.lower() == 'content-type':
            # Return the main type without charset
            # "application/json; charset=utf-8" -> "application/json"
            return value.split(';')[0].strip()
    return 'text/plain'


def is_json_response(headers: Dict[str, str], body: str) -> bool:
    """
    Check if response is JSON.

    Uses both content-type header and body parsing as fallback.

    Args:
        headers: Response headers
        body: Response body

    Returns:
        True if response is JSON, False otherwise
    """
    content_type = parse_content_type(headers)
    if 'json' in content_type.lower():
        return True

    # Fallback: try to parse body as JSON
    if body:
        try:
            json.loads(body)
            return True
        except:
            pass
    return False


# ============================================================================
# WIREMOCK STUB GENERATION
# ============================================================================

def create_wiremock_stub(record: Dict[str, Any], priority: int = 5,
                         request_matching: str = 'url',
                         ignore_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convert a TraceTap record to WireMock stub format.

    A WireMock stub consists of:
    - request: Matching criteria (URL, method, headers, body)
    - response: What to return (status, headers, body, delay)
    - priority: Matching precedence (lower number = higher priority)

    The ignore_config allows excluding dynamic fields to create more flexible
    stubs that match requests with varying timestamps, IDs, etc.

    Args:
        record: Captured HTTP request/response record
        priority: Stub priority (lower = higher precedence)
        request_matching: Matching mode (url, urlPath, urlPattern, urlPathPattern)
        ignore_config: Configuration for ignoring dynamic fields

    Returns:
        WireMock stub as dictionary
    """
    if ignore_config is None:
        ignore_config = {}

    parsed_url = urlparse(record['url'])
    path = parsed_url.path or '/'
    query_params = parse_qs(parsed_url.query) if parsed_url.query else {}

    # Convert path to pattern if configured (replaces dynamic segments)
    path_pattern = convert_path_to_pattern(path, ignore_config)
    patternized = (path_pattern != path)  # Did we modify the path?

    # Build request matcher
    request_matcher = {
        "method": record['method']
    }

    # Decide how to match the URL/path
    if request_matching in ('urlPattern', 'urlPathPattern') or patternized:
        # Use pattern matching (regex) for dynamic paths
        # Add anchors ^ and $ to match the entire path
        regex = f"^{path_pattern}$"
        request_matcher["urlPathPattern"] = regex
    elif request_matching == 'urlPath':
        # Match exact path, ignore query parameters
        request_matcher["urlPath"] = path
    else:
        # Default: exact URL matching with query parameters
        request_matcher["url"] = path
        if query_params:
            # Filter out ignored query parameters
            filtered_params = {}
            for key, values in query_params.items():
                if not should_ignore_query_param(key, ignore_config):
                    # Use first value (WireMock can handle multiple if needed)
                    filtered_params[key] = {"equalTo": values[0]}
            if filtered_params:
                request_matcher["queryParameters"] = filtered_params

    # Add request headers matching if configured
    if ignore_config.get('match_headers'):
        headers_to_match = {}
        for key, value in record.get('req_headers', {}).items():
            if not should_ignore_header(key, ignore_config):
                headers_to_match[key] = {"equalTo": value}

        if headers_to_match:
            request_matcher["headers"] = headers_to_match

    # Add request body matching if present
    if record.get('req_body'):
        req_content_type = parse_content_type(record.get('req_headers', {}))
        if 'json' in req_content_type.lower():
            try:
                # Parse JSON body
                json_body = json.loads(record['req_body'])

                # Filter out ignored fields (timestamps, IDs, etc.)
                if ignore_config.get('ignore_json_fields'):
                    json_body = filter_json_body(json_body, ignore_config)

                # Only add body pattern if there are fields left to match
                if json_body:
                    request_matcher["bodyPatterns"] = [
                        {
                            "equalToJson": json.dumps(json_body),
                            # Flexible matching options
                            "ignoreArrayOrder": True,  # [1,2,3] == [3,2,1]
                            "ignoreExtraElements": True  # Allows additional fields
                        }
                    ]
            except:
                # Fallback to exact text matching for non-JSON or parse errors
                if not ignore_config.get('ignore_request_body'):
                    request_matcher["bodyPatterns"] = [
                        {"equalTo": record['req_body']}
                    ]
        elif not ignore_config.get('ignore_request_body'):
            # Non-JSON body - use exact text matching
            request_matcher["bodyPatterns"] = [
                {"equalTo": record['req_body']}
            ]

    # Build response
    response = {
        "status": record['status'],
        "headers": {}
    }

    # Add response headers (filtered)
    for key, value in record.get('resp_headers', {}).items():
        # Always filter out these headers (WireMock shouldn't proxy them)
        if key.lower() in ['transfer-encoding', 'connection']:
            continue

        # Check user-configured ignore list
        if not should_ignore_header(key, ignore_config):
            response["headers"][key] = value

    # Add response body
    resp_body = record.get('resp_body', '')
    if resp_body:
        if is_json_response(record.get('resp_headers', {}), resp_body):
            # Format JSON nicely in the stub
            try:
                json_obj = json.loads(resp_body)

                # Filter out ignored response fields
                if ignore_config.get('ignore_response_json_fields'):
                    json_obj = filter_json_body(
                        json_obj,
                        {'ignore_json_fields': ignore_config.get('ignore_response_json_fields', [])}
                    )

                response["jsonBody"] = json_obj
            except:
                # Fallback to plain text if JSON parsing fails
                response["body"] = resp_body
        else:
            # Non-JSON response
            response["body"] = resp_body

    # Add realistic delay if configured (and not ignored)
    duration_ms = record.get('duration_ms', 0)
    if duration_ms > 0 and not ignore_config.get('ignore_delays'):
        response["fixedDelayMilliseconds"] = duration_ms

    # Create the complete stub
    stub = {
        "priority": priority,  # Lower number = higher priority
        "request": request_matcher,  # What to match
        "response": response  # What to return
    }

    return stub


def generate_stub_filename(record: Dict[str, Any], index: int) -> str:
    """
    Generate a descriptive filename for the stub.

    Format: {METHOD}_{ENDPOINT}_{STATUS}_{HASH}.json
    Example: POST_initiatePayment_200_a1b2c3d4.json

    Args:
        record: HTTP request/response record
        index: Request index (for uniqueness)

    Returns:
        Filename string
    """
    method = record['method']
    parsed = urlparse(record['url'])
    path = parsed.path or '/'

    # Use last path segment as endpoint name
    path_parts = [p for p in path.split('/') if p]
    if path_parts:
        name = f"{method}_{path_parts[-1]}"
    else:
        name = f"{method}_root"

    # Add query param indicator if present
    if parsed.query:
        name += "_with_params"

    # Add status code
    status = record.get('status', 0)
    name += f"_{status}"

    # Sanitize filename
    name = sanitize_filename(name)

    # Add unique hash to prevent filename collisions
    # Different URLs with same endpoint name won't overwrite each other
    unique_id = hashlib.md5(f"{record['url']}{index}".encode()).hexdigest()[:8]

    return f"{name}_{unique_id}.json"


# ============================================================================
# MAIN CONVERSION LOGIC
# ============================================================================

def convert_raw_log_to_wiremock(input_file: str, output_dir: str,
                                priority: int = 5,
                                request_matching: str = 'url',
                                group_by_endpoint: bool = False,
                                config_file: str = None) -> int:
    """
    Convert TraceTap raw log to WireMock stubs.

    Main conversion workflow:
    1. Load ignore configuration (if provided)
    2. Read and parse TraceTap JSON file
    3. Convert each request to a WireMock stub
    4. Write stub files to output directory

    Args:
        input_file: Path to TraceTap raw log JSON
        output_dir: Directory for WireMock stub files
        priority: Default stub priority
        request_matching: URL matching mode
        group_by_endpoint: Group stubs by endpoint (not implemented)
        config_file: Path to ignore configuration JSON

    Returns:
        0 on success, 1 on error
    """
    # Load ignore configuration if provided
    ignore_config = {}
    if config_file:
        ignore_config = load_ignore_config(config_file)
        print(f"Loaded ignore configuration from: {config_file}")
        if ignore_config:
            print(f"  - Ignoring {len(ignore_config.get('ignore_headers', []))} headers")
            print(f"  - Ignoring {len(ignore_config.get('ignore_query_params', []))} query params")
            print(f"  - Ignoring {len(ignore_config.get('ignore_json_fields', []))} JSON fields")
        print()

    # Read TraceTap log file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"✗ Error: File not found: {input_file}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON in {input_file}: {e}", file=sys.stderr)
        return 1

    # Extract requests array
    requests = data.get('requests', [])
    if not requests:
        print(f"⚠ No requests found in {input_file}", file=sys.stderr)
        return 1

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Show conversion info
    print(f"Converting {len(requests)} requests to WireMock stubs...")
    print(f"Output directory: {output_path.absolute()}")
    print(f"Request matching: {request_matching}")
    print(f"Priority: {priority}")
    print()

    # Convert each request to a stub
    created_files = []
    for idx, record in enumerate(requests, 1):
        try:
            # Create WireMock stub
            stub = create_wiremock_stub(record, priority, request_matching, ignore_config)

            # Generate unique filename
            filename = generate_stub_filename(record, idx)
            output_file = output_path / filename

            # Write stub to file (pretty-printed JSON)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(stub, f, indent=2, ensure_ascii=False)

            created_files.append(filename)

            # Show progress
            method = record['method']
            url = record['url']
            status = record.get('status', 0)
            print(f"✓ [{idx}/{len(requests)}] {method} {url} → {status} → {filename}")

        except Exception as e:
            # Log error but continue with remaining requests
            print(f"✗ Error processing request {idx}: {e}", file=sys.stderr)
            continue

    # Show summary
    print()
    print(f"✓ Created {len(created_files)} WireMock stub files")
    print(f"\nTo use with WireMock:")
    print(f"  1. Copy the mappings to your WireMock directory")
    print(f"  2. Start WireMock: java -jar wiremock-standalone.jar --port 8080")
    print(
        f"  3. Or use Docker: docker run -p 8080:8080 -v {output_path.absolute()}:/home/wiremock/mappings wiremock/wiremock")

    return 0


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

def main():
    """Parse arguments and run conversion."""
    parser = argparse.ArgumentParser(
        description="Convert TraceTap raw log to WireMock stubs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion
  %(prog)s raw_capture.json --output wiremock/mappings/

  # Custom priority (lower = higher priority in WireMock)
  %(prog)s raw_capture.json --output stubs/ --priority 1

  # Use URL pattern matching instead of exact URLs
  %(prog)s raw_capture.json --output stubs/ --matching urlPattern

  # Match only path (ignore query parameters)
  %(prog)s raw_capture.json --output stubs/ --matching urlPath

  # With ignore configuration (recommended!)
  %(prog)s raw_capture.json --output stubs/ --config ignore-config.json

Configuration File:
  The --config option accepts a JSON file specifying fields to ignore in matching.
  This is useful for dynamic values like timestamps, IDs, tokens, etc.

  Example config file (ignore-config.json):
  {
    "ignore_headers": ["Date", "X-Request-Id", "Authorization"],
    "ignore_query_params": ["timestamp", "nonce"],
    "ignore_json_fields": ["createdAt", "id", "token"],
    "ignore_response_json_fields": ["serverTime"],
    "match_headers": false,
    "ignore_request_body": false,
    "ignore_delays": false
  }

  Available config options:
    - ignore_headers: List of HTTP headers to ignore (case-insensitive)
    - ignore_query_params: List of query parameters to ignore
    - ignore_json_fields: List of JSON field names to ignore in request body
    - ignore_response_json_fields: List of JSON fields to ignore in response
    - match_headers: If true, match request headers (default: false)
    - ignore_request_body: If true, don't match request body at all
    - ignore_delays: If true, don't include timing delays in stubs

Request Matching Modes:
  url          - Exact URL with query parameters (default)
  urlPath      - Exact path, any query parameters
  urlPattern   - Regex pattern matching
  urlPathPattern - Path pattern matching

WireMock Usage:
  # Standalone
  java -jar wiremock-standalone.jar --port 8080 --root-dir .

  # Docker
  docker run -p 8080:8080 -v $(pwd)/mappings:/home/wiremock/mappings wiremock/wiremock

For more information, see: https://wiremock.org/docs/request-matching/
        """
    )

    parser.add_argument(
        'input',
        help='TraceTap raw log JSON file'
    )

    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output directory for WireMock mappings'
    )

    parser.add_argument(
        '--priority', '-p',
        type=int,
        default=5,
        help='Stub priority (lower = higher priority, default: 5)'
    )

    parser.add_argument(
        '--matching', '-m',
        choices=['url', 'urlPath', 'urlPattern', 'urlPathPattern'],
        default='url',
        help='Request matching mode (default: url)'
    )

    parser.add_argument(
        '--group-by-endpoint',
        action='store_true',
        help='Group stubs by endpoint in subdirectories (not yet implemented)'
    )

    parser.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        dest='config',
        help='JSON config file specifying fields to ignore in matching'
    )

    args = parser.parse_args()

    return convert_raw_log_to_wiremock(
        args.input,
        args.output,
        args.priority,
        args.matching,
        args.group_by_endpoint,
        args.config
    )


if __name__ == '__main__':
    sys.exit(main())