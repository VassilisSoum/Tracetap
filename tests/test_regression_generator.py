"""
Tests for RegressionGenerator

Tests variable extraction, request grouping, and test generation.
"""

import json
import pytest
import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from tracetap.generators.regression_generator import (
    VariableExtractor,
    RequestGrouper,
    PlaywrightGenerator,
    RegressionGenerator,
    generate_regression_tests
)


class TestVariableExtractor:
    """Test dynamic variable extraction"""

    def test_extract_uuid_from_url(self):
        extractor = VariableExtractor()

        url = "https://api.example.com/users/550e8400-e29b-41d4-a716-446655440000"
        parameterized, extracted = extractor.extract_from_url(url)

        assert '${uuid}' in parameterized
        assert 'uuid' in extracted
        assert extracted['uuid'] == '550e8400-e29b-41d4-a716-446655440000'

    def test_extract_numeric_id_from_url(self):
        extractor = VariableExtractor()

        url = "https://api.example.com/users/123456"
        parameterized, extracted = extractor.extract_from_url(url)

        assert '${id}' in parameterized
        assert 'id' in extracted
        assert extracted['id'] == '123456'

    def test_extract_multiple_variables(self):
        extractor = VariableExtractor()

        url = "https://api.example.com/users/123456/orders/789012"
        parameterized, extracted = extractor.extract_from_url(url)

        # Should extract both IDs
        assert '${id}' in parameterized
        assert 'id' in extracted or 'id2' in extracted

    def test_extract_from_json_body(self):
        extractor = VariableExtractor()

        body = '{"id": "123456", "uuid": "550e8400-e29b-41d4-a716-446655440000"}'
        extracted = extractor.extract_from_body(body)

        assert len(extracted) >= 1

    def test_handles_invalid_json_gracefully(self):
        extractor = VariableExtractor()

        body = "not valid json"
        extracted = extractor.extract_from_body(body)

        assert extracted == {}

    def test_variable_reuse(self):
        """Test that same value gets same variable name"""
        extractor = VariableExtractor()

        url1 = "https://api.example.com/users/12345"
        url2 = "https://api.example.com/orders/12345"

        _, extracted1 = extractor.extract_from_url(url1)
        _, extracted2 = extractor.extract_from_url(url2)

        # Second extraction should reuse the variable
        assert len(extractor.variables) == 1


class TestRequestGrouper:
    """Test request grouping strategies"""

    def test_group_by_endpoint(self):
        grouper = RequestGrouper()

        requests = [
            {'method': 'GET', 'url': 'https://api.example.com/users/123'},
            {'method': 'GET', 'url': 'https://api.example.com/users/456'},
            {'method': 'POST', 'url': 'https://api.example.com/users'},
        ]

        groups = grouper.group_by_endpoint(requests)

        # Should have 2 groups: GET /users/{id} and POST /users
        assert len(groups) == 2
        assert any('GET' in key for key in groups.keys())
        assert any('POST' in key for key in groups.keys())

    def test_path_normalization(self):
        grouper = RequestGrouper()

        # Different IDs should normalize to same endpoint
        endpoint1 = grouper._get_endpoint_key({
            'method': 'GET',
            'url': 'https://api.example.com/users/123'
        })
        endpoint2 = grouper._get_endpoint_key({
            'method': 'GET',
            'url': 'https://api.example.com/users/456'
        })

        assert endpoint1 == endpoint2
        assert '{id}' in endpoint1

    def test_normalize_uuid_in_path(self):
        grouper = RequestGrouper()

        path = "/users/550e8400-e29b-41d4-a716-446655440000/profile"
        normalized = grouper._normalize_path(path)

        assert '{uuid}' in normalized
        assert 'profile' in normalized

    def test_group_by_flow(self):
        grouper = RequestGrouper()

        # Requests within time gap
        requests = [
            {'method': 'GET', 'url': 'https://api.example.com/users', 'timestamp': '2024-01-01T10:00:00Z'},
            {'method': 'POST', 'url': 'https://api.example.com/users', 'timestamp': '2024-01-01T10:00:05Z'},
            # Large gap - should be different flow
            {'method': 'GET', 'url': 'https://api.example.com/orders', 'timestamp': '2024-01-01T10:05:00Z'},
        ]

        flows = grouper.group_by_flow(requests, time_gap_seconds=30)

        # Should have 2 flows
        assert len(flows) == 2
        assert len(flows[0]) == 2  # First two requests
        assert len(flows[1]) == 1  # Last request

    def test_empty_requests(self):
        grouper = RequestGrouper()

        groups = grouper.group_by_endpoint([])
        assert len(groups) == 0

        flows = grouper.group_by_flow([])
        assert len(flows) == 0


