"""
AI-powered test script analyzer and converter.

Converts Postman test scripts (pm.test) to Playwright assertions (expect).
Uses Claude AI for intelligent conversion of complex scripts.
"""

import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    import anthropic
except ImportError:
    anthropic = None


@dataclass
class TestAssertion:
    """Represents a test assertion."""
    description: str
    code: str
    confidence: str  # 'high', 'medium', 'low'


@dataclass
class VariableExtraction:
    """Represents a variable extraction from response."""
    variable_name: str
    json_path: str
    description: str


class ScriptAnalyzer:
    """Parse and convert Postman test scripts to Playwright."""

    # Common patterns for regex-based conversion
    PATTERN_CONVERSIONS = {
        # Status code
        r'pm\.response\.to\.have\.status\((\d+)\)': r'expect(response.status()).toBe(\1)',
        r'pm\.expect\(pm\.response\.code\)\.to\.(?:equal|eql)\((\d+)\)': r'expect(response.status()).toBe(\1)',

        # Response time
        r'pm\.expect\(pm\.response\.responseTime\)\.to\.be\.below\((\d+)\)': r'// Response time: expect(responseTime).toBeLessThan(\1)',

        # JSON response
        r'pm\.response\.json\(\)': r'await response.json()',
        r'const\s+(\w+)\s*=\s*pm\.response\.json\(\)': r'const \1 = await response.json()',

        # Existence checks
        r'pm\.expect\(([^)]+)\)\.to\.exist': r'expect(\1).toBeTruthy()',
        r'pm\.expect\(([^)]+)\)\.to\.not\.exist': r'expect(\1).toBeFalsy()',

        # Equality
        r'pm\.expect\(([^)]+)\)\.to\.equal\(([^)]+)\)': r'expect(\1).toBe(\2)',
        r'pm\.expect\(([^)]+)\)\.to\.eql\(([^)]+)\)': r'expect(\1).toEqual(\2)',

        # Boolean
        r'pm\.expect\(([^)]+)\)\.to\.be\.true': r'expect(\1).toBe(true)',
        r'pm\.expect\(([^)]+)\)\.to\.be\.false': r'expect(\1).toBe(false)',

        # String contains
        r'pm\.expect\(([^)]+)\)\.to\.include\(([^)]+)\)': r'expect(\1).toContain(\2)',

        # Array/Object
        r'pm\.expect\(([^)]+)\)\.to\.be\.an?\((["\'])array\2\)': r'expect(Array.isArray(\1)).toBe(true)',
        r'pm\.expect\(([^)]+)\)\.to\.be\.an?\((["\'])object\2\)': r'expect(typeof \1).toBe("object")',

        # Greater than / Less than
        r'pm\.expect\(([^)]+)\)\.to\.be\.above\(([^)]+)\)': r'expect(\1).toBeGreaterThan(\2)',
        r'pm\.expect\(([^)]+)\)\.to\.be\.below\(([^)]+)\)': r'expect(\1).toBeLessThan(\2)',
    }

    def __init__(self, ai_client: Optional[Any] = None, use_ai: bool = True):
        """
        Initialize script analyzer.

        Args:
            ai_client: Anthropic client for AI-powered conversion
            use_ai: Whether to use AI for conversion (fallback to patterns if False)
        """
        self.ai_client = ai_client
        self.use_ai = use_ai and ai_client is not None

    def convert_script(self, script_lines: List[str]) -> tuple[List[TestAssertion], List[VariableExtraction]]:
        """
        Convert Postman test script to Playwright assertions.

        Args:
            script_lines: Lines of Postman test script

        Returns:
            Tuple of (assertions, variable_extractions)
        """
        if not script_lines:
            return [], []

        script_text = '\n'.join(script_lines)

        # Try AI conversion first if available
        if self.use_ai:
            try:
                return self._ai_convert_script(script_text)
            except Exception as e:
                print(f"AI conversion failed, falling back to pattern matching: {e}")

        # Fallback to pattern-based conversion
        return self._pattern_convert_script(script_lines)

    def _ai_convert_script(self, script_text: str) -> tuple[List[TestAssertion], List[VariableExtraction]]:
        """
        Use Claude AI to convert test script.

        Args:
            script_text: Complete Postman test script

        Returns:
            Tuple of (assertions, variable_extractions)
        """
        prompt = f"""Convert this Postman test script to Playwright assertions.

Postman test script:
```javascript
{script_text}
```

Instructions:
1. Convert all pm.test() blocks to Playwright expect() assertions
2. Convert pm.response.json() to await response.json()
3. Convert pm.expect() to expect()
4. Identify any pm.collectionVariables.set() or pm.environment.set() calls as variable extractions
5. Use Playwright's assertion API (toBe, toEqual, toBeTruthy, toContain, etc.)

Output a JSON object with this structure:
{{
  "assertions": [
    {{
      "description": "Test description",
      "code": "expect(response.status()).toBe(200);",
      "confidence": "high"
    }}
  ],
  "variable_extractions": [
    {{
      "variable_name": "authToken",
      "json_path": "response.token",
      "description": "Extract auth token from response"
    }}
  ]
}}

Only output valid JSON, no additional text."""

        message = self.ai_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())

            assertions = [
                TestAssertion(**a) for a in result.get('assertions', [])
            ]
            extractions = [
                VariableExtraction(**v) for v in result.get('variable_extractions', [])
            ]

            return assertions, extractions

        # If parsing fails, fall back to pattern matching
        return self._pattern_convert_script(script_text.split('\n'))

    def _pattern_convert_script(self, script_lines: List[str]) -> tuple[List[TestAssertion], List[VariableExtraction]]:
        """
        Convert script using regex patterns.

        Args:
            script_lines: Lines of Postman test script

        Returns:
            Tuple of (assertions, variable_extractions)
        """
        assertions = []
        extractions = []

        current_test_name = None

        for line in script_lines:
            line = line.strip()

            # Extract test name from pm.test('name', ...)
            test_name_match = re.search(r'pm\.test\(["\']([^"\']+)["\']', line)
            if test_name_match:
                current_test_name = test_name_match.group(1)
                continue

            # Detect variable extraction
            var_set_match = re.search(r'pm\.(?:collectionVariables|environment|globals)\.set\(["\']([^"\']+)["\'],\s*(.+?)\)', line)
            if var_set_match:
                var_name = var_set_match.group(1)
                var_value = var_set_match.group(2)

                # Convert to camelCase
                camel_var = self._to_camel_case(var_name)

                extractions.append(VariableExtraction(
                    variable_name=camel_var,
                    json_path=var_value,
                    description=f"Extract {var_name} from response"
                ))

                # Also add as code comment
                assertions.append(TestAssertion(
                    description=f"Store {camel_var}",
                    code=f"const {camel_var} = {self._convert_line(var_value)};",
                    confidence='medium'
                ))
                continue

            # Try pattern conversions
            converted = self._convert_line(line)
            if converted and converted != line:
                assertions.append(TestAssertion(
                    description=current_test_name or "Assertion",
                    code=converted,
                    confidence='high'
                ))

        return assertions, extractions

    def _convert_line(self, line: str) -> str:
        """
        Convert a single line using pattern matching.

        Args:
            line: Line of Postman script

        Returns:
            Converted Playwright code or original line
        """
        for pattern, replacement in self.PATTERN_CONVERSIONS.items():
            line = re.sub(pattern, replacement, line)

        return line

    def _to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])

    def detect_variable_extraction(self, script_lines: List[str]) -> List[VariableExtraction]:
        """
        Detect variable extractions in script.

        Args:
            script_lines: Lines of Postman test script

        Returns:
            List of variable extractions found
        """
        extractions = []

        script_text = '\n'.join(script_lines)

        # Pattern for pm.collectionVariables.set(), pm.environment.set(), etc.
        pattern = r'pm\.(?:collectionVariables|environment|globals)\.set\(["\']([^"\']+)["\'],\s*(.+?)\)'

        for match in re.finditer(pattern, script_text):
            var_name = match.group(1)
            var_value = match.group(2)

            camel_var = self._to_camel_case(var_name)

            extractions.append(VariableExtraction(
                variable_name=camel_var,
                json_path=var_value,
                description=f"Extract {var_name} from response"
            ))

        return extractions

    def analyze_request_dependencies(
        self,
        requests_with_scripts: List[Dict[str, Any]]
    ) -> Dict[int, List[str]]:
        """
        Analyze which requests depend on variables from previous requests.

        Args:
            requests_with_scripts: List of request dicts with test_script field

        Returns:
            Dictionary mapping request index to list of variables it extracts
        """
        dependencies = {}

        for idx, request in enumerate(requests_with_scripts):
            script = request.get('test_script', [])
            if script:
                extractions = self.detect_variable_extraction(script)
                if extractions:
                    dependencies[idx] = [e.variable_name for e in extractions]

        return dependencies
