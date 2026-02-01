"""
Tests for Contract Creator

Tests OpenAPI contract generation from captured HTTP traffic.
"""

import json
import pytest
import yaml
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from tracetap.contract.contract_creator import (
    ContractCreator,
    create_contract_from_traffic
)


class TestContractCreator:
    """Test ContractCreator core functionality"""

    def test_initialization(self):
        creator = ContractCreator(title="Test API", version="1.0.0")
        assert creator.title == "Test API"
        assert creator.version == "1.0.0"
        assert creator.base_url is None

    def test_initialization_with_base_url(self):
        creator = ContractCreator(
            title="My API",
            version="2.0.0",
            base_url="https://api.example.com"
        )
        assert creator.base_url == "https://api.example.com"

    def test_create_empty_contract(self):
        creator = ContractCreator()
        contract = creator.create_contract([])

        assert contract['openapi'] == '3.0.0'
        assert contract['info']['title'] == 'API'
        assert contract['paths'] == {}

    def test_create_contract_extracts_base_url(self):
        creator = ContractCreator()
        requests = [
            {'method': 'GET', 'url': 'https://api.test.com/users', 'status_code': 200}
        ]

        contract = creator.create_contract(requests)

        assert contract['servers'][0]['url'] == 'https://api.test.com'

    def test_create_contract_basic_structure(self):
        creator = ContractCreator(title="Test API", version="1.0.0")
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users',
                'status_code': 200,
                'response_body': json.dumps({'id': 1, 'name': 'Test'})
            }
        ]

        contract = creator.create_contract(requests)

        assert contract['openapi'] == '3.0.0'
        assert contract['info']['title'] == 'Test API'
        assert contract['info']['version'] == '1.0.0'
        assert 'description' in contract['info']
        assert len(contract['servers']) == 1
        assert 'paths' in contract
        assert 'components' in contract


class TestPathNormalization:
    """Test path normalization and parameter detection"""

    def test_normalize_numeric_id(self):
        creator = ContractCreator()
        path = creator._normalize_path('/users/123')
        assert path == '/users/{id}'

    def test_normalize_uuid(self):
        creator = ContractCreator()
        path = creator._normalize_path('/users/550e8400-e29b-41d4-a716-446655440000')
        assert path == '/users/{id}'

    def test_normalize_mongodb_objectid(self):
        creator = ContractCreator()
        path = creator._normalize_path('/items/507f1f77bcf86cd799439011')
        assert path == '/items/{id}'

    def test_normalize_multiple_ids(self):
        creator = ContractCreator()
        path = creator._normalize_path('/users/123/orders/456')
        assert path == '/users/{id}/orders/{id}'

    def test_normalize_mixed_path(self):
        creator = ContractCreator()
        path = creator._normalize_path('/api/v1/users/550e8400-e29b-41d4-a716-446655440000/profile')
        assert path == '/api/v1/users/{id}/profile'

    def test_normalize_preserves_static_segments(self):
        creator = ContractCreator()
        path = creator._normalize_path('/api/users/profile')
        assert path == '/api/users/profile'

    def test_normalize_root_path(self):
        creator = ContractCreator()
        path = creator._normalize_path('/')
        assert path == '/'

    def test_normalize_empty_path(self):
        creator = ContractCreator()
        path = creator._normalize_path('')
        assert path == '/'


class TestRequestGrouping:
    """Test endpoint grouping logic"""

    def test_group_by_endpoint(self):
        creator = ContractCreator()
        requests = [
            {'method': 'GET', 'url': 'https://api.test.com/users/1', 'status_code': 200},
            {'method': 'GET', 'url': 'https://api.test.com/users/2', 'status_code': 200},
            {'method': 'POST', 'url': 'https://api.test.com/users', 'status_code': 201},
        ]

        groups = creator._group_by_endpoint(requests)

        assert len(groups) == 2
        assert 'GET::/users/{id}' in groups
        assert 'POST::/users' in groups
        assert len(groups['GET::/users/{id}']) == 2
        assert len(groups['POST::/users']) == 1

    def test_endpoint_key_extraction(self):
        creator = ContractCreator()
        req = {'method': 'PUT', 'url': 'https://api.test.com/items/123'}

        key = creator._get_endpoint_key(req)

        assert key == 'PUT::/items/{id}'

    def test_parse_endpoint_key(self):
        creator = ContractCreator()

        method, path = creator._parse_endpoint_key('GET::/users/{id}')
        assert method == 'GET'
        assert path == '/users/{id}'


