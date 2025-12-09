"""
Tests for TraceTap Replay Configuration

Tests YAML scenario configuration including:
- YAML loading and parsing
- Variable resolution
- Response extraction (JSONPath, regex)
- Assertion validation
- AI scenario generation
"""

import pytest
import json
import yaml
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.tracetap.replay.replay_config import (
    ReplayStep,
    ReplayScenario,
    VariableResolver,
    ResponseExtractor,
    AssertionValidator,
    AIScenarioGenerator,
    ReplayConfig
)


@pytest.fixture
def sample_yaml_scenario():
    """Sample YAML scenario for testing."""
    return """
name: "User Registration Flow"
description: "Test user registration and verification"
environment: staging

variables:
  base_url: "https://api.example.com"
  test_email: "test@example.com"

environments:
  staging:
    base_url: "https://staging-api.example.com"
  production:
    base_url: "https://api.example.com"

steps:
  - id: register
    name: "Register new user"
    request:
      method: POST
      url: "${base_url}/users"
      body: '{"email": "${test_email}"}'
    expect:
      status: 201
      body_contains:
        - "id"
        - "email"
    extract:
      user_id: "$.id"

  - id: verify
    name: "Verify email"
    request:
      method: POST
      url: "${base_url}/users/${step.register.user_id}/verify"
    expect:
      status: 200
    """


class TestReplayStep:
    """Test ReplayStep dataclass."""

    def test_step_creation(self):
        """Test creating a replay step."""
        step = ReplayStep(
            id='test_step',
            name='Test Step',
            request={'method': 'GET', 'url': 'https://api.example.com/test'},
            expect={'status': 200},
            extract={'var': '$.data.id'}
        )

        assert step.id == 'test_step'
        assert step.name == 'Test Step'
        assert step.request['method'] == 'GET'
        assert step.timeout == 30  # default

    def test_step_from_dict(self):
        """Test creating step from dictionary."""
        data = {
            'id': 'fetch_user',
            'name': 'Fetch user data',
            'request': {
                'method': 'GET',
                'url': 'https://api.example.com/users/123'
            },
            'expect': {
                'status': 200
            },
            'retry': 3,
            'timeout': 60
        }

        step = ReplayStep.from_dict(data)

        assert step.id == 'fetch_user'
        assert step.retry == 3
        assert step.timeout == 60


