"""
Tests for Performance Analyzer

Tests performance threshold extraction and formatting.
"""

import pytest
from pathlib import Path
from dataclasses import dataclass

# Add src to path

from tracetap.generators.performance_analyzer import (
    PerformanceAnalyzer,
    PerformanceThreshold,
    PerformanceConfig,
)


# Mock network call for testing
@dataclass
class MockNetworkCall:
    """Mock network call with duration"""

    url: str
    method: str
    duration: int


# Mock correlated event for testing
@dataclass
class MockCorrelatedEvent:
    """Mock correlated event"""

    network_calls: list


class TestPerformanceAnalyzer:
    """Test performance threshold extraction"""

    def test_extract_single_threshold(self):
        """Test extracting threshold from single network call"""
        analyzer = PerformanceAnalyzer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(
                        url="/api/users",
                        method="GET",
                        duration=200,
                    )
                ]
            )
        ]

        thresholds = analyzer.extract_thresholds(events)

        assert len(thresholds) == 1
        assert thresholds[0].endpoint == "/api/users"
        assert thresholds[0].method == "GET"
        assert thresholds[0].observed_duration_ms == 200
        assert thresholds[0].threshold_ms == 300  # 1.5x of 200

    def test_extract_multiple_thresholds(self):
        """Test extracting thresholds from multiple network calls"""
        analyzer = PerformanceAnalyzer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users", method="GET", duration=150),
                    MockNetworkCall(url="/api/orders", method="POST", duration=300),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/products", method="GET", duration=100),
                ]
            ),
        ]

        thresholds = analyzer.extract_thresholds(events)

        assert len(thresholds) == 3

        # Check first threshold
        assert thresholds[0].endpoint == "/api/users"
        assert thresholds[0].observed_duration_ms == 150
        assert thresholds[0].threshold_ms == 225  # 1.5x

        # Check second threshold
        assert thresholds[1].endpoint == "/api/orders"
        assert thresholds[1].observed_duration_ms == 300
        assert thresholds[1].threshold_ms == 450  # 1.5x

    def test_threshold_minimum_bound(self):
        """Test minimum threshold enforcement"""
        analyzer = PerformanceAnalyzer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(
                        url="/api/fast",
                        method="GET",
                        duration=50,  # Very fast
                    )
                ]
            )
        ]

        thresholds = analyzer.extract_thresholds(events)

        # 1.5x of 50 = 75, but min is 100
        assert thresholds[0].threshold_ms == 100

    def test_threshold_maximum_bound(self):
        """Test maximum threshold enforcement"""
        analyzer = PerformanceAnalyzer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(
                        url="/api/slow",
                        method="POST",
                        duration=25000,  # Very slow
                    )
                ]
            )
        ]

        thresholds = analyzer.extract_thresholds(events)

        # 1.5x of 25000 = 37500, but max is 30000
        assert thresholds[0].threshold_ms == 30000

    def test_custom_threshold_multiplier(self):
        """Test custom threshold multiplier"""
        config = PerformanceConfig(threshold_multiplier=2.0)
        analyzer = PerformanceAnalyzer(config)

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users", method="GET", duration=200)
                ]
            )
        ]

        thresholds = analyzer.extract_thresholds(events)

        # 2.0x of 200 = 400
        assert thresholds[0].threshold_ms == 400

    def test_custom_min_max_thresholds(self):
        """Test custom min/max threshold bounds"""
        config = PerformanceConfig(
            min_threshold_ms=500,
            max_threshold_ms=10000,
        )
        analyzer = PerformanceAnalyzer(config)

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/fast", method="GET", duration=100),
                    MockNetworkCall(url="/api/slow", method="GET", duration=15000),
                ]
            )
        ]

        thresholds = analyzer.extract_thresholds(events)

        # First: 1.5x of 100 = 150, but min is 500
        assert thresholds[0].threshold_ms == 500

        # Second: 1.5x of 15000 = 22500, but max is 10000
        assert thresholds[1].threshold_ms == 10000

    def test_ignore_zero_duration(self):
        """Test that zero duration calls are ignored"""
        analyzer = PerformanceAnalyzer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/cached", method="GET", duration=0),
                    MockNetworkCall(url="/api/normal", method="GET", duration=200),
                ]
            )
        ]

        thresholds = analyzer.extract_thresholds(events)

        # Should only have one threshold (zero duration ignored)
        assert len(thresholds) == 1
        assert thresholds[0].endpoint == "/api/normal"

    def test_ignore_none_duration(self):
        """Test that None duration is handled gracefully"""
        analyzer = PerformanceAnalyzer()

        @dataclass
        class NoDurationCall:
            url: str
            method: str
            duration: None = None

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    NoDurationCall(url="/api/unknown", method="GET"),
                    MockNetworkCall(url="/api/normal", method="GET", duration=200),
                ]
            )
        ]

        thresholds = analyzer.extract_thresholds(events)

        # Should only extract threshold from call with duration
        assert len(thresholds) == 1
        assert thresholds[0].endpoint == "/api/normal"

    def test_empty_events_list(self):
        """Test handling of empty events list"""
        analyzer = PerformanceAnalyzer()

        thresholds = analyzer.extract_thresholds([])

        assert len(thresholds) == 0

    def test_events_without_network_calls(self):
        """Test events with no network calls"""
        analyzer = PerformanceAnalyzer()

        events = [MockCorrelatedEvent(network_calls=[])]

        thresholds = analyzer.extract_thresholds(events)

        assert len(thresholds) == 0


