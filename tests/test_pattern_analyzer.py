"""
Tests for AI Pattern Analyzer

Tests pattern detection strategies and edge cases.
"""

import json
import pytest
from pathlib import Path
import sys
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from tracetap.ai.pattern_analyzer import (
    Pattern,
    PatternAnalyzer,
    analyze_traffic_file
)


class TestPattern:
    """Test Pattern class"""

    def test_pattern_creation(self):
        pattern = Pattern(
            pattern_type='empty-array',
            severity='HIGH',
            title='Test Pattern',
            description='Test description',
            evidence=['evidence1', 'evidence2'],
            suggestion='Test suggestion',
            confidence=0.9
        )

        assert pattern.pattern_type == 'empty-array'
        assert pattern.severity == 'HIGH'
        assert pattern.confidence == 0.9

    def test_pattern_to_dict(self):
        pattern = Pattern(
            pattern_type='error-path',
            severity='MEDIUM',
            title='Test',
            description='Desc',
            evidence=['e1'],
            suggestion='Suggest'
        )

        result = pattern.to_dict()

        assert result['type'] == 'error-path'
        assert result['severity'] == 'MEDIUM'
        assert result['title'] == 'Test'
        assert result['confidence'] == 1.0  # Default


class TestPatternAnalyzer:
    """Test PatternAnalyzer core functionality"""

    def test_initialization_without_ai(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)
        assert analyzer.use_ai is False
        assert analyzer.ai_client is None
        assert analyzer.ai_available is False

    def test_initialization_with_ai_unavailable(self):
        # AI will be unavailable if no API key
        analyzer = PatternAnalyzer(use_ai=True, verbose=False)
        # Should initialize without crashing
        assert analyzer is not None

    def test_analyze_empty_traffic(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)
        result = analyzer.analyze_traffic([])

        assert result['patterns'] == []
        assert result['stats'] == {}
        assert result['ai_enhanced'] is False

    def test_compute_statistics(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        requests = [
            {'method': 'GET', 'url': 'http://api.test/users', 'status_code': 200},
            {'method': 'POST', 'url': 'http://api.test/users', 'status_code': 201},
            {'method': 'GET', 'url': 'http://api.test/orders', 'status_code': 200},
            {'method': 'GET', 'url': 'http://api.test/users', 'status_code': 404},
        ]

        stats = analyzer._compute_statistics(requests)

        assert stats['total_requests'] == 4
        assert stats['unique_endpoints'] == 3  # GET /users, POST /users, GET /orders
        assert stats['status_codes'][200] == 2
        assert stats['status_codes'][201] == 1
        assert stats['status_codes'][404] == 1
        assert stats['methods']['GET'] == 3
        assert stats['methods']['POST'] == 1
        assert stats['success_rate'] == 0.75  # 3 successful out of 4

    def test_normalize_endpoint(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        # Numeric ID
        req1 = {'method': 'GET', 'url': 'http://api.test/users/123'}
        assert 'GET /users/{id}' in analyzer._normalize_endpoint(req1)

        # UUID
        req2 = {'method': 'GET', 'url': 'http://api.test/users/550e8400-e29b-41d4-a716-446655440000'}
        assert '{uuid}' in analyzer._normalize_endpoint(req2)

        # MongoDB ObjectId
        req3 = {'method': 'POST', 'url': 'http://api.test/items/507f1f77bcf86cd799439011'}
        assert '{objectId}' in analyzer._normalize_endpoint(req3)


class TestEmptyArrayDetection:
    """Test empty array pattern detection"""

    def test_detects_always_populated_arrays(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        requests = [
            {
                'method': 'GET',
                'url': 'http://api.test/users',
                'status_code': 200,
                'response_body': json.dumps([{'id': 1}, {'id': 2}])
            },
            {
                'method': 'GET',
                'url': 'http://api.test/users',
                'status_code': 200,
                'response_body': json.dumps([{'id': 3}])
            },
            {
                'method': 'GET',
                'url': 'http://api.test/users',
                'status_code': 200,
                'response_body': json.dumps([{'id': 4}, {'id': 5}, {'id': 6}])
            }
        ]

        patterns = analyzer._detect_empty_array_patterns(requests)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == 'empty-array'
        assert patterns[0].severity == 'MEDIUM'
        assert 'GET /users' in patterns[0].title
        assert 'never empty' in patterns[0].description.lower() or 'always returns data' in patterns[0].description.lower()

    def test_ignores_endpoints_with_empty_arrays(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        requests = [
            {
                'method': 'GET',
                'url': 'http://api.test/users',
                'status_code': 200,
                'response_body': json.dumps([{'id': 1}])
            },
            {
                'method': 'GET',
                'url': 'http://api.test/users',
                'status_code': 200,
                'response_body': json.dumps([])  # Empty array present
            },
            {
                'method': 'GET',
                'url': 'http://api.test/users',
                'status_code': 200,
                'response_body': json.dumps([{'id': 2}])
            }
        ]

        patterns = analyzer._detect_empty_array_patterns(requests)

        # Should not flag since empty array was seen
        assert len(patterns) == 0

    def test_requires_minimum_samples(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        # Only 2 samples
        requests = [
            {
                'method': 'GET',
                'url': 'http://api.test/users',
                'status_code': 200,
                'response_body': json.dumps([{'id': 1}])
            },
            {
                'method': 'GET',
                'url': 'http://api.test/users',
                'status_code': 200,
                'response_body': json.dumps([{'id': 2}])
            }
        ]

        patterns = analyzer._detect_empty_array_patterns(requests)

        # Needs at least 3 samples
        assert len(patterns) == 0


class TestErrorPathDetection:
    """Test error path coverage detection"""

    def test_detects_missing_error_codes(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        # Only 2xx responses
        requests = [
            {'method': 'GET', 'url': 'http://api.test/users/1', 'status_code': 200},
            {'method': 'GET', 'url': 'http://api.test/users/2', 'status_code': 200},
            {'method': 'GET', 'url': 'http://api.test/users/3', 'status_code': 200},
        ]

        patterns = analyzer._detect_error_path_gaps(requests)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == 'error-path'
        assert patterns[0].severity == 'HIGH'
        assert 'error' in patterns[0].title.lower()
        assert '2xx' in patterns[0].description or 'success' in patterns[0].description.lower()

    def test_ignores_endpoints_with_error_responses(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        requests = [
            {'method': 'GET', 'url': 'http://api.test/users/1', 'status_code': 200},
            {'method': 'GET', 'url': 'http://api.test/users/2', 'status_code': 404},
            {'method': 'GET', 'url': 'http://api.test/users/3', 'status_code': 200},
        ]

        patterns = analyzer._detect_error_path_gaps(requests)

        # Should not flag since error code (404) was seen
        assert len(patterns) == 0


class TestConcurrencyDetection:
    """Test concurrency pattern detection"""

    def test_detects_concurrent_writes(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        # Requests within 100ms
        requests = [
            {
                'method': 'POST',
                'url': 'http://api.test/orders',
                'timestamp': '2024-01-01T10:00:00.000Z'
            },
            {
                'method': 'POST',
                'url': 'http://api.test/orders',
                'timestamp': '2024-01-01T10:00:00.050Z'  # 50ms later
            }
        ]

        patterns = analyzer._detect_concurrency_patterns(requests)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == 'concurrency'
        assert patterns[0].severity == 'HIGH'
        assert 'concurrent' in patterns[0].title.lower()

    def test_ignores_sequential_requests(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        # Requests > 100ms apart
        requests = [
            {
                'method': 'POST',
                'url': 'http://api.test/orders',
                'timestamp': '2024-01-01T10:00:00.000Z'
            },
            {
                'method': 'POST',
                'url': 'http://api.test/orders',
                'timestamp': '2024-01-01T10:00:01.000Z'  # 1 second later
            }
        ]

        patterns = analyzer._detect_concurrency_patterns(requests)

        # Not concurrent
        assert len(patterns) == 0

    def test_ignores_concurrent_reads(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        # Concurrent GETs are safe
        requests = [
            {
                'method': 'GET',
                'url': 'http://api.test/users',
                'timestamp': '2024-01-01T10:00:00.000Z'
            },
            {
                'method': 'GET',
                'url': 'http://api.test/users',
                'timestamp': '2024-01-01T10:00:00.050Z'
            }
        ]

        patterns = analyzer._detect_concurrency_patterns(requests)

        # GET requests don't cause race conditions
        assert len(patterns) == 0


class TestBoundaryDetection:
    """Test boundary condition detection"""

    def test_detects_missing_zero_test(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        requests = [
            {'method': 'GET', 'url': 'http://api.test/users/1'},
            {'method': 'GET', 'url': 'http://api.test/users/100'},
            {'method': 'GET', 'url': 'http://api.test/users/500'},
        ]

        patterns = analyzer._detect_boundary_conditions(requests)

        assert len(patterns) >= 1
        boundary_pattern = next((p for p in patterns if p.pattern_type == 'boundary'), None)
        assert boundary_pattern is not None
        assert 'zero' in ' '.join(boundary_pattern.evidence).lower() or 'missing' in boundary_pattern.description.lower()

    def test_detects_missing_negative_test(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        requests = [
            {'method': 'GET', 'url': 'http://api.test/users/1'},
            {'method': 'GET', 'url': 'http://api.test/users/5'},
            {'method': 'GET', 'url': 'http://api.test/users/10'},
        ]

        patterns = analyzer._detect_boundary_conditions(requests)

        assert len(patterns) >= 1
        boundary_pattern = next((p for p in patterns if p.pattern_type == 'boundary'), None)
        assert boundary_pattern is not None

    def test_extracts_numbers_from_json(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        data = {
            'user': {
                'id': 123,
                'age': 25,
                'scores': [90, 85, 95]
            }
        }

        numbers = analyzer._extract_numbers_from_json(data)

        assert 123 in numbers
        assert 25 in numbers
        assert 90 in numbers
        assert 85 in numbers
        assert 95 in numbers


class TestSuccessBiasDetection:
    """Test success bias detection"""

    def test_detects_high_success_rate(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        # 95% success
        requests = [
            {'status_code': 200} for _ in range(19)
        ] + [{'status_code': 404}]

        patterns = analyzer._detect_success_bias(requests)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == 'success-bias'
        assert patterns[0].severity == 'HIGH'
        assert '95' in patterns[0].description

    def test_ignores_balanced_traffic(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        # 70% success (not flagged)
        requests = [
            {'status_code': 200} for _ in range(7)
        ] + [{'status_code': 404} for _ in range(3)]

        patterns = analyzer._detect_success_bias(requests)

        # Not biased enough to flag
        assert len(patterns) == 0

    def test_requires_minimum_requests(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        # Only 5 requests, all success
        requests = [{'status_code': 200} for _ in range(5)]

        patterns = analyzer._detect_success_bias(requests)

        # Needs at least 10 requests
        assert len(patterns) == 0


class TestIntegration:
    """Integration tests for complete analysis"""

    def test_analyze_traffic_with_multiple_patterns(self):
        analyzer = PatternAnalyzer(use_ai=False, verbose=False)

        requests = [
            # Success bias (all 200s)
            {'method': 'GET', 'url': 'http://api.test/users/1', 'status_code': 200, 'response_body': json.dumps([{'id': 1}])},
            {'method': 'GET', 'url': 'http://api.test/users/2', 'status_code': 200, 'response_body': json.dumps([{'id': 2}])},
            {'method': 'GET', 'url': 'http://api.test/users/3', 'status_code': 200, 'response_body': json.dumps([{'id': 3}])},
            {'method': 'GET', 'url': 'http://api.test/users/4', 'status_code': 200, 'response_body': json.dumps([{'id': 4}])},
            {'method': 'GET', 'url': 'http://api.test/users/5', 'status_code': 200, 'response_body': json.dumps([{'id': 5}])},
            # Empty array pattern (never empty)
            {'method': 'GET', 'url': 'http://api.test/items', 'status_code': 200, 'response_body': json.dumps([1, 2])},
            {'method': 'GET', 'url': 'http://api.test/items', 'status_code': 200, 'response_body': json.dumps([3, 4])},
            {'method': 'GET', 'url': 'http://api.test/items', 'status_code': 200, 'response_body': json.dumps([5])},
            # More to reach 10+ requests
            {'method': 'POST', 'url': 'http://api.test/orders', 'status_code': 201},
            {'method': 'PUT', 'url': 'http://api.test/users/1', 'status_code': 200},
        ]

        result = analyzer.analyze_traffic(requests)

        assert len(result['patterns']) >= 2  # Should find multiple patterns
        assert result['ai_enhanced'] is False
        assert result['stats']['total_requests'] == 10
        assert result['stats']['success_rate'] == 1.0  # All successful

    def test_analyze_traffic_file_convenience_function(self, tmp_path):
        # Create temporary traffic file
        traffic_file = tmp_path / "test_traffic.json"
        data = {
            'requests': [
                {'method': 'GET', 'url': 'http://api.test/users', 'status_code': 200, 'response_body': '[]'},
                {'method': 'GET', 'url': 'http://api.test/users', 'status_code': 200, 'response_body': '[]'},
            ]
        }
        traffic_file.write_text(json.dumps(data))

        result = analyze_traffic_file(str(traffic_file), use_ai=False, verbose=False)

        assert 'patterns' in result
        assert 'stats' in result
        assert result['ai_enhanced'] is False


class TestAIEnhancement:
    """Test AI enhancement (mocked)"""

    @patch('tracetap.ai.pattern_analyzer.create_anthropic_client')
    def test_ai_enhancement_with_mock(self, mock_create_client):
        # Mock AI client
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Additional security testing needed")]
        mock_client.messages.create.return_value = mock_message

        mock_create_client.return_value = (mock_client, True, "AI enabled")

        analyzer = PatternAnalyzer(use_ai=True, verbose=False)
        analyzer.ai_client = mock_client
        analyzer.ai_available = True

        requests = [
            {'method': 'GET', 'url': 'http://api.test/users/1', 'status_code': 200},
            {'method': 'GET', 'url': 'http://api.test/users/2', 'status_code': 200},
            {'method': 'GET', 'url': 'http://api.test/users/3', 'status_code': 200},
        ]

        # Should have some base patterns
        base_patterns = [Pattern('test', 'HIGH', 'Test', 'Test', [], 'Test')]

        # Enhance with AI
        enhanced = analyzer._enhance_with_ai(base_patterns, requests, {})

        # Should add AI insight pattern
        assert len(enhanced) > len(base_patterns)
        ai_pattern = next((p for p in enhanced if p.pattern_type == 'ai-insight'), None)
        assert ai_pattern is not None

    def test_ai_enhancement_graceful_failure(self):
        analyzer = PatternAnalyzer(use_ai=True, verbose=False)
        analyzer.ai_client = None
        analyzer.ai_available = False

        # Should not crash when AI unavailable
        result = analyzer.analyze_traffic([
            {'method': 'GET', 'url': 'http://api.test/users', 'status_code': 200}
        ])

        assert result['ai_enhanced'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
