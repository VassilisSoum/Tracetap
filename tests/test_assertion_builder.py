"""
Tests for AssertionBuilder

Tests all assertion strategies and their integration.
"""

import json
import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from tracetap.generators.assertion_builder import (
    AssertionBuilder,
    StatusCodeStrategy,
    ResponseSchemaStrategy,
    CriticalFieldsStrategy,
    SnapshotStrategy,
    SchemaInferrer,
    create_assertion_builder
)


class TestSchemaInferrer:
    """Test JSON schema inference"""

    def test_infer_primitive_types(self):
        inferrer = SchemaInferrer()

        assert inferrer.infer_schema(None) == {'type': 'null'}
        assert inferrer.infer_schema(True) == {'type': 'boolean'}
        assert inferrer.infer_schema(42) == {'type': 'integer'}
        assert inferrer.infer_schema(3.14) == {'type': 'number'}
        assert inferrer.infer_schema("hello") == {'type': 'string'}

    def test_infer_array_schema(self):
        inferrer = SchemaInferrer()

        # Empty array
        schema = inferrer.infer_schema([])
        assert schema['type'] == 'array'
        assert schema['items'] == {}

        # Array of strings
        schema = inferrer.infer_schema(["a", "b", "c"])
        assert schema['type'] == 'array'
        assert schema['items']['type'] == 'string'

    def test_infer_object_schema(self):
        inferrer = SchemaInferrer()

        data = {
            "id": 123,
            "name": "Test",
            "active": True,
            "score": 4.5
        }

        schema = inferrer.infer_schema(data)

        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert schema['properties']['id']['type'] == 'integer'
        assert schema['properties']['name']['type'] == 'string'
        assert schema['properties']['active']['type'] == 'boolean'
        assert schema['properties']['score']['type'] == 'number'
        assert set(schema['required']) == {'id', 'name', 'active', 'score'}

    def test_infer_nested_object(self):
        inferrer = SchemaInferrer()

        data = {
            "user": {
                "id": 1,
                "profile": {
                    "name": "Test"
                }
            }
        }

        schema = inferrer.infer_schema(data)

        assert schema['type'] == 'object'
        assert schema['properties']['user']['type'] == 'object'
        assert schema['properties']['user']['properties']['profile']['type'] == 'object'


class TestStatusCodeStrategy:
    """Test status code assertion generation"""

    def test_generates_status_assertion(self):
        strategy = StatusCodeStrategy()
        request = {}
        response = {'status_code': 200}

        assertions = strategy.generate_assertions(request, response)

        assert len(assertions) == 1
        assert 'expect(response.status()).toBe(200)' in assertions[0]

    def test_handles_different_status_codes(self):
        strategy = StatusCodeStrategy()

        for status in [200, 201, 204, 400, 404, 500]:
            response = {'status_code': status}
            assertions = strategy.generate_assertions({}, response)
            assert f'toBe({status})' in assertions[0]

    def test_disabled_strategy(self):
        strategy = StatusCodeStrategy(enabled=False)
        assertions = strategy.generate_assertions({}, {'status_code': 200})
        assert len(assertions) == 0


class TestResponseSchemaStrategy:
    """Test response schema validation"""

    def test_generates_schema_assertions(self):
        strategy = ResponseSchemaStrategy()

        request = {}
        response = {
            'status_code': 200,
            'response_body': '{"id": 123, "name": "Test"}'
        }

        assertions = strategy.generate_assertions(request, response)

        # Should generate assertions for required fields and types
        assert any('toHaveProperty' in a for a in assertions)
        assert any('typeof' in a for a in assertions)

    def test_handles_array_response(self):
        strategy = ResponseSchemaStrategy()

        response = {
            'response_body': '[{"id": 1}, {"id": 2}]'
        }

        assertions = strategy.generate_assertions({}, response)

        # Should detect array
        assert any('Array.isArray' in a for a in assertions)

    def test_handles_empty_response(self):
        strategy = ResponseSchemaStrategy()

        response = {'response_body': None}
        assertions = strategy.generate_assertions({}, response)
        assert len(assertions) == 0

    def test_handles_invalid_json(self):
        strategy = ResponseSchemaStrategy()

        response = {'response_body': 'not json'}
        assertions = strategy.generate_assertions({}, response)
        assert len(assertions) == 0


class TestCriticalFieldsStrategy:
    """Test critical fields assertion"""

    def test_asserts_critical_fields(self):
        strategy = CriticalFieldsStrategy(fields=['id', 'name'])

        response = {
            'response_body': '{"id": 123, "name": "Test", "extra": "data"}'
        }

        assertions = strategy.generate_assertions({}, response)

        # Should assert both critical fields
        assert any('data.id' in a for a in assertions)
        assert any('data.name' in a for a in assertions)
        # Should not assert non-critical fields
        assert not any('data.extra' in a for a in assertions)

    def test_nested_field_paths(self):
        strategy = CriticalFieldsStrategy(fields=['user.profile.name'])

        response = {
            'response_body': '{"user": {"profile": {"name": "Test"}}}'
        }

        assertions = strategy.generate_assertions({}, response)

        assert any('user.profile.name' in a for a in assertions)

    def test_empty_fields_list(self):
        strategy = CriticalFieldsStrategy(fields=[])

        response = {'response_body': '{"id": 123}'}
        assertions = strategy.generate_assertions({}, response)

        assert len(assertions) == 0

    def test_missing_field_handled_gracefully(self):
        strategy = CriticalFieldsStrategy(fields=['missing'])

        response = {'response_body': '{"id": 123}'}
        assertions = strategy.generate_assertions({}, response)

        # Should not crash, just return empty
        assert len(assertions) == 0


