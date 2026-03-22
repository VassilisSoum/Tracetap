"""
Recording session management for TraceTap.

Manages the complete recording workflow: start browser, capture user
interactions + network traffic, correlate events, save results.

Usage:
    session = RecordingSession(session_name="login-flow")
    await session.start("https://app.example.com")
    await session.wait_for_user()
    await session.stop()
    result = session.get_result()
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import json
import uuid
import logging

from .interaction_recorder import InteractionRecorder, RecorderOptions, RecordedEvent, NetworkCall
from .correlator import (
    EventCorrelator, CorrelationOptions, CorrelationResult,
    NetworkRequest, CorrelatedEvent, CorrelationMetadata, CorrelationMethod,
)
from .parser import TraceTapEvent, EventType

logger = logging.getLogger(__name__)


@dataclass
class SessionMetadata:
    """Metadata for a recording session."""

    session_id: str
    session_name: str
    url: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    output_dir: Optional[Path] = None
    events_file: Optional[Path] = None
    traffic_file: Optional[Path] = None
    correlation_file: Optional[Path] = None
    status: str = "initialized"


@dataclass
class SessionResult:
    """Complete session result with all data."""

    metadata: SessionMetadata
    ui_events: List[Dict[str, Any]]
    network_calls: List[Dict[str, Any]]
    correlation_result: Optional[CorrelationResult] = None


class RecordingSession:
    """Manages complete recording sessions.

    Orchestrates the InteractionRecorder to capture user interactions and
    network traffic, then correlates them for test generation.

    Example:
        session = RecordingSession(session_name="checkout-flow")
        await session.start("https://shop.example.com")
        await session.wait_for_user()
        result = await session.stop()
        session.save(result)
    """

    def __init__(
        self,
        session_name: str,
        output_dir: str = "recordings",
        recorder_options: Optional[RecorderOptions] = None,
        correlation_options: Optional[CorrelationOptions] = None,
        proxy: Optional[str] = None,
    ):
        self.session_name = session_name
        self.output_dir = Path(output_dir)
        self.recorder_options = recorder_options or RecorderOptions()
        self.correlation_options = correlation_options or CorrelationOptions()
        self.proxy = proxy
        self.metadata: Optional[SessionMetadata] = None
        self.recorder: Optional[InteractionRecorder] = None
        self._result: Optional[SessionResult] = None

    async def start(self, url: str) -> SessionMetadata:
        """Start recording session.

        Args:
            url: Target URL to record

        Returns:
            Session metadata
        """
        if self.metadata and self.metadata.status == "recording":
            raise RuntimeError("Recording already in progress.")

        # Generate session ID and create output directory
        session_id = self._generate_session_id()
        session_dir = self._create_output_directory(session_id)

        self.metadata = SessionMetadata(
            session_id=session_id,
            session_name=self.session_name,
            url=url,
            start_time=datetime.now(),
            output_dir=session_dir,
            events_file=session_dir / "events.json",
            traffic_file=session_dir / "traffic.json",
            correlation_file=session_dir / "correlation.json",
            status="recording",
        )

        self._save_metadata()

        # Create and start recorder
        self.recorder = InteractionRecorder(self.recorder_options)
        await self.recorder.start(url, proxy=self.proxy)

        self.metadata.status = "recording"
        logger.info(f"Session {session_id} started for {url}")
        return self.metadata

    async def wait_for_user(self) -> None:
        """Wait for user to finish interacting."""
        if not self.recorder:
            raise RuntimeError("Recording not started.")
        await self.recorder.wait_for_user()

    async def stop(self) -> SessionResult:
        """Stop recording, correlate events, and return results.

        Returns:
            SessionResult with UI events, network calls, and correlations
        """
        if not self.recorder or not self.metadata:
            raise RuntimeError("Recording not started.")

        # Stop recorder and get raw data
        raw_result = await self.recorder.stop()
        self.recorder = None

        # Update metadata
        self.metadata.end_time = datetime.now()
        self.metadata.duration = (
            self.metadata.end_time - self.metadata.start_time
        ).total_seconds()
        self.metadata.status = "completed"

        ui_events = raw_result["ui_events"]
        network_calls = raw_result["network_calls"]

        logger.info(
            f"Captured {len(ui_events)} UI events, "
            f"{len(network_calls)} network calls"
        )

        # Correlate UI events with network calls
        correlation_result = self._correlate(ui_events, network_calls)

        self._result = SessionResult(
            metadata=self.metadata,
            ui_events=ui_events,
            network_calls=network_calls,
            correlation_result=correlation_result,
        )

        return self._result

    def save(self, result: Optional[SessionResult] = None) -> Path:
        """Save session results to disk.

        Args:
            result: Session result to save (uses last result if not provided)

        Returns:
            Path to session output directory
        """
        result = result or self._result
        if not result:
            raise RuntimeError("No results to save. Run stop() first.")

        output_dir = result.metadata.output_dir
        logger.info(f"Saving session to {output_dir}")

        # Save UI events
        with open(result.metadata.events_file, "w", encoding="utf-8") as f:
            json.dump({"events": result.ui_events}, f, indent=2)

        # Save network traffic
        with open(result.metadata.traffic_file, "w", encoding="utf-8") as f:
            json.dump({"requests": result.network_calls}, f, indent=2)

        # Save correlation results
        if result.correlation_result:
            correlator = EventCorrelator(self.correlation_options)
            correlation_json = correlator.format_result(result.correlation_result)
            with open(result.metadata.correlation_file, "w", encoding="utf-8") as f:
                f.write(correlation_json)

        # Save metadata
        self._save_metadata()

        logger.info(
            f"Session saved: {len(result.ui_events)} events, "
            f"{len(result.network_calls)} network calls"
        )
        return output_dir

    def _correlate(
        self,
        ui_events: List[Dict[str, Any]],
        network_calls: List[Dict[str, Any]],
    ) -> Optional[CorrelationResult]:
        """Correlate UI events with network traffic.

        Converts raw event dicts to the formats expected by EventCorrelator,
        then runs correlation.
        """
        if not ui_events or not network_calls:
            logger.info("Skipping correlation (no UI events or no network calls)")
            return None

        # Convert UI events to TraceTapEvent objects for correlator
        tracetap_events = []
        for evt in ui_events:
            event_type_str = evt.get("type", "click")
            try:
                event_type = EventType(event_type_str)
            except ValueError:
                event_type = EventType.CLICK

            tracetap_events.append(TraceTapEvent(
                type=event_type,
                timestamp=evt.get("timestamp", 0),
                duration=0,
                selector=evt.get("selector"),
                value=evt.get("value"),
                url=evt.get("url"),
                metadata=evt.get("metadata"),
            ))

        # Convert network calls to NetworkRequest objects
        network_requests = []
        for nc in network_calls:
            from urllib.parse import urlparse
            parsed = urlparse(nc.get("url", ""))
            network_requests.append(NetworkRequest(
                method=nc.get("method", "GET"),
                url=nc.get("url", ""),
                host=parsed.netloc,
                path=parsed.path,
                timestamp=nc.get("timestamp", 0),
                request_headers=nc.get("request_headers", {}),
                request_body=nc.get("request_body"),
                response_status=nc.get("response_status"),
                response_headers=nc.get("response_headers", {}),
                response_body=nc.get("response_body"),
                duration=nc.get("duration"),
            ))

        # Run correlation
        correlator = EventCorrelator(self.correlation_options)
        result = correlator.correlate(tracetap_events, network_requests)

        logger.info(
            f"Correlation: {len(result.correlated_events)} events correlated, "
            f"rate={result.stats['correlation_rate']:.0%}, "
            f"confidence={result.stats['average_confidence']:.0%}"
        )

        return result

    def _generate_session_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}"

    def _create_output_directory(self, session_id: str) -> Path:
        session_dir = self.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def _save_metadata(self) -> None:
        if not self.metadata or not self.metadata.output_dir:
            return

        metadata_file = self.metadata.output_dir / "metadata.json"
        data = {
            "session_id": self.metadata.session_id,
            "session_name": self.metadata.session_name,
            "url": self.metadata.url,
            "start_time": self.metadata.start_time.isoformat(),
            "end_time": self.metadata.end_time.isoformat() if self.metadata.end_time else None,
            "duration": self.metadata.duration,
            "output_dir": str(self.metadata.output_dir),
            "events_file": str(self.metadata.events_file),
            "traffic_file": str(self.metadata.traffic_file),
            "correlation_file": str(self.metadata.correlation_file),
            "status": self.metadata.status,
        }

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
