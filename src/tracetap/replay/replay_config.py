"""
TraceTap Replay Configuration

YAML-based replay scenarios with environment support, variable management,
and AI-powered test generation using Claude.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
import yaml
from textwrap import dedent

# Import common utilities for AI client
from ..common import create_anthropic_client, ANTHROPIC_AVAILABLE

try:
    import jsonpath_ng
    from jsonpath_ng.ext import parse as jsonpath_parse
    JSONPATH_AVAILABLE = True
except ImportError:
    JSONPATH_AVAILABLE = False


@dataclass
class ReplayStep:
    """Represents a single step in a replay scenario."""

    id: str
    name: str
    request: Dict[str, Any]
    expect: Optional[Dict[str, Any]] = None
    extract: Optional[Dict[str, str]] = None
    skip_if: Optional[str] = None
    retry: int = 0
    timeout: int = 30

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReplayStep':
        """Create ReplayStep from dictionary."""
        return cls(
            id=data.get('id', 'unknown'),
            name=data.get('name', ''),
            request=data.get('request', {}),
            expect=data.get('expect'),
            extract=data.get('extract'),
            skip_if=data.get('skip_if'),
            retry=data.get('retry', 0),
            timeout=data.get('timeout', 30)
        )


@dataclass
class ReplayScenario:
    """Represents a complete replay scenario."""

    name: str
    description: str = ""
    environment: str = "default"
    variables: Dict[str, Any] = field(default_factory=dict)
    environments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    steps: List[ReplayStep] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'ReplayScenario':
        """Load scenario from YAML file."""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReplayScenario':
        """Create scenario from dictionary."""
        steps = [ReplayStep.from_dict(step) for step in data.get('steps', [])]

        return cls(
            name=data.get('name', 'Unnamed Scenario'),
            description=data.get('description', ''),
            environment=data.get('environment', 'default'),
            variables=data.get('variables', {}),
            environments=data.get('environments', {}),
            steps=steps
        )

    def get_environment_variables(self) -> Dict[str, Any]:
        """Get variables for current environment."""
        env_vars = self.environments.get(self.environment, {})
        # Merge with base variables (env vars take precedence)
        return {**self.variables, **env_vars}


class VariableResolver:
    """
    Resolves variables in strings using ${variable} syntax.

    Supports:
    - Simple variables: ${base_url}
    - Environment variables: ${env.API_KEY}
    - Step extractions: ${step.register.user_id}
    - Nested references: ${users[0].id}
    """

    def __init__(self, variables: Dict[str, Any], env_vars: Optional[Dict[str, str]] = None):
        """
        Initialize resolver.

        Args:
            variables: Scenario variables
            env_vars: Environment variables (defaults to os.environ)
        """
        self.variables = variables
        self.env_vars = env_vars or dict(os.environ)
        self.extracted = {}  # Values extracted from responses

    def add_extracted(self, step_id: str, key: str, value: Any):
        """Add an extracted value from a response."""
        if step_id not in self.extracted:
            self.extracted[step_id] = {}
        self.extracted[step_id][key] = value

    def resolve(self, text: Union[str, Dict, List]) -> Union[str, Dict, List]:
        """
        Resolve variables in text, recursively handling dicts and lists.

        Args:
            text: String, dict, or list to resolve

        Returns:
            Resolved value
        """
        if isinstance(text, str):
            return self._resolve_string(text)
        elif isinstance(text, dict):
            return {k: self.resolve(v) for k, v in text.items()}
        elif isinstance(text, list):
            return [self.resolve(item) for item in text]
        else:
            return text

    def _resolve_string(self, text: str) -> str:
        """Resolve variables in a string."""
        # Pattern: ${variable_name} or ${step.id.key}
        pattern = r'\$\{([^}]+)\}'

        def replacer(match):
            var_path = match.group(1)
            value = self._get_value(var_path)
            return str(value) if value is not None else match.group(0)

        return re.sub(pattern, replacer, text)

    def _get_value(self, path: str) -> Optional[Any]:
        """Get value from variable path."""
        parts = path.split('.')

        # Handle env.VAR
        if parts[0] == 'env':
            return self.env_vars.get('.'.join(parts[1:]))

        # Handle step.id.key
        if parts[0] == 'step':
            if len(parts) < 3:
                return None
            step_id = parts[1]
            key = '.'.join(parts[2:])
            return self.extracted.get(step_id, {}).get(key)

        # Handle simple variables
        if len(parts) == 1:
            return self.variables.get(parts[0])

        # Handle nested: users[0].id
        current = self.variables.get(parts[0])
        for part in parts[1:]:
            if current is None:
                return None

            # Handle array indexing: [0]
            if part.startswith('[') and part.endswith(']'):
                try:
                    index = int(part[1:-1])
                    current = current[index]
                except (ValueError, IndexError, TypeError, KeyError):
                    return None
            # Handle dict access
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current


class ResponseExtractor:
    """
    Extract values from HTTP responses using JSONPath or regex.
    """

    def __init__(self):
        """Initialize extractor."""
        self.use_jsonpath = JSONPATH_AVAILABLE

    def extract(self, response_body: str, extractions: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract values from response body.

        Args:
            response_body: Response body as string
            extractions: Dict mapping variable names to extraction expressions
                        (JSONPath for JSON, regex for text)

        Returns:
            Dict of extracted values
        """
        results = {}

        # Try to parse as JSON
        try:
            response_json = json.loads(response_body)
            is_json = True
        except (json.JSONDecodeError, TypeError):
            response_json = None
            is_json = False

        for var_name, expression in extractions.items():
            # JSONPath extraction (if JSON response)
            if is_json and expression.startswith('$.'):
                value = self._extract_jsonpath(response_json, expression)
                results[var_name] = value

            # Regex extraction
            elif expression.startswith('regex:'):
                regex_pattern = expression[6:]  # Remove 'regex:' prefix
                value = self._extract_regex(response_body, regex_pattern)
                results[var_name] = value

            else:
                # Default to JSONPath if available
                if is_json and self.use_jsonpath:
                    value = self._extract_jsonpath(response_json, expression)
                    results[var_name] = value
                else:
                    results[var_name] = None

        return results

    def _extract_jsonpath(self, data: Any, path: str) -> Optional[Any]:
        """Extract value using JSONPath."""
        if not self.use_jsonpath:
            return None

        try:
            jsonpath_expr = jsonpath_parse(path)
            matches = jsonpath_expr.find(data)

            if matches:
                # Return first match value
                return matches[0].value
            return None
        except Exception:
            return None

    def _extract_regex(self, text: str, pattern: str) -> Optional[str]:
        """Extract value using regex."""
        try:
            match = re.search(pattern, text)
            if match:
                # Return first group if groups exist, else full match
                return match.group(1) if match.groups() else match.group(0)
            return None
        except Exception:
            return None


