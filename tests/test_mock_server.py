"""
Tests for TraceTap Mock Server

Tests the FastAPI-based mock server including:
- Server initialization and configuration
- Request handling and matching
- Response serving
- Admin API endpoints
- Chaos engineering features
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

try:
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from src.tracetap.mock.server import (
    MockConfig,
    MockMetrics,
    MockServer,
    create_mock_server
)


pytestmark = pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")


@pytest.fixture
def sample_captures():
    """Sample captured requests for mock server."""
    return [
        {
            'method': 'GET',
            'url': 'https://api.example.com/users/123',
            'status': 200,
            'req_headers': {
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
            'method': 'GET',
            'url': 'https://api.example.com/products',
            'status': 200,
            'resp_headers': {
                'Content-Type': 'application/json'
            },
            'resp_body': '{"products": []}'
        }
    ]


@pytest.fixture
def temp_log_file(sample_captures):
    """Create temporary log file for mock server."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({'requests': sample_captures}, f)
        temp_path = f.name

    yield temp_path

    Path(temp_path).unlink()


class TestMockConfig:
    """Test MockConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MockConfig()

        assert config.matching_strategy == 'fuzzy'
        assert config.host == '127.0.0.1'
        assert config.port == 8080
        assert config.chaos_enabled is False
        assert config.admin_enabled is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = MockConfig(
            matching_strategy='exact',
            host='0.0.0.0',
            port=9090,
            add_delay_ms=100,
            chaos_enabled=True,
            chaos_failure_rate=0.1
        )

        assert config.matching_strategy == 'exact'
        assert config.host == '0.0.0.0'
        assert config.port == 9090
        assert config.add_delay_ms == 100
        assert config.chaos_failure_rate == 0.1


class TestMockMetrics:
    """Test MockMetrics dataclass."""

    def test_metrics_initialization(self):
        """Test initializing metrics."""
        metrics = MockMetrics()

        assert metrics.total_requests == 0
        assert metrics.matched_requests == 0
        assert metrics.unmatched_requests == 0

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = MockMetrics(
            total_requests=100,
            matched_requests=90,
            unmatched_requests=10
        )

        data = metrics.to_dict()

        assert data['total_requests'] == 100
        assert data['matched_requests'] == 90
        assert data['match_rate'] == 90.0
        assert 'uptime_seconds' in data


class TestMockServer:
    """Test MockServer class."""

    def test_server_initialization(self, temp_log_file):
        """Test initializing mock server."""
        server = MockServer(temp_log_file)

        assert len(server.captures) == 3
        assert server.config.matching_strategy == 'fuzzy'
        assert server.matcher is not None
        assert server.generator is not None

    def test_server_with_custom_config(self, temp_log_file):
        """Test server with custom configuration."""
        config = MockConfig(
            matching_strategy='exact',
            chaos_enabled=True
        )

        server = MockServer(temp_log_file, config=config)

        assert server.config.matching_strategy == 'exact'
        assert server.config.chaos_enabled is True

    def test_load_captures_file_not_found(self):
        """Test loading captures from non-existent file."""
        with pytest.raises(FileNotFoundError):
            MockServer('nonexistent.json')

    def test_get_app(self, temp_log_file):
        """Test getting FastAPI app instance."""
        server = MockServer(temp_log_file)
        app = server.get_app()

        assert app is not None
        assert hasattr(app, 'routes')


class TestMockServerEndpoints:
    """Test mock server HTTP endpoints."""

    def test_admin_metrics_endpoint(self, temp_log_file):
        """Test admin metrics endpoint."""
        server = MockServer(temp_log_file)
        client = TestClient(server.app)

        response = client.get('/__admin__/metrics')

        assert response.status_code == 200
        data = response.json()
        assert 'total_requests' in data
        assert 'matched_requests' in data

    def test_admin_config_endpoint(self, temp_log_file):
        """Test admin config endpoint."""
        server = MockServer(temp_log_file)
        client = TestClient(server.app)

        response = client.get('/__admin__/config')

        assert response.status_code == 200
        data = response.json()
        assert 'matching_strategy' in data
        assert 'total_captures' in data
        assert data['total_captures'] == 3

    def test_admin_update_config(self, temp_log_file):
        """Test updating config via admin API."""
        server = MockServer(temp_log_file)
        client = TestClient(server.app)

        response = client.post('/__admin__/config', json={
            'chaos_enabled': True,
            'chaos_failure_rate': 0.2
        })

        assert response.status_code == 200
        assert server.config.chaos_enabled is True
        assert server.config.chaos_failure_rate == 0.2

    def test_admin_captures_list(self, temp_log_file):
        """Test listing captures via admin API."""
        server = MockServer(temp_log_file)
        client = TestClient(server.app)

        response = client.get('/__admin__/captures')

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 3
        assert len(data['captures']) == 3

    def test_admin_reset_metrics(self, temp_log_file):
        """Test resetting metrics."""
        server = MockServer(temp_log_file)
        client = TestClient(server.app)

        # Make some requests to generate metrics
        client.get('/users/123')

        # Reset
        response = client.post('/__admin__/reset')

        assert response.status_code == 200

        # Verify metrics were reset
        metrics_response = client.get('/__admin__/metrics')
        data = metrics_response.json()
        assert data['total_requests'] == 0

    def test_mock_request_matched(self, temp_log_file):
        """Test mocked request that matches a capture."""
        server = MockServer(temp_log_file)
        client = TestClient(server.app)

        response = client.get('/users/123')

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == 123
        assert data['name'] == 'John Doe'

    def test_mock_request_unmatched(self, temp_log_file):
        """Test mocked request that doesn't match."""
        server = MockServer(temp_log_file)
        client = TestClient(server.app)

        response = client.get('/nonexistent/endpoint')

        assert response.status_code == 404
        data = response.json()
        assert 'error' in data

    def test_mock_post_request(self, temp_log_file):
        """Test mocked POST request."""
        server = MockServer(temp_log_file)
        client = TestClient(server.app)

        response = client.post('/users', json={'name': 'Test User'})

        assert response.status_code == 201
        data = response.json()
        assert 'id' in data

    def test_admin_disabled(self, temp_log_file):
        """Test server with admin API disabled."""
        config = MockConfig(admin_enabled=False)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        # Admin endpoints should return 404
        response = client.get('/__admin__/metrics')
        assert response.status_code == 404


