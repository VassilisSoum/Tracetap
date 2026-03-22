"""
Trace file parser for extracting UI events from Playwright traces.

This module parses Playwright trace.zip files and extracts UI events in
TraceTap format. It processes the trace.trace JSON file with microsecond-precision
timestamps and converts Playwright actions into standardized TraceTap events.

Key features:
- Extracts and unzips trace.zip archives
- Parses trace.trace JSON with microsecond timestamps
- Filters for relevant UI actions (clicks, fills, navigation, etc.)
- Converts to TraceTap event format with metadata
- Calculates session statistics

Reference Implementation: spike/poc/trace-parser.ts
"""

import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """TraceTap event types."""

    CLICK = "click"
    FILL = "fill"
    NAVIGATE = "navigate"
    PRESS = "press"
    SELECT = "select"
    CHECK = "check"
    UPLOAD = "upload"
    HOVER = "hover"


@dataclass
class TraceTapEvent:
    """TraceTap event format for UI interactions.

    Attributes:
        type: Event type (click, fill, navigate, etc.)
        timestamp: Unix timestamp in milliseconds
        duration: Event duration in milliseconds
        selector: CSS selector for the target element (if applicable)
        value: Input value for fill/press events (if applicable)
        url: URL for navigation events (if applicable)
        metadata: Original Playwright action metadata
    """

    type: EventType
    timestamp: int
    duration: int
    selector: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ParseResult:
    """Parse result with events and statistics.

    Attributes:
        events: List of extracted TraceTap events
        stats: Session statistics
    """

    events: List[TraceTapEvent]
    stats: Dict[str, Any]