class AssertionValidator:
    """
    Validate response assertions.
    """

    def validate(self, response: Dict[str, Any], expectations: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate response against expectations.

        Args:
            response: Response dict with status, headers, body
            expectations: Expected conditions

        Returns:
            Tuple of (success, error_messages)
        """
        errors = []

        # Status code
        if 'status' in expectations:
            expected_status = expectations['status']
            actual_status = response.get('status', 0)

            if isinstance(expected_status, list):
                if actual_status not in expected_status:
                    errors.append(f"Status {actual_status} not in {expected_status}")
            else:
                if actual_status != expected_status:
                    errors.append(f"Status {actual_status} != {expected_status}")

        # Headers
        if 'headers' in expectations:
            actual_headers = response.get('resp_headers', {})
            for header, expected_value in expectations['headers'].items():
                actual_value = actual_headers.get(header, actual_headers.get(header.lower()))
                if actual_value != expected_value:
                    errors.append(f"Header {header}: {actual_value} != {expected_value}")

        # Body contains
        if 'body_contains' in expectations:
            body = str(response.get('resp_body', ''))
            for text in expectations['body_contains']:
                if text not in body:
                    errors.append(f"Body missing: {text}")

        # Response time
        if 'response_time_ms' in expectations:
            constraint = expectations['response_time_ms']
            actual_time = response.get('duration_ms', 0)

            # Parse constraint: "< 500" or "between 100 and 500"
            if isinstance(constraint, str):
                if constraint.startswith('<'):
                    max_time = int(constraint[1:].strip())
                    if actual_time >= max_time:
                        errors.append(f"Response time {actual_time}ms >= {max_time}ms")
                elif constraint.startswith('>'):
                    min_time = int(constraint[1:].strip())
                    if actual_time <= min_time:
                        errors.append(f"Response time {actual_time}ms <= {min_time}ms")
            elif isinstance(constraint, int):
                if actual_time > constraint:
                    errors.append(f"Response time {actual_time}ms > {constraint}ms")

        success = len(errors) == 0
        return success, errors


class AIScenarioGenerator:
    """
    AI-powered scenario generator using Claude.

    Analyzes raw HTTP captures and generates YAML replay scenarios.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize AI generator."""
        # Use centralized AI client initialization
        self.client, self.ai_available, _ = create_anthropic_client(
            api_key=api_key,
            raise_on_error=False,
            verbose=False
        )

    def generate_scenario(
        self,
        captures: List[Dict[str, Any]],
        intent: str = "",
        scenario_name: Optional[str] = None
    ) -> Optional[ReplayScenario]:
        """
        Generate replay scenario from captures using Claude.

        Args:
            captures: List of HTTP captures
            intent: Optional description of what the scenario should test
            scenario_name: Optional name for scenario

        Returns:
            ReplayScenario or None if generation fails
        """
        if not self.ai_available:
            return None

        # Prepare sample data
        sample_size = min(30, len(captures))
        sample_captures = captures[:sample_size]

        # Create prompt
        prompt = self._create_prompt(sample_captures, intent, scenario_name)

        try:
            # Call Claude
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse YAML response
            response_text = message.content[0].text
            yaml_content = self._extract_yaml(response_text)

            if yaml_content:
                scenario_data = yaml.safe_load(yaml_content)
                return ReplayScenario.from_dict(scenario_data)

            return None

        except Exception:
            return None

    def _create_prompt(self, captures: List[Dict], intent: str, name: Optional[str]) -> str:
        """Create prompt for Claude."""
        captures_json = json.dumps([
            {
                'method': c.get('method'),
                'url': c.get('url'),
                'status': c.get('status'),
                'req_body': c.get('req_body', '')[:200],
                'resp_body': c.get('resp_body', '')[:200]
            }
            for c in captures
        ], indent=2)

        intent_section = f"\n\nSCENARIO INTENT: {intent}" if intent else ""
        name_section = f"\n\nSCENARIO NAME: {name}" if name else ""

        return dedent(f"""
        You are creating a YAML replay scenario from HTTP captures for API testing.
        {intent_section}{name_section}

        HTTP Captures:
        ```json
        {captures_json}
        ```

        Create a YAML scenario following this structure:
        ```yaml
        name: "Scenario Name"
        description: "What this scenario tests"
        variables:
          base_url: "https://api.example.com"

        steps:
          - id: step1
            name: "Description of step"
            request:
              method: POST
              url: "${{base_url}}/path"
              body: '{{"key": "value"}}'
            expect:
              status: 200
            extract:
              variable_name: "$.response.field"
        ```

        INSTRUCTIONS:
        1. Identify logical flow steps from the captures
        2. Extract common base URL as variable
        3. Use variable substitution with ${{variable}} syntax
        4. Add assertions (status codes)
        5. Extract dynamic values that are reused in later steps
        6. Keep it simple and focused on the main flow

        Output the YAML scenario now:
        """).strip()

    def _extract_yaml(self, response: str) -> Optional[str]:
        """Extract YAML from Claude's response."""
        # Try to find YAML in code blocks
        yaml_pattern = r'```(?:yaml|yml)?\s*\n(.*?)\n```'
        matches = re.findall(yaml_pattern, response, re.DOTALL)

        if matches:
            return matches[0]

        # Try to parse entire response
        try:
            yaml.safe_load(response)
            return response
        except (yaml.YAMLError, AttributeError):
            return None


class ReplayConfig:
    """
    Main class for loading and managing replay configurations.
    """

    def __init__(self, yaml_path: Optional[str] = None):
        """
        Initialize replay config.

        Args:
            yaml_path: Path to YAML scenario file (optional)
        """
        self.scenario = None

        if yaml_path:
            self.load(yaml_path)

    def load(self, yaml_path: str):
        """Load scenario from YAML file."""
        self.scenario = ReplayScenario.from_yaml(yaml_path)
        return self.scenario

    def save(self, yaml_path: str):
        """Save scenario to YAML file."""
        if not self.scenario:
            raise ValueError("No scenario loaded")

        data = {
            'name': self.scenario.name,
            'description': self.scenario.description,
            'environment': self.scenario.environment,
            'variables': self.scenario.variables,
            'environments': self.scenario.environments,
            'steps': [
                {
                    'id': step.id,
                    'name': step.name,
                    'request': step.request,
                    'expect': step.expect,
                    'extract': step.extract,
                    'skip_if': step.skip_if,
                    'retry': step.retry,
                    'timeout': step.timeout
                }
                for step in self.scenario.steps
            ]
        }

        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