class TestSnapshotStrategy:
    """Test snapshot assertion"""

    def test_generates_snapshot_assertion(self):
        strategy = SnapshotStrategy()

        response = {
            'response_body': '{"id": 123, "name": "Test"}'
        }

        assertions = strategy.generate_assertions({}, response)

        assert any('toMatchSnapshot' in a for a in assertions)

    def test_inline_snapshot(self):
        strategy = SnapshotStrategy(inline=True)

        response = {
            'response_body': '{"id": 123}'
        }

        assertions = strategy.generate_assertions({}, response)

        # Should include the actual snapshot data
        assert any('expectedSnapshot' in a for a in assertions)
        assert any('toEqual' in a for a in assertions)

    def test_handles_empty_response(self):
        strategy = SnapshotStrategy()

        response = {'response_body': None}
        assertions = strategy.generate_assertions({}, response)

        assert len(assertions) == 0


class TestAssertionBuilder:
    """Test AssertionBuilder orchestration"""

    def test_default_builder(self):
        builder = AssertionBuilder()

        # Default should only have status codes enabled
        assert len(builder.strategies) == 1
        assert isinstance(builder.strategies[0], StatusCodeStrategy)

    def test_multiple_strategies(self):
        builder = AssertionBuilder(
            status_codes=True,
            response_schemas=True,
            critical_fields=['id', 'name']
        )

        assert len(builder.strategies) == 3

    def test_build_assertions(self):
        builder = AssertionBuilder(
            status_codes=True,
            response_schemas=True
        )

        request = {}
        response = {
            'status_code': 200,
            'response_body': '{"id": 123, "name": "Test"}'
        }

        assertions = builder.build_assertions(request, response)

        # Should have assertions from both strategies
        assert len(assertions) > 1
        assert any('status()' in a for a in assertions)
        assert any('toHaveProperty' in a for a in assertions)

    def test_build_assertions_code(self):
        builder = AssertionBuilder(status_codes=True)

        request = {}
        response = {'status_code': 200}

        code = builder.build_assertions_code(request, response, indent=4)

        assert 'expect(response.status()).toBe(200)' in code
        assert code.startswith('    ')  # Check indentation

    def test_assertion_summary(self):
        builder = AssertionBuilder(
            status_codes=True,
            response_schemas=True,
            critical_fields=['id', 'name']
        )

        summary = builder.get_assertion_summary()

        assert 'Status Codes' in summary
        assert 'Response Schemas' in summary
        assert 'Critical Fields' in summary


class TestCreateAssertionBuilder:
    """Test factory function"""

    def test_create_with_status_codes(self):
        builder = create_assertion_builder(['status-codes'])

        assert len(builder.strategies) == 1
        assert isinstance(builder.strategies[0], StatusCodeStrategy)

    def test_create_with_multiple_types(self):
        builder = create_assertion_builder(
            ['status-codes', 'response-schemas'],
            critical_fields=['id', 'name']
        )

        # Should have 2 strategies (status + schema, fields not enabled without flag)
        assert len(builder.strategies) == 2

    def test_create_with_critical_fields(self):
        builder = create_assertion_builder(
            ['critical-fields'],
            critical_fields=['user.id', 'order.total']
        )

        # Find the critical fields strategy
        strategy = None
        for s in builder.strategies:
            if isinstance(s, CriticalFieldsStrategy):
                strategy = s
                break

        assert strategy is not None
        assert len(strategy.fields) == 2
        assert 'user.id' in strategy.fields


# Integration tests
class TestAssertionIntegration:
    """Integration tests with real-world scenarios"""

    def test_complete_workflow(self):
        """Test complete assertion generation workflow"""
        builder = AssertionBuilder(
            status_codes=True,
            response_schemas=True,
            critical_fields=['id', 'email']
        )

        request = {
            'method': 'GET',
            'url': 'https://api.example.com/users/123'
        }

        response = {
            'status_code': 200,
            'response_body': '{"id": 123, "name": "Test User", "email": "test@example.com"}'
        }

        code = builder.build_assertions_code(request, response, indent=4)

        # Verify generated code
        assert 'expect(response.status()).toBe(200)' in code
        assert 'expect(data).toHaveProperty(\'id\')' in code
        assert 'expect(data).toHaveProperty(\'email\')' in code
        assert 'expect(typeof data.id).toBe(\'number\')' in code

    def test_handles_error_response(self):
        """Test assertion generation for error responses"""
        builder = AssertionBuilder(status_codes=True)

        request = {}
        response = {
            'status_code': 404,
            'response_body': '{"error": "Not Found"}'
        }

        assertions = builder.build_assertions(request, response)

        assert any('toBe(404)' in a for a in assertions)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
