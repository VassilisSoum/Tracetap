"""
Tests for TraceTap Traffic Replayer

Tests the core replay engine functionality including:
- Loading captures from JSON
- Replaying requests to target servers
- Variable substitution
- Metrics tracking
- Concurrent execution
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

from src.tracetap.replay.replayer import (
    TrafficReplayer,
    ReplayMetrics,
    ReplayResult
)


@pytest.fixture
def sample_captures():
    """Sample captured requests for testing."""
    return [
        {
            'method': 'GET',
            'url': 'https://api.example.com/users/123',
            'status': 200,
            'duration_ms': 150,
            'req_headers': {
                'User-Agent': 'TestClient/1.0',
                'Accept': 'application/json'
            },
            'resp_headers': {
                'Content-Type': 'application/json'
            },
            'resp_body': '{"id": 123, "name": "John Doe"}'
        },
        {
            'method': 'POST',
            'url': 'https://api.example.com/users',
            'status': 201,
            'duration_ms': 200,
            'req_headers': {
                'Content-Type': 'application/json'
            },
            'req_body': '{"name": "Jane Smith"}',
            'resp_headers': {
                'Content-Type': 'application/json'
            },
            'resp_body': '{"id": 456, "name": "Jane Smith"}'
        },
        {
            'method': 'PUT',
            'url': 'https://api.example.com/users/123',
            'status': 200,
            'duration_ms': 180,
            'req_headers': {
                'Content-Type': 'application/json'
            },
            'req_body': '{"name": "John Updated"}',
            'resp_headers': {
                'Content-Type': 'application/json'
            },
            'resp_body': '{"id": 123, "name": "John Updated"}'
        }
    ]


@pytest.fixture
def temp_log_file(sample_captures):
    """Create temporary log file with sample captures."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({'requests': sample_captures}, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink()


class TestReplayMetrics:
    """Test ReplayMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating metrics object."""
        metrics = ReplayMetrics(
            original_url='https://api.example.com/users/123',
            replayed_url='http://localhost:8080/users/123',
            original_status=200,
            replayed_status=200,
            original_duration_ms=150,
            replayed_duration_ms=120.5,
            status_match=True
        )

        assert metrics.original_url == 'https://api.example.com/users/123'
        assert metrics.status_match is True
        assert metrics.error is None

    def test_duration_diff(self):
        """Test duration difference calculation."""
        metrics = ReplayMetrics(
            original_url='https://api.example.com/test',
            replayed_url='http://localhost:8080/test',
            original_status=200,
            replayed_status=200,
            original_duration_ms=100,
            replayed_duration_ms=150,
            status_match=True
        )

        assert metrics.duration_diff_ms == 50
        assert metrics.duration_diff_percent == 50.0

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = ReplayMetrics(
            original_url='https://api.example.com/test',
            replayed_url='http://localhost:8080/test',
            original_status=200,
            replayed_status=200,
            original_duration_ms=100,
            replayed_duration_ms=120,
            status_match=True
        )

        data = metrics.to_dict()

        assert data['original_url'] == 'https://api.example.com/test'
        assert data['status_match'] is True
        assert data['duration_diff_ms'] == 20
        assert data['duration_diff_percent'] == 20.0


class TestReplayResult:
    """Test ReplayResult dataclass."""

    def test_success_rate(self):
        """Test success rate calculation."""
        result = ReplayResult(
            total_requests=10,
            successful_replays=8,
            failed_replays=2,
            status_matches=7,
            status_mismatches=1,
            total_duration_sec=5.0
        )

        assert result.success_rate == 80.0

    def test_status_match_rate(self):
        """Test status match rate calculation."""
        result = ReplayResult(
            total_requests=10,
            successful_replays=8,
            failed_replays=2,
            status_matches=6,
            status_mismatches=2,
            total_duration_sec=5.0
        )

        assert result.status_match_rate == 75.0

    def test_avg_duration(self):
        """Test average duration calculation."""
        metrics = [
            ReplayMetrics(
                original_url='',
                replayed_url='',
                original_status=200,
                replayed_status=200,
                original_duration_ms=100,
                replayed_duration_ms=150,
                status_match=True
            ),
            ReplayMetrics(
                original_url='',
                replayed_url='',
                original_status=200,
                replayed_status=200,
                original_duration_ms=100,
                replayed_duration_ms=250,
                status_match=True
            )
        ]

        result = ReplayResult(
            total_requests=2,
            successful_replays=2,
            failed_replays=0,
            status_matches=2,
            status_mismatches=0,
            total_duration_sec=1.0,
            metrics=metrics
        )

        assert result.avg_duration_ms == 200.0


