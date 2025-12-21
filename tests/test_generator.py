"""
Tests for TraceTap Response Generator

Tests AI-powered response generation including:
- Static response generation
- Template-based responses
- Response transformers
- AI-powered intelligent responses
- Sequential responses
"""

import pytest
import json
from unittest.mock import Mock, patch

from src.tracetap.mock.generator import (
    ResponseTemplate,
    ResponseGenerator,
    add_timestamp_transformer,
    replace_ids_transformer,
    cors_headers_transformer,
    pretty_json_transformer
)


@pytest.fixture
def sample_capture():
    """Sample capture for response generation."""
    return {
        'method': 'GET',
        'url': 'https://api.example.com/users/123',
        'status': 200,
        'resp_headers': {
            'Content-Type': 'application/json',
            'X-Custom-Header': 'value'
        },
        'resp_body': '{"id": 123, "name": "John Doe", "email": "john@example.com"}'
    }


class TestResponseTemplate:
    """Test ResponseTemplate dataclass."""

    def test_template_creation(self):
        """Test creating response template."""
        template = ResponseTemplate(
            status_code=200,
            headers={'Content-Type': 'application/json'},
            body_template='{"id": "{{user_id}}", "name": "{{name}}"}',
            variables={'user_id': '123'}
        )

        assert template.status_code == 200
        assert template.body_template.startswith('{')

    def test_template_render(self):
        """Test rendering template with context."""
        template = ResponseTemplate(
            status_code=200,
            headers={'Content-Type': 'application/json'},
            body_template='{"id": "{{user_id}}", "name": "{{name}}"}',
            variables={}
        )

        context = {
            'user_id': '999',
            'name': 'Test User'
        }

        rendered = template.render(context)

        assert rendered['status'] == 200
        assert '999' in rendered['resp_body']
        assert 'Test User' in rendered['resp_body']

    def test_template_render_headers(self):
        """Test rendering template with variables in headers."""
        template = ResponseTemplate(
            status_code=200,
            headers={'X-User-Id': '{{user_id}}'},
            body_template='{}',
            variables={}
        )

        context = {'user_id': '123'}

        rendered = template.render(context)

        assert rendered['resp_headers']['X-User-Id'] == '123'


class TestResponseGenerator:
    """Test ResponseGenerator class."""

    def test_generator_initialization_no_ai(self):
        """Test initializing generator without AI."""
        generator = ResponseGenerator(use_ai=False)

        assert generator.use_ai is False
        assert generator.client is None

    @patch('src.tracetap.common.ai_utils.create_anthropic_client')
    def test_generator_initialization_with_ai(self, mock_create_client):
        """Test initializing generator with AI."""
        mock_client = Mock()
        mock_create_client.return_value = (mock_client, True, "AI enabled")

        generator = ResponseGenerator(use_ai=True, api_key='test-key')

        assert generator.use_ai is True

    def test_generate_static(self, sample_capture):
        """Test static response generation."""
        generator = ResponseGenerator()

        response = generator.generate(sample_capture, mode='static')

        assert response['status'] == 200
        assert response['resp_headers']['Content-Type'] == 'application/json'
        assert '123' in response['resp_body']

    def test_generate_template(self, sample_capture):
        """Test template-based response generation."""
        generator = ResponseGenerator()

        # Modify capture to have template variables
        capture = sample_capture.copy()
        capture['resp_body'] = '{"id": {{user_id}}, "name": "{{name}}"}'

        context = {
            'user_id': '999',
            'name': 'Test User'
        }

        response = generator.generate(capture, context, mode='template')

        assert '999' in response['resp_body']
        assert 'Test User' in response['resp_body']

    @pytest.mark.skip(reason="add_transformer method removed as dead code")
    def test_generate_transformed(self, sample_capture):
        """Test response generation with transformers."""
        generator = ResponseGenerator()

        # Add a simple transformer
        def test_transformer(response, context):
            response['resp_headers']['X-Transformed'] = 'true'
            return response

        generator.add_transformer(test_transformer)

        response = generator.generate(sample_capture, mode='transform')

        assert response['resp_headers']['X-Transformed'] == 'true'

    def test_generate_ai_success(self, sample_capture):
        """Test AI-powered response generation."""
        # Mock Claude response
        mock_response = Mock()
        mock_response.content = [Mock(text='{"id": 999, "name": "AI Generated"}')]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        generator = ResponseGenerator(use_ai=False, api_key='test-key')
        # Manually set AI attributes to bypass ANTHROPIC_AVAILABLE check
        generator.use_ai = True
        generator.client = mock_client

        context = {
            'method': 'GET',
            'url': 'https://api.example.com/users/999',
            'body': ''
        }

        response = generator._generate_ai(sample_capture, context)

        assert '999' in response['resp_body']
        assert 'AI Generated' in response['resp_body']

    def test_extract_response_body_from_code_block(self):
        """Test extracting response body from code block."""
        generator = ResponseGenerator()

        response_text = '''
        Here's the response:
        ```json
        {"id": 123, "name": "Test"}
        ```
        '''

        body = generator._extract_response_body(response_text)

        assert '123' in body
        assert 'Test' in body

    def test_extract_response_body_plain_json(self):
        """Test extracting plain JSON response."""
        generator = ResponseGenerator()

        response_text = '{"id": 123, "name": "Test"}'

        body = generator._extract_response_body(response_text)

        assert body == response_text