class TestSchemaInference:
    """Test schema inference from request/response bodies"""

    def test_infer_request_body_schema(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'POST',
                'url': 'https://api.test.com/users',
                'body': json.dumps({'name': 'John', 'email': 'john@test.com', 'age': 30}),
                'status_code': 201
            }
        ]

        contract = creator.create_contract(requests)
        post_op = contract['paths']['/users']['post']

        assert 'requestBody' in post_op
        assert post_op['requestBody']['required'] is True
        assert 'application/json' in post_op['requestBody']['content']

        schema = post_op['requestBody']['content']['application/json']['schema']
        assert schema['type'] == 'object'
        assert 'name' in schema['properties']
        assert 'email' in schema['properties']
        assert 'age' in schema['properties']

    def test_infer_response_body_schema(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users/1',
                'status_code': 200,
                'response_body': json.dumps({'id': 1, 'name': 'John', 'active': True})
            }
        ]

        contract = creator.create_contract(requests)
        get_op = contract['paths']['/users/{id}']['get']

        assert '200' in get_op['responses']
        response = get_op['responses']['200']
        assert 'application/json' in response['content']

        schema = response['content']['application/json']['schema']
        assert schema['type'] == 'object'
        assert 'id' in schema['properties']
        assert 'name' in schema['properties']
        assert 'active' in schema['properties']

    def test_handles_array_responses(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users',
                'status_code': 200,
                'response_body': json.dumps([{'id': 1, 'name': 'John'}, {'id': 2, 'name': 'Jane'}])
            }
        ]

        contract = creator.create_contract(requests)
        get_op = contract['paths']['/users']['get']

        schema = get_op['responses']['200']['content']['application/json']['schema']
        assert schema['type'] == 'array'
        assert 'items' in schema


class TestParameterExtraction:
    """Test parameter extraction (path and query)"""

    def test_extract_path_parameters(self):
        creator = ContractCreator()
        requests = [
            {'method': 'GET', 'url': 'https://api.test.com/users/123', 'status_code': 200}
        ]

        contract = creator.create_contract(requests)
        get_op = contract['paths']['/users/{id}']['get']

        assert 'parameters' in get_op
        params = get_op['parameters']
        assert len(params) == 1
        assert params[0]['name'] == 'id'
        assert params[0]['in'] == 'path'
        assert params[0]['required'] is True

    def test_extract_query_parameters(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users?limit=10&offset=20&active=true',
                'status_code': 200
            }
        ]

        contract = creator.create_contract(requests)
        get_op = contract['paths']['/users']['get']

        assert 'parameters' in get_op
        param_names = {p['name'] for p in get_op['parameters']}
        assert 'limit' in param_names
        assert 'offset' in param_names
        assert 'active' in param_names

    def test_query_parameter_type_inference(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/items?page=1&sort=name',
                'status_code': 200
            }
        ]

        contract = creator.create_contract(requests)
        get_op = contract['paths']['/items']['get']

        params = {p['name']: p for p in get_op['parameters']}

        # Numeric query param should be integer
        assert params['page']['schema']['type'] == 'integer'

        # Non-numeric should be string
        assert params['sort']['schema']['type'] == 'string'

    def test_query_parameters_optional(self):
        creator = ContractCreator()
        requests = [
            {'method': 'GET', 'url': 'https://api.test.com/users?filter=active', 'status_code': 200}
        ]

        contract = creator.create_contract(requests)
        get_op = contract['paths']['/users']['get']

        params = get_op['parameters']
        assert all(p['required'] is False for p in params)


class TestSecurityDetection:
    """Test security scheme detection"""

    def test_detect_bearer_auth(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users',
                'headers': {'Authorization': 'Bearer token123'},
                'status_code': 200
            }
        ]

        contract = creator.create_contract(requests)

        assert 'bearerAuth' in contract['components']['securitySchemes']
        scheme = contract['components']['securitySchemes']['bearerAuth']
        assert scheme['type'] == 'http'
        assert scheme['scheme'] == 'bearer'
        assert scheme['bearerFormat'] == 'JWT'

    def test_detect_basic_auth(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users',
                'headers': {'Authorization': 'Basic dXNlcjpwYXNz'},
                'status_code': 200
            }
        ]

        contract = creator.create_contract(requests)

        assert 'basicAuth' in contract['components']['securitySchemes']
        scheme = contract['components']['securitySchemes']['basicAuth']
        assert scheme['type'] == 'http'
        assert scheme['scheme'] == 'basic'

    def test_detect_api_key(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users',
                'headers': {'X-API-Key': 'key123'},
                'status_code': 200
            }
        ]

        contract = creator.create_contract(requests)

        assert 'apiKeyAuth' in contract['components']['securitySchemes']
        scheme = contract['components']['securitySchemes']['apiKeyAuth']
        assert scheme['type'] == 'apiKey'
        assert scheme['in'] == 'header'
        assert scheme['name'] == 'X-API-Key'

    def test_operation_security(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users',
                'headers': {'Authorization': 'Bearer token123'},
                'status_code': 200
            }
        ]

        contract = creator.create_contract(requests)
        get_op = contract['paths']['/users']['get']

        assert 'security' in get_op
        assert get_op['security'] == [{'bearerAuth': []}]