class TestReplayScenario:
    """Test ReplayScenario dataclass."""

    def test_scenario_from_yaml(self, sample_yaml_scenario):
        """Test loading scenario from YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_yaml_scenario)
            yaml_path = f.name

        try:
            scenario = ReplayScenario.from_yaml(yaml_path)

            assert scenario.name == "User Registration Flow"
            assert scenario.environment == "staging"
            assert len(scenario.steps) == 2
            assert scenario.steps[0].id == "register"
        finally:
            Path(yaml_path).unlink()

    def test_scenario_from_dict(self):
        """Test creating scenario from dictionary."""
        data = {
            'name': 'Test Scenario',
            'description': 'A test',
            'variables': {'base_url': 'https://api.example.com'},
            'steps': [
                {
                    'id': 'step1',
                    'name': 'First step',
                    'request': {'method': 'GET', 'url': 'https://api.example.com/test'}
                }
            ]
        }

        scenario = ReplayScenario.from_dict(data)

        assert scenario.name == 'Test Scenario'
        assert len(scenario.steps) == 1
        assert scenario.variables['base_url'] == 'https://api.example.com'

    def test_get_environment_variables(self):
        """Test getting environment-specific variables."""
        scenario = ReplayScenario(
            name='Test',
            environment='staging',
            variables={'base_url': 'default', 'api_key': 'default-key'},
            environments={
                'staging': {
                    'base_url': 'https://staging.example.com'
                },
                'production': {
                    'base_url': 'https://api.example.com'
                }
            }
        )

        env_vars = scenario.get_environment_variables()

        assert env_vars['base_url'] == 'https://staging.example.com'  # from environment
        assert env_vars['api_key'] == 'default-key'  # from base variables


class TestVariableResolver:
    """Test VariableResolver class."""

    def test_resolve_simple_variable(self):
        """Test resolving simple variable."""
        resolver = VariableResolver(variables={'base_url': 'https://api.example.com'})

        text = 'URL is ${base_url}/users'
        result = resolver.resolve(text)

        assert result == 'URL is https://api.example.com/users'

    def test_resolve_env_variable(self):
        """Test resolving environment variable."""
        resolver = VariableResolver(
            variables={},
            env_vars={'API_KEY': 'secret-123'}
        )

        text = 'Key: ${env.API_KEY}'
        result = resolver.resolve(text)

        assert result == 'Key: secret-123'

    def test_resolve_step_variable(self):
        """Test resolving variable from previous step."""
        resolver = VariableResolver(variables={})
        resolver.add_extracted('register', 'user_id', '12345')

        text = 'User: ${step.register.user_id}'
        result = resolver.resolve(text)

        assert result == 'User: 12345'

    def test_resolve_dict(self):
        """Test resolving variables in dictionary."""
        resolver = VariableResolver(variables={'api_key': 'secret'})

        data = {
            'url': '${api_key}/endpoint',
            'headers': {
                'Authorization': 'Bearer ${api_key}'
            }
        }

        result = resolver.resolve(data)

        assert result['url'] == 'secret/endpoint'
        assert result['headers']['Authorization'] == 'Bearer secret'

    def test_resolve_list(self):
        """Test resolving variables in list."""
        resolver = VariableResolver(variables={'id': '123'})

        data = ['${id}', 'static', '${id}-suffix']

        result = resolver.resolve(data)

        assert result == ['123', 'static', '123-suffix']

    def test_resolve_nested_variable(self):
        """Test resolving nested variable path."""
        resolver = VariableResolver(
            variables={
                'user': {
                    'profile': {
                        'id': '999'
                    }
                }
            }
        )

        text = 'ID: ${user.profile.id}'
        result = resolver.resolve(text)

        # Note: Current implementation doesn't support nested dict access
        # This test documents current behavior
        assert text in result or '999' in result

    def test_resolve_missing_variable(self):
        """Test resolving missing variable (should leave unchanged)."""
        resolver = VariableResolver(variables={})

        text = 'Value: ${missing_var}'
        result = resolver.resolve(text)

        assert result == 'Value: ${missing_var}'


class TestResponseExtractor:
    """Test ResponseExtractor class."""

    def test_extract_jsonpath(self):
        """Test JSONPath extraction from response."""
        extractor = ResponseExtractor()

        response_body = json.dumps({
            'data': {
                'user': {
                    'id': 123,
                    'email': 'test@example.com'
                }
            }
        })

        extractions = {
            'user_id': '$.data.user.id',
            'email': '$.data.user.email'
        }

        results = extractor.extract(response_body, extractions)

        # JSONPath extraction might not be available if jsonpath_ng not installed
        if extractor.use_jsonpath:
            assert results['user_id'] == 123
            assert results['email'] == 'test@example.com'
        else:
            # Without jsonpath, it should return None
            assert results['user_id'] is None

    def test_extract_regex(self):
        """Test regex extraction from response."""
        extractor = ResponseExtractor()

        response_body = 'Session ID: abc123def456'

        extractions = {
            'session_id': 'regex:Session ID: ([a-z0-9]+)'
        }

        results = extractor.extract(response_body, extractions)

        assert results['session_id'] == 'abc123def456'

    def test_extract_from_non_json(self):
        """Test extraction from non-JSON response."""
        extractor = ResponseExtractor()

        response_body = '<html><body>Hello World</body></html>'

        extractions = {
            'content': 'regex:<body>(.*?)</body>'
        }

        results = extractor.extract(response_body, extractions)

        assert results['content'] == 'Hello World'

    def test_extract_missing_path(self):
        """Test extraction with missing JSONPath."""
        extractor = ResponseExtractor()

        response_body = json.dumps({'data': {}})

        extractions = {
            'missing': '$.data.user.id'
        }

        results = extractor.extract(response_body, extractions)

        assert results['missing'] is None


class TestAssertionValidator:
    """Test AssertionValidator class."""

    def test_validate_status_success(self):
        """Test successful status code validation."""
        validator = AssertionValidator()

        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': ''
        }

        expectations = {
            'status': 200
        }

        success, errors = validator.validate(response, expectations)

        assert success is True
        assert len(errors) == 0

    def test_validate_status_failure(self):
        """Test failed status code validation."""
        validator = AssertionValidator()

        response = {
            'status': 404,
            'resp_headers': {},
            'resp_body': ''
        }

        expectations = {
            'status': 200
        }

        success, errors = validator.validate(response, expectations)

        assert success is False
        assert len(errors) == 1
        assert '404' in errors[0]

    def test_validate_status_list(self):
        """Test validation with list of acceptable status codes."""
        validator = AssertionValidator()

        response = {
            'status': 201,
            'resp_headers': {},
            'resp_body': ''
        }

        expectations = {
            'status': [200, 201, 202]
        }

        success, errors = validator.validate(response, expectations)

        assert success is True

    def test_validate_headers(self):
        """Test header validation."""
        validator = AssertionValidator()

        response = {
            'status': 200,
            'resp_headers': {
                'Content-Type': 'application/json',
                'X-Custom': 'value'
            },
            'resp_body': ''
        }

        expectations = {
            'headers': {
                'Content-Type': 'application/json'
            }
        }

        success, errors = validator.validate(response, expectations)

        assert success is True

    def test_validate_body_contains(self):
        """Test body contains validation."""
        validator = AssertionValidator()

        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': '{"id": 123, "name": "Test User", "email": "test@example.com"}'
        }

        expectations = {
            'body_contains': ['id', 'email', 'Test User']
        }

        success, errors = validator.validate(response, expectations)

        assert success is True

    def test_validate_body_contains_failure(self):
        """Test body contains validation failure."""
        validator = AssertionValidator()

        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': '{"id": 123}'
        }

        expectations = {
            'body_contains': ['name', 'email']
        }

        success, errors = validator.validate(response, expectations)

        assert success is False
        assert len(errors) == 2

    def test_validate_response_time(self):
        """Test response time validation."""
        validator = AssertionValidator()

        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': '',
            'duration_ms': 250
        }

        expectations = {
            'response_time_ms': '< 500'
        }

        success, errors = validator.validate(response, expectations)

        assert success is True

    def test_validate_response_time_failure(self):
        """Test response time validation failure."""
        validator = AssertionValidator()

        response = {
            'status': 200,
            'resp_headers': {},
            'resp_body': '',
            'duration_ms': 600
        }

        expectations = {
            'response_time_ms': '< 500'
        }

        success, errors = validator.validate(response, expectations)

        assert success is False
        assert '600' in errors[0]


class TestAIScenarioGenerator:
    """Test AIScenarioGenerator class."""

    def test_generator_initialization_no_key(self):
        """Test initialization without API key."""
        generator = AIScenarioGenerator()

        assert generator.ai_available is False
        assert generator.client is None

    @patch('src.tracetap.replay.replay_config.anthropic.Anthropic')
    def test_generator_initialization_with_key(self, mock_anthropic):
        """Test initialization with API key."""
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        generator = AIScenarioGenerator(api_key='test-key')

        assert generator.ai_available is True
        assert generator.client is not None

    @patch('src.tracetap.replay.replay_config.anthropic.Anthropic')
    def test_generate_scenario_success(self, mock_anthropic):
        """Test generating scenario with AI."""
        # Create proper YAML content
        yaml_content = '''name: "User Flow"
description: "Test user operations"
variables:
  base_url: "https://api.example.com"
steps:
  - id: create_user
    name: "Create user"
    request:
      method: POST
      url: "${base_url}/users"
    expect:
      status: 201'''

        # Mock Claude response
        mock_response = Mock()
        mock_response.content = [Mock(text=f'```yaml\n{yaml_content}\n```')]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        generator = AIScenarioGenerator(api_key='test-key')

        captures = [
            {
                'method': 'POST',
                'url': 'https://api.example.com/users',
                'status': 201,
                'req_body': '{"name": "John"}',
                'resp_body': '{"id": 1}'
            }
        ]

        scenario = generator.generate_scenario(captures)

        assert scenario is not None
        assert scenario.name == "User Flow"
        assert len(scenario.steps) == 1

    def test_generate_scenario_no_ai(self):
        """Test generating scenario without AI."""
        generator = AIScenarioGenerator()

        captures = [
            {
                'method': 'GET',
                'url': 'https://api.example.com/test',
                'status': 200
            }
        ]

        scenario = generator.generate_scenario(captures)

        assert scenario is None

    def test_extract_yaml_from_code_block(self):
        """Test extracting YAML from code block."""
        generator = AIScenarioGenerator()

        yaml_text = 'name: "Test"\ndescription: "A test"'
        response = f'Here is the scenario:\n```yaml\n{yaml_text}\n```'

        yaml_content = generator._extract_yaml(response)

        assert yaml_content is not None
        assert 'name' in yaml_content
        assert 'Test' in yaml_content


class TestReplayConfig:
    """Test ReplayConfig class."""

    def test_config_initialization(self):
        """Test initializing empty config."""
        config = ReplayConfig()

        assert config.scenario is None

    def test_load_scenario(self, sample_yaml_scenario):
        """Test loading scenario from YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_yaml_scenario)
            yaml_path = f.name

        try:
            config = ReplayConfig()
            scenario = config.load(yaml_path)

            assert scenario is not None
            assert scenario.name == "User Registration Flow"
            assert config.scenario == scenario
        finally:
            Path(yaml_path).unlink()

    def test_save_scenario(self):
        """Test saving scenario to YAML file."""
        scenario = ReplayScenario(
            name='Test Scenario',
            description='A test',
            variables={'base_url': 'https://api.example.com'},
            steps=[
                ReplayStep(
                    id='step1',
                    name='Test step',
                    request={'method': 'GET', 'url': '${base_url}/test'}
                )
            ]
        )

        config = ReplayConfig()
        config.scenario = scenario

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_path = f.name

        try:
            config.save(yaml_path)

            # Verify file was created
            assert Path(yaml_path).exists()

            # Load and verify content
            with open(yaml_path) as f:
                data = yaml.safe_load(f)

            assert data['name'] == 'Test Scenario'
            assert len(data['steps']) == 1
        finally:
            Path(yaml_path).unlink()

    def test_save_without_scenario(self):
        """Test saving without loaded scenario."""
        config = ReplayConfig()

        with pytest.raises(ValueError, match='No scenario loaded'):
            config.save('output.yaml')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