class TestResponseTemplates:
    """Test template management."""

    def test_add_template(self):
        """Test adding named template."""
        generator = ResponseGenerator()

        template = ResponseTemplate(
            status_code=200,
            headers={'Content-Type': 'application/json'},
            body_template='{"id": "{{id}}"}',
            variables={}
        )

        generator.add_template('user_response', template)

        assert 'user_response' in generator.templates

    def test_generate_from_named_template(self):
        """Test generating from named template."""
        generator = ResponseGenerator()

        template = ResponseTemplate(
            status_code=201,
            headers={'Content-Type': 'application/json'},
            body_template='{"id": "{{id}}", "status": "created"}',
            variables={}
        )

        generator.add_template('create_user', template)

        context = {'id': '999'}
        response = generator.generate_from_named_template('create_user', context)

        assert response is not None
        assert response['status'] == 201
        assert '999' in response['resp_body']

    def test_generate_from_missing_template(self):
        """Test generating from non-existent template."""
        generator = ResponseGenerator()

        response = generator.generate_from_named_template('nonexistent', {})

        assert response is None


class TestResponseSequences:
    """Test sequential response generation."""

    @pytest.mark.skip(reason="create_sequence and get_next_from_sequence methods removed as dead code")
    def test_create_sequence(self):
        """Test creating response sequence."""
        generator = ResponseGenerator()

        responses = [
            {'status': 200, 'resp_body': 'First'},
            {'status': 200, 'resp_body': 'Second'},
            {'status': 200, 'resp_body': 'Third'}
        ]

        generator.create_sequence('test_seq', responses)

        assert 'test_seq' in generator.sequences

    @pytest.mark.skip(reason="create_sequence and get_next_from_sequence methods removed as dead code")
    def test_get_next_from_sequence(self):
        """Test getting next response from sequence."""
        generator = ResponseGenerator()

        responses = [
            {'status': 200, 'resp_body': 'First'},
            {'status': 200, 'resp_body': 'Second'}
        ]

        generator.create_sequence('test_seq', responses)

        # First call
        resp1 = generator.get_next_from_sequence('test_seq')
        assert resp1['resp_body'] == 'First'

        # Second call
        resp2 = generator.get_next_from_sequence('test_seq')
        assert resp2['resp_body'] == 'Second'

        # Should cycle back to first
        resp3 = generator.get_next_from_sequence('test_seq')
        assert resp3['resp_body'] == 'First'

    @pytest.mark.skip(reason="create_sequence and get_next_from_sequence methods removed as dead code")
    def test_get_next_from_missing_sequence(self):
        """Test getting from non-existent sequence."""
        generator = ResponseGenerator()

        response = generator.get_next_from_sequence('nonexistent')

        assert response is None


