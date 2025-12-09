"""
Generate Playwright fixtures for authentication and variables.

Creates TypeScript fixtures for managing auth tokens, base URLs, and other shared state.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from .postman_parser import AuthConfig
from .script_analyzer import VariableExtraction


@dataclass
class FixtureDefinition:
    """Represents a Playwright fixture definition."""
    name: str
    type: str  # Type annotation
    code: str  # Implementation code
    description: str


class FixtureGenerator:
    """Generate Playwright fixtures for auth and variables."""

    def __init__(self):
        """Initialize fixture generator."""
        pass

    def generate_fixtures(
        self,
        variables: Dict[str, str],
        auth_config: Optional[AuthConfig],
        used_variables: List[str],
        variable_extractions: List[VariableExtraction]
    ) -> List[FixtureDefinition]:
        """
        Generate all necessary fixtures.

        Args:
            variables: Collection variables
            auth_config: Authentication configuration
            used_variables: List of variables actually used in tests
            variable_extractions: Variables extracted from responses

        Returns:
            List of fixture definitions
        """
        fixtures = []

        # Generate base URL fixture if needed
        if 'baseUrl' in used_variables or 'base_url' in variables:
            fixtures.append(self._generate_base_url_fixture(variables))

        # Generate auth fixture if configured
        if auth_config and auth_config.auth_type == 'bearer':
            fixtures.append(self._generate_auth_fixture(auth_config, variables))

        # Generate variable fixtures for commonly used variables
        for var_name in used_variables:
            if var_name in ['baseUrl', 'authToken']:  # Skip already handled
                continue

            original_name = self._to_snake_case(var_name)
            if original_name in variables:
                fixtures.append(self._generate_variable_fixture(
                    var_name,
                    variables[original_name]
                ))

        return fixtures

    def _generate_base_url_fixture(self, variables: Dict[str, str]) -> FixtureDefinition:
        """Generate base URL fixture."""
        base_url = variables.get('base_url', variables.get('baseUrl', 'https://api.example.com'))

        code = f"""
baseUrl: async ({{}}, use) => {{
  // Use environment variable if available, otherwise use collection default
  const url = process.env.BASE_URL || '{base_url}';
  await use(url);
}}"""

        return FixtureDefinition(
            name='baseUrl',
            type='string',
            code=code.strip(),
            description='Base URL for API endpoints'
        )

    def _generate_auth_fixture(self, auth_config: AuthConfig, variables: Dict[str, str]) -> FixtureDefinition:
        """Generate authentication fixture for Bearer token."""
        token_var = auth_config.token_variable or ''

        # Try to extract token from variable reference
        token_value = ''
        if token_var.startswith('{{') and token_var.endswith('}}'):
            var_name = token_var[2:-2]
            token_value = variables.get(var_name, '')

        code = f"""
authToken: async ({{ request, baseUrl }}, use) => {{
  // Option 1: Use environment variable
  if (process.env.AUTH_TOKEN) {{
    await use(process.env.AUTH_TOKEN);
    return;
  }}

  // Option 2: Perform login to get token
  // Uncomment and modify if you have a login endpoint:
  /*
  const response = await request.post(`${{baseUrl}}/auth/login`, {{
    data: {{
      username: process.env.USERNAME || 'test',
      password: process.env.PASSWORD || 'test'
    }}
  }});
  const data = await response.json();
  await use(data.token);
  */

  // Option 3: Use hardcoded token (NOT RECOMMENDED for production)
  await use('{token_value}');
}}"""

        return FixtureDefinition(
            name='authToken',
            type='string',
            code=code.strip(),
            description='Authentication token for API requests'
        )

    def _generate_variable_fixture(self, var_name: str, value: str) -> FixtureDefinition:
        """Generate fixture for a collection variable."""
        code = f"""
{var_name}: async ({{}}, use) => {{
  await use(process.env.{var_name.upper()} || '{value}');
}}"""

        return FixtureDefinition(
            name=var_name,
            type='string',
            code=code.strip(),
            description=f'Collection variable: {var_name}'
        )

    def generate_fixture_extension(self, fixtures: List[FixtureDefinition]) -> str:
        """
        Generate complete fixture extension code.

        Args:
            fixtures: List of fixture definitions

        Returns:
            TypeScript code for test.extend()
        """
        if not fixtures:
            return ''

        # Build type definition
        type_fields = [f"  {f.name}: {f.type};" for f in fixtures]
        type_def = "type CustomFixtures = {\n" + "\n".join(type_fields) + "\n};"

        # Build fixture implementations
        fixture_impls = []
        for fixture in fixtures:
            fixture_impls.append(f"  {fixture.code}")

        fixtures_code = "const test = base.extend<CustomFixtures>({\n" + ",\n\n".join(fixture_impls) + "\n});"

        return f"{type_def}\n\n{fixtures_code}"

    def detect_request_chains(
        self,
        requests: List[Dict],
        variable_dependencies: Dict[int, List[str]]
    ) -> List[tuple]:
        """
        Detect request chains where one request depends on another.

        Args:
            requests: List of request objects
            variable_dependencies: Dict mapping request index to variables it extracts

        Returns:
            List of (source_idx, target_idx, variable_name) tuples
        """
        chains = []

        # Track which variables are extracted by which request
        var_sources = {}
        for req_idx, var_names in variable_dependencies.items():
            for var_name in var_names:
                var_sources[var_name] = req_idx

        # Check each request for variable usage
        for idx, request in enumerate(requests):
            request_str = str(request)

            # Check if it uses any extracted variables
            for var_name, source_idx in var_sources.items():
                if source_idx < idx:  # Only check previous requests
                    # Look for ${varName} pattern
                    if f"${{{var_name}}}" in request_str:
                        chains.append((source_idx, idx, var_name))

        return chains

    def _to_snake_case(self, camel_str: str) -> str:
        """Convert camelCase to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
