"""
Contract Creator - Generate OpenAPI 3.0 Contracts from Traffic

Converts captured HTTP traffic into OpenAPI 3.0 specifications.
Infers schemas, detects parameters, and generates valid contracts.
"""

import json
import re
import yaml
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, parse_qs

# Reuse schema inferrer from assertion builder
from ..generators.assertion_builder import SchemaInferrer
from ..common.progress import ProgressBar, StatusLine


class ContractCreator:
    """
    Creates OpenAPI 3.0 contracts from captured HTTP traffic

    Features:
    - Schema inference from JSON responses
    - Path parameter detection (IDs, UUIDs, slugs)
    - Request/response examples
    - Logical endpoint grouping
    - Valid OpenAPI 3.0 YAML output
    """

    def __init__(self, title: str = "API", version: str = "1.0.0", base_url: Optional[str] = None):
        """
        Initialize contract creator

        Args:
            title: API title for OpenAPI spec
            version: API version for OpenAPI spec
            base_url: Base URL for servers section
        """
        self.title = title
        self.version = version
        self.base_url = base_url
        self.schema_inferrer = SchemaInferrer()

    def create_contract(self, requests: List[Dict], verbose: bool = False) -> Dict[str, Any]:
        """
        Create OpenAPI 3.0 contract from captured requests

        Args:
            requests: List of captured HTTP requests
            verbose: Show progress indicators

        Returns:
            OpenAPI 3.0 specification as dictionary
        """
        if not requests:
            return self._empty_contract()

        status = StatusLine(verbose)

        # Extract base URL if not provided
        status.start(f"Analyzing {len(requests)} requests...")
        progress = ProgressBar(len(requests), label="Analyzing", width=20)

        if not self.base_url and requests:
            first_url = requests[0].get('url', '')
            if first_url:
                parsed = urlparse(first_url)
                self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Group requests by endpoint
        endpoint_groups = self._group_by_endpoint(requests)
        progress.finish()
        status.progress(f"Found {len(endpoint_groups)} unique endpoints")

        # Build paths section
        status.start("Generating OpenAPI operations...")
        progress = ProgressBar(len(endpoint_groups), label="Operations", width=20)

        paths = {}
        for endpoint_key, endpoint_requests in endpoint_groups.items():
            method, path_template = self._parse_endpoint_key(endpoint_key)

            if path_template not in paths:
                paths[path_template] = {}

            paths[path_template][method.lower()] = self._create_operation(
                method,
                path_template,
                endpoint_requests
            )
            progress.update()
        progress.finish()

        # Build complete OpenAPI spec
        status.start("Building OpenAPI specification...")
        spec = {
            'openapi': '3.0.0',
            'info': {
                'title': self.title,
                'version': self.version,
                'description': f'API contract generated from captured traffic on {datetime.now().strftime("%Y-%m-%d")}',
            },
            'servers': [
                {'url': self.base_url or 'http://localhost:8080'}
            ],
            'paths': paths,
            'components': {
                'schemas': {},
                'securitySchemes': self._detect_security_schemes(requests)
            }
        }

        return spec

    def save_contract(self, requests: List[Dict], output_file: str, verbose: bool = False) -> bool:
        """
        Create and save contract to YAML file

        Args:
            requests: List of captured requests
            output_file: Path to save contract YAML
            verbose: Show progress indicators

        Returns:
            True if successful, False otherwise
        """
        try:
            contract = self.create_contract(requests, verbose=verbose)

            status = StatusLine(verbose)
            status.start("Writing contract file...")

            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as f:
                yaml.dump(contract, f, default_flow_style=False, sort_keys=False)

            return True
        except Exception as e:
            print(f"Error saving contract: {e}")
            return False

    def _empty_contract(self) -> Dict[str, Any]:
        """Create empty OpenAPI contract"""
        return {
            'openapi': '3.0.0',
            'info': {
                'title': self.title,
                'version': self.version
            },
            'paths': {}
        }

    def _group_by_endpoint(self, requests: List[Dict]) -> Dict[str, List[Dict]]:
        """Group requests by endpoint (method + normalized path)"""
        groups = defaultdict(list)

        for req in requests:
            endpoint_key = self._get_endpoint_key(req)
            groups[endpoint_key].append(req)

        return dict(groups)

    def _get_endpoint_key(self, request: Dict) -> str:
        """Get endpoint key for grouping"""
        method = request.get('method', 'GET').upper()
        url = request.get('url', '')

        parsed = urlparse(url)
        path = self._normalize_path(parsed.path)

        return f"{method}::{path}"

    def _parse_endpoint_key(self, endpoint_key: str) -> Tuple[str, str]:
        """Parse endpoint key into method and path"""
        parts = endpoint_key.split('::', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return 'GET', parts[0]

    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing IDs with parameters"""
        if not path:
            return '/'

        parts = path.split('/')
        normalized = []

        for part in parts:
            if not part:
                normalized.append(part)
                continue

            # UUID pattern
            if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', part, re.IGNORECASE):
                normalized.append('{id}')
            # Numeric ID (6+ digits or all digits)
            elif part.isdigit():
                normalized.append('{id}')
            # MongoDB ObjectId
            elif re.match(r'^[0-9a-f]{24}$', part):
                normalized.append('{id}')
            # Keep as-is
            else:
                normalized.append(part)

        return '/'.join(normalized)

    def _create_operation(
        self,
        method: str,
        path: str,
        requests: List[Dict]
    ) -> Dict[str, Any]:
        """Create OpenAPI operation object for an endpoint"""
        operation = {
            'summary': self._generate_summary(method, path),
            'operationId': self._generate_operation_id(method, path),
            'tags': self._extract_tags(path),
            'responses': {}
        }

        # Add path parameters
        path_params = self._extract_path_parameters(path)
        if path_params:
            operation['parameters'] = path_params

        # Add query parameters
        query_params = self._extract_query_parameters(requests)
        if query_params:
            if 'parameters' not in operation:
                operation['parameters'] = []
            operation['parameters'].extend(query_params)

        # Add request body for POST/PUT/PATCH
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            request_body = self._create_request_body(requests)
            if request_body:
                operation['requestBody'] = request_body

        # Add responses
        operation['responses'] = self._create_responses(requests)

        # Add security if detected
        security = self._detect_operation_security(requests)
        if security:
            operation['security'] = security

        return operation

    def _generate_summary(self, method: str, path: str) -> str:
        """Generate human-readable summary for operation"""
        # Extract resource name from path
        parts = [p for p in path.split('/') if p and '{' not in p]
        resource = parts[-1] if parts else 'resource'

        method_map = {
            'GET': f'Get {resource}',
            'POST': f'Create {resource}',
            'PUT': f'Update {resource}',
            'PATCH': f'Partially update {resource}',
            'DELETE': f'Delete {resource}'
        }

        return method_map.get(method.upper(), f'{method} {path}')

    def _generate_operation_id(self, method: str, path: str) -> str:
        """Generate operationId"""
        # Convert path to camelCase operation ID
        parts = [p for p in path.split('/') if p]

        # Remove parameters
        parts = [p.replace('{', '').replace('}', '') for p in parts]

        # Build operation ID
        if not parts:
            return method.lower()

        operation_id = method.lower() + ''.join(p.capitalize() for p in parts)
        return operation_id

    def _extract_tags(self, path: str) -> List[str]:
        """Extract tags from path (typically first segment)"""
        parts = [p for p in path.split('/') if p and '{' not in p]
        if parts:
            return [parts[0]]
        return ['default']

    def _extract_path_parameters(self, path: str) -> List[Dict[str, Any]]:
        """Extract path parameters from path template"""
        params = []

        # Find all {param} in path
        param_names = re.findall(r'\{([^}]+)\}', path)

        for param_name in param_names:
            param = {
                'name': param_name,
                'in': 'path',
                'required': True,
                'schema': {
                    'type': 'string'  # Default to string, could be improved
                },
                'description': f'The {param_name} parameter'
            }
            params.append(param)

        return params

    def _extract_query_parameters(self, requests: List[Dict]) -> List[Dict[str, Any]]:
        """Extract query parameters from requests"""
        # Collect all query parameters seen
        query_params = defaultdict(set)

        for req in requests:
            url = req.get('url', '')
            parsed = urlparse(url)

            if parsed.query:
                params = parse_qs(parsed.query)
                for key, values in params.items():
                    for value in values:
                        query_params[key].add(value)

        # Convert to OpenAPI parameters
        parameters = []
        for param_name, values in query_params.items():
            # Infer type from values
            param_type = 'string'
            if values and all(v.isdigit() for v in values):
                param_type = 'integer'

            param = {
                'name': param_name,
                'in': 'query',
                'required': False,
                'schema': {
                    'type': param_type
                },
                'description': f'Query parameter: {param_name}'
            }

            # Add example if available
            if values:
                param['example'] = list(values)[0]

            parameters.append(param)

        return parameters

    def _create_request_body(self, requests: List[Dict]) -> Optional[Dict[str, Any]]:
        """Create request body specification"""
        # Find requests with bodies
        bodies = []
        for req in requests:
            body = req.get('body')
            if body:
                try:
                    parsed = json.loads(body)
                    bodies.append(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass

        if not bodies:
            return None

        # Infer schema from bodies
        # Use first body as representative (could merge schemas)
        schema = self.schema_inferrer.infer_schema(bodies[0])

        return {
            'required': True,
            'content': {
                'application/json': {
                    'schema': schema,
                    'example': bodies[0]
                }
            }
        }

    def _create_responses(self, requests: List[Dict]) -> Dict[str, Any]:
        """Create responses section for operation"""
        responses = {}

        # Group by status code
        status_groups = defaultdict(list)
        for req in requests:
            status = req.get('status_code', 200)
            status_groups[status].append(req)

        # Create response for each status code
        for status_code, status_requests in status_groups.items():
            responses[str(status_code)] = self._create_response(status_code, status_requests)

        # Ensure at least one response
        if not responses:
            responses['200'] = {
                'description': 'Successful response'
            }

        return responses

    def _create_response(self, status_code: int, requests: List[Dict]) -> Dict[str, Any]:
        """Create single response specification"""
        response = {
            'description': self._get_status_description(status_code)
        }

        # Extract response bodies
        bodies = []
        for req in requests:
            body = req.get('response_body')
            if body:
                try:
                    parsed = json.loads(body)
                    bodies.append(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass

        if bodies:
            # Infer schema from response bodies
            schema = self.schema_inferrer.infer_schema(bodies[0])

            response['content'] = {
                'application/json': {
                    'schema': schema,
                    'example': bodies[0]
                }
            }

        return response

    def _get_status_description(self, status_code: int) -> str:
        """Get description for HTTP status code"""
        descriptions = {
            200: 'Successful response',
            201: 'Resource created successfully',
            204: 'No content',
            400: 'Bad request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Resource not found',
            422: 'Validation error',
            429: 'Too many requests',
            500: 'Internal server error',
            503: 'Service unavailable'
        }
        return descriptions.get(status_code, f'Response with status {status_code}')

    def _detect_security_schemes(self, requests: List[Dict]) -> Dict[str, Any]:
        """Detect security schemes from requests"""
        schemes = {}

        # Check for Authorization headers
        has_bearer = False
        has_basic = False
        has_api_key = False

        for req in requests:
            headers = req.get('headers', {})

            # Check Authorization header
            auth_header = headers.get('Authorization') or headers.get('authorization')
            if auth_header:
                if 'Bearer' in auth_header:
                    has_bearer = True
                elif 'Basic' in auth_header:
                    has_basic = True

            # Check for API key headers
            if 'X-API-Key' in headers or 'x-api-key' in headers:
                has_api_key = True

        # Add detected schemes
        if has_bearer:
            schemes['bearerAuth'] = {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT'
            }

        if has_basic:
            schemes['basicAuth'] = {
                'type': 'http',
                'scheme': 'basic'
            }

        if has_api_key:
            schemes['apiKeyAuth'] = {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API-Key'
            }

        return schemes

    def _detect_operation_security(self, requests: List[Dict]) -> Optional[List[Dict]]:
        """Detect security requirements for operation"""
        # Check if any request has authorization
        has_auth = any(
            req.get('headers', {}).get('Authorization') or
            req.get('headers', {}).get('authorization')
            for req in requests
        )

        if has_auth:
            # Detect scheme type
            for req in requests:
                auth_header = req.get('headers', {}).get('Authorization') or \
                             req.get('headers', {}).get('authorization')
                if auth_header:
                    if 'Bearer' in auth_header:
                        return [{'bearerAuth': []}]
                    elif 'Basic' in auth_header:
                        return [{'basicAuth': []}]

        # Check for API key
        has_api_key = any(
            'X-API-Key' in req.get('headers', {}) or
            'x-api-key' in req.get('headers', {})
            for req in requests
        )

        if has_api_key:
            return [{'apiKeyAuth': []}]

        return None


def create_contract_from_traffic(
    json_file: str,
    output_file: str,
    title: str = "API",
    version: str = "1.0.0",
    verbose: bool = True
) -> bool:
    """
    Convenience function to create OpenAPI contract from traffic file

    Args:
        json_file: Path to captured traffic JSON
        output_file: Path to save OpenAPI YAML
        title: API title
        version: API version
        verbose: Print status messages

    Returns:
        True if successful, False otherwise
    """
    try:
        status = StatusLine(verbose)

        # Load traffic
        status.start(f"Loading traffic from {json_file}...")
        with open(json_file, 'r') as f:
            data = json.load(f)

        requests = data.get('requests', [])

        if not requests:
            if verbose:
                print("No requests found in traffic file")
            return False

        if verbose:
            print(f"📋 Creating OpenAPI contract from {len(requests)} requests...")

        # Extract base URL from first request
        base_url = None
        if requests:
            first_url = requests[0].get('url', '')
            if first_url:
                parsed = urlparse(first_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Create contract
        creator = ContractCreator(title=title, version=version, base_url=base_url)
        success = creator.save_contract(requests, output_file, verbose=verbose)

        if success and verbose:
            print()
            status.success(f"Contract created ({len(requests)} requests analyzed)")

            # Count endpoints
            contract = creator.create_contract(requests, verbose=False)
            endpoint_count = sum(len(methods) for methods in contract.get('paths', {}).values())
            print(f"  • {endpoint_count} endpoints documented")
            print(f"  • Saved to {output_file}")
            print(f"  • OpenAPI 3.0 specification")

        return success

    except FileNotFoundError:
        if verbose:
            status = StatusLine(verbose)
            status.error(f"File not found: {json_file}")
        return False
    except json.JSONDecodeError as e:
        if verbose:
            status = StatusLine(verbose)
            status.error(f"Invalid JSON in {json_file}: {e}")
        return False
    except Exception as e:
        if verbose:
            status = StatusLine(verbose)
            status.error(f"Error creating contract: {e}")
        return False
