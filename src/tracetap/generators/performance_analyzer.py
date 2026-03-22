"""Performance analysis module for TraceTap.

Extracts performance metrics from recorded network calls and generates
timing assertions for test generation. Uses already-captured duration data
to set reasonable performance thresholds.
"""

from dataclasses import dataclass
from typing import List, Optional, Any


@dataclass
class PerformanceThreshold:
    """Performance threshold for a single API endpoint.

    Attributes:
        endpoint: The API endpoint URL
        method: HTTP method (GET, POST, etc.)
        observed_duration_ms: Observed duration during recording in milliseconds
        threshold_ms: Calculated threshold for assertion (typically 1.5x observed)
    """

    endpoint: str
    method: str
    observed_duration_ms: int
    threshold_ms: int


@dataclass
class PerformanceConfig:
    """Configuration for performance threshold calculation.

    Attributes:
        threshold_multiplier: Multiplier for observed duration (default: 1.5x)
        min_threshold_ms: Minimum threshold to prevent overly strict assertions (default: 100ms)
        max_threshold_ms: Maximum threshold to catch severe regressions (default: 30000ms)
    """

    threshold_multiplier: float = 1.5
    min_threshold_ms: int = 100
    max_threshold_ms: int = 30000


class PerformanceAnalyzer:
    """Analyzes performance data from recorded sessions.

    This class extracts timing information from correlated events and
    generates performance thresholds for test assertions.

    Example:
        >>> analyzer = PerformanceAnalyzer()
        >>> thresholds = analyzer.extract_thresholds(correlated_events)
        >>> prompt_context = analyzer.format_for_prompt(thresholds)
        >>> # prompt_context contains formatted instructions for AI
    """

    def __init__(self, config: Optional[PerformanceConfig] = None):
        """Initialize performance analyzer.

        Args:
            config: Performance configuration. If None, uses defaults.
        """
        self.config = config or PerformanceConfig()

    def extract_thresholds(
        self, correlated_events: List[Any]
    ) -> List[PerformanceThreshold]:
        """Extract performance thresholds from correlated events.

        Analyzes network call durations from the recording and calculates
        reasonable thresholds for performance assertions in generated tests.

        Args:
            correlated_events: List of CorrelatedEvent objects from recording

        Returns:
            List of PerformanceThreshold objects with calculated thresholds
        """
        thresholds = []

        for event in correlated_events:
            # Extract network calls from event
            network_calls = getattr(event, "network_calls", [])

            for net_call in network_calls:
                # Check if duration data is available
                duration = getattr(net_call, "duration", None)

                if duration is not None and duration > 0:
                    # Calculate threshold as multiplier of observed duration
                    threshold = int(duration * self.config.threshold_multiplier)

                    # Apply min/max bounds
                    threshold = max(
                        self.config.min_threshold_ms,
                        min(self.config.max_threshold_ms, threshold),
                    )

                    thresholds.append(
                        PerformanceThreshold(
                            endpoint=net_call.url,
                            method=net_call.method,
                            observed_duration_ms=int(duration),
                            threshold_ms=threshold,
                        )
                    )

        return thresholds

    def format_for_prompt(self, thresholds: List[PerformanceThreshold]) -> str:
        """Format performance thresholds for AI prompt injection.

        Creates a formatted string that can be injected into the AI prompt
        to instruct the model to generate timing assertions.

        Args:
            thresholds: List of performance thresholds

        Returns:
            Formatted string with performance context for AI prompt

        Example output:
            ## Performance Thresholds (add timing assertions):

            Add timing assertions using this pattern:

            ```typescript
            const startTime = Date.now();
            const response = await page.waitForResponse('/api/endpoint');
            const duration = Date.now() - startTime;
            expect(duration).toBeLessThan(threshold_ms); // Observed Xms during recording
            ```

            Apply these thresholds:
            - GET /api/users: observed 245ms, assert < 368ms
            - POST /api/login: observed 156ms, assert < 234ms
        """
        if not thresholds:
            return ""

        lines = [
            "## Performance Thresholds (add timing assertions):",
            "",
            "Add timing assertions using this pattern:",
            "",
            "```typescript",
            "const startTime = Date.now();",
            "const response = await page.waitForResponse('/api/endpoint');",
            "const duration = Date.now() - startTime;",
            "expect(duration).toBeLessThan({threshold_ms}); // Observed {observed_ms}ms during recording",
            "```",
            "",
            "Apply these thresholds:",
        ]

        for threshold in thresholds:
            lines.append(
                f"- {threshold.method} {threshold.endpoint}: "
                f"observed {threshold.observed_duration_ms}ms, "
                f"assert < {threshold.threshold_ms}ms"
            )

        return "\n".join(lines)

    def get_statistics(self, thresholds: List[PerformanceThreshold]) -> dict:
        """Calculate statistics about performance thresholds.

        Args:
            thresholds: List of performance thresholds

        Returns:
            Dictionary with statistics (count, avg_duration, max_threshold, etc.)
        """
        if not thresholds:
            return {
                "count": 0,
                "avg_duration_ms": 0,
                "max_threshold_ms": 0,
                "min_threshold_ms": 0,
            }

        durations = [t.observed_duration_ms for t in thresholds]
        threshold_values = [t.threshold_ms for t in thresholds]

        return {
            "count": len(thresholds),
            "avg_duration_ms": sum(durations) // len(durations),
            "max_threshold_ms": max(threshold_values),
            "min_threshold_ms": min(threshold_values),
            "endpoints": len(set(t.endpoint for t in thresholds)),
        }