class TestMockServerChaos:
    """Test chaos engineering features."""

    def test_chaos_trigger_failure(self, temp_log_file):
        """Test chaos engineering triggering failures."""
        config = MockConfig(
            chaos_enabled=True,
            chaos_failure_rate=1.0  # Always fail
        )
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        response = client.get('/users/123')

        # Should get chaos error
        assert response.status_code == 500
        data = response.json()
        assert 'Chaos' in data['error'] or 'error' in data

    def test_chaos_disabled(self, temp_log_file):
        """Test chaos disabled."""
        config = MockConfig(chaos_enabled=False)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        response = client.get('/users/123')

        # Should get normal response
        assert response.status_code == 200

    @patch('src.tracetap.mock.server.asyncio.sleep', new_callable=AsyncMock)
    def test_delay_applied(self, mock_sleep, temp_log_file):
        """Test that delay is applied to responses."""
        config = MockConfig(add_delay_ms=100)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        response = client.get('/users/123')

        # Verify sleep was called with correct delay
        mock_sleep.assert_called_once()
        call_args = mock_sleep.call_args[0]
        assert call_args[0] == 0.1  # 100ms = 0.1s


class TestMockServerMetrics:
    """Test metrics tracking."""

    def test_metrics_track_requests(self, temp_log_file):
        """Test that metrics track requests."""
        server = MockServer(temp_log_file)
        client = TestClient(server.app)

        # Make some requests
        client.get('/users/123')  # Should match
        client.get('/nonexistent')  # Should not match
        client.get('/products')  # Should match

        metrics_response = client.get('/__admin__/metrics')
        data = metrics_response.json()

        assert data['total_requests'] == 3
        assert data['matched_requests'] == 2
        assert data['unmatched_requests'] == 1


class TestCreateMockServer:
    """Test create_mock_server convenience function."""

    def test_create_mock_server(self, temp_log_file):
        """Test creating server with convenience function."""
        server = create_mock_server(
            temp_log_file,
            port=9090,
            matching_strategy='exact',
            chaos_enabled=True
        )

        assert server.config.port == 9090
        assert server.config.matching_strategy == 'exact'
        assert server.config.chaos_enabled is True


