"""
Assertion Builder for Regression Tests

Generates smart, configurable assertions for Playwright tests.
Supports status codes, response schemas, critical fields, and snapshots.
"""

import json
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict


class SchemaInferrer:
    """Infer JSON schema from response data"""

    def infer_schema(self, data: Any, path: str = '') -> Dict[str, Any]:
        """
        Infer JSON schema from data

        Args:
            data: JSON data (dict, list, or primitive)
            path: Current path in data structure

        Returns:
            JSON schema object
        """
        if data is None:
            return {'type': 'null'}

        if isinstance(data, bool):
            return {'type': 'boolean'}

        if isinstance(data, int):
            return {'type': 'integer'}

        if isinstance(data, float):
            return {'type': 'number'}

        if isinstance(data, str):
            return {'type': 'string'}

        if isinstance(data, list):
            if not data:
                return {
                    'type': 'array',
                    'items': {}
                }

            # Infer schema from first item (assume homogeneous)
            item_schema = self.infer_schema(data[0], f"{path}[]")
            return {
                'type': 'array',
                'items': item_schema,
                'minItems': 0
            }

        if isinstance(data, dict):
            properties = {}
            required = []

            for key, value in data.items():
                properties[key] = self.infer_schema(value, f"{path}.{key}")
                # Mark non-null fields as required
                if value is not None:
                    required.append(key)

            schema = {
                'type': 'object',
                'properties': properties
            }

            if required:
                schema['required'] = required

            return schema

        return {}

    def schema_to_typescript_type(self, schema: Dict[str, Any], name: str = 'Response') -> str:
        """
        Convert JSON schema to TypeScript type definition

        Args:
            schema: JSON schema
            name: Type name

        Returns:
            TypeScript type definition
        """
        if schema.get('type') == 'object':
            properties = schema.get('properties', {})
            required = set(schema.get('required', []))

            fields = []
            for key, prop_schema in properties.items():
                optional = '' if key in required else '?'
                ts_type = self._schema_type_to_ts(prop_schema)
                fields.append(f"  {key}{optional}: {ts_type};")

            fields_str = '\n'.join(fields)
            return f"interface {name} {{\n{fields_str}\n}}"

        return f"type {name} = {self._schema_type_to_ts(schema)};"

    def _schema_type_to_ts(self, schema: Dict[str, Any]) -> str:
        """Convert schema type to TypeScript type"""
        schema_type = schema.get('type')

        if schema_type == 'null':
            return 'null'
        elif schema_type == 'boolean':
            return 'boolean'
        elif schema_type == 'integer' or schema_type == 'number':
            return 'number'
        elif schema_type == 'string':
            return 'string'
        elif schema_type == 'array':
            item_type = self._schema_type_to_ts(schema.get('items', {}))
            return f"Array<{item_type}>"
        elif schema_type == 'object':
            # Nested object - use inline type
            properties = schema.get('properties', {})
            if not properties:
                return 'object'

            required = set(schema.get('required', []))
            fields = []
            for key, prop_schema in properties.items():
                optional = '' if key in required else '?'
                ts_type = self._schema_type_to_ts(prop_schema)
                fields.append(f"{key}{optional}: {ts_type}")

            return f"{{ {'; '.join(fields)} }}"

        return 'any'


