"""
Parse Postman Collection v2.1 JSON files.

Extracts requests, variables, authentication config, and folder structure.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PostmanRequest:
    """Represents a single Postman request."""
    name: str
    method: str
    url: str
    headers: List[Dict[str, str]] = field(default_factory=list)
    body: Optional[Dict[str, Any]] = None
    test_script: Optional[List[str]] = None
    pre_request_script: Optional[List[str]] = None
    description: Optional[str] = None
    folder_path: List[str] = field(default_factory=list)
    raw_request: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthConfig:
    """Authentication configuration from collection."""
    auth_type: str  # bearer, apikey, basic, oauth2, etc.
    token_variable: Optional[str] = None
    header_name: Optional[str] = None
    prefix: Optional[str] = None  # e.g., "Bearer"


@dataclass
class CollectionStructure:
    """Complete collection structure."""
    name: str
    description: Optional[str]
    requests: List[PostmanRequest]
    variables: Dict[str, str]
    auth_config: Optional[AuthConfig]
    folders: List[str]


class PostmanParser:
    """Parse Postman Collection v2.1 JSON."""

    def __init__(self, collection_path: str):
        """
        Initialize parser.

        Args:
            collection_path: Path to Postman collection JSON file
        """
        self.collection_path = Path(collection_path)
        self.collection = self._load_collection()

    def _load_collection(self) -> Dict[str, Any]:
        """Load and validate Postman collection."""
        if not self.collection_path.exists():
            raise FileNotFoundError(f"Collection file not found: {self.collection_path}")

        with open(self.collection_path, 'r', encoding='utf-8') as f:
            collection = json.load(f)

        # Validate schema
        if 'info' not in collection:
            raise ValueError("Invalid Postman collection: missing 'info' field")

        schema = collection.get('info', {}).get('schema', '')
        if 'v2.1' not in schema:
            print(f"Warning: Collection schema is {schema}, expected v2.1")

        return collection

    def extract_structure(self) -> CollectionStructure:
        """Extract complete collection structure."""
        info = self.collection.get('info', {})

        return CollectionStructure(
            name=info.get('name', 'API Tests'),
            description=info.get('description'),
            requests=self.get_requests(),
            variables=self.get_variables(),
            auth_config=self.get_auth_config(),
            folders=self._get_folder_names()
        )

    def get_requests(self) -> List[PostmanRequest]:
        """
        Get all requests in order, including nested requests in folders.

        Returns:
            List of PostmanRequest objects
        """
        requests = []
        items = self.collection.get('item', [])
        self._extract_requests_recursive(items, [], requests)
        return requests

    def _extract_requests_recursive(
        self,
        items: List[Dict[str, Any]],
        folder_path: List[str],
        requests: List[PostmanRequest]
    ):
        """Recursively extract requests from items and folders."""
        for item in items:
            if 'request' in item:
                # This is a request
                request = self._parse_request(item, folder_path)
                requests.append(request)
            elif 'item' in item:
                # This is a folder
                folder_name = item.get('name', 'Unnamed Folder')
                new_path = folder_path + [folder_name]
                self._extract_requests_recursive(item['item'], new_path, requests)

    def _parse_request(
        self,
        item: Dict[str, Any],
        folder_path: List[str]
    ) -> PostmanRequest:
        """Parse a single request item."""
        request_data = item.get('request', {})

        # Extract URL
        url = self._extract_url(request_data)

        # Extract headers
        headers = []
        for header in request_data.get('header', []):
            if isinstance(header, dict):
                headers.append({
                    'key': header.get('key', ''),
                    'value': header.get('value', ''),
                    'disabled': header.get('disabled', False)
                })

        # Extract body
        body = None
        if 'body' in request_data:
            body = self._parse_body(request_data['body'])

        # Extract test scripts
        test_script = None
        pre_request_script = None

        for event in item.get('event', []):
            listen_type = event.get('listen')
            script = event.get('script', {})
            exec_lines = script.get('exec', [])

            if listen_type == 'test' and exec_lines:
                test_script = exec_lines
            elif listen_type == 'prerequest' and exec_lines:
                pre_request_script = exec_lines

        return PostmanRequest(
            name=item.get('name', 'Unnamed Request'),
            method=request_data.get('method', 'GET').upper(),
            url=url,
            headers=headers,
            body=body,
            test_script=test_script,
            pre_request_script=pre_request_script,
            description=request_data.get('description'),
            folder_path=folder_path,
            raw_request=request_data
        )

    def _extract_url(self, request_data: Dict[str, Any]) -> str:
        """Extract URL from various Postman formats."""
        url_data = request_data.get('url', '')

        # String format
        if isinstance(url_data, str):
            return url_data

        # Object format
        if isinstance(url_data, dict):
            # Try raw URL first
            raw = url_data.get('raw')
            if raw:
                return raw

            # Reconstruct from components
            protocol = url_data.get('protocol', 'https')
            host = url_data.get('host', [])
            path = url_data.get('path', [])
            query = url_data.get('query', [])

            # Build URL
            url_parts = []

            # Host
            if host:
                host_str = '.'.join(host) if isinstance(host, list) else str(host)
                url_parts.append(f"{protocol}://{host_str}")

            # Path
            if path:
                path_str = '/'.join(path) if isinstance(path, list) else str(path)
                if not path_str.startswith('/'):
                    path_str = '/' + path_str
                url_parts.append(path_str)

            # Query parameters
            if query and isinstance(query, list):
                query_params = []
                for param in query:
                    if isinstance(param, dict) and not param.get('disabled', False):
                        key = param.get('key', '')
                        value = param.get('value', '')
                        query_params.append(f"{key}={value}")
                if query_params:
                    url_parts.append('?' + '&'.join(query_params))

            return ''.join(url_parts)

        return ''

    def _parse_body(self, body_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse request body."""
        mode = body_data.get('mode', '')

        if mode == 'raw':
            raw_content = body_data.get('raw', '')
            try:
                # Try to parse as JSON
                import json
                return {
                    'mode': 'raw',
                    'content': json.loads(raw_content) if raw_content else None,
                    'raw': raw_content
                }
            except (json.JSONDecodeError, ValueError):
                # Not JSON, keep as string
                return {
                    'mode': 'raw',
                    'content': raw_content,
                    'raw': raw_content
                }
        elif mode == 'formdata':
            return {
                'mode': 'formdata',
                'formdata': body_data.get('formdata', [])
            }
        elif mode == 'urlencoded':
            return {
                'mode': 'urlencoded',
                'urlencoded': body_data.get('urlencoded', [])
            }

        return None

    def get_variables(self) -> Dict[str, str]:
        """
        Extract collection variables as key-value dictionary.

        Returns:
            Dictionary of variable names to values
        """
        variables = {}

        for var in self.collection.get('variable', []):
            if isinstance(var, dict):
                key = var.get('key')
                value = var.get('value')
                if key:
                    variables[key] = value if value is not None else ''

        return variables

    def get_auth_config(self) -> Optional[AuthConfig]:
        """
        Detect authentication configuration from collection.

        Returns:
            AuthConfig if auth is configured, None otherwise
        """
        auth = self.collection.get('auth')

        if not auth:
            return None

        auth_type = auth.get('type', '')

        if auth_type == 'bearer':
            bearer_data = auth.get('bearer', [])
            token_var = None
            for item in bearer_data:
                if isinstance(item, dict) and item.get('key') == 'token':
                    token_var = item.get('value')

            return AuthConfig(
                auth_type='bearer',
                token_variable=token_var,
                header_name='Authorization',
                prefix='Bearer'
            )

        elif auth_type == 'apikey':
            apikey_data = auth.get('apikey', [])
            key_name = None
            value = None
            in_location = 'header'

            for item in apikey_data:
                if isinstance(item, dict):
                    if item.get('key') == 'key':
                        key_name = item.get('value')
                    elif item.get('key') == 'value':
                        value = item.get('value')
                    elif item.get('key') == 'in':
                        in_location = item.get('value', 'header')

            return AuthConfig(
                auth_type='apikey',
                token_variable=value,
                header_name=key_name
            )

        # Add more auth types as needed
        return AuthConfig(auth_type=auth_type)

    def _get_folder_names(self) -> List[str]:
        """Extract all folder names in collection."""
        folders = []
        self._extract_folders_recursive(self.collection.get('item', []), folders)
        return folders

    def _extract_folders_recursive(self, items: List[Dict[str, Any]], folders: List[str]):
        """Recursively extract folder names."""
        for item in items:
            if 'item' in item and 'request' not in item:
                # This is a folder
                folder_name = item.get('name', 'Unnamed Folder')
                folders.append(folder_name)
                self._extract_folders_recursive(item['item'], folders)
