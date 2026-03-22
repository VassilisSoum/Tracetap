"""
UI Interaction Recording Module for TraceTap

This module provides functionality to record user interactions during manual
testing sessions using Playwright trace files. It captures both UI events
(clicks, fills, navigation) and correlates them with network traffic for
automated test generation.

The recording workflow consists of:
1. TraceRecorder - Records browser interactions using Playwright tracing
2. TraceParser - Extracts UI events from trace files with microsecond precision
3. EventCorrelator - Correlates UI events with network traffic
4. RecordingSession - Manages complete recording sessions

Example Usage:
    from tracetap.record import TraceRecorder, TraceParser, EventCorrelator

    # Record a session
    recorder = TraceRecorder()
    await recorder.start_recording("https://example.com")
    # ... user interacts manually ...
    await recorder.stop_recording("session.zip")

    # Parse and correlate
    parser = TraceParser()
    events = await parser.parse("session.zip")

    correlator = EventCorrelator()
    correlated = correlator.correlate(events, network_traffic)
"""

from typing import List

# Version constant
__version__ = "1.0.0"

# Main classes
from .recorder import TraceRecorder, RecorderOptions
from .codegen_recorder import CodegenRecorder, CodegenOptions
from .codegen_parser import CodegenParser
from .parser import TraceParser
from .correlator import EventCorrelator, CorrelationOptions, NetworkRequest, load_mitmproxy_traffic
from .session import RecordingSession, SessionMetadata, SessionResult

__all__ = [
    "TraceRecorder",
    "RecorderOptions",
    "CodegenRecorder",
    "CodegenOptions",
    "CodegenParser",
    "TraceParser",
    "EventCorrelator",
    "CorrelationOptions",
    "NetworkRequest",
    "load_mitmproxy_traffic",
    "RecordingSession",
    "SessionMetadata",
    "SessionResult",
]