class TestPlaywrightGenerator:
    """Test Playwright test code generation"""

    def test_generates_valid_test_structure(self):
        generator = PlaywrightGenerator()

        requests = [
            {
                'method': 'GET',
                'url': 'https://api.example.com/users',
                'status_code': 200,
                'response_body': '{"users": []}'
            }
        ]

        code = generator.generate_test_file(requests, grouping='endpoint')

        # Check for required Playwright imports
        assert 'import { test, expect }' in code
        assert "from '@playwright/test'" in code

        # Check for test structure
        assert 'test.describe' in code
        assert 'test(' in code
        assert 'async' in code

    def test_generates_endpoint_grouped_tests(self):
        generator = PlaywrightGenerator()

        requests = [
            {
                'method': 'GET',
                'url': 'https://api.example.com/users/123',
                'status_code': 200,
                'response_body': '{"id": 123}'
            },
            {
                'method': 'POST',
                'url': 'https://api.example.com/users',
                'status_code': 201,
                'body': '{"name": "Test"}',
                'response_body': '{"id": 456}'
            }
        ]

        code = generator.generate_test_file(requests, grouping='endpoint')

        # Should have separate tests for GET and POST
        assert code.count('test(') >= 2
        assert 'request.get' in code
        assert 'request.post' in code

    def test_generates_flow_grouped_tests(self):
        generator = PlaywrightGenerator()

        requests = [
            {
                'method': 'GET',
                'url': 'https://api.example.com/users',
                'status_code': 200,
                'timestamp': '2024-01-01T10:00:00Z'
            },
            {
                'method': 'POST',
                'url': 'https://api.example.com/users',
                'status_code': 201,
                'timestamp': '2024-01-01T10:00:05Z'
            }
        ]

        code = generator.generate_test_file(requests, grouping='flow')

        # Should have flow-based test
        assert 'Flow' in code

    def test_includes_request_body_for_post(self):
        generator = PlaywrightGenerator()

        request = {
            'method': 'POST',
            'url': 'https://api.example.com/users',
            'status_code': 201,
            'body': '{"name": "Test User", "email": "test@example.com"}',
            'response_body': '{"id": 123}'
        }

        code = generator._generate_single_test('Create User', request)

        # Should include request body data
        assert 'data:' in code
        assert 'Test User' in code

    def test_handles_variables_in_url(self):
        generator = PlaywrightGenerator()

        request = {
            'method': 'GET',
            'url': 'https://api.example.com/users/123456',
            'status_code': 200,
            'response_body': '{}'
        }

        code = generator._generate_single_test('Get User', request)

        # Should have variable declaration and usage
        assert 'const' in code
        assert '${' in code

    def test_assertion_integration(self):
        """Test that assertions from AssertionBuilder are included"""
        from tracetap.generators.assertion_builder import AssertionBuilder

        builder = AssertionBuilder(status_codes=True, response_schemas=True)
        generator = PlaywrightGenerator(assertion_builder=builder)

        request = {
            'method': 'GET',
            'url': 'https://api.example.com/users',
            'status_code': 200,
            'response_body': '{"id": 123, "name": "Test"}'
        }

        code = generator._generate_single_test('Get Users', request)

        # Should include assertions from builder
        assert 'expect(' in code


