"""
Element merging logic for collection updates.

Handles intelligent merging of request elements while preserving
user customizations and updating with fresh capture data.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class MergeResult:
    """Result of merging a request."""
    request: Dict[str, Any]
    changes: List[str]  # List of what changed
    preserved: List[str]  # List of what was preserved
    warnings: List[str]  # Any warnings or notes


class ElementMerger:
    """Handles element-by-element merging with preservation logic."""

    def __init__(
        self,
        preserve_tests: bool = True,
        preserve_auth: bool = True,
        preserve_descriptions: bool = True,
        preserve_variables: bool = True
    ):
        """
        Initialize merger with preservation settings.

        Args:
            preserve_tests: Keep existing test scripts
            preserve_auth: Keep existing authentication
            preserve_descriptions: Keep existing descriptions
            preserve_variables: Keep variable references in bodies/URLs
        """
        self.preserve_tests = preserve_tests
        self.preserve_auth = preserve_auth
        self.preserve_descriptions = preserve_descriptions
        self.preserve_variables = preserve_variables

    def merge_request(
        self,
        existing: Dict[str, Any],
        capture: Dict[str, Any],
        confidence: float
    ) -> MergeResult:
        """
        Merge an existing request with capture data.

        Strategy:
        - PRESERVE: Name, descriptions, test scripts, custom headers
        - UPDATE: URL, method, captured headers, body (if no variables)
        - MERGE: Headers (combine custom + captured)
        """
        changes = []
        preserved = []
        warnings = []

        # Extract existing request data
        existing_request = existing.get('request', {})
        existing_name = existing.get('name', 'Unnamed Request')

        # Build merged request
        merged = {
            'name': existing_name,  # Always preserve name
            'request': {}
        }

        # Preserve name
        preserved.append('name')

        # Merge request components
        method_result = self._merge_method(existing_request, capture)
        if method_result['changed']:
            changes.append('method')
            if method_result.get('warning'):
                warnings.append(method_result['warning'])

        url_result = self._merge_url(existing_request, capture, confidence)
        if url_result['changed']:
            changes.append('url')
        if url_result.get('warning'):
            warnings.append(url_result['warning'])

        headers_result = self._merge_headers(existing_request, capture)
        if headers_result['added'] or headers_result['updated']:
            changes.append(f"headers ({headers_result['updated']} updated, {headers_result['added']} added)")
        if headers_result['preserved']:
            preserved.append(f"custom_headers ({headers_result['preserved']})")

        body_result = self._merge_body(existing_request, capture)
        if body_result['changed']:
            changes.append('body')
        if body_result['preserved']:
            preserved.append('body_variables')

        # Build merged request object
        merged['request'] = {
            'method': method_result['method'],
            'url': url_result['url'],
            'header': headers_result['headers']
        }

        if body_result['body']:
            merged['request']['body'] = body_result['body']

        # Preserve description
        if existing_request.get('description'):
            merged['request']['description'] = existing_request['description']
            preserved.append('description')

        # Preserve test scripts
        if self.preserve_tests and existing.get('event'):
            merged['event'] = existing['event']
            preserved.append('test_scripts')

        # Preserve authentication
        if self.preserve_auth and existing_request.get('auth'):
            merged['request']['auth'] = existing_request['auth']
            preserved.append('authentication')

        # Add response example from capture
        if capture.get('res_body') or capture.get('status'):
            merged['response'] = self._create_response_example(capture)
            changes.append('response_example')

        return MergeResult(
            request=merged,
            changes=changes,
            preserved=preserved,
            warnings=warnings
        )

    def _merge_method(
        self,
        existing_request: Dict[str, Any],
        capture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge HTTP method."""
        existing_method = existing_request.get('method', 'GET').upper()
        capture_method = capture.get('method', 'GET').upper()

        if existing_method != capture_method:
            return {
                'method': capture_method,
                'changed': True,
                'warning': f"Method changed: {existing_method} → {capture_method}"
            }

        return {
            'method': capture_method,
            'changed': False
        }

    def _merge_url(
        self,
        existing_request: Dict[str, Any],
        capture: Dict[str, Any],
        confidence: float
    ) -> Dict[str, Any]:
        """Merge URL with confidence-based logic."""
        # Extract existing URL
        existing_url_data = existing_request.get('url', {})
        if isinstance(existing_url_data, str):
            existing_url = existing_url_data
        elif isinstance(existing_url_data, dict):
            existing_url = existing_url_data.get('raw', '')
        else:
            existing_url = ''

        capture_url = capture.get('url', '')

        # High confidence: auto-update
        if confidence >= 0.85:
            return {
                'url': capture_url if capture_url else existing_url,
                'changed': existing_url != capture_url
            }

        # Medium confidence: update with warning
        if confidence >= 0.6:
            return {
                'url': capture_url if capture_url else existing_url,
                'changed': True,
                'warning': f"URL updated (confidence: {confidence:.0%}) - review recommended"
            }

        # Low confidence: preserve existing
        return {
            'url': existing_url,
            'changed': False,
            'warning': f"Low confidence match ({confidence:.0%}) - kept existing URL"
        }

    def _merge_headers(
        self,
        existing_request: Dict[str, Any],
        capture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge headers intelligently.

        Strategy:
        1. Keep user-added custom headers
        2. Update captured headers with new values
        3. Add new headers from capture
        4. Preserve disabled state
        """
        existing_headers = existing_request.get('header', [])
        captured_headers = capture.get('req_headers', {})

        # Convert existing headers to dict for easier processing
        existing_map = {}
        for header in existing_headers:
            key = header.get('key', '').lower()
            existing_map[key] = header

        # Track changes
        captured_keys = {k.lower() for k in captured_headers.keys()}
        updated_count = 0
        added_count = 0
        preserved_count = 0

        result_headers = []

        # Process existing headers
        for header in existing_headers:
            key = header.get('key', '')
            key_lower = key.lower()

            # Skip Content-Length (Postman auto-generates)
            if key_lower == 'content-length':
                continue

            if key_lower in captured_keys:
                # Update with captured value
                captured_value = captured_headers.get(key) or captured_headers.get(key.lower())
                result_headers.append({
                    'key': key,
                    'value': str(captured_value) if captured_value else header.get('value', ''),
                    'disabled': header.get('disabled', False),
                    'type': 'text'
                })
                updated_count += 1
                captured_keys.discard(key_lower)
            else:
                # Keep user-added header unchanged
                result_headers.append(header)
                preserved_count += 1

        # Add new captured headers
        for key in captured_keys:
            # Find original case key
            original_key = None
            for k in captured_headers.keys():
                if k.lower() == key:
                    original_key = k
                    break

            if original_key and original_key.lower() != 'content-length':
                result_headers.append({
                    'key': original_key,
                    'value': str(captured_headers[original_key]),
                    'type': 'text'
                })
                added_count += 1

        return {
            'headers': result_headers,
            'updated': updated_count,
            'added': added_count,
            'preserved': preserved_count
        }

    def _merge_body(
        self,
        existing_request: Dict[str, Any],
        capture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge request body intelligently.

        Strategy:
        - If existing body has variables ({{var}}), preserve it
        - Otherwise, update with captured body
        """
        existing_body = existing_request.get('body', {})
        capture_body = capture.get('req_body', '')

        if not existing_body:
            # No existing body, use capture
            return {
                'body': self._parse_body(capture_body),
                'changed': bool(capture_body),
                'preserved': False
            }

        existing_raw = existing_body.get('raw', '')

        # Check for variable references
        has_variables = '{{' in existing_raw and '}}' in existing_raw

        if has_variables and self.preserve_variables:
            # Preserve body with variables
            return {
                'body': existing_body,
                'changed': False,
                'preserved': True
            }

        # No variables or not preserving - update with capture
        return {
            'body': self._parse_body(capture_body),
            'changed': capture_body != existing_raw,
            'preserved': False
        }

    def _parse_body(self, body_str: str) -> Optional[Dict[str, Any]]:
        """Parse body string into Postman body format."""
        if not body_str:
            return None

        # Try to parse as JSON
        try:
            parsed = json.loads(body_str)
            return {
                'mode': 'raw',
                'raw': json.dumps(parsed, indent=2),
                'options': {
                    'raw': {
                        'language': 'json'
                    }
                }
            }
        except (json.JSONDecodeError, TypeError):
            # Not JSON, return as raw text
            return {
                'mode': 'raw',
                'raw': body_str
            }

    def _create_response_example(self, capture: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create response example from capture data."""
        response_body = capture.get('res_body', '')
        status_code = capture.get('status', 200)

        # Determine status name
        status_names = {
            200: 'OK',
            201: 'Created',
            204: 'No Content',
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            500: 'Internal Server Error'
        }
        status_name = status_names.get(status_code, 'Response')

        example = {
            'name': f'Example Response ({status_code})',
            'status': status_name,
            'code': status_code,
            '_postman_previewlanguage': 'json',
            'header': [],
            'body': response_body
        }

        return [example]