class TestOperationGeneration:
    """Test OpenAPI operation generation"""

    def test_generate_summary(self):
        creator = ContractCreator()

        assert creator._generate_summary('GET', '/users') == 'Get users'
        assert creator._generate_summary('POST', '/users') == 'Create users'
        assert creator._generate_summary('PUT', '/users/{id}') == 'Update users'
        assert creator._generate_summary('DELETE', '/orders/{id}') == 'Delete orders'

    def test_generate_operation_id(self):
        creator = ContractCreator()

        assert creator._generate_operation_id('GET', '/users') == 'getUsers'
        assert creator._generate_operation_id('POST', '/users') == 'postUsers'
        assert creator._generate_operation_id('GET', '/users/{id}') == 'getUsersId'
        assert creator._generate_operation_id('GET', '/users/{id}/orders') == 'getUsersIdOrders'

    def test_extract_tags(self):
        creator = ContractCreator()

        tags = creator._extract_tags('/users')
        assert tags == ['users']

        tags = creator._extract_tags('/users/{id}')
        assert tags == ['users']

        tags = creator._extract_tags('/')
        assert tags == ['default']

    def test_create_operation_structure(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users',
                'status_code': 200,
                'response_body': json.dumps([])
            }
        ]

        contract = creator.create_contract(requests)
        get_op = contract['paths']['/users']['get']

        assert 'summary' in get_op
        assert 'operationId' in get_op
        assert 'tags' in get_op
        assert 'responses' in get_op


class TestResponseGeneration:
    """Test response generation"""

    def test_multiple_status_codes(self):
        creator = ContractCreator()
        requests = [
            {'method': 'GET', 'url': 'https://api.test.com/users/1', 'status_code': 200},
            {'method': 'GET', 'url': 'https://api.test.com/users/999', 'status_code': 404},
            {'method': 'GET', 'url': 'https://api.test.com/users/2', 'status_code': 200},
        ]

        contract = creator.create_contract(requests)
        get_op = contract['paths']['/users/{id}']['get']

        assert '200' in get_op['responses']
        assert '404' in get_op['responses']

    def test_status_descriptions(self):
        creator = ContractCreator()

        assert creator._get_status_description(200) == 'Successful response'
        assert creator._get_status_description(201) == 'Resource created successfully'
        assert creator._get_status_description(404) == 'Resource not found'
        assert creator._get_status_description(500) == 'Internal server error'

    def test_empty_response_body(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'DELETE',
                'url': 'https://api.test.com/users/1',
                'status_code': 204,
                'response_body': None
            }
        ]

        contract = creator.create_contract(requests)
        delete_op = contract['paths']['/users/{id}']['delete']

        assert '204' in delete_op['responses']
        response = delete_op['responses']['204']
        assert 'content' not in response or response.get('content') is None


class TestFileIO:
    """Test file I/O operations"""

    def test_save_contract(self, tmp_path):
        creator = ContractCreator(title="Test API", version="1.0.0")
        requests = [
            {'method': 'GET', 'url': 'https://api.test.com/users', 'status_code': 200}
        ]

        output_file = tmp_path / "contract.yaml"
        success = creator.save_contract(requests, str(output_file))

        assert success
        assert output_file.exists()

        # Verify it's valid YAML
        with open(output_file) as f:
            contract = yaml.safe_load(f)

        assert contract['openapi'] == '3.0.0'
        assert contract['info']['title'] == 'Test API'

    def test_save_contract_creates_directory(self, tmp_path):
        creator = ContractCreator()
        requests = [{'method': 'GET', 'url': 'https://api.test.com/test', 'status_code': 200}]

        output_file = tmp_path / "contracts" / "subdirectory" / "contract.yaml"
        success = creator.save_contract(requests, str(output_file))

        assert success
        assert output_file.exists()


