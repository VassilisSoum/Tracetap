"""
Event correlator for linking UI events with network traffic.

This module correlates UI events from Playwright traces with network traffic
from mitmproxy captures. It uses time-window based correlation with confidence
scoring to build an interaction graph (UI event → API calls).

Key features:
- Time-window based correlation (default ±500ms)
- Confidence scoring based on timing, event type, and HTTP methods
- Handles one-to-many relationships (one click → multiple API calls)
- Quality assessment and statistics
- Prevents duplicate network call correlation

Reference Implementation: spike/poc/event-correlator.ts
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CorrelationMethod(str, Enum):
    """Method used to correlate UI event with network calls."""

    EXACT = "exact"  # Very close timing (<50ms)
    WINDOW = "window"  # Within time window
    INFERENCE = "inference"  # No direct correlation, inferred


@dataclass
class NetworkRequest:
    """Network request from mitmproxy capture.

    Attributes:
        method: HTTP method (GET, POST, PUT, etc.)
        url: Full URL of the request
        host: Hostname
        path: URL path
        timestamp: Unix timestamp in milliseconds
        request_headers: Request headers dictionary
        request_body: Request body (if applicable)
        response_status: HTTP response status code
        response_headers: Response headers dictionary
        response_body: Response body (if applicable)
        duration: Request duration in milliseconds
    """

    method: str
    url: str
    host: str
    path: str
    timestamp: int
    request_headers: Dict[str, str]
    request_body: Optional[str] = None
    response_status: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    response_body: Optional[str] = None
    duration: Optional[int] = None


@dataclass
class CorrelationMetadata:
    """Metadata about the correlation between UI event and network calls.

    Attributes:
        confidence: Confidence score (0.0 to 1.0)
        time_delta: Average milliseconds between UI event and network calls
        method: Correlation method used
        reasoning: Human-readable explanation
    """

    confidence: float
    time_delta: float
    method: CorrelationMethod
    reasoning: str


@dataclass
class CorrelatedEvent:
    """Correlated event combining UI action and network calls.

    Attributes:
        sequence: Event sequence number
        ui_event: Original UI event from trace parser
        network_calls: List of correlated network requests
        correlation: Correlation metadata
    """

    sequence: int
    ui_event: Any  # TraceTapEvent from parser module
    network_calls: List[NetworkRequest]
    correlation: CorrelationMetadata


@dataclass
class CorrelationResult:
    """Correlation result with statistics.

    Attributes:
        correlated_events: List of correlated events
        stats: Correlation statistics
    """

    correlated_events: List[CorrelatedEvent]
    stats: Dict[str, Any]


@dataclass
class CorrelationOptions:
    """Configuration options for event correlation.

    Attributes:
        window_ms: Time window for correlation in milliseconds (default 500)
        min_confidence: Minimum confidence threshold (default 0.5)
        include_orphans: Include UI events with no network calls (default False)
    """

    window_ms: int = 500
    min_confidence: float = 0.5
    include_orphans: bool = False


class EventCorrelator:
    """Correlates UI events with network traffic.

    This class implements time-window based correlation with confidence scoring
    to link UI interactions with their corresponding API calls. It builds an
    interaction graph suitable for automated test generation.

    Example:
        correlator = EventCorrelator(CorrelationOptions(window_ms=500))
        result = correlator.correlate(ui_events, network_calls)
        correlator.print_summary(result)
        print(f"Correlation rate: {result.stats['correlation_rate']:.1%}")
    """

    def __init__(self, options: Optional[CorrelationOptions] = None):
        """Initialize the event correlator.

        Args:
            options: Correlation configuration options
        """
        self.options = options or CorrelationOptions()

    def correlate(
        self,
        ui_events: List[Any],  # List[TraceTapEvent]
        network_calls: List[NetworkRequest],
    ) -> CorrelationResult:
        """Correlate UI events with network traffic.

        Finds network calls that occurred within the time window after each
        UI event, calculates confidence scores, and builds correlated events.

        Args:
            ui_events: List of UI events from trace parser
            network_calls: List of network requests from mitmproxy

        Returns:
            CorrelationResult with correlated events and statistics
        """
        logger.info("Starting correlation...")
        logger.info(f"   UI Events: {len(ui_events)}")
        logger.info(f"   Network Calls: {len(network_calls)}")
        logger.info(f"   Time Window: ±{self.options.window_ms}ms")

        correlated_events: List[CorrelatedEvent] = []
        used_network_calls: Set[int] = set()

        # Sort events by timestamp
        sorted_ui_events = sorted(ui_events, key=lambda e: e.timestamp)
        sorted_network_calls = sorted(network_calls, key=lambda nc: nc.timestamp)

        # Correlate each UI event with network calls
        for i, ui_event in enumerate(sorted_ui_events):
            # Find network calls within time window
            related_calls = self._find_related_network_calls(
                ui_event, sorted_network_calls, used_network_calls
            )

            # Calculate correlation confidence
            correlation = self._calculate_correlation(ui_event, related_calls)

            # Only include if confidence meets threshold (or if including orphans)
            if correlation.confidence >= self.options.min_confidence or (
                self.options.include_orphans and len(related_calls) == 0
            ):
                correlated_events.append(
                    CorrelatedEvent(
                        sequence=i + 1,
                        ui_event=ui_event,
                        network_calls=related_calls,
                        correlation=correlation,
                    )
                )

                # Mark network calls as used
                for call in related_calls:
                    original_index = next(
                        (
                            idx
                            for idx, nc in enumerate(sorted_network_calls)
                            if nc.timestamp == call.timestamp and nc.url == call.url
                        ),
                        None,
                    )
                    if original_index is not None:
                        used_network_calls.add(original_index)

        # Calculate statistics
        stats = self._calculate_stats(
            ui_events, network_calls, correlated_events, used_network_calls
        )

        logger.info("Correlation complete!")
        logger.info(f"   Correlated Events: {len(correlated_events)}")
        logger.info(f"   Correlation Rate: {stats['correlation_rate'] * 100:.1f}%")
        logger.info(f"   Average Confidence: {stats['average_confidence'] * 100:.1f}%")

        return CorrelationResult(correlated_events=correlated_events, stats=stats)

    def _find_related_network_calls(
        self,
        ui_event: Any,  # TraceTapEvent
        all_network_calls: List[NetworkRequest],
        used_calls: Set[int],
    ) -> List[NetworkRequest]:
        """Find network calls related to a UI event.

        Searches for network calls that occur within the time window
        after the UI event timestamp, excluding already correlated calls.

        Args:
            ui_event: UI event to correlate
            all_network_calls: All available network calls (sorted by timestamp)
            used_calls: Set of already correlated network call indices

        Returns:
            List of related network requests
        """
        related_calls: List[NetworkRequest] = []
        ui_timestamp = ui_event.timestamp

        # Search for network calls within the time window
        for i, network_call in enumerate(all_network_calls):
            if i in used_calls:
                continue  # Skip already correlated calls

            time_delta = network_call.timestamp - ui_timestamp

            # Network call must happen AFTER UI event (within window)
            if 0 <= time_delta <= self.options.window_ms:
                related_calls.append(network_call)

            # Stop searching if we're past the window
            if time_delta > self.options.window_ms:
                break

        return related_calls

    def _calculate_correlation(
        self,
        ui_event: Any,  # TraceTapEvent
        network_calls: List[NetworkRequest],
    ) -> CorrelationMetadata:
        """Calculate correlation confidence and metadata.

        Uses heuristics based on timing, event type, HTTP method, and
        call count to determine confidence score.

        Confidence boosters:
        - Shorter time deltas (+0.1 to +0.3)
        - Click/navigate events (+0.1)
        - Single network call (+0.1)
        - Mutation methods (POST/PUT/DELETE) on click (+0.1)

        Args:
            ui_event: UI event being correlated
            network_calls: Related network requests

        Returns:
            Correlation metadata with confidence score
        """
        if len(network_calls) == 0:
            return CorrelationMetadata(
                confidence=0.0,
                time_delta=0.0,
                method=CorrelationMethod.INFERENCE,
                reasoning="No network calls within time window",
            )

        # Calculate average time delta
        time_deltas = [nc.timestamp - ui_event.timestamp for nc in network_calls]
        avg_time_delta = sum(time_deltas) / len(time_deltas)

        # Base confidence on timing and event type
        confidence = 0.5  # Base confidence

        # Boost confidence for shorter time deltas
        if avg_time_delta < 100:
            confidence += 0.3
        elif avg_time_delta < 250:
            confidence += 0.2
        elif avg_time_delta < 500:
            confidence += 0.1

        # Boost confidence for specific event types
        event_type = getattr(ui_event, "type", "").lower()
        if event_type in ("click", "navigate"):
            confidence += 0.1  # Clicks/navigation often trigger API calls

        # Boost confidence if there's exactly one network call (clear correlation)
        if len(network_calls) == 1:
            confidence += 0.1

        # Boost confidence for POST/PUT/DELETE (mutations)
        has_mutation = any(
            nc.method.upper() in ("POST", "PUT", "DELETE", "PATCH")
            for nc in network_calls
        )
        if has_mutation and event_type == "click":
            confidence += 0.1

        # Cap confidence at 1.0
        confidence = min(confidence, 1.0)

        # Determine correlation method
        method = CorrelationMethod.WINDOW
        if avg_time_delta < 50:
            method = CorrelationMethod.EXACT

        # Generate reasoning
        reasoning = self._generate_reasoning(ui_event, network_calls, avg_time_delta)

        return CorrelationMetadata(
            confidence=confidence,
            time_delta=avg_time_delta,
            method=method,
            reasoning=reasoning,
        )

    def _generate_reasoning(
        self,
        ui_event: Any,  # TraceTapEvent
        network_calls: List[NetworkRequest],
        avg_time_delta: float,
    ) -> str:
        """Generate human-readable reasoning for correlation.

        Creates a concise explanation of why these network calls were
        correlated with the UI event.

        Args:
            ui_event: UI event being correlated
            network_calls: Correlated network requests
            avg_time_delta: Average time between event and calls

        Returns:
            Human-readable reasoning string
        """
        if len(network_calls) == 0:
            return "No network activity"

        methods = ", ".join(nc.method for nc in network_calls)
        urls = ", ".join(urlparse(nc.url).path for nc in network_calls)
        event_type = getattr(ui_event, "type", "unknown")

        return (
            f"{event_type} triggered {len(network_calls)} call(s) "
            f"[{methods}] to {urls} after {avg_time_delta:.0f}ms"
        )

    def _calculate_stats(
        self,
        all_ui_events: List[Any],
        all_network_calls: List[NetworkRequest],
        correlated_events: List[CorrelatedEvent],
        used_network_calls: Set[int],
    ) -> Dict[str, Any]:
        """Calculate correlation statistics.

        Computes metrics like correlation rate, average confidence,
        average time delta, and coverage.

        Args:
            all_ui_events: All UI events
            all_network_calls: All network calls
            correlated_events: Successfully correlated events
            used_network_calls: Set of correlated network call indices

        Returns:
            Statistics dictionary
        """
        total_ui_events = len(all_ui_events)
        total_network_calls = len(all_network_calls)
        correlated_ui_events = len(correlated_events)
        correlated_network_calls = len(used_network_calls)

        average_confidence = (
            sum(e.correlation.confidence for e in correlated_events)
            / len(correlated_events)
            if correlated_events
            else 0.0
        )

        average_time_delta = (
            sum(e.correlation.time_delta for e in correlated_events)
            / len(correlated_events)
            if correlated_events
            else 0.0
        )

        correlation_rate = (
            correlated_ui_events / total_ui_events if total_ui_events > 0 else 0.0
        )

        return {
            "total_ui_events": total_ui_events,
            "total_network_calls": total_network_calls,
            "correlated_ui_events": correlated_ui_events,
            "correlated_network_calls": correlated_network_calls,
            "average_confidence": average_confidence,
            "average_time_delta": average_time_delta,
            "correlation_rate": correlation_rate,
        }

    def print_summary(self, result: CorrelationResult) -> None:
        """Print correlation summary to console.

        Displays correlation statistics and quality assessment.

        Args:
            result: Correlation result with statistics
        """
        stats = result.stats
        print("\n📊 Correlation Statistics:")
        print(f"   Total UI Events: {stats['total_ui_events']}")
        print(f"   Total Network Calls: {stats['total_network_calls']}")
        print(f"   Correlated UI Events: {stats['correlated_ui_events']}")
        print(f"   Correlated Network Calls: {stats['correlated_network_calls']}")
        print(f"   Correlation Rate: {stats['correlation_rate'] * 100:.1f}%")
        print(f"   Average Confidence: {stats['average_confidence'] * 100:.1f}%")
        print(f"   Average Time Delta: {stats['average_time_delta']:.1f}ms")

        # Quality assessment
        print("\n🎯 Quality Assessment:")
        rate = stats["correlation_rate"]
        confidence = stats["average_confidence"]

        if rate >= 0.8 and confidence >= 0.7:
            print("   ✅ EXCELLENT - High correlation with strong confidence")
        elif rate >= 0.6 and confidence >= 0.6:
            print("   ✅ GOOD - Acceptable correlation quality")
        elif rate >= 0.4 or confidence >= 0.5:
            print("   ⚠️  MODERATE - May need tuning or longer time windows")
        else:
            print("   ❌ POOR - Correlation quality insufficient")

    def print_timeline(self, result: CorrelationResult, limit: int = 10) -> None:
        """Print correlation timeline to console.

        Displays chronological list of correlated events with network calls.

        Args:
            result: Correlation result
            limit: Maximum number of events to display
        """
        print(f"\n⏱️  Correlation Timeline (first {limit}):")

        for event in result.correlated_events[:limit]:
            time = datetime.fromtimestamp(event.ui_event.timestamp / 1000).strftime(
                "%H:%M:%S.%f"
            )[:-3]
            ui_type = getattr(event.ui_event, "type", "unknown").ljust(8)
            selector = (
                getattr(event.ui_event, "selector", None)
                or getattr(event.ui_event, "url", None)
                or ""
            )
            network_count = len(event.network_calls)
            confidence = int(event.correlation.confidence * 100)

            print(f"   {event.sequence}. [{time}] {ui_type} {selector}")
            print(
                f"      └─ {network_count} call(s), {confidence}% confidence, "
                f"+{event.correlation.time_delta:.0f}ms"
            )

            for i, nc in enumerate(event.network_calls):
                url = urlparse(nc.url).path
                status = nc.response_status if nc.response_status else "?"
                print(f"         {i + 1}. {nc.method} {url} ({status})")

        if len(result.correlated_events) > limit:
            remaining = len(result.correlated_events) - limit
            print(f"   ... and {remaining} more events")

    def format_result(self, result: CorrelationResult) -> str:
        """Format result as JSON.

        Args:
            result: Correlation result

        Returns:
            JSON string representation
        """

        def convert_to_serializable(obj: Any) -> Any:
            """Convert dataclass objects to dictionaries for JSON serialization."""
            if hasattr(obj, "__dataclass_fields__"):
                return asdict(obj)
            elif isinstance(obj, Enum):
                return obj.value
            elif hasattr(obj, "__dict__"):
                return obj.__dict__
            else:
                return obj

        # Convert result to dictionary
        result_dict = {
            "correlated_events": [
                {
                    "sequence": e.sequence,
                    "ui_event": convert_to_serializable(e.ui_event),
                    "network_calls": [asdict(nc) for nc in e.network_calls],
                    "correlation": {
                        "confidence": e.correlation.confidence,
                        "time_delta": e.correlation.time_delta,
                        "method": e.correlation.method.value,
                        "reasoning": e.correlation.reasoning,
                    },
                }
                for e in result.correlated_events
            ],
            "stats": result.stats,
        }

        return json.dumps(result_dict, indent=2)


def load_mitmproxy_traffic(file_path: str) -> List[NetworkRequest]:
    """Load network traffic from mitmproxy JSON export.

    Parses mitmproxy export format and converts to TraceTap NetworkRequest
    format. Handles various mitmproxy export formats.

    Args:
        file_path: Path to mitmproxy JSON export file

    Returns:
        List of network requests

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Traffic file not found: {file_path}")

    logger.info(f"Loading mitmproxy traffic: {file_path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in {file_path}: {e}")

    # Handle different mitmproxy export formats
    # Expect either {"requests": [...]} or [...]
    raw_requests = data.get("requests", data) if isinstance(data, dict) else data

    if not isinstance(raw_requests, list):
        raise ValueError("Expected list of requests or dict with 'requests' key")

    requests: List[NetworkRequest] = []

    for req in raw_requests:
        try:
            # Parse URL to extract host and path
            parsed_url = urlparse(req["url"])

            # Extract request data
            request_data = req.get("request", {})
            response_data = req.get("response")

            # Create NetworkRequest
            network_request = NetworkRequest(
                method=req["method"],
                url=req["url"],
                host=req.get("host", parsed_url.netloc),
                path=req.get("path", parsed_url.path),
                timestamp=req.get("timestamp", 0),
                request_headers=request_data.get("headers", {}),
                request_body=request_data.get("body"),
                response_status=response_data.get("status") if response_data else None,
                response_headers=(
                    response_data.get("headers") if response_data else None
                ),
                response_body=response_data.get("body") if response_data else None,
                duration=req.get("duration", req.get("response_time")),
            )

            requests.append(network_request)

        except (KeyError, TypeError) as e:
            logger.warning(f"Skipping malformed request: {e}")
            continue

    logger.info(f"Loaded {len(requests)} network requests")
    return requests
