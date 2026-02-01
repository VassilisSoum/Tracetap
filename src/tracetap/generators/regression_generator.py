"""
Regression Test Generator

Converts captured HTTP traffic into Playwright regression test suites.
Generates valid, runnable tests with smart grouping and variable extraction.
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, parse_qs

from .assertion_builder import AssertionBuilder


class VariableExtractor:
    """Extract and track dynamic variables from requests (IDs, tokens, UUIDs)"""

    # Patterns for detecting dynamic values
    UUID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)
    NUMERIC_ID_PATTERN = re.compile(r'\b\d{6,}\b')  # 6+ digit numbers (likely IDs)
    TOKEN_PATTERN = re.compile(r'[A-Za-z0-9_-]{20,}')  # Long alphanumeric strings (likely tokens)
    MONGO_ID_PATTERN = re.compile(r'\b[0-9a-f]{24}\b')  # MongoDB ObjectIds

    def __init__(self):
        self.variables: Dict[str, str] = {}  # Maps actual values to variable names
        self.counters: Dict[str, int] = defaultdict(int)  # Counters for variable naming

    def extract_from_url(self, url: str) -> Tuple[str, Dict[str, str]]:
        """
        Extract variables from URL and return parameterized URL

        Args:
            url: Original URL

        Returns:
            Tuple of (parameterized_url, extracted_variables)
        """
        parsed = urlparse(url)
        path = parsed.path
        extracted = {}

        # Extract UUIDs
        for match in self.UUID_PATTERN.finditer(path):
            uuid_val = match.group()
            if uuid_val not in self.variables:
                var_name = self._generate_var_name('uuid')
                self.variables[uuid_val] = var_name
                extracted[var_name] = uuid_val
            path = path.replace(uuid_val, f'${{{self.variables[uuid_val]}}}')

        # Extract numeric IDs
        path_parts = path.split('/')
        for i, part in enumerate(path_parts):
            if self.NUMERIC_ID_PATTERN.fullmatch(part):
                if part not in self.variables:
                    var_name = self._generate_var_name('id')
                    self.variables[part] = var_name
                    extracted[var_name] = part
                path_parts[i] = f'${{{self.variables[part]}}}'

        path = '/'.join(path_parts)

        # Reconstruct URL
        parameterized = f"{parsed.scheme}://{parsed.netloc}{path}"
        if parsed.query:
            parameterized += f"?{parsed.query}"

        return parameterized, extracted

    def extract_from_body(self, body: Optional[str]) -> Dict[str, str]:
        """Extract variables from request/response body"""
        if not body:
            return {}

        extracted = {}

        try:
            data = json.loads(body)
            self._extract_from_json(data, extracted)
        except (json.JSONDecodeError, TypeError):
            pass

        return extracted

    def _extract_from_json(self, data: Any, extracted: Dict[str, str], path: str = ''):
        """Recursively extract variables from JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                if isinstance(value, str):
                    # Check for UUID
                    if self.UUID_PATTERN.fullmatch(value):
                        if value not in self.variables:
                            var_name = self._generate_var_name(f'{key}_uuid')
                            self.variables[value] = var_name
                            extracted[var_name] = value

                    # Check for numeric ID
                    elif value.isdigit() and len(value) >= 6:
                        if value not in self.variables:
                            var_name = self._generate_var_name(f'{key}_id')
                            self.variables[value] = var_name
                            extracted[var_name] = value

                elif isinstance(value, (dict, list)):
                    self._extract_from_json(value, extracted, current_path)

        elif isinstance(data, list):
            for item in data:
                self._extract_from_json(item, extracted, path)

    def _generate_var_name(self, prefix: str) -> str:
        """Generate unique variable name"""
        self.counters[prefix] += 1
        count = self.counters[prefix]
        return f"{prefix}{count}" if count > 1 else prefix


