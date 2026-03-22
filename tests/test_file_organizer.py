"""
Tests for File Organizer

Tests endpoint-based test organization and grouping.
"""

import pytest
from pathlib import Path
from dataclasses import dataclass

# Add src to path

from tracetap.generators.file_organizer import (
    FileOrganizer,
    TestFileSpec,
)


# Mock network call for testing
@dataclass
class MockNetworkCall:
    """Mock network call"""

    url: str
    method: str


# Mock correlated event for testing
@dataclass
class MockCorrelatedEvent:
    """Mock correlated event"""

    network_calls: list


class TestFileOrganizer:
    """Test file organization by endpoint"""

    def test_organize_single_endpoint(self):
        """Test organizing single endpoint"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="https://api.example.com/users", method="GET")
                ]
            )
        ]

        specs = organizer.organize(events, Path("tests"))

        assert len(specs) == 1
        assert specs[0].relative_path == Path("users/get.spec.ts")
        assert "users" in specs[0].test_name
        assert len(specs[0].events) == 1

    def test_organize_multiple_endpoints(self):
        """Test organizing multiple different endpoints"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users", method="GET"),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/orders", method="POST"),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/products", method="GET"),
                ]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))

        assert len(specs) == 3

        # Check users endpoint
        users_spec = next(s for s in specs if "users" in str(s.relative_path))
        assert users_spec.relative_path == Path("users/get.spec.ts")

        # Check orders endpoint
        orders_spec = next(s for s in specs if "orders" in str(s.relative_path))
        assert orders_spec.relative_path == Path("orders/post.spec.ts")

    def test_normalize_id_patterns(self):
        """Test URL normalization with IDs"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users/123", method="GET"),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users/456", method="GET"),
                ]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))

        # Both should be grouped together (IDs normalized to {id})
        assert len(specs) == 1
        assert specs[0].relative_path == Path("users/get.spec.ts")
        assert len(specs[0].events) == 2

    def test_normalize_uuid_patterns(self):
        """Test UUID normalization"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(
                        url="/api/orders/a1b2c3d4-1234-5678-9012-abcdef123456",
                        method="GET",
                    ),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(
                        url="/api/orders/f9e8d7c6-4321-8765-2109-fedcba987654",
                        method="GET",
                    ),
                ]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))

        # Both should be grouped together (UUIDs normalized)
        assert len(specs) == 1
        assert len(specs[0].events) == 2

    def test_group_by_http_method(self):
        """Test grouping by HTTP method"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users", method="GET"),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users", method="POST"),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users", method="PUT"),
                ]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))

        # Should create separate files for each method
        assert len(specs) == 3

        methods = {str(spec.relative_path).split("/")[1].split(".")[0] for spec in specs}
        assert methods == {"get", "post", "put"}

    def test_auth_endpoint_detection(self):
        """Test detection of auth endpoints"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/login", method="POST"),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/logout", method="POST"),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/auth/signin", method="POST"),
                ]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))

        # All should be grouped under 'auth' feature
        for spec in specs:
            assert spec.relative_path.parts[0] == "auth"

    def test_feature_pattern_matching(self):
        """Test pattern matching for common features"""
        organizer = FileOrganizer()

        test_cases = [
            ("/api/users", "users"),
            ("/api/products", "products"),
            ("/api/orders", "orders"),
            ("/api/cart", "cart"),
            ("/api/checkout", "checkout"),
            ("/api/payment", "payment"),
            ("/api/dashboard", "dashboard"),
        ]

        for url, expected_feature in test_cases:
            events = [
                MockCorrelatedEvent(
                    network_calls=[MockNetworkCall(url=url, method="GET")]
                )
            ]

            specs = organizer.organize(events, Path("tests"))

            assert len(specs) == 1
            assert specs[0].relative_path.parts[0] == expected_feature

    def test_fallback_to_first_segment(self):
        """Test fallback to first path segment for unknown patterns"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/custom/endpoint", method="GET"),
                ]
            )
        ]

        specs = organizer.organize(events, Path("tests"))

        assert len(specs) == 1
        # Should use 'custom' as feature name (first segment after 'api')
        assert specs[0].relative_path.parts[0] == "custom"

    def test_versioned_api_paths(self):
        """Test handling of versioned API paths"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/v1/users", method="GET"),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/v2/users", method="GET"),
                ]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))

        # Both should be grouped under 'users' (version ignored)
        assert len(specs) == 1
        assert specs[0].relative_path.parts[0] == "users"

    def test_events_without_network_calls(self):
        """Test handling of events without network calls"""
        organizer = FileOrganizer()

        @dataclass
        class MockUIEvent:
            type: str

        @dataclass
        class EventWithUI:
            network_calls: list
            ui_event: MockUIEvent

        events = [
            EventWithUI(network_calls=[], ui_event=MockUIEvent(type="click")),
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/users", method="GET")]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))

        # Should create separate groups for UI and API events
        assert len(specs) >= 1

    def test_multiple_events_same_endpoint(self):
        """Test multiple events for same endpoint"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users/1", method="GET"),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users/2", method="GET"),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users/3", method="GET"),
                ]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))

        # All should be grouped together
        assert len(specs) == 1
        assert len(specs[0].events) == 3

    def test_empty_events_list(self):
        """Test handling of empty events list"""
        organizer = FileOrganizer()

        specs = organizer.organize([], Path("tests"))

        assert len(specs) == 0


class TestEndpointNormalization:
    """Test URL normalization logic"""

    def test_numeric_id_replacement(self):
        """Test numeric ID replacement"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/users/123/posts/456", method="GET")]
            )
        ]

        specs = organizer.organize(events, Path("tests"))

        # IDs should be normalized but feature should be extracted correctly
        assert len(specs) == 1

    def test_alphanumeric_id_replacement(self):
        """Test alphanumeric ID replacement"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/users/abc123def456/profile", method="GET")
                ]
            )
        ]

        specs = organizer.organize(events, Path("tests"))

        assert len(specs) == 1

    def test_query_params_ignored(self):
        """Test that query parameters don't affect grouping"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users?page=1&limit=10", method="GET"),
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users?page=2&limit=20", method="GET"),
                ]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))

        # Should be grouped together (query params don't affect path)
        assert len(specs) == 1
        assert len(specs[0].events) == 2


