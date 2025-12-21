"""
TraceTap AI-Powered Variable Extractor

Uses Claude AI to intelligently detect and extract variables from HTTP traffic
for replay scenarios. Detects IDs, tokens, timestamps, and other dynamic values.
"""

import json
import re
import os
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from textwrap import dedent

# Import common utilities for AI client and header filtering
from ..common import create_anthropic_client, ANTHROPIC_AVAILABLE, filter_interesting_headers


@dataclass
class Variable:
    """Represents a detected variable in HTTP traffic."""

    name: str               # Variable name (e.g., "user_id", "auth_token")
    type: str              # Variable type (e.g., "uuid", "integer", "timestamp")
    example_values: List[str]  # Example values from captures
    locations: List[str]    # Where found (e.g., "url_path", "query_param", "header")
    pattern: Optional[str] = None  # Regex pattern if applicable
    description: Optional[str] = None  # AI-generated description


class VariableExtractor:
    """
    AI-powered variable extraction from HTTP captures.

    Uses Claude to intelligently identify dynamic values that should be
    parameterized for replay scenarios.

    Features:
    - Automatic detection of IDs, tokens, timestamps
    - Pattern recognition (UUIDs, JWTs, numeric IDs)
    - Cross-request variable tracking
    - Dependency detection (variable from response used in next request)
    - AI-powered intelligent analysis

    Example:
        extractor = VariableExtractor('session.json', api_key=os.getenv('ANTHROPIC_API_KEY'))
        variables = extractor.extract_variables()
        for var in variables:
            print(f"{var.name}: {var.type} - {var.example_values[0]}")
    """

    def __init__(
        self,
        captures: List[Dict[str, Any]],
        api_key: Optional[str] = None,
        use_ai: bool = True
    ):
        """
        Initialize Variable Extractor.

        Args:
            captures: List of captured HTTP requests
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            use_ai: Whether to use Claude AI (falls back to regex if False)
        """
        self.captures = captures

        # Initialize Claude client using centralized utility
        if use_ai and ANTHROPIC_AVAILABLE:
            self.client, self.use_ai, msg = create_anthropic_client(
                api_key=api_key,
                raise_on_error=False,
                verbose=False
            )
            # Customize message for variable extraction context
            if self.use_ai:
                self.ai_message = "✓ Claude AI enabled for intelligent variable detection"
            else:
                self.ai_message = f"⚠️  {msg} (using regex fallback)"
        else:
            self.client = None
            self.use_ai = False
            if not use_ai:
                self.ai_message = "⚠️  Claude AI disabled (use_ai=False)"
            else:
                self.ai_message = "⚠️  anthropic library not installed (using regex fallback)"

    def extract_variables(self, verbose: bool = False) -> List[Variable]:
        """
        Extract variables from captures using AI or regex fallback.

        Args:
            verbose: Print detailed progress

        Returns:
            List of detected Variable objects
        """
        if verbose:
            print(f"Variable Extraction: {self.ai_message}")

        if self.use_ai:
            return self._extract_with_ai(verbose)
        else:
            return self._extract_with_regex(verbose)

    def _extract_with_ai(self, verbose: bool = False) -> List[Variable]:
        """Use Claude AI to intelligently detect variables."""
        if verbose:
            print(f"Analyzing {len(self.captures)} requests with Claude...")

        # Prepare sample data for AI (limit to avoid token limits)
        sample_size = min(50, len(self.captures))
        sample_captures = self.captures[:sample_size]

        # Build analysis data
        analysis_data = []
        for i, capture in enumerate(sample_captures, 1):
            analysis_data.append({
                'index': i,
                'method': capture.get('method'),
                'url': capture.get('url'),
                'status': capture.get('status'),
                'req_headers': filter_interesting_headers(capture.get('req_headers', {})),
                'resp_headers': filter_interesting_headers(capture.get('resp_headers', {})),
                'req_body_sample': self._truncate_body(capture.get('req_body', '')),
                'resp_body_sample': self._truncate_body(capture.get('resp_body', ''))
            })

        # Create prompt for Claude
        prompt = self._create_analysis_prompt(analysis_data)

        try:
            # Call Claude API
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            response_text = message.content[0].text
            variables = self._parse_ai_response(response_text)

            if verbose:
                print(f"✓ Claude detected {len(variables)} variables")

            return variables

        except Exception as e:
            if verbose:
                print(f"⚠️  AI extraction failed: {e}, falling back to regex")
            return self._extract_with_regex(verbose)

    def _create_analysis_prompt(self, analysis_data: List[Dict]) -> str:
        """Create prompt for Claude to analyze variables."""
        data_json = json.dumps(analysis_data, indent=2)

        return dedent(f"""
        You are analyzing HTTP request/response pairs to identify dynamic variables that should be parameterized for API testing.

        HTTP Captures (sample of {len(analysis_data)} requests):
        ```json
        {data_json}
        ```

        TASK: Identify all dynamic values that appear across multiple requests and should be extracted as variables.

        INSTRUCTIONS:

        1. **Look for these patterns**:
           - UUIDs (e.g., "123e4567-e89b-12d3-a456-426614174000")
           - Numeric IDs (e.g., "/users/12345")
           - JWT tokens in Authorization headers
           - Session tokens/cookies
           - Timestamps (ISO 8601, Unix timestamps)
           - API keys
           - Correlation IDs
           - CSRF tokens

        2. **Identify variable characteristics**:
           - Name (descriptive, snake_case)
           - Type (uuid, integer, jwt, timestamp, string, etc.)
           - Where it appears (url_path, query_param, header, request_body, response_body)
           - Example values from the captures
           - Pattern (regex if applicable)

        3. **Track dependencies**:
           - Note if a value from one response is used in a subsequent request
           - Example: "token from response 1 used in Authorization header of request 2"

        4. **Be specific**:
           - Use actual values from the captures as examples
           - Provide clear descriptions of what each variable represents

        Output a JSON array of variables with this structure:
        ```json
        [
          {{
            "name": "user_id",
            "type": "integer",
            "example_values": ["12345", "67890"],
            "locations": ["url_path", "query_param"],
            "pattern": "\\\\d+",
            "description": "User identifier appearing in URL paths and query parameters"
          }}
        ]
        ```

        Analyze the captures and output the JSON array now:
        """).strip()

    def _parse_ai_response(self, response: str) -> List[Variable]:
        """Parse Claude's response into Variable objects."""
        # Try to extract JSON from response
        json_pattern = r'```(?:json)?\s*\n(.*?)\n```'
        matches = re.findall(json_pattern, response, re.DOTALL)

        json_str = matches[0] if matches else response

        try:
            variables_data = json.loads(json_str)

            variables = []
            for var_data in variables_data:
                var = Variable(
                    name=var_data.get('name', 'unknown'),
                    type=var_data.get('type', 'string'),
                    example_values=var_data.get('example_values', []),
                    locations=var_data.get('locations', []),
                    pattern=var_data.get('pattern'),
                    description=var_data.get('description')
                )
                variables.append(var)

            return variables

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"⚠️  Failed to parse AI response: {e}")
            return []

    def _extract_with_regex(self, verbose: bool = False) -> List[Variable]:
        """Fallback: Use regex patterns to detect common variables."""
        if verbose:
            print(f"Using regex-based variable detection...")

        detected = {}

        # Common patterns
        patterns = {
            'uuid': (r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'uuid'),
            'numeric_id': (r'/(\d{3,})', 'integer'),
            'jwt': (r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', 'jwt'),
            'timestamp_iso': (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', 'timestamp'),
            'timestamp_unix': (r'\b\d{10}\b', 'unix_timestamp'),
        }

        for capture in self.captures[:100]:  # Sample first 100
            url = capture.get('url', '')
            headers = capture.get('req_headers', {})
            body = capture.get('req_body', '')

            for var_name, (pattern, var_type) in patterns.items():
                # Check URL
                matches = re.findall(pattern, url)
                if matches:
                    if var_name not in detected:
                        detected[var_name] = {
                            'type': var_type,
                            'examples': set(),
                            'locations': set()
                        }
                    detected[var_name]['examples'].update(matches[:3])
                    detected[var_name]['locations'].add('url_path')

                # Check headers
                for header_value in headers.values():
                    if isinstance(header_value, str):
                        matches = re.findall(pattern, header_value)
                        if matches and var_name in detected:
                            detected[var_name]['examples'].update(matches[:3])
                            detected[var_name]['locations'].add('header')

        # Convert to Variable objects
        variables = []
        for name, data in detected.items():
            var = Variable(
                name=name,
                type=data['type'],
                example_values=list(data['examples'])[:5],
                locations=list(data['locations']),
                pattern=patterns[name][0],
                description=f"Auto-detected {data['type']} pattern"
            )
            variables.append(var)

        if verbose:
            print(f"✓ Regex detected {len(variables)} variable patterns")

        return variables

    def _truncate_body(self, body: str, max_length: int = 500) -> str:
        """Truncate body for AI analysis."""
        if len(body) <= max_length:
            return body
        return body[:max_length] + "... [truncated]"


class VariableSubstitutor:
    """
    Substitute variables in requests for replay.

    Takes a request and a variable mapping, performs substitutions.
    """

    def __init__(self, variables: Dict[str, str]):
        """
        Initialize substitutor.

        Args:
            variables: Dict mapping variable names to values
        """
        self.variables = variables

    def substitute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute variables in a request.

        Args:
            request: Request dict to modify

        Returns:
            Modified request with substitutions
        """
        modified = request.copy()

        # Substitute in URL
        if 'url' in modified:
            modified['url'] = self._substitute_string(modified['url'])

        # Substitute in headers
        if 'req_headers' in modified:
            modified['req_headers'] = {
                k: self._substitute_string(v) if isinstance(v, str) else v
                for k, v in modified['req_headers'].items()
            }

        # Substitute in body
        if 'req_body' in modified and isinstance(modified['req_body'], str):
            modified['req_body'] = self._substitute_string(modified['req_body'])

        return modified

    def _substitute_string(self, text: str) -> str:
        """Substitute all variables in a string."""
        result = text
        for var_name, var_value in self.variables.items():
            # Support both {var} and {{var}} syntax
            result = result.replace(f'{{{var_name}}}', var_value)
            result = result.replace(f'{{{{{var_name}}}}}', var_value)
        return result

    def get_template(self, request: Dict[str, Any], variables: List[Variable]) -> str:
        """
        Convert a request to a template with variable placeholders.

        Args:
            request: Request to templateize
            variables: List of variables to replace

        Returns:
            URL template string
        """
        url = request.get('url', '')

        # Replace detected patterns with {variable_name}
        for var in variables:
            if var.pattern and var.example_values:
                # Try to replace first example value
                example = var.example_values[0]
                url = url.replace(example, f'{{{var.name}}}')

        return url