class TestPerformancePromptFormatting:
    """Test performance context formatting for AI prompts"""

    def test_format_single_threshold(self):
        """Test formatting single threshold"""
        analyzer = PerformanceAnalyzer()

        thresholds = [
            PerformanceThreshold(
                endpoint="/api/users",
                method="GET",
                observed_duration_ms=245,
                threshold_ms=368,
            )
        ]

        formatted = analyzer.format_for_prompt(thresholds)

        assert "## Performance Thresholds" in formatted
        assert "GET /api/users" in formatted
        assert "observed 245ms" in formatted
        assert "assert < 368ms" in formatted
        assert "```typescript" in formatted

    def test_format_multiple_thresholds(self):
        """Test formatting multiple thresholds"""
        analyzer = PerformanceAnalyzer()

        thresholds = [
            PerformanceThreshold(
                endpoint="/api/users",
                method="GET",
                observed_duration_ms=200,
                threshold_ms=300,
            ),
            PerformanceThreshold(
                endpoint="/api/orders",
                method="POST",
                observed_duration_ms=350,
                threshold_ms=525,
            ),
        ]

        formatted = analyzer.format_for_prompt(thresholds)

        # Check both endpoints are included
        assert "GET /api/users" in formatted
        assert "POST /api/orders" in formatted
        assert "observed 200ms" in formatted
        assert "observed 350ms" in formatted

    def test_format_empty_thresholds(self):
        """Test formatting empty threshold list"""
        analyzer = PerformanceAnalyzer()

        formatted = analyzer.format_for_prompt([])

        assert formatted == ""

    def test_format_includes_code_example(self):
        """Test that formatted output includes code example"""
        analyzer = PerformanceAnalyzer()

        thresholds = [
            PerformanceThreshold(
                endpoint="/api/test",
                method="GET",
                observed_duration_ms=100,
                threshold_ms=150,
            )
        ]

        formatted = analyzer.format_for_prompt(thresholds)

        # Should include TypeScript example
        assert "const startTime = Date.now()" in formatted
        assert "page.waitForResponse" in formatted
        assert "expect(duration).toBeLessThan" in formatted