class TestHTTPMethods:
    """Test different HTTP methods"""

    def test_get_operation(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users',
                'status_code': 200,
                'response_body': json.dumps([])
            }
        ]

        contract = creator.create_contract(requests)

        assert '/users' in contract['paths']
        assert 'get' in contract['paths']['/users']
        assert 'requestBody' not in contract['paths']['/users']['get']

    def test_post_operation(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'POST',
                'url': 'https://api.test.com/users',
                'body': json.dumps({'name': 'Test'}),
                'status_code': 201,
                'response_body': json.dumps({'id': 1, 'name': 'Test'})
            }
        ]

        contract = creator.create_contract(requests)

        assert '/users' in contract['paths']
        assert 'post' in contract['paths']['/users']
        assert 'requestBody' in contract['paths']['/users']['post']

    def test_put_operation(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'PUT',
                'url': 'https://api.test.com/users/1',
                'body': json.dumps({'name': 'Updated'}),
                'status_code': 200
            }
        ]

        contract = creator.create_contract(requests)

        assert '/users/{id}' in contract['paths']
        assert 'put' in contract['paths']['/users/{id}']
        assert 'requestBody' in contract['paths']['/users/{id}']['put']

    def test_delete_operation(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'DELETE',
                'url': 'https://api.test.com/users/1',
                'status_code': 204
            }
        ]

        contract = creator.create_contract(requests)

        assert '/users/{id}' in contract['paths']
        assert 'delete' in contract['paths']['/users/{id}']


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_invalid_json_body_ignored(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'POST',
                'url': 'https://api.test.com/users',
                'body': 'invalid json{',
                'status_code': 201
            }
        ]

        contract = creator.create_contract(requests)
        post_op = contract['paths']['/users']['post']

        # Should not have request body if JSON is invalid
        assert 'requestBody' not in post_op or post_op.get('requestBody') is None

    def test_missing_response_body(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users',
                'status_code': 200
                # No response_body field
            }
        ]

        contract = creator.create_contract(requests)

        # Should not crash
        assert '/users' in contract['paths']

    def test_no_headers(self):
        creator = ContractCreator()
        requests = [
            {
                'method': 'GET',
                'url': 'https://api.test.com/users',
                'status_code': 200
                # No headers field
            }
        ]

        contract = creator.create_contract(requests)

        # Should not detect security schemes
        assert contract['components']['securitySchemes'] == {}


class TestIntegrationWithSampleTraffic:
    """Integration tests with sample-traffic.json"""

    def test_create_from_sample_traffic(self):
        creator = ContractCreator(title="Example API", version="1.0.0")

        # Load sample traffic
        sample_file = Path(__file__).parent / 'fixtures' / 'sample-traffic.json'
        with open(sample_file) as f:
            data = json.load(f)

        requests = data['requests']
        contract = creator.create_contract(requests)

        # Verify contract structure
        assert contract['openapi'] == '3.0.0'
        assert contract['info']['title'] == 'Example API'

        # Should have detected endpoints
        assert '/users/{id}' in contract['paths']
        assert '/users' in contract['paths']

        # Should have multiple methods
        assert 'get' in contract['paths']['/users']
        assert 'post' in contract['paths']['/users']
        assert 'get' in contract['paths']['/users/{id}']
        assert 'put' in contract['paths']['/users/{id}']
        assert 'delete' in contract['paths']['/users/{id}']

    def test_detect_bearer_auth_from_sample(self):
        creator = ContractCreator()

        sample_file = Path(__file__).parent / 'fixtures' / 'sample-traffic.json'
        with open(sample_file) as f:
            data = json.load(f)

        contract = creator.create_contract(data['requests'])

        # Sample traffic has Bearer token
        assert 'bearerAuth' in contract['components']['securitySchemes']


class TestConvenienceFunction:
    """Test convenience function create_contract_from_traffic"""

    def test_create_contract_from_traffic(self, tmp_path):
        # Create input file
        input_file = tmp_path / "traffic.json"
        data = {
            'requests': [
                {
                    'method': 'GET',
                    'url': 'https://api.test.com/items',
                    'status_code': 200,
                    'response_body': json.dumps([{'id': 1}])
                }
            ]
        }
        input_file.write_text(json.dumps(data))

        # Create contract
        output_file = tmp_path / "contract.yaml"
        success = create_contract_from_traffic(
            str(input_file),
            str(output_file),
            title="Test API",
            version="1.0.0",
            verbose=False
        )

        assert success
        assert output_file.exists()

        # Verify contract
        with open(output_file) as f:
            contract = yaml.safe_load(f)

        assert contract['info']['title'] == 'Test API'
        assert '/items' in contract['paths']

    def test_handles_missing_file(self, tmp_path):
        output_file = tmp_path / "contract.yaml"

        success = create_contract_from_traffic(
            "/nonexistent/file.json",
            str(output_file),
            verbose=False
        )

        assert not success
        assert not output_file.exists()

    def test_handles_invalid_json(self, tmp_path):
        input_file = tmp_path / "invalid.json"
        input_file.write_text("{invalid json")

        output_file = tmp_path / "contract.yaml"
        success = create_contract_from_traffic(
            str(input_file),
            str(output_file),
            verbose=False
        )

        assert not success

    def test_handles_empty_requests(self, tmp_path):
        input_file = tmp_path / "empty.json"
        input_file.write_text(json.dumps({'requests': []}))

        output_file = tmp_path / "contract.yaml"
        success = create_contract_from_traffic(
            str(input_file),
            str(output_file),
            verbose=False
        )

        assert not success


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