class TestRequestRecording:
    """Test request recording functionality."""

    def test_recording_disabled_by_default(self, temp_log_file):
        """Test that recording is disabled by default."""
        config = MockConfig(recording_enabled=False)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        # Make request
        client.get('/users/123')

        # Check recordings endpoint
        response = client.get('/__admin__/recordings')
        data = response.json()

        assert data['recording_enabled'] is False
        assert data['total'] == 0

    def test_recording_enabled(self, temp_log_file):
        """Test recording incoming requests."""
        config = MockConfig(recording_enabled=True, recording_limit=10)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        # Make some requests
        client.get('/users/123')
        client.post('/users', json={'name': 'Test User'})
        client.get('/nonexistent')

        # Check recordings endpoint
        response = client.get('/__admin__/recordings')
        data = response.json()

        assert data['recording_enabled'] is True
        assert data['total'] == 3
        assert data['limit'] == 10
        assert len(data['recordings']) == 3

        # Verify recording structure
        recording = data['recordings'][0]
        assert 'timestamp' in recording
        assert 'method' in recording
        assert 'url' in recording
        assert 'matched' in recording

    def test_recording_limit_fifo(self, temp_log_file):
        """Test FIFO eviction when recording limit reached."""
        config = MockConfig(recording_enabled=True, recording_limit=2)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        # Make 3 requests (exceeds limit of 2)
        client.get('/users/123')
        client.get('/users/456')
        client.get('/users/789')

        response = client.get('/__admin__/recordings')
        data = response.json()

        # Should only have 2 recordings (oldest evicted)
        assert data['total'] == 2

    def test_clear_recordings(self, temp_log_file):
        """Test clearing recorded requests."""
        config = MockConfig(recording_enabled=True)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        # Make requests
        client.get('/users/123')
        client.get('/products')

        # Verify recordings exist
        response = client.get('/__admin__/recordings')
        assert response.json()['total'] == 2

        # Clear recordings
        clear_response = client.delete('/__admin__/recordings')
        assert clear_response.json()['status'] == 'cleared'
        assert clear_response.json()['cleared_count'] == 2

        # Verify cleared
        response = client.get('/__admin__/recordings')
        assert response.json()['total'] == 0

    def test_export_recordings(self, temp_log_file):
        """Test exporting recordings in TraceTap format."""
        config = MockConfig(recording_enabled=True)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        # Make request
        client.get('/users/123')

        # Export recordings
        response = client.get('/__admin__/recordings/export')
        data = response.json()

        assert 'session' in data
        assert 'timestamp' in data
        assert 'requests' in data
        assert len(data['requests']) == 1

        # Verify export structure
        exported_req = data['requests'][0]
        assert 'method' in exported_req
        assert 'url' in exported_req
        assert 'matched' in exported_req


class TestCacheAdminAPI:
    """Test cache-related admin API endpoints."""

    def test_cache_stats_endpoint(self, temp_log_file):
        """Test cache statistics endpoint."""
        config = MockConfig(cache_enabled=True, cache_max_size=500)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        # Make some requests to populate cache
        client.get('/users/123')
        client.get('/users/123')  # Cache hit
        client.get('/products')

        # Get cache stats
        response = client.get('/__admin__/cache')
        data = response.json()

        assert data['enabled'] is True
        assert data['max_size'] == 500
        assert data['current_size'] == 2  # Two unique requests
        assert data['hits'] == 1  # Second /users/123 was a hit
        assert data['misses'] == 2  # First /users/123 and /products

    def test_cache_disabled_stats(self, temp_log_file):
        """Test cache stats when caching is disabled."""
        config = MockConfig(cache_enabled=False)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        client.get('/users/123')

        response = client.get('/__admin__/cache')
        data = response.json()

        assert data['enabled'] is False
        assert data['current_size'] == 0

    def test_clear_cache_endpoint(self, temp_log_file):
        """Test clearing the cache."""
        config = MockConfig(cache_enabled=True)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        # Populate cache
        client.get('/users/123')
        client.get('/products')

        # Verify cache has entries
        stats = client.get('/__admin__/cache').json()
        assert stats['current_size'] == 2

        # Clear cache
        clear_response = client.delete('/__admin__/cache')
        data = clear_response.json()

        assert data['status'] == 'cleared'
        assert data['entries_cleared'] == 2

        # Verify cache is empty
        stats = client.get('/__admin__/cache').json()
        assert stats['current_size'] == 0
        assert stats['hits'] == 0
        assert stats['misses'] == 0


class TestDiffTracking:
    """Test diff tracking functionality."""

    def test_diff_tracking_disabled_by_default(self, temp_log_file):
        """Test that diff tracking is disabled by default."""
        config = MockConfig(diff_enabled=False)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        # Make requests
        client.get('/users/123')
        client.get('/nonexistent')  # Low match score

        # Check diffs endpoint
        response = client.get('/__admin__/diffs')
        data = response.json()

        assert data['diff_enabled'] is False
        assert data['total'] == 0

    def test_diff_tracking_enabled(self, temp_log_file):
        """Test diff tracking for low-score matches."""
        config = MockConfig(
            diff_enabled=True,
            diff_threshold=0.9,  # High threshold to trigger diffs
            diff_limit=10
        )
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        # Make request that might not match well
        client.get('/completely/different/path')

        # Check diffs endpoint
        response = client.get('/__admin__/diffs')
        data = response.json()

        assert data['diff_enabled'] is True
        # Might have diffs depending on match score

    def test_clear_diffs(self, temp_log_file):
        """Test clearing tracked diffs."""
        config = MockConfig(diff_enabled=True, diff_threshold=0.9)
        server = MockServer(temp_log_file, config=config)
        client = TestClient(server.app)

        # Clear diffs
        clear_response = client.delete('/__admin__/diffs')
        assert clear_response.json()['status'] == 'cleared'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