class TestStatistics:
    """Test organization statistics"""

    def test_statistics_single_file(self):
        """Test statistics for single file"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/users", method="GET")]
            )
        ]

        specs = organizer.organize(events, Path("tests"))
        stats = organizer.get_statistics(specs)

        assert stats["file_count"] == 1
        assert stats["feature_count"] == 1
        assert stats["total_events"] == 1
        assert stats["avg_events_per_file"] == 1
        assert "users" in stats["features"]

    def test_statistics_multiple_files(self):
        """Test statistics for multiple files"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/users", method="GET")]
            ),
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/orders", method="POST")]
            ),
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/products", method="GET")]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))
        stats = organizer.get_statistics(specs)

        assert stats["file_count"] == 3
        assert stats["feature_count"] == 3
        assert stats["total_events"] == 3
        assert stats["avg_events_per_file"] == 1

    def test_statistics_multiple_features(self):
        """Test statistics with multiple files per feature"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/users", method="GET")]
            ),
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/users", method="POST")]
            ),
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/orders", method="GET")]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))
        stats = organizer.get_statistics(specs)

        assert stats["file_count"] == 3  # users/get, users/post, orders/get
        assert stats["feature_count"] == 2  # users, orders
        assert sorted(stats["features"]) == ["orders", "users"]

    def test_statistics_empty_specs(self):
        """Test statistics for empty specs list"""
        organizer = FileOrganizer()

        stats = organizer.get_statistics([])

        assert stats["file_count"] == 0
        assert stats["feature_count"] == 0
        assert stats["total_events"] == 0
        assert stats["avg_events_per_file"] == 0


class TestRealWorldScenarios:
    """Test realistic organization scenarios"""

    def test_complex_ecommerce_api(self):
        """Test organization of complex e-commerce API"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/auth/login", method="POST")]
            ),
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/products", method="GET")]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/products/123", method="GET")
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/cart", method="GET")]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/cart/items", method="POST")
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/checkout", method="POST")
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/orders/abc-123", method="GET")
                ]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))

        # Check that we have organized structure
        features = {spec.relative_path.parts[0] for spec in specs}
        assert "auth" in features
        assert "products" in features
        assert "cart" in features
        assert "checkout" in features
        assert "orders" in features

    def test_rest_crud_operations(self):
        """Test organization of REST CRUD operations"""
        organizer = FileOrganizer()

        events = [
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/users", method="GET")]
            ),
            MockCorrelatedEvent(
                network_calls=[MockNetworkCall(url="/api/users", method="POST")]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users/123", method="PUT")
                ]
            ),
            MockCorrelatedEvent(
                network_calls=[
                    MockNetworkCall(url="/api/users/123", method="DELETE")
                ]
            ),
        ]

        specs = organizer.organize(events, Path("tests"))

        # Should create 4 files under users/
        assert len(specs) == 4
        assert all(spec.relative_path.parts[0] == "users" for spec in specs)

        # Check all HTTP methods are present
        methods = {
            spec.relative_path.stem.split(".")[0] for spec in specs
        }  # get.spec -> get
        assert methods == {"get", "post", "put", "delete"}


class TestTestFileSpec:
    """Test TestFileSpec dataclass"""

    def test_file_spec_creation(self):
        """Test creating TestFileSpec"""
        spec = TestFileSpec(
            relative_path=Path("auth/login.spec.ts"),
            test_name="auth login operations",
            events=[],
        )

        assert spec.relative_path == Path("auth/login.spec.ts")
        assert spec.test_name == "auth login operations"
        assert spec.events == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