class TestTrafficReplayer:
    """Test TrafficReplayer class."""

    def test_load_captures_dict_format(self, temp_log_file):
        """Test loading captures from dict format."""
        replayer = TrafficReplayer(temp_log_file)

        assert len(replayer.captures) == 3
        assert replayer.captures[0]['method'] == 'GET'
        assert replayer.captures[1]['method'] == 'POST'

    def test_load_captures_list_format(self, sample_captures):
        """Test loading captures from list format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_captures, f)
            temp_path = f.name

        try:
            replayer = TrafficReplayer(temp_path)
            assert len(replayer.captures) == 3
        finally:
            Path(temp_path).unlink()

    def test_load_captures_file_not_found(self):
        """Test loading captures from non-existent file."""
        with pytest.raises(FileNotFoundError):
            TrafficReplayer('nonexistent.json')

    def test_replace_base_url(self, temp_log_file):
        """Test replacing base URL while preserving path."""
        replayer = TrafficReplayer(temp_log_file)

        original = 'https://api.example.com/users/123?limit=10'
        new_base = 'http://localhost:8080'

        result = replayer._replace_base_url(original, new_base)

        assert result == 'http://localhost:8080/users/123?limit=10'

    def test_replace_base_url_preserves_query(self, temp_log_file):
        """Test that query parameters are preserved."""
        replayer = TrafficReplayer(temp_log_file)

        original = 'https://api.example.com/search?q=test&page=2'
        new_base = 'http://localhost:9000'

        result = replayer._replace_base_url(original, new_base)

        assert 'q=test' in result
        assert 'page=2' in result
        assert result.startswith('http://localhost:9000')

    @patch('src.tracetap.replay.replayer.requests.Session')
    def test_replay_single_success(self, mock_session_class, temp_log_file):
        """Test replaying a single request successfully."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        replayer = TrafficReplayer(temp_log_file)
        replayer.session = mock_session

        capture = replayer.captures[0]
        metrics = replayer._replay_single(capture)

        assert metrics.replayed_status == 200
        assert metrics.status_match is True
        assert metrics.error is None

    @patch('src.tracetap.replay.replayer.requests.Session')
    def test_replay_single_with_error(self, mock_session_class, temp_log_file):
        """Test replaying a single request with error."""
        # Setup mock to raise exception
        mock_session = Mock()
        mock_session.request.side_effect = requests.exceptions.ConnectionError('Connection failed')
        mock_session_class.return_value = mock_session

        replayer = TrafficReplayer(temp_log_file)
        replayer.session = mock_session

        capture = replayer.captures[0]
        metrics = replayer._replay_single(capture)

        assert metrics.replayed_status == 0
        assert metrics.status_match is False
        assert 'Connection failed' in metrics.error

    @patch('src.tracetap.replay.replayer.requests.Session')
    def test_replay_with_variable_substitution(self, mock_session_class, temp_log_file):
        """Test replay with variable substitution."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        replayer = TrafficReplayer(temp_log_file)
        replayer.session = mock_session

        # Modify capture to have variable placeholder
        capture = replayer.captures[0].copy()
        capture['url'] = 'https://api.example.com/users/{user_id}'

        metrics = replayer._replay_single(
            capture,
            variables={'user_id': '999'}
        )

        # Check that the URL was substituted
        call_args = mock_session.request.call_args
        assert '999' in call_args.kwargs['url']

    @patch('src.tracetap.replay.replayer.requests.Session')
    def test_replay_full_workflow(self, mock_session_class, temp_log_file):
        """Test complete replay workflow."""
        # Setup mock responses
        mock_responses = [
            Mock(status_code=200),
            Mock(status_code=201),
            Mock(status_code=200)
        ]

        mock_session = Mock()
        mock_session.request.side_effect = mock_responses
        mock_session_class.return_value = mock_session

        replayer = TrafficReplayer(temp_log_file)
        replayer.session = mock_session

        result = replayer.replay(
            target_base_url='http://localhost:8080',
            max_workers=1,
            verbose=False
        )

        assert result.total_requests == 3
        assert result.successful_replays == 3
        assert result.failed_replays == 0
        assert result.status_matches == 3  # All status codes match (mocked responses)

    @patch('src.tracetap.replay.replayer.requests.Session')
    def test_replay_with_filter(self, mock_session_class, temp_log_file):
        """Test replay with filter function."""
        mock_response = Mock(status_code=200)
        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        replayer = TrafficReplayer(temp_log_file)
        replayer.session = mock_session

        # Filter to only replay GET requests
        def filter_get_only(capture):
            return capture.get('method') == 'GET'

        result = replayer.replay(
            filter_fn=filter_get_only,
            max_workers=1
        )

        assert result.total_requests == 1  # Only 1 GET request

    def test_save_result(self, temp_log_file):
        """Test saving replay results to file."""
        result = ReplayResult(
            total_requests=10,
            successful_replays=8,
            failed_replays=2,
            status_matches=7,
            status_mismatches=1,
            total_duration_sec=5.0
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name

        try:
            replayer = TrafficReplayer(temp_log_file)
            replayer.save_result(result, output_path)

            # Verify file was created and contains correct data
            with open(output_path) as f:
                data = json.load(f)

            assert data['total_requests'] == 10
            assert data['success_rate'] == 80.0
        finally:
            Path(output_path).unlink()


class TestReplayerConfiguration:
    """Test replayer configuration options."""

    def test_custom_timeout(self, temp_log_file):
        """Test setting custom timeout."""
        replayer = TrafficReplayer(temp_log_file, timeout=60)
        assert replayer.timeout == 60

    def test_ssl_verification_disabled(self, temp_log_file):
        """Test disabling SSL verification."""
        replayer = TrafficReplayer(temp_log_file, verify_ssl=False)
        assert replayer.verify_ssl is False

    def test_custom_retries(self, temp_log_file):
        """Test setting custom retry count."""
        replayer = TrafficReplayer(temp_log_file, max_retries=5)
        assert replayer.max_retries == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