class TestIntelligentGeneration:
    """Test intelligent response generation."""

    def test_generate_intelligent_uses_ai(self, sample_capture):
        """Test intelligent generation uses AI when available."""
        mock_response = Mock()
        mock_response.content = [Mock(text='{"id": 123}')]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        generator = ResponseGenerator(use_ai=False, api_key='test-key')
        # Manually set AI attributes to bypass ANTHROPIC_AVAILABLE check
        generator.use_ai = True
        generator.client = mock_client

        context = {
            'method': 'GET',
            'url': 'https://api.example.com/test'
        }

        response = generator.generate_intelligent(sample_capture, context)

        # Should have used AI
        mock_client.messages.create.assert_called_once()

    def test_generate_intelligent_fallback_to_static(self, sample_capture):
        """Test intelligent generation falls back to static."""
        generator = ResponseGenerator(use_ai=False)

        context = {}

        response = generator.generate_intelligent(sample_capture, context)

        # Should return static response
        assert response['status'] == 200


class TestTransformerFunctions:
    """Test built-in transformer functions."""

    def test_add_timestamp_transformer(self):
        """Test timestamp transformer."""
        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': '{"id": 123}'
        }

        transformed = add_timestamp_transformer(response, {})

        # Should add timestamp to JSON body
        body = json.loads(transformed['resp_body'])
        assert 'timestamp' in body

    def test_add_timestamp_transformer_non_json(self):
        """Test timestamp transformer with non-JSON."""
        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': 'plain text'
        }

        transformed = add_timestamp_transformer(response, {})

        # Should not modify non-JSON body
        assert transformed['resp_body'] == 'plain text'

    def test_replace_ids_transformer(self):
        """Test ID replacement transformer."""
        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': '{"id": 123, "user_id": 456}'
        }

        context = {
            'id': 999,
            'user_id': 888
        }

        transformed = replace_ids_transformer(response, context)

        body = json.loads(transformed['resp_body'])
        assert body['id'] == 999
        assert body['user_id'] == 888

    def test_cors_headers_transformer(self):
        """Test CORS headers transformer."""
        response = {
            'status': 200,
            'resp_headers': {'Content-Type': 'application/json'},
            'resp_body': '{}'
        }

        transformed = cors_headers_transformer(response, {})

        headers = transformed['resp_headers']
        assert 'Access-Control-Allow-Origin' in headers
        assert headers['Access-Control-Allow-Origin'] == '*'
        assert 'Access-Control-Allow-Methods' in headers

    def test_pretty_json_transformer(self):
        """Test pretty JSON transformer."""
        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': '{"id":123,"name":"John"}'
        }

        transformed = pretty_json_transformer(response, {})

        # Should be pretty-printed
        assert '\n' in transformed['resp_body']
        assert '  ' in transformed['resp_body']  # Indentation


class TestTransformerChaining:
    """Test chaining multiple transformers."""

    @pytest.mark.skip(reason="add_transformer method removed as dead code")
    def test_multiple_transformers(self):
        """Test applying multiple transformers in sequence."""
        generator = ResponseGenerator()

        # Add multiple transformers
        generator.add_transformer(add_timestamp_transformer)
        generator.add_transformer(cors_headers_transformer)
        generator.add_transformer(pretty_json_transformer)

        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': '{"id": 123}'
        }

        transformed = generator._generate_transformed(response, {})

        # Check all transformations were applied
        body = json.loads(transformed['resp_body'])
        assert 'timestamp' in body  # From timestamp transformer
        assert 'Access-Control-Allow-Origin' in transformed['resp_headers']  # From CORS
        assert '\n' in transformed['resp_body']  # From pretty print


class TestCustomTransformers:
    """Test custom transformer functions."""

    @pytest.mark.skip(reason="add_transformer method removed as dead code")
    def test_custom_transformer(self):
        """Test adding and using custom transformer."""
        generator = ResponseGenerator()

        def custom_transformer(response, context):
            """Add custom header."""
            response['resp_headers']['X-Custom'] = 'custom-value'
            return response

        generator.add_transformer(custom_transformer)

        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': '{}'
        }

        transformed = generator._generate_transformed(response, {})

        assert transformed['resp_headers']['X-Custom'] == 'custom-value'

    @pytest.mark.skip(reason="add_transformer method removed as dead code")
    def test_transformer_with_context(self):
        """Test transformer using context."""
        generator = ResponseGenerator()

        def context_transformer(response, context):
            """Use context in transformation."""
            if 'add_header' in context:
                response['resp_headers']['X-Context'] = context['add_header']
            return response

        generator.add_transformer(context_transformer)

        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': '{}'
        }

        context = {'add_header': 'context-value'}

        transformed = generator._generate_transformed(response, context)

        assert transformed['resp_headers']['X-Context'] == 'context-value'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