class TraceParser:
    """Parses Playwright trace files and extracts UI events.

    This class handles the complete parsing workflow: extracting the trace.zip
    archive, parsing the trace.trace JSON, filtering relevant actions, and
    converting them to TraceTap event format.

    Example:
        parser = TraceParser()
        result = await parser.parse("session.zip")
        print(f"Extracted {len(result.events)} events")
        parser.print_summary(result)
    """

    def __init__(self):
        """Initialize the trace parser."""
        self._relevant_apis = [
            'click',
            'dblclick',
            'fill',
            'type',
            'press',
            'selectOption',
            'check',
            'uncheck',
            'setInputFiles',
            'hover',
            'goto',
            'goBack',
            'goForward'
        ]

    async def parse(self, trace_path: str) -> ParseResult:
        """Parse trace ZIP file and extract events.

        Extracts the trace.zip archive, parses the trace.trace JSON file,
        filters for relevant UI actions, and converts them to TraceTap format.

        Args:
            trace_path: Path to the trace.zip file

        Returns:
            ParseResult containing events and statistics

        Raises:
            FileNotFoundError: If trace file doesn't exist
            ValueError: If trace file is invalid or missing trace.trace
        """
        logger.info(f"📂 Opening trace file: {trace_path}")

        # Validate file exists
        path = Path(trace_path)
        if not path.exists():
            raise FileNotFoundError(f"Trace file not found: {trace_path}")

        # Extract and parse trace data
        trace_data = self._extract_zip(trace_path)

        # Extract actions
        actions = trace_data.get('actions', [])
        logger.info(f"📊 Found {len(actions)} total actions")

        # Convert to TraceTap events
        events = self._convert_to_tracetap_events(actions)
        logger.info(f"✅ Extracted {len(events)} relevant events")

        # Calculate statistics
        stats = self._calculate_stats(actions, events)

        return ParseResult(events=events, stats=stats)

    def _extract_zip(self, trace_path: str) -> Dict[str, Any]:
        """Extract and parse trace.trace from ZIP file.

        Args:
            trace_path: Path to trace.zip file

        Returns:
            Parsed trace data as dictionary
        """
        logger.info("📖 Reading trace data...")

        try:
            with zipfile.ZipFile(trace_path, 'r') as zip_file:
                # List all files in the archive for debugging
                file_list = zip_file.namelist()
                logger.debug(f"Files in archive: {file_list}")

                # Try to find trace.trace file
                if 'trace.trace' not in file_list:
                    raise ValueError(
                        "trace.trace not found in ZIP. "
                        "This may not be a valid Playwright trace file. "
                        f"Available files: {file_list}"
                    )

                # Extract and parse trace.trace (NDJSON format)
                # Playwright trace files contain newline-delimited JSON objects
                with zip_file.open('trace.trace') as trace_file:
                    actions = []
                    line_num = 0

                    for line in trace_file:
                        line_num += 1
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            obj = json.loads(line)
                            # Collect action objects for the expected output format
                            if obj.get('type') == 'action':
                                actions.append(obj)
                        except json.JSONDecodeError as e:
                            logger.warning(
                                f"⚠️  Skipping malformed JSON at line {line_num}: {e}"
                            )
                            continue

                    # Return in expected format for line 138: actions = trace_data.get('actions', [])
                    return {'actions': actions}

        except zipfile.BadZipFile as e:
            raise ValueError(f"Invalid ZIP file: {trace_path}") from e

    def _convert_to_tracetap_events(self, actions: List[Dict[str, Any]]) -> List[TraceTapEvent]:
        """Convert Playwright actions to TraceTap events.

        Filters relevant actions and maps them to TraceTap event format.

        Args:
            actions: List of Playwright actions from trace.trace

        Returns:
            List of TraceTap events
        """
        events = []
        for action in actions:
            if self._is_relevant_action(action):
                event = self._convert_action(action)
                if event:
                    events.append(event)
        return events

    def _is_relevant_action(self, action: Dict[str, Any]) -> bool:
        """Check if action is relevant for test generation.

        Filters for user-triggered actions like clicks, fills, navigation.
        Excludes internal actions like waitForSelector, etc.

        Args:
            action: Playwright action dictionary

        Returns:
            True if action is relevant for test generation
        """
        api_name = action.get('apiName', '')
        return any(api in api_name for api in self._relevant_apis)

    def _convert_action(self, action: Dict[str, Any]) -> Optional[TraceTapEvent]:
        """Convert single Playwright action to TraceTap event.

        Maps Playwright apiName to TraceTap event type and extracts
        relevant parameters (selector, value, url).

        Args:
            action: Playwright action dictionary

        Returns:
            TraceTap event or None if conversion fails
        """
        try:
            api_name = action.get('apiName', '')
            params = action.get('params', {})

            # Base event properties
            # wallTime is in microseconds, convert to milliseconds
            timestamp = action.get('wallTime', 0)
            start_time = action.get('startTime', 0)
            end_time = action.get('endTime', 0)
            duration = end_time - start_time if end_time else 0

            # Build metadata
            metadata = {
                'apiName': api_name,
                'params': params,
                'success': 'error' not in action,
                'error': action.get('error')
            }

            # Map Playwright API to TraceTap event type
            if 'click' in api_name:
                return TraceTapEvent(
                    type=EventType.CLICK,
                    timestamp=timestamp,
                    duration=duration,
                    selector=params.get('selector'),
                    metadata=metadata
                )

            if 'fill' in api_name or 'type' in api_name:
                return TraceTapEvent(
                    type=EventType.FILL,
                    timestamp=timestamp,
                    duration=duration,
                    selector=params.get('selector'),
                    value=params.get('value') or params.get('text'),
                    metadata=metadata
                )

            if 'press' in api_name:
                return TraceTapEvent(
                    type=EventType.PRESS,
                    timestamp=timestamp,
                    duration=duration,
                    selector=params.get('selector'),
                    value=params.get('key'),
                    metadata=metadata
                )

            if 'selectOption' in api_name:
                values = params.get('values') or params.get('value')
                return TraceTapEvent(
                    type=EventType.SELECT,
                    timestamp=timestamp,
                    duration=duration,
                    selector=params.get('selector'),
                    value=json.dumps(values) if values else None,
                    metadata=metadata
                )

            if 'check' in api_name or 'uncheck' in api_name:
                return TraceTapEvent(
                    type=EventType.CHECK,
                    timestamp=timestamp,
                    duration=duration,
                    selector=params.get('selector'),
                    metadata=metadata
                )

            if 'setInputFiles' in api_name:
                files = params.get('files')
                return TraceTapEvent(
                    type=EventType.UPLOAD,
                    timestamp=timestamp,
                    duration=duration,
                    selector=params.get('selector'),
                    value=json.dumps(files) if files else None,
                    metadata=metadata
                )

            if 'hover' in api_name:
                return TraceTapEvent(
                    type=EventType.HOVER,
                    timestamp=timestamp,
                    duration=duration,
                    selector=params.get('selector'),
                    metadata=metadata
                )

            if 'goto' in api_name:
                return TraceTapEvent(
                    type=EventType.NAVIGATE,
                    timestamp=timestamp,
                    duration=duration,
                    url=params.get('url'),
                    metadata=metadata
                )

            return None

        except Exception as e:
            logger.warning(f"⚠️  Failed to convert action: {action.get('apiName')}", exc_info=e)
            return None

    def _calculate_stats(self, actions: List[Dict[str, Any]], events: List[TraceTapEvent]) -> Dict[str, Any]:
        """Calculate session statistics.

        Computes total actions, relevant events, duration, start/end times,
        and event type breakdown.

        Args:
            actions: All Playwright actions
            events: Filtered TraceTap events

        Returns:
            Statistics dictionary
        """
        if not actions:
            return {
                'totalActions': 0,
                'relevantActions': 0,
                'duration': 0,
                'startTime': 0,
                'endTime': 0
            }

        # Get time range from actions
        wall_times = [a.get('wallTime', 0) for a in actions if 'wallTime' in a]
        start_time = min(wall_times) if wall_times else 0
        end_time = max(wall_times) if wall_times else 0

        return {
            'totalActions': len(actions),
            'relevantActions': len(events),
            'duration': end_time - start_time,
            'startTime': start_time,
            'endTime': end_time
        }

    def format_events(self, result: ParseResult) -> str:
        """Format events as pretty JSON.

        Args:
            result: Parse result with events

        Returns:
            JSON string representation
        """
        # Convert events to dictionaries
        result_dict = {
            'events': [asdict(event) for event in result.events],
            'stats': result.stats
        }
        return json.dumps(result_dict, indent=2)

    def print_summary(self, result: ParseResult) -> None:
        """Print summary statistics to console.

        Displays total actions, event count, duration, and event breakdown.

        Args:
            result: Parse result with statistics
        """
        stats = result.stats

        print("\n📊 Session Statistics:")
        print(f"   Total Actions: {stats['totalActions']}")
        print(f"   Relevant Events: {stats['relevantActions']}")
        print(f"   Session Duration: {stats['duration'] / 1000:.1f}s")

        # Format timestamps
        if stats['startTime']:
            start_dt = datetime.fromtimestamp(stats['startTime'] / 1000)
            print(f"   Start Time: {start_dt.isoformat()}")

        if stats['endTime']:
            end_dt = datetime.fromtimestamp(stats['endTime'] / 1000)
            print(f"   End Time: {end_dt.isoformat()}")

        # Event type breakdown
        print("\n📝 Event Breakdown:")
        event_types: Dict[str, int] = {}
        for event in result.events:
            event_type = event.type.value
            event_types[event_type] = event_types.get(event_type, 0) + 1

        # Sort by count descending
        for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {event_type}: {count}")

    def print_timeline(self, result: ParseResult, limit: int = 10) -> None:
        """Print event timeline to console.

        Displays chronological list of events with timestamps.

        Args:
            result: Parse result with events
            limit: Maximum number of events to display
        """
        print(f"\n⏱️  Event Timeline (first {limit}):")

        for index, event in enumerate(result.events[:limit]):
            # Format timestamp
            dt = datetime.fromtimestamp(event.timestamp / 1000)
            time_str = dt.strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds

            # Build display string
            selector = f" {event.selector}" if event.selector else ""
            value = f' = "{event.value}"' if event.value else ""
            url = f" → {event.url}" if event.url else ""

            print(f"   {index + 1}. [{time_str}] {event.type.value}{selector}{value}{url}")

        if len(result.events) > limit:
            print(f"   ... and {len(result.events) - limit} more events")
