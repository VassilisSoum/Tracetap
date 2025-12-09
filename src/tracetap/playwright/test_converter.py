"""
Convert Postman requests to Playwright test cases.

Handles HTTP method mapping, headers, body, and request structure.
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .postman_parser import PostmanRequest, CollectionStructure


@dataclass
class PlaywrightTest:
    """Represents a Playwright test case."""
    name: str
    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    assertions: List[str] = field(default_factory=list)
    variable_extractions: List[Dict[str, str]] = field(default_factory=list)
    folder_path: List[str] = field(default_factory=list)
    description: Optional[str] = None
    setup_code: List[str] = field(default_factory=list)


@dataclass
class PlaywrightTestFile:
    """Represents a complete Playwright test file."""
    name: str
    imports: List[str] = field(default_factory=list)
    fixtures: List[str] = field(default_factory=list)
    tests: List[PlaywrightTest] = field(default_factory=list)
    describe_blocks: Dict[str, List[PlaywrightTest]] = field(default_factory=dict)


class TestConverter:
    """Convert Postman requests to Playwright tests."""

    def __init__(self, variables: Optional[Dict[str, str]] = None):
        """
        Initialize converter.

        Args:
            variables: Collection variables for expansion
        """
        self.variables = variables or {}

    def convert_request(self, request: PostmanRequest) -> PlaywrightTest:
        """
        Convert single Postman request to Playwright test.

        Args:
            request: PostmanRequest to convert

        Returns:
            PlaywrightTest object
        """
        # Expand variables in URL
        url = self._expand_variables(request.url)

        # Convert headers
        headers = self._convert_headers(request.headers)

        # Convert body
        body = self._convert_body(request.body)

        # Create test name
        test_name = self._sanitize_test_name(request.name)

        return PlaywrightTest(
            name=test_name,
            method=request.method.lower(),
            url=url,
            headers=headers,
            body=body,
            folder_path=request.folder_path,
            description=request.description
        )

    def convert_collection(self, structure: CollectionStructure) -> PlaywrightTestFile:
        """
        Convert entire collection to Playwright test file.

        Args:
            structure: CollectionStructure from parser

        Returns:
            PlaywrightTestFile with all tests
        """
        tests = [self.convert_request(req) for req in structure.requests]

        # Group by folder
        describe_blocks = self._group_by_folder(tests)

        return PlaywrightTestFile(
            name=self._sanitize_test_name(structure.name),
            tests=tests,
            describe_blocks=describe_blocks
        )

    def _expand_variables(self, text: str) -> str:
        """
        Expand {{variable}} references to TypeScript template literals.

        Args:
            text: String that may contain {{variable}} references

        Returns:
            Text with variables converted to ${variable} format
        """
        if not text:
            return text

        # Replace {{variable}} with ${variable} for TypeScript template literals
        def replace_var(match):
            var_name = match.group(1)
            # Convert to camelCase if snake_case
            camel_var = self._to_camel_case(var_name)
            return f"${{{camel_var}}}"

        return re.sub(r'\{\{([^}]+)\}\}', replace_var, text)

    def _to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])

    def _convert_headers(self, headers: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Convert Postman headers to Playwright format.

        Args:
            headers: List of header objects from Postman

        Returns:
            Dictionary of header key-value pairs
        """
        result = {}

        for header in headers:
            if isinstance(header, dict):
                # Skip disabled headers
                if header.get('disabled', False):
                    continue

                key = header.get('key', '')
                value = header.get('value', '')

                # Expand variables in value
                value = self._expand_variables(value)

                if key:
                    result[key] = value

        return result

    def _convert_body(self, body: Optional[Dict[str, Any]]) -> Any:
        """
        Convert Postman body to Playwright format.

        Args:
            body: Body data from Postman parser

        Returns:
            Body in appropriate format for Playwright
        """
        if not body:
            return None

        mode = body.get('mode', '')

        if mode == 'raw':
            content = body.get('content')

            # If content is already a dict/list (JSON), return it
            if isinstance(content, (dict, list)):
                return self._expand_variables_in_object(content)

            # If it's a string, expand variables
            if isinstance(content, str):
                expanded = self._expand_variables(content)
                # Try to parse as JSON
                try:
                    return json.loads(expanded.replace('${', '{{').replace('}', '}}'))
                except (json.JSONDecodeError, ValueError):
                    return expanded

        elif mode == 'formdata':
            formdata = {}
            for field in body.get('formdata', []):
                if isinstance(field, dict) and not field.get('disabled', False):
                    key = field.get('key', '')
                    value = field.get('value', '')
                    if key:
                        formdata[key] = self._expand_variables(value)
            return formdata

        elif mode == 'urlencoded':
            urlencoded = {}
            for field in body.get('urlencoded', []):
                if isinstance(field, dict) and not field.get('disabled', False):
                    key = field.get('key', '')
                    value = field.get('value', '')
                    if key:
                        urlencoded[key] = self._expand_variables(value)
            return urlencoded

        return None

    def _expand_variables_in_object(self, obj: Any) -> Any:
        """Recursively expand variables in nested objects."""
        if isinstance(obj, dict):
            return {k: self._expand_variables_in_object(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_variables_in_object(item) for item in obj]
        elif isinstance(obj, str):
            return self._expand_variables(obj)
        return obj

    def _sanitize_test_name(self, name: str) -> str:
        """
        Sanitize test name for TypeScript.

        Args:
            name: Original test name

        Returns:
            Sanitized name safe for use in test()
        """
        # Remove special characters, keep alphanumeric, spaces, hyphens
        sanitized = re.sub(r'[^\w\s-]', '', name)

        # Collapse multiple spaces
        sanitized = re.sub(r'\s+', ' ', sanitized)

        return sanitized.strip()

    def _group_by_folder(self, tests: List[PlaywrightTest]) -> Dict[str, List[PlaywrightTest]]:
        """
        Group tests by their folder path for test.describe() blocks.

        Args:
            tests: List of PlaywrightTest objects

        Returns:
            Dictionary mapping folder paths to tests
        """
        grouped = {}

        for test in tests:
            # Create folder key
            folder_key = ' > '.join(test.folder_path) if test.folder_path else '__root__'

            if folder_key not in grouped:
                grouped[folder_key] = []

            grouped[folder_key].append(test)

        return grouped

    def detect_variable_usage(self, tests: List[PlaywrightTest]) -> List[str]:
        """
        Detect which collection variables are actually used in tests.

        Args:
            tests: List of tests to analyze

        Returns:
            List of variable names used
        """
        used_vars = set()

        for test in tests:
            # Check URL
            used_vars.update(self._extract_variable_names(test.url))

            # Check headers
            for value in test.headers.values():
                used_vars.update(self._extract_variable_names(value))

            # Check body
            if test.body:
                body_str = json.dumps(test.body) if not isinstance(test.body, str) else test.body
                used_vars.update(self._extract_variable_names(body_str))

        return sorted(list(used_vars))

    def _extract_variable_names(self, text: str) -> set:
        """Extract variable names from text with ${var} format."""
        if not text:
            return set()

        # Find all ${variable} patterns
        matches = re.findall(r'\$\{([^}]+)\}', text)
        return set(matches)