class TestRegressionGenerator:
    """Test main regression generator"""

    @pytest.fixture
    def sample_traffic_file(self):
        """Create a temporary sample traffic file"""
        data = {
            "metadata": {"session_name": "test"},
            "requests": [
                {
                    "method": "GET",
                    "url": "https://api.example.com/users",
                    "status_code": 200,
                    "response_body": '{"users": []}'
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            return f.name

    def test_generate_from_file_success(self, sample_traffic_file):
        generator = RegressionGenerator()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.spec.ts', delete=False) as output_file:
            output_path = output_file.name

        try:
            success = generator.generate_from_file(
                json_file=sample_traffic_file,
                output_file=output_path,
                grouping='endpoint'
            )

            assert success is True
            assert Path(output_path).exists()

            # Verify generated content
            content = Path(output_path).read_text()
            assert 'import { test, expect }' in content
            assert 'test.describe' in content

        finally:
            # Cleanup
            Path(sample_traffic_file).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

    def test_handles_missing_file(self):
        generator = RegressionGenerator()

        success = generator.generate_from_file(
            json_file='/nonexistent/file.json',
            output_file='/tmp/output.spec.ts'
        )

        assert success is False

    def test_handles_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json {]")
            invalid_file = f.name

        try:
            generator = RegressionGenerator()
            success = generator.generate_from_file(
                json_file=invalid_file,
                output_file='/tmp/output.spec.ts'
            )

            assert success is False

        finally:
            Path(invalid_file).unlink(missing_ok=True)

    def test_handles_empty_requests(self):
        data = {"metadata": {}, "requests": []}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            empty_file = f.name

        try:
            generator = RegressionGenerator()
            success = generator.generate_from_file(
                json_file=empty_file,
                output_file='/tmp/output.spec.ts'
            )

            assert success is False  # Should fail with no requests

        finally:
            Path(empty_file).unlink(missing_ok=True)

    def test_assertion_configuration(self, sample_traffic_file):
        """Test assertion type configuration"""
        generator = RegressionGenerator()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.spec.ts', delete=False) as output_file:
            output_path = output_file.name

        try:
            success = generator.generate_from_file(
                json_file=sample_traffic_file,
                output_file=output_path,
                assert_types=['status-codes', 'response-schemas']
            )

            assert success is True
            assert generator.assertion_builder is not None

        finally:
            Path(sample_traffic_file).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)


class TestGenerateRegressionTests:
    """Test convenience function"""

    def test_convenience_function(self):
        """Test the module-level convenience function"""
        # Use the sample traffic fixture file
        fixture_path = Path(__file__).parent / 'fixtures' / 'sample-traffic.json'

        if not fixture_path.exists():
            pytest.skip("Sample traffic fixture not found")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.spec.ts', delete=False) as output_file:
            output_path = output_file.name

        try:
            success = generate_regression_tests(
                json_file=str(fixture_path),
                output_file=output_path,
                grouping='endpoint',
                assert_types=['status-codes']
            )

            assert success is True
            assert Path(output_path).exists()

            # Verify it's valid Playwright code
            content = Path(output_path).read_text()
            assert 'import' in content
            assert 'test(' in content

        finally:
            Path(output_path).unlink(missing_ok=True)


# Integration tests with real fixture data
class TestIntegrationWithFixture:
    """Integration tests using the sample-traffic.json fixture"""

    @pytest.fixture
    def fixture_file(self):
        return Path(__file__).parent / 'fixtures' / 'sample-traffic.json'

    def test_full_generation_workflow(self, fixture_file):
        """Test complete generation workflow with real data"""
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.spec.ts', delete=False) as f:
            output_path = f.name

        try:
            success = generate_regression_tests(
                json_file=str(fixture_file),
                output_file=output_path,
                grouping='endpoint',
                base_url='https://api.example.com',
                assert_types=['status-codes', 'response-schemas'],
                critical_fields=['id', 'email']
            )

            assert success is True

            content = Path(output_path).read_text()

            # Verify structure
            assert 'import { test, expect }' in content
            assert 'test.describe' in content
            assert 'async' in content

            # Verify HTTP methods are present
            assert 'request.get' in content
            assert 'request.post' in content
            assert 'request.put' in content
            assert 'request.delete' in content

            # Verify assertions
            assert 'expect(' in content
            assert '.status()' in content or 'status_code' in content

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_handles_100_plus_requests(self, fixture_file):
        """Test that generator can handle 100+ requests efficiently"""
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        # Load and duplicate requests to get 100+
        with open(fixture_file) as f:
            data = json.load(f)

        original_requests = data['requests']
        data['requests'] = original_requests * 25  # 5 * 25 = 125 requests

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            large_file = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.spec.ts', delete=False) as f:
            output_path = f.name

        try:
            success = generate_regression_tests(
                json_file=large_file,
                output_file=output_path
            )

            assert success is True
            assert Path(output_path).exists()

        finally:
            Path(large_file).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