class AssertionStrategy:
    """Base class for assertion strategies"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def generate_assertions(self, request: Dict[str, Any], response: Dict[str, Any]) -> List[str]:
        """
        Generate assertion code for a request/response pair

        Args:
            request: Request data
            response: Response data

        Returns:
            List of assertion code lines
        """
        raise NotImplementedError


class StatusCodeStrategy(AssertionStrategy):
    """Assert response status codes"""

    def generate_assertions(self, request: Dict[str, Any], response: Dict[str, Any]) -> List[str]:
        if not self.enabled:
            return []

        status = response.get('status_code', 200)
        return [
            f"expect(response.status()).toBe({status});"
        ]


class ResponseSchemaStrategy(AssertionStrategy):
    """Assert response conforms to inferred schema"""

    def __init__(self, enabled: bool = True, strict: bool = False):
        super().__init__(enabled)
        self.strict = strict
        self.schema_inferrer = SchemaInferrer()

    def generate_assertions(self, request: Dict[str, Any], response: Dict[str, Any]) -> List[str]:
        if not self.enabled:
            return []

        assertions = []
        body = response.get('response_body')

        if not body:
            return []

        try:
            data = json.loads(body)
            schema = self.schema_inferrer.infer_schema(data)

            # Generate schema validation assertions
            assertions.extend(self._generate_schema_checks(data, schema))

        except (json.JSONDecodeError, TypeError):
            pass

        return assertions

    def _generate_schema_checks(self, data: Any, schema: Dict[str, Any], path: str = 'data') -> List[str]:
        """Generate schema validation code"""
        assertions = []
        schema_type = schema.get('type')

        if schema_type == 'object':
            properties = schema.get('properties', {})
            required = schema.get('required', [])

            # Check required fields exist
            for field in required:
                assertions.append(f"expect({path}).toHaveProperty('{field}');")

            # Check field types
            for field, field_schema in properties.items():
                field_type = field_schema.get('type')
                field_path = f"{path}.{field}"

                if field_type == 'string':
                    assertions.append(f"expect(typeof {field_path}).toBe('string');")
                elif field_type == 'number' or field_type == 'integer':
                    assertions.append(f"expect(typeof {field_path}).toBe('number');")
                elif field_type == 'boolean':
                    assertions.append(f"expect(typeof {field_path}).toBe('boolean');")
                elif field_type == 'array':
                    assertions.append(f"expect(Array.isArray({field_path})).toBe(true);")
                elif field_type == 'object':
                    assertions.append(f"expect(typeof {field_path}).toBe('object');")

        elif schema_type == 'array':
            assertions.append(f"expect(Array.isArray({path})).toBe(true);")

            # Check array length if data is non-empty
            if isinstance(data, list) and data:
                assertions.append(f"expect({path}.length).toBeGreaterThan(0);")

        return assertions


class CriticalFieldsStrategy(AssertionStrategy):
    """Assert specific critical fields have expected values"""

    def __init__(self, fields: List[str], enabled: bool = True):
        """
        Initialize critical fields strategy

        Args:
            fields: List of field paths (e.g., ['user.id', 'order.total'])
            enabled: Whether strategy is enabled
        """
        super().__init__(enabled)
        self.fields = fields

    def generate_assertions(self, request: Dict[str, Any], response: Dict[str, Any]) -> List[str]:
        if not self.enabled or not self.fields:
            return []

        assertions = []
        body = response.get('response_body')

        if not body:
            return []

        try:
            data = json.loads(body)

            for field_path in self.fields:
                value = self._get_nested_value(data, field_path)

                if value is not None:
                    # Generate assertion for this field
                    js_path = self._to_js_path(field_path)
                    assertions.append(f"expect(data.{js_path}).toBeDefined();")

                    # Add type-specific assertions
                    if isinstance(value, str):
                        if value:  # Non-empty string
                            assertions.append(f"expect(data.{js_path}).toBeTruthy();")
                    elif isinstance(value, (int, float)):
                        assertions.append(f"expect(typeof data.{js_path}).toBe('number');")
                    elif isinstance(value, bool):
                        assertions.append(f"expect(typeof data.{js_path}).toBe('boolean');")

        except (json.JSONDecodeError, TypeError):
            pass

        return assertions

    def _get_nested_value(self, data: Any, path: str) -> Any:
        """Get value from nested path (e.g., 'user.profile.name')"""
        parts = path.split('.')
        current = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                return None

        return current

    def _to_js_path(self, path: str) -> str:
        """Convert dot path to JavaScript property access"""
        parts = path.split('.')
        js_parts = []

        for part in parts:
            if part.isdigit():
                js_parts.append(f"[{part}]")
            else:
                js_parts.append(part)

        return '.'.join(js_parts)


class SnapshotStrategy(AssertionStrategy):
    """Generate snapshot assertions for response comparison"""

    def __init__(self, enabled: bool = True, inline: bool = False):
        """
        Initialize snapshot strategy

        Args:
            enabled: Whether strategy is enabled
            inline: If True, include full response snapshot in test
        """
        super().__init__(enabled)
        self.inline = inline

    def generate_assertions(self, request: Dict[str, Any], response: Dict[str, Any]) -> List[str]:
        if not self.enabled:
            return []

        body = response.get('response_body')

        if not body:
            return []

        try:
            data = json.loads(body)

            if self.inline:
                # Include full snapshot in test
                snapshot = json.dumps(data, indent=2)
                return [
                    f"// Snapshot assertion",
                    f"const expectedSnapshot = {snapshot};",
                    f"expect(data).toEqual(expectedSnapshot);"
                ]
            else:
                # Use Playwright's snapshot feature
                return [
                    "// Compare against saved snapshot",
                    "expect(data).toMatchSnapshot();"
                ]

        except (json.JSONDecodeError, TypeError):
            return []


class AssertionBuilder:
    """Main assertion builder - orchestrates assertion strategies"""

    def __init__(
        self,
        status_codes: bool = True,
        response_schemas: bool = False,
        critical_fields: Optional[List[str]] = None,
        snapshots: bool = False,
        snapshot_inline: bool = False
    ):
        """
        Initialize assertion builder

        Args:
            status_codes: Enable status code assertions
            response_schemas: Enable response schema validation
            critical_fields: List of critical field paths to assert
            snapshots: Enable snapshot assertions
            snapshot_inline: Include inline snapshots vs external
        """
        self.strategies: List[AssertionStrategy] = []

        # Add enabled strategies
        if status_codes:
            self.strategies.append(StatusCodeStrategy())

        if response_schemas:
            self.strategies.append(ResponseSchemaStrategy())

        if critical_fields:
            self.strategies.append(CriticalFieldsStrategy(critical_fields))

        if snapshots:
            self.strategies.append(SnapshotStrategy(inline=snapshot_inline))

    def build_assertions(self, request: Dict[str, Any], response: Dict[str, Any]) -> List[str]:
        """
        Build all assertions for a request/response pair

        Args:
            request: Request data
            response: Response data

        Returns:
            List of assertion code lines
        """
        all_assertions = []

        for strategy in self.strategies:
            assertions = strategy.generate_assertions(request, response)
            all_assertions.extend(assertions)

        return all_assertions

    def build_assertions_code(self, request: Dict[str, Any], response: Dict[str, Any], indent: int = 4) -> str:
        """
        Build assertions as formatted code string

        Args:
            request: Request data
            response: Response data
            indent: Number of spaces for indentation

        Returns:
            Formatted assertion code
        """
        assertions = self.build_assertions(request, response)

        if not assertions:
            return ""

        indent_str = ' ' * indent
        code_lines = [f"{indent_str}{assertion}" for assertion in assertions]

        return '\n'.join(code_lines)

    def get_assertion_summary(self) -> str:
        """Get summary of enabled assertion strategies"""
        enabled = []

        for strategy in self.strategies:
            if isinstance(strategy, StatusCodeStrategy):
                enabled.append("Status Codes")
            elif isinstance(strategy, ResponseSchemaStrategy):
                enabled.append("Response Schemas")
            elif isinstance(strategy, CriticalFieldsStrategy):
                enabled.append(f"Critical Fields ({len(strategy.fields)} fields)")
            elif isinstance(strategy, SnapshotStrategy):
                enabled.append("Snapshots")

        return ", ".join(enabled) if enabled else "None"


def create_assertion_builder(
    assert_types: List[str],
    critical_fields: Optional[List[str]] = None
) -> AssertionBuilder:
    """
    Create assertion builder from command-line style arguments

    Args:
        assert_types: List of assertion types (e.g., ['status-codes', 'response-schemas'])
        critical_fields: List of critical field paths

    Returns:
        Configured AssertionBuilder instance
    """
    return AssertionBuilder(
        status_codes='status-codes' in assert_types,
        response_schemas='response-schemas' in assert_types,
        critical_fields=critical_fields if 'critical-fields' in assert_types else None,
        snapshots='snapshots' in assert_types,
        snapshot_inline='snapshots-inline' in assert_types
    )
