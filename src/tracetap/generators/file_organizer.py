"""File organization module for TraceTap.

Organizes generated tests into logical directory structures based on
endpoint patterns and feature groupings. Creates clean, maintainable
test hierarchies instead of monolithic test files.
"""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from collections import defaultdict
from urllib.parse import urlparse


@dataclass
class TestFileSpec:
    """Specification for a single test file.

    Attributes:
        relative_path: Relative path from output directory (e.g., "auth/login.spec.ts")
        test_name: Descriptive name for the test suite
        events: List of correlated events for this test file
    """

    relative_path: Path
    test_name: str
    events: List[Any]


class FileOrganizer:
    """Organizes tests into logical directory structures.

    This class groups correlated events by endpoint patterns and creates
    a clean directory hierarchy for generated tests. For example:

    tests/
      auth/
        login.spec.ts
        logout.spec.ts
      users/
        get.spec.ts
        post.spec.ts
      orders/
        create.spec.ts

    Example:
        >>> organizer = FileOrganizer()
        >>> specs = organizer.organize(correlated_events, Path("tests"))
        >>> for spec in specs:
        ...     print(f"{spec.relative_path}: {len(spec.events)} events")
    """

    # Feature detection patterns (regex pattern -> feature name)
    FEATURE_PATTERNS = {
        r"/auth/": "auth",
        r"/login": "auth",
        r"/logout": "auth",
        r"/signin": "auth",
        r"/signup": "auth",
        r"/users?/": "users",
        r"/accounts?/": "accounts",
        r"/products?/": "products",
        r"/items?/": "items",
        r"/orders?/": "orders",
        r"/cart": "cart",
        r"/checkout": "checkout",
        r"/payment": "payment",
        r"/profile": "profile",
        r"/settings": "settings",
        r"/dashboard": "dashboard",
        r"/admin": "admin",
        r"/api/v\d+/": "api",
    }

    def organize(
        self, correlated_events: List[Any], base_output: Path
    ) -> List[TestFileSpec]:
        """Organize correlated events into test file specifications.

        Groups events by endpoint patterns and creates logical test file
        structures. Events with similar endpoints are grouped together.

        Args:
            correlated_events: List of CorrelatedEvent objects from recording
            base_output: Base output directory path (not used in paths, just for context)

        Returns:
            List of TestFileSpec objects defining the test file structure
        """
        # Group events by normalized endpoint
        groups = self._group_by_endpoint(correlated_events)

        # Convert groups to file specifications
        specs = []
        for endpoint_key, events in groups.items():
            spec = self._create_file_spec(endpoint_key, events)
            specs.append(spec)

        return specs

    def _group_by_endpoint(self, events: List[Any]) -> Dict[str, List[Any]]:
        """Group events by normalized endpoint key.

        Args:
            events: List of correlated events

        Returns:
            Dictionary mapping endpoint keys to event lists
        """
        groups = defaultdict(list)

        for event in events:
            # Get network calls from event
            network_calls = getattr(event, "network_calls", [])

            if network_calls:
                # Use first network call as primary endpoint
                primary_call = network_calls[0]
                key = self._get_endpoint_key(primary_call.url, primary_call.method)
                groups[key].append(event)
            else:
                # Fallback: group by UI event type
                ui_event = getattr(event, "ui_event", None)
                if ui_event:
                    event_type = getattr(ui_event, "type", "unknown")
                    key = f"ui/{event_type}"
                    groups[key].append(event)

        return dict(groups)

    def _get_endpoint_key(self, url: str, method: str) -> str:
        """Generate a normalized endpoint key for grouping.

        Normalizes URLs by replacing IDs with placeholders and extracts
        the feature/resource name.

        Args:
            url: Full URL string
            method: HTTP method (GET, POST, etc.)

        Returns:
            Endpoint key like "auth/post" or "users/get"

        Example:
            >>> _get_endpoint_key("https://api.com/users/123", "GET")
            "users/get"
            >>> _get_endpoint_key("https://api.com/orders/abc-def", "POST")
            "orders/post"
        """
        # Parse URL to get path
        parsed = urlparse(url)
        path = parsed.path

        # Normalize path: replace numeric IDs with {id}
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)

        # Replace UUIDs with {id}
        path = re.sub(r"/[a-f0-9-]{36}(?=/|$)", "/{id}", path, flags=re.IGNORECASE)

        # Replace other ID-like patterns (alphanumeric with hyphens/underscores)
        path = re.sub(r"/[a-zA-Z0-9_-]{8,}(?=/|$)", "/{id}", path)

        # Extract feature from path
        feature = self._extract_feature(path)

        # Normalize method
        method_lower = method.lower()

        # Create key: feature/method
        return f"{feature}/{method_lower}" if feature else f"api/{method_lower}"

    def _extract_feature(self, path: str) -> Optional[str]:
        """Extract feature name from URL path.

        Uses pattern matching to identify common features (auth, users, etc.)
        or falls back to the first path segment.

        Args:
            path: URL path string (e.g., "/api/v1/users/123")

        Returns:
            Feature name (e.g., "users") or None if path is empty
        """
        # Try pattern matching first
        for pattern, feature in self.FEATURE_PATTERNS.items():
            if re.search(pattern, path, re.IGNORECASE):
                return feature

        # Fallback: extract first meaningful path segment
        segments = [s for s in path.split("/") if s and s not in ["api", "v1", "v2", "v3"]]

        if segments:
            # Use first segment, remove trailing 's' for plural resources
            feature = segments[0].lower()

            # Remove common ID patterns from segment
            feature = re.sub(r"\{id\}|\d+|[a-f0-9-]{8,}", "", feature)

            # Clean up any remaining special characters
            feature = re.sub(r"[^a-z0-9_-]", "", feature)

            return feature if feature else "api"

        return "api"

    def _create_file_spec(self, endpoint_key: str, events: List[Any]) -> TestFileSpec:
        """Create a TestFileSpec from an endpoint key and events.

        Args:
            endpoint_key: Endpoint key like "auth/post" or "users/get"
            events: List of correlated events for this endpoint

        Returns:
            TestFileSpec with relative path and test name
        """
        # Parse endpoint key: "feature/method"
        parts = endpoint_key.split("/")

        if len(parts) == 2:
            feature, method = parts
        else:
            # Fallback for unexpected format
            feature = "api"
            method = parts[-1] if parts else "test"

        # Create relative path: feature/method.spec.ts
        relative_path = Path(feature) / f"{method}.spec.ts"

        # Create descriptive test name
        test_name = f"{feature} {method} operations"

        return TestFileSpec(
            relative_path=relative_path, test_name=test_name, events=events
        )

    def get_statistics(self, specs: List[TestFileSpec]) -> dict:
        """Calculate statistics about the organized test structure.

        Args:
            specs: List of TestFileSpec objects

        Returns:
            Dictionary with statistics (file_count, features, avg_events_per_file, etc.)
        """
        if not specs:
            return {
                "file_count": 0,
                "feature_count": 0,
                "total_events": 0,
                "avg_events_per_file": 0,
            }

        # Extract unique features (first directory in path)
        features = set()
        total_events = 0

        for spec in specs:
            features.add(spec.relative_path.parts[0])
            total_events += len(spec.events)

        return {
            "file_count": len(specs),
            "feature_count": len(features),
            "total_events": total_events,
            "avg_events_per_file": total_events // len(specs) if specs else 0,
            "features": sorted(features),
        }
