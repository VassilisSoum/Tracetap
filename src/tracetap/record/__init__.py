"""
UI Interaction Recording Module for TraceTap

Records real user interactions (clicks, typing, navigation) and network
traffic from a single browser instance. Correlates UI events with API
calls for automated test generation.

Usage:
    from tracetap.record import RecordingSession

    session = RecordingSession(session_name="login-flow")
    await session.start("https://example.com")
    await session.wait_for_user()
    result = await session.stop()
    session.save(result)
"""

from .interaction_recorder import (
    InteractionRecorder,
    RecorderOptions,
    RecordedEvent,
    NetworkCall,
)
from .correlator import (
    EventCorrelator,
    CorrelationOptions,
    CorrelationResult,
    NetworkRequest,
    load_mitmproxy_traffic,
)
from .parser import TraceParser, TraceTapEvent, EventType, ParseResult
from .session import RecordingSession, SessionMetadata, SessionResult

__all__ = [
    "InteractionRecorder",
    "RecorderOptions",
    "RecordedEvent",
    "NetworkCall",
    "EventCorrelator",
    "CorrelationOptions",
    "CorrelationResult",
    "NetworkRequest",
    "load_mitmproxy_traffic",
    "TraceParser",
    "TraceTapEvent",
    "EventType",
    "ParseResult",
    "RecordingSession",
    "SessionMetadata",
    "SessionResult",
]
