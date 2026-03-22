"""
Recording session management for TraceTap.

This module provides high-level session management for complete recording
workflows. It orchestrates the TraceRecorder, TraceParser, and EventCorrelator
to provide a unified API for recording, parsing, and correlating test sessions.

Key features:
- Unified session lifecycle management
- Coordinates recorder, parser, and correlator
- Saves session metadata and results
- Provides session replay and analysis tools
- Handles concurrent recording and network capture

Usage:
    session = RecordingSession(
        session_name="login-flow",
        output_dir="recordings/"
    )

    await session.start("https://app.example.com")
    # User interacts manually...
    await session.stop()

    # Parse and correlate
    result = await session.analyze(network_traffic_path="traffic.json")
    session.save_results(result)
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import asyncio
import subprocess
import signal
import sys
import os
import json
import uuid
import logging

from .recorder import TraceRecorder, RecorderOptions
from .codegen_recorder import CodegenRecorder, CodegenOptions
from .parser import TraceParser
from .correlator import EventCorrelator, CorrelationOptions, load_mitmproxy_traffic

logger = logging.getLogger(__name__)


# TODO: Implement session management
# Key responsibilities:
# - Coordinate TraceRecorder, TraceParser, and EventCorrelator
# - Manage session lifecycle (start, stop, pause, resume)
# - Save session metadata (start time, end time, URL, etc.)
# - Generate unique session IDs
# - Organize output files (traces, events, correlations)
# - Provide session replay capabilities
# - Handle errors and cleanup


@dataclass
class SessionMetadata:
    """Metadata for a recording session.

    Attributes:
        session_id: Unique session identifier
        session_name: Human-readable session name
        url: Target URL that was recorded
        start_time: Session start timestamp
        end_time: Session end timestamp (if completed)
        duration: Total session duration in seconds
        output_dir: Directory containing session files
        trace_file: Path to trace.zip file
        events_file: Path to parsed events JSON
        correlation_file: Path to correlation results JSON
        status: Session status (recording, completed, error)
    """

    session_id: str
    session_name: str
    url: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    output_dir: Optional[Path] = None
    trace_file: Optional[Path] = None
    events_file: Optional[Path] = None
    correlation_file: Optional[Path] = None
    traffic_path: Optional[Path] = None
    status: str = "initialized"


@dataclass
class SessionResult:
    """Complete session result with all analysis data.

    Attributes:
        metadata: Session metadata
        parse_result: Parsed events and statistics
        correlation_result: Correlated events and statistics (if available)
    """

    metadata: SessionMetadata
    parse_result: Optional[Any] = None  # ParseResult from parser
    correlation_result: Optional[Any] = None  # CorrelationResult from correlator


class RecordingSession:
    """Manages complete recording sessions with parsing and correlation.

    This class provides a high-level API for the entire recording workflow:
    recording → parsing → correlation → analysis. It handles session lifecycle,
    file management, and coordinates the recorder, parser, and correlator.

    Example:
        session = RecordingSession(
            session_name="checkout-flow",
            output_dir="recordings/",
            recorder_options=RecorderOptions(headless=False)
        )

        await session.start("https://shop.example.com")
        # User completes checkout...
        await session.stop()

        result = await session.analyze(
            network_traffic_path="traffic.json",
            correlation_options=CorrelationOptions(window_ms=1000)
        )

        session.save_results(result)
        print(f"Session saved to: {result.metadata.output_dir}")
    """

    def __init__(
        self,
        session_name: str,
        output_dir: str = "recordings",
        recorder_options: Optional[RecorderOptions] = None,
        proxy_port: int = 8888,
    ):
        """Initialize a recording session.

        Args:
            session_name: Human-readable name for the session
            output_dir: Directory to save session files
            recorder_options: Options for TraceRecorder
            proxy_port: Port for mitmproxy (default 8888)
        """
        self.session_name = session_name
        self.output_dir = Path(output_dir)
        self.recorder_options = recorder_options or RecorderOptions()
        self.proxy_port = proxy_port
        self.metadata: Optional[SessionMetadata] = None

        # Component instances
        self.recorder = None  # Can be TraceRecorder or CodegenRecorder
        self.parser: Optional[TraceParser] = None
        self.correlator: Optional[EventCorrelator] = None
        self._codegen_events: Optional[List[Dict[str, Any]]] = None  # Store codegen events

        # mitmproxy process
        self._mitm_process: Optional[subprocess.Popen] = None
        self._mitm_output_path: Optional[Path] = None

    async def start(self, url: str) -> SessionMetadata:
        """Start recording session at the given URL.

        Initializes session metadata, creates output directory structure,
        starts mitmproxy, and starts the TraceRecorder.

        Args:
            url: Target URL to navigate to and begin recording

        Returns:
            Session metadata

        Raises:
            RuntimeError: If session is already recording
        """
        if self.metadata and self.metadata.status == "recording":
            raise RuntimeError("Recording already in progress. Call stop() first.")

        logger.info(f"🎬 Starting recording session: {self.session_name}")

        # Generate session ID and create output directory
        session_id = self._generate_session_id()
        session_dir = self._create_output_directory(session_id)

        # Initialize metadata
        self.metadata = SessionMetadata(
            session_id=session_id,
            session_name=self.session_name,
            url=url,
            start_time=datetime.now(),
            output_dir=session_dir,
            trace_file=session_dir / "trace.zip",
            events_file=session_dir / "events.json",
            correlation_file=session_dir / "correlation.json",
            traffic_path=session_dir / "traffic.json",
            status="recording",
        )

        # Save initial metadata
        self._save_metadata(self.metadata)

        # Start mitmproxy for network capture
        self._start_mitmproxy()

        # Start recorder based on mode
        recording_mode = self.recorder_options.recording_mode
        proxy_url = f"http://localhost:{self.proxy_port}"

        if recording_mode == "codegen":
            # Use codegen recorder for manual interaction capture
            logger.info("📝 Using codegen mode for manual interaction recording")
            codegen_options = CodegenOptions(
                viewport_width=self.recorder_options.viewport_width,
                viewport_height=self.recorder_options.viewport_height,
            )
            self.recorder = CodegenRecorder(codegen_options)
            await self.recorder.start_recording(url, proxy=proxy_url)
        else:
            # Use trace recorder (legacy mode)
            logger.info("🎥 Using trace mode for API call recording")
            self.recorder = TraceRecorder(self.recorder_options)
            await self.recorder.start_recording(url, proxy=proxy_url)

        logger.info("✅ Recording session started!")
        return self.metadata

    async def stop(self) -> SessionMetadata:
        """Stop recording session and save trace file.

        Stops the TraceRecorder, stops mitmproxy, finalizes session metadata,
        and saves the trace.zip file.

        Returns:
            Updated session metadata

        Raises:
            RuntimeError: If session has not been started
        """
        if not self.metadata or self.metadata.status != "recording":
            raise RuntimeError("Recording not started. Call start() first.")

        logger.info("⏹️  Stopping recording session...")

        # Stop recorder based on type
        if self.recorder:
            if isinstance(self.recorder, CodegenRecorder):
                # Codegen recorder returns dict with events and files
                result = await self.recorder.stop_recording()
                self._codegen_events = result['events']
                logger.info(f"   Captured {len(self._codegen_events)} codegen events")

                # Save trace file path if available (for hybrid mode)
                if result.get('trace_file'):
                    # Update metadata to point to the trace file from codegen
                    self.metadata.trace_file = Path(result['trace_file'])
                    logger.info(f"   Trace file: {self.metadata.trace_file}")

                # Save events to file
                import json
                with open(self.metadata.events_file, 'w', encoding='utf-8') as f:
                    json.dump({'events': self._codegen_events}, f, indent=2)
            else:
                # Trace recorder saves trace.zip
                await self.recorder.stop_recording(str(self.metadata.trace_file))

            self.recorder = None

        # Stop mitmproxy
        self._stop_mitmproxy()

        # Update metadata
        self.metadata.end_time = datetime.now()
        self.metadata.duration = (
            self.metadata.end_time - self.metadata.start_time
        ).total_seconds()
        self.metadata.status = "completed"

        # Save updated metadata
        self._save_metadata(self.metadata)

        logger.info("✅ Recording session stopped!")
        logger.info(f"   Duration: {self.metadata.duration:.1f}s")
        logger.info(f"   Trace: {self.metadata.trace_file}")
        logger.info(f"   Traffic: {self.metadata.traffic_path}")

        return self.metadata

    async def pause(self) -> None:
        """Pause recording session (if supported by Playwright).

        Note: Playwright tracing does not support pause/resume.
        This is a placeholder for future implementation.
        """
        raise NotImplementedError("Pause/resume not currently supported by Playwright tracing")

    async def resume(self) -> None:
        """Resume paused recording session (if supported by Playwright).

        Note: Playwright tracing does not support pause/resume.
        This is a placeholder for future implementation.
        """
        raise NotImplementedError("Pause/resume not currently supported by Playwright tracing")

    async def analyze(
        self,
        network_traffic_path: Optional[str] = None,
        correlation_options: Optional[CorrelationOptions] = None,
    ) -> SessionResult:
        """Analyze recorded session: parse events and correlate with network.

        Parses the trace file to extract UI events, and optionally correlates
        with network traffic if provided.

        Args:
            network_traffic_path: Path to mitmproxy traffic JSON (optional, uses session traffic if not provided)
            correlation_options: Options for EventCorrelator

        Returns:
            Complete session result with parsed events and correlations

        Raises:
            RuntimeError: If session has not been stopped
            FileNotFoundError: If trace file or network traffic file missing
        """
        if not self.metadata or self.metadata.status != "completed":
            raise RuntimeError("Session must be stopped before analysis. Call stop() first.")

        logger.info("📊 Analyzing recording session...")

        # Get events based on recording mode
        parse_result = None
        if self._codegen_events:
            # Events already extracted from codegen
            logger.info("   Using codegen events...")
            # Create a minimal parse result structure
            from dataclasses import dataclass
            @dataclass
            class CodegenParseResult:
                events: List
                stats: Dict[str, Any]

            parse_result = CodegenParseResult(
                events=self._codegen_events,
                stats={
                    'total_events': len(self._codegen_events),
                    'event_types': self._count_event_types(self._codegen_events),
                }
            )
            logger.info(f"   Found {len(self._codegen_events)} UI events")
        elif self.metadata.trace_file and self.metadata.trace_file.exists():
            # Parse trace file (legacy mode)
            logger.info("   Parsing trace file...")
            self.parser = TraceParser()
            parse_result = await self.parser.parse(str(self.metadata.trace_file))
            logger.info(f"   Found {len(parse_result.events)} UI events")
        else:
            logger.warning("   No events found (no trace file or codegen events)")

        # Correlate with network traffic if available
        correlation_result = None
        traffic_file = network_traffic_path or str(self.metadata.traffic_path)

        if traffic_file and Path(traffic_file).exists():
            logger.info("   Loading network traffic...")
            network_calls = load_mitmproxy_traffic(traffic_file)

            logger.info(f"   Found {len(network_calls)} network requests")
            logger.info("   Correlating events...")

            self.correlator = EventCorrelator(correlation_options or CorrelationOptions())
            correlation_result = self.correlator.correlate(parse_result.events, network_calls)

            logger.info(f"   Correlated {len(correlation_result.correlated_events)} events")
            logger.info(f"   Correlation rate: {correlation_result.stats['correlation_rate'] * 100:.1f}%")
        else:
            logger.warning("   No network traffic file found, skipping correlation")

        # Create session result
        result = SessionResult(
            metadata=self.metadata,
            parse_result=parse_result,
            correlation_result=correlation_result,
        )

        logger.info("✅ Analysis complete!")
        return result

    def save_results(self, result: SessionResult) -> None:
        """Save session results to disk.

        Saves parsed events, correlation results, and session metadata
        as JSON files in the output directory.

        Args:
            result: Complete session result
        """
        logger.info("💾 Saving session results...")

        # Save parsed events
        if result.parse_result:
            events_file = result.metadata.events_file
            with open(events_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"events": [asdict(e) for e in result.parse_result.events]},
                    f,
                    indent=2,
                )
            logger.info(f"   Events: {events_file}")

        # Save correlation results
        if result.correlation_result and self.correlator:
            correlation_file = result.metadata.correlation_file
            correlation_json = self.correlator.format_result(result.correlation_result)
            with open(correlation_file, "w", encoding="utf-8") as f:
                f.write(correlation_json)
            logger.info(f"   Correlation: {correlation_file}")

        # Update and save metadata
        self._save_metadata(result.metadata)
        logger.info(f"   Metadata: {result.metadata.output_dir / 'metadata.json'}")

        logger.info("✅ Results saved!")

    def load_session(self, session_id: str) -> SessionResult:
        """Load a previously recorded session.

        Loads session metadata and results from disk.

        Args:
            session_id: Session ID to load

        Returns:
            Complete session result

        Raises:
            FileNotFoundError: If session files not found
        """
        logger.info(f"📂 Loading session: {session_id}")

        # Load metadata
        metadata = self._load_metadata(session_id)

        # Load parsed events if available
        parse_result = None
        if metadata.events_file and metadata.events_file.exists():
            with open(metadata.events_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Note: Would need to reconstruct TraceTapEvent objects here
                # For now, just store raw data
                parse_result = data

        # Load correlation results if available
        correlation_result = None
        if metadata.correlation_file and metadata.correlation_file.exists():
            with open(metadata.correlation_file, "r", encoding="utf-8") as f:
                correlation_result = json.load(f)

        result = SessionResult(
            metadata=metadata,
            parse_result=parse_result,
            correlation_result=correlation_result,
        )

        logger.info("✅ Session loaded!")
        return result

    def list_sessions(self) -> List[SessionMetadata]:
        """List all recorded sessions in the output directory.

        Returns:
            List of session metadata for all sessions
        """
        sessions = []

        if not self.output_dir.exists():
            return sessions

        # Iterate through session directories
        for session_dir in self.output_dir.iterdir():
            if not session_dir.is_dir():
                continue

            metadata_file = session_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                metadata = self._load_metadata(session_dir.name)
                sessions.append(metadata)
            except Exception as e:
                logger.warning(f"Failed to load session {session_dir.name}: {e}")
                continue

        # Sort by start time (newest first)
        sessions.sort(key=lambda s: s.start_time, reverse=True)

        return sessions

    def delete_session(self, session_id: str) -> None:
        """Delete a recorded session and all its files.

        Args:
            session_id: Session ID to delete

        Raises:
            FileNotFoundError: If session not found
        """
        import shutil

        session_dir = self.output_dir / session_id

        if not session_dir.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        shutil.rmtree(session_dir)
        logger.info(f"Deleted session: {session_id}")

    def _start_mitmproxy(self) -> None:
        """Start mitmproxy process in background for network capture.

        Raises:
            RuntimeError: If mitmproxy fails to start
        """
        if self._mitm_process is not None:
            raise RuntimeError("mitmproxy already running")

        logger.info(f"🌐 Starting mitmproxy on port {self.proxy_port}...")

        # Get path to capture addon
        addon_path = Path(__file__).parent / "capture_addon.py"
        if not addon_path.exists():
            raise RuntimeError(f"Capture addon not found: {addon_path}")

        # Set environment variables for addon configuration
        self._mitm_output_path = self.metadata.traffic_path
        env = os.environ.copy()
        env["TRACETAP_RECORD_OUTPUT"] = str(self._mitm_output_path)
        env["TRACETAP_RECORD_SESSION"] = self.session_name
        env["TRACETAP_RECORD_QUIET"] = "true"

        # Build mitmproxy command
        cmd = [
            "mitmdump",
            "--listen-host", "0.0.0.0",
            "--listen-port", str(self.proxy_port),
            "--set", "ssl_insecure=true",
            "--set", "upstream_cert=false",
            "--quiet",
            "-s", str(addon_path),
        ]

        try:
            # Start mitmproxy in background
            self._mitm_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )

            # Wait a moment for mitmproxy to start
            import time
            time.sleep(2)

            # Check if process started successfully
            if self._mitm_process.poll() is not None:
                _, stderr = self._mitm_process.communicate()
                raise RuntimeError(f"mitmproxy failed to start: {stderr.decode()}")

            logger.info(f"   mitmproxy started (PID: {self._mitm_process.pid})")

        except FileNotFoundError:
            raise RuntimeError(
                "mitmproxy not found. Install with: pip install mitmproxy"
            )
        except Exception as e:
            if self._mitm_process:
                self._mitm_process.kill()
                self._mitm_process = None
            raise RuntimeError(f"Failed to start mitmproxy: {e}")

    def _stop_mitmproxy(self) -> None:
        """Stop mitmproxy process and save captured traffic."""
        if self._mitm_process is None:
            return

        logger.info("🛑 Stopping mitmproxy...")

        try:
            # Send SIGTERM to allow graceful shutdown (triggers done() callback)
            self._mitm_process.send_signal(signal.SIGTERM)

            # Wait for process to exit (with timeout)
            try:
                self._mitm_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't exit gracefully
                logger.warning("   Force killing mitmproxy (timeout)")
                self._mitm_process.kill()
                self._mitm_process.wait()

            logger.info("   mitmproxy stopped")

        except Exception as e:
            logger.error(f"Error stopping mitmproxy: {e}")
        finally:
            self._mitm_process = None

    def _generate_session_id(self) -> str:
        """Generate unique session ID.

        Returns:
            Unique session identifier
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}"

    def _create_output_directory(self, session_id: str) -> Path:
        """Create output directory structure for session.

        Args:
            session_id: Session identifier

        Returns:
            Path to session output directory
        """
        session_dir = self.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def _save_metadata(self, metadata: SessionMetadata) -> None:
        """Save session metadata to disk.

        Args:
            metadata: Session metadata to save
        """
        metadata_file = metadata.output_dir / "metadata.json"

        # Convert metadata to dict, handling Path objects
        metadata_dict = asdict(metadata)
        metadata_dict["start_time"] = metadata.start_time.isoformat()
        if metadata.end_time:
            metadata_dict["end_time"] = metadata.end_time.isoformat()

        # Convert Path objects to strings
        for key in ["output_dir", "trace_file", "events_file", "correlation_file", "traffic_path"]:
            if metadata_dict[key]:
                metadata_dict[key] = str(metadata_dict[key])

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata_dict, f, indent=2)

    def _load_metadata(self, session_id: str) -> SessionMetadata:
        """Load session metadata from disk.

        Args:
            session_id: Session identifier

        Returns:
            Session metadata

        Raises:
            FileNotFoundError: If metadata file not found
        """
        session_dir = self.output_dir / session_id
        metadata_file = session_dir / "metadata.json"

        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Convert strings back to Path objects
        for key in ["output_dir", "trace_file", "events_file", "correlation_file", "traffic_path"]:
            if data[key]:
                data[key] = Path(data[key])

        # Convert ISO strings back to datetime
        data["start_time"] = datetime.fromisoformat(data["start_time"])
        if data["end_time"]:
            data["end_time"] = datetime.fromisoformat(data["end_time"])

        return SessionMetadata(**data)

    def _count_event_types(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count event types from event list.

        Args:
            events: List of event dictionaries

        Returns:
            Dictionary mapping event type to count
        """
        type_counts = {}
        for event in events:
            event_type = event.get('apiName', 'unknown')
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        return type_counts