class TestPerformanceStatistics:
    """Test performance statistics calculation"""

    def test_statistics_single_threshold(self):
        """Test statistics for single threshold"""
        analyzer = PerformanceAnalyzer()

        thresholds = [
            PerformanceThreshold(
                endpoint="/api/users",
                method="GET",
                observed_duration_ms=200,
                threshold_ms=300,
            )
        ]

        stats = analyzer.get_statistics(thresholds)

        assert stats["count"] == 1
        assert stats["avg_duration_ms"] == 200
        assert stats["max_threshold_ms"] == 300
        assert stats["min_threshold_ms"] == 300
        assert stats["endpoints"] == 1

    def test_statistics_multiple_thresholds(self):
        """Test statistics for multiple thresholds"""
        analyzer = PerformanceAnalyzer()

        thresholds = [
            PerformanceThreshold(
                endpoint="/api/users",
                method="GET",
                observed_duration_ms=100,
                threshold_ms=150,
            ),
            PerformanceThreshold(
                endpoint="/api/orders",
                method="POST",
                observed_duration_ms=300,
                threshold_ms=450,
            ),
            PerformanceThreshold(
                endpoint="/api/products",
                method="GET",
                observed_duration_ms=200,
                threshold_ms=300,
            ),
        ]

        stats = analyzer.get_statistics(thresholds)

        assert stats["count"] == 3
        assert stats["avg_duration_ms"] == 200  # (100+300+200)/3
        assert stats["max_threshold_ms"] == 450
        assert stats["min_threshold_ms"] == 150
        assert stats["endpoints"] == 3

    def test_statistics_empty_thresholds(self):
        """Test statistics for empty threshold list"""
        analyzer = PerformanceAnalyzer()

        stats = analyzer.get_statistics([])

        assert stats["count"] == 0
        assert stats["avg_duration_ms"] == 0
        assert stats["max_threshold_ms"] == 0
        assert stats["min_threshold_ms"] == 0

    def test_statistics_duplicate_endpoints(self):
        """Test statistics with duplicate endpoints"""
        analyzer = PerformanceAnalyzer()

        thresholds = [
            PerformanceThreshold(
                endpoint="/api/users",
                method="GET",
                observed_duration_ms=100,
                threshold_ms=150,
            ),
            PerformanceThreshold(
                endpoint="/api/users",  # Duplicate
                method="POST",
                observed_duration_ms=200,
                threshold_ms=300,
            ),
        ]

        stats = analyzer.get_statistics(thresholds)

        # Should count unique endpoints
        assert stats["count"] == 2  # Total thresholds
        assert stats["endpoints"] == 1  # Unique endpoints


class TestPerformanceConfig:
    """Test performance configuration"""

    def test_default_config(self):
        """Test default configuration values"""
        config = PerformanceConfig()

        assert config.threshold_multiplier == 1.5
        assert config.min_threshold_ms == 100
        assert config.max_threshold_ms == 30000

    def test_custom_config(self):
        """Test custom configuration"""
        config = PerformanceConfig(
            threshold_multiplier=2.0,
            min_threshold_ms=200,
            max_threshold_ms=20000,
        )

        assert config.threshold_multiplier == 2.0
        assert config.min_threshold_ms == 200
        assert config.max_threshold_ms == 20000


class TestRealWorldScenarios:
    """Test realistic performance scenarios"""

    def test_typical_api_response_times(self):
        """Test with typical API response times"""
        analyzer = PerformanceAnalyzer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/login", method="POST", duration=250),
                    MockNetworkCall(url="/api/users", method="GET", duration=150),
                    MockNetworkCall(
                        url="/api/orders", method="GET", duration=500
                    ),  # Slower
                    MockNetworkCall(url="/api/products", method="GET", duration=180),
                ]
            )
        ]

        thresholds = analyzer.extract_thresholds(events)

        assert len(thresholds) == 4

        # Verify thresholds are reasonable
        for threshold in thresholds:
            # All should be at least min threshold
            assert threshold.threshold_ms >= 100
            # All should be at most max threshold
            assert threshold.threshold_ms <= 30000
            # Threshold should be approximately 1.5x observed
            assert (
                threshold.observed_duration_ms * 1.4
                <= threshold.threshold_ms
                <= threshold.observed_duration_ms * 1.6
                or threshold.threshold_ms == 100
                or threshold.threshold_ms == 30000
            )

    def test_mixed_fast_and_slow_endpoints(self):
        """Test with mix of fast and slow endpoints"""
        analyzer = PerformanceAnalyzer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(
                        url="/api/cached", method="GET", duration=20
                    ),  # Very fast
                    MockNetworkCall(
                        url="/api/heavy", method="POST", duration=5000
                    ),  # Slow
                ]
            )
        ]

        thresholds = analyzer.extract_thresholds(events)

        # Fast endpoint should hit minimum
        fast_threshold = next(t for t in thresholds if t.endpoint == "/api/cached")
        assert fast_threshold.threshold_ms == 100  # Minimum enforced

        # Slow endpoint should be proportional
        slow_threshold = next(t for t in thresholds if t.endpoint == "/api/heavy")
        assert slow_threshold.threshold_ms == 7500  # 1.5x of 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