class RequestGrouper:
    """Group requests by endpoint and logical flows"""

    def __init__(self):
        self.endpoint_groups: Dict[str, List[Dict]] = defaultdict(list)
        self.flow_groups: List[List[Dict]] = []

    def group_by_endpoint(self, requests: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group requests by endpoint (method + path pattern)

        Args:
            requests: List of captured requests

        Returns:
            Dictionary mapping endpoint to list of requests
        """
        for req in requests:
            endpoint = self._get_endpoint_key(req)
            self.endpoint_groups[endpoint].append(req)

        return dict(self.endpoint_groups)

    def group_by_flow(self, requests: List[Dict], time_gap_seconds: int = 30) -> List[List[Dict]]:
        """
        Group requests into logical flows based on timing

        Args:
            requests: List of captured requests
            time_gap_seconds: Max seconds between requests in same flow

        Returns:
            List of flows (each flow is a list of requests)
        """
        if not requests:
            return []

        current_flow = [requests[0]]
        flows = []

        for i in range(1, len(requests)):
            prev_time = self._parse_timestamp(requests[i - 1].get('timestamp', ''))
            curr_time = self._parse_timestamp(requests[i].get('timestamp', ''))

            time_diff = (curr_time - prev_time) if (curr_time and prev_time) else 0

            if time_diff <= time_gap_seconds:
                current_flow.append(requests[i])
            else:
                flows.append(current_flow)
                current_flow = [requests[i]]

        if current_flow:
            flows.append(current_flow)

        self.flow_groups = flows
        return flows

    def _get_endpoint_key(self, request: Dict) -> str:
        """Get endpoint key for grouping (method + normalized path)"""
        method = request.get('method', 'GET')
        url = request.get('url', '')
        parsed = urlparse(url)
        path = self._normalize_path(parsed.path)
        return f"{method} {path}"

    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing IDs with placeholders"""
        parts = path.split('/')
        normalized = []

        for part in parts:
            # Replace UUIDs
            if re.match(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', part, re.IGNORECASE):
                normalized.append('{uuid}')
            # Replace numeric IDs
            elif part.isdigit():
                normalized.append('{id}')
            # Replace MongoDB IDs
            elif re.match(r'[0-9a-f]{24}', part):
                normalized.append('{objectId}')
            else:
                normalized.append(part)

        return '/'.join(normalized)

    def _parse_timestamp(self, timestamp: str) -> Optional[float]:
        """Parse timestamp to seconds since epoch"""
        if not timestamp:
            return None

        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.timestamp()
        except (ValueError, AttributeError):
            return None


class PlaywrightGenerator:
    """Generate Playwright test code from grouped requests"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        assertion_builder: Optional[AssertionBuilder] = None
    ):
        self.base_url = base_url
        self.variable_extractor = VariableExtractor()
        self.assertion_builder = assertion_builder or AssertionBuilder(status_codes=True)

    def generate_test_file(
        self,
        requests: List[Dict],
        grouping: str = 'endpoint',
        test_name: str = 'regression'
    ) -> str:
        """
        Generate complete Playwright test file

        Args:
            requests: List of captured requests
            grouping: 'endpoint' or 'flow'
            test_name: Base name for test file

        Returns:
            Complete Playwright test file content
        """
        grouper = RequestGrouper()

        if grouping == 'flow':
            groups = grouper.group_by_flow(requests)
            group_type = 'flow'
        else:
            groups = grouper.group_by_endpoint(requests)
            group_type = 'endpoint'

        # Generate test code
        imports = self._generate_imports()
        setup = self._generate_setup()

        if grouping == 'flow':
            tests = self._generate_flow_tests(groups)
        else:
            tests = self._generate_endpoint_tests(groups)

        return f"{imports}\n\n{setup}\n\n{tests}"

    def _generate_imports(self) -> str:
        """Generate import statements"""
        return """import { test, expect } from '@playwright/test';

// Generated by TraceTap - Regression Test Suite
// This file contains automated regression tests generated from captured traffic"""

    def _generate_setup(self) -> str:
        """Generate test setup code"""
        base_url = self.base_url or 'http://localhost:8080'

        return f"""
test.describe('API Regression Tests', () => {{
  const baseURL = '{base_url}';

  test.beforeEach(async ({{ request }}) => {{
    // Setup code runs before each test
  }});"""

    def _generate_endpoint_tests(self, endpoint_groups: Dict[str, List[Dict]]) -> str:
        """Generate tests grouped by endpoint"""
        tests = []

        for endpoint, requests in endpoint_groups.items():
            if not requests:
                continue

            # Use first request as template
            template = requests[0]
            test_code = self._generate_single_test(endpoint, template)
            tests.append(test_code)

        tests.append("});")  # Close describe block
        return '\n\n'.join(tests)

    def _generate_flow_tests(self, flows: List[List[Dict]]) -> str:
        """Generate tests grouped by flow"""
        tests = []

        for i, flow in enumerate(flows, 1):
            flow_name = f"Flow {i} - {len(flow)} requests"
            test_code = self._generate_flow_test(flow_name, flow)
            tests.append(test_code)

        tests.append("});")  # Close describe block
        return '\n\n'.join(tests)

    def _generate_single_test(self, test_name: str, request: Dict) -> str:
        """Generate a single test case"""
        method = request.get('method', 'GET').upper()
        url = request.get('url', '')
        body = request.get('body')

        # Extract variables from URL
        parameterized_url, variables = self.variable_extractor.extract_from_url(url)

        # Generate variable declarations
        var_declarations = ""
        if variables:
            var_decls = [f"const {name} = '{value}';" for name, value in variables.items()]
            var_declarations = "\n    ".join(var_decls)
            var_declarations += "\n    "

        # Clean test name
        safe_test_name = test_name.replace('{uuid}', 'ID').replace('{id}', 'ID').replace('{objectId}', 'ID')

        test_code = f"""  test('{safe_test_name}', async ({{ request }}) => {{
    {var_declarations}const response = await request.{method.lower()}('{parameterized_url}'"""

        # Add request body if present
        if body and method in ['POST', 'PUT', 'PATCH']:
            test_code += f""", {{
      data: {json.dumps(json.loads(body), indent=6)}
    }}"""

        test_code += """);

    // Get response data
    const data = await response.json();

    // Assertions"""

        # Generate assertions using assertion builder
        response_data = {
            'status_code': request.get('status_code', 200),
            'response_body': request.get('response_body')
        }
        assertions = self.assertion_builder.build_assertions_code(request, response_data, indent=4)

        if assertions:
            test_code += f"\n{assertions}"
        else:
            # Fallback assertions
            test_code += f"""
    expect(response.status()).toBe({request.get('status_code', 200)});
    expect(data).toBeDefined();"""

        test_code += "\n  });"

        return test_code

    def _generate_flow_test(self, flow_name: str, requests: List[Dict]) -> str:
        """Generate a test case for a complete flow"""
        test_code = f"""  test('{flow_name}', async ({{ request }}) => {{
    // This test represents a captured user flow"""

        for i, req in enumerate(requests, 1):
            method = req.get('method', 'GET').lower()
            url = req.get('url', '')
            status = req.get('status_code', 200)

            test_code += f"""

    // Step {i}: {method.upper()} {url}
    const response{i} = await request.{method}('{url}');
    expect(response{i}.status()).toBe({status});"""

        test_code += "\n  });"

        return test_code


class RegressionGenerator:
    """Main regression test generator"""

    def __init__(self, assertion_builder: Optional[AssertionBuilder] = None):
        self.assertion_builder = assertion_builder
        self.playwright_gen = PlaywrightGenerator(assertion_builder=assertion_builder)

    def generate_from_file(
        self,
        json_file: str,
        output_file: str,
        grouping: str = 'endpoint',
        base_url: Optional[str] = None,
        assert_types: Optional[List[str]] = None,
        critical_fields: Optional[List[str]] = None
    ) -> bool:
        """
        Generate regression tests from captured traffic JSON

        Args:
            json_file: Path to captured traffic JSON
            output_file: Path to save generated test file
            grouping: 'endpoint' or 'flow'
            base_url: Base URL for API (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load captured traffic
            with open(json_file, 'r') as f:
                data = json.load(f)

            requests = data.get('requests', [])

            if not requests:
                print("No requests found in capture file")
                return False

            print(f"Loaded {len(requests)} requests from {json_file}")

            # Set base URL
            if base_url:
                self.playwright_gen.base_url = base_url

            # Configure assertion builder if not already set
            if assert_types and not self.assertion_builder:
                from .assertion_builder import create_assertion_builder
                self.assertion_builder = create_assertion_builder(assert_types, critical_fields)
                self.playwright_gen.assertion_builder = self.assertion_builder

            # Generate test file
            test_code = self.playwright_gen.generate_test_file(
                requests,
                grouping=grouping,
                test_name=Path(output_file).stem
            )

            # Save to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(test_code, encoding='utf-8')

            print(f"✓ Generated {output_file}")
            print(f"  - {len(requests)} requests processed")
            print(f"  - Grouping: {grouping}")

            if self.assertion_builder:
                print(f"  - Assertions: {self.assertion_builder.get_assertion_summary()}")

            return True

        except FileNotFoundError:
            print(f"Error: File not found: {json_file}")
            return False
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {json_file}: {e}")
            return False
        except Exception as e:
            print(f"Error generating regression tests: {e}")
            return False


def generate_regression_tests(
    json_file: str,
    output_file: str,
    grouping: str = 'endpoint',
    base_url: Optional[str] = None,
    assert_types: Optional[List[str]] = None,
    critical_fields: Optional[List[str]] = None
) -> bool:
    """
    Convenience function to generate regression tests

    Args:
        json_file: Path to captured traffic JSON
        output_file: Path to save generated test file
        grouping: 'endpoint' or 'flow'
        base_url: Base URL for API (optional)
        assert_types: List of assertion types to enable
        critical_fields: List of critical field paths

    Returns:
        True if successful, False otherwise
    """
    generator = RegressionGenerator()
    return generator.generate_from_file(
        json_file,
        output_file,
        grouping,
        base_url,
        assert_types,
        critical_fields
    )
