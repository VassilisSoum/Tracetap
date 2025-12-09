"""
TraceTap Traffic Replayer

Core replay engine for captured HTTP traffic with metrics tracking and response comparison.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import common utilities
from ..common import CaptureLoader


@dataclass
class ReplayMetrics:
    """Metrics for a single replayed request."""

    original_url: str
    replayed_url: str
    original_status: int
    replayed_status: int
    original_duration_ms: int
    replayed_duration_ms: float
    status_match: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None

    @property
    def duration_diff_ms(self) -> float:
        """Calculate difference in response time."""
        return self.replayed_duration_ms - self.original_duration_ms

    @property
    def duration_diff_percent(self) -> float:
        """Calculate percentage change in response time."""
        if self.original_duration_ms == 0:
            return 0.0
        return ((self.replayed_duration_ms - self.original_duration_ms) /
                self.original_duration_ms) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['duration_diff_ms'] = self.duration_diff_ms
        data['duration_diff_percent'] = round(self.duration_diff_percent, 2)
        return data


@dataclass
class ReplayResult:
    """Results from a replay session."""

    total_requests: int
    successful_replays: int
    failed_replays: int
    status_matches: int
    status_mismatches: int
    total_duration_sec: float
    metrics: List[ReplayMetrics] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_replays / self.total_requests) * 100

    @property
    def status_match_rate(self) -> float:
        """Calculate status code match rate percentage."""
        if self.successful_replays == 0:
            return 0.0
        return (self.status_matches / self.successful_replays) * 100

    @property
    def avg_duration_ms(self) -> float:
        """Calculate average response time."""
        if not self.metrics:
            return 0.0
        return sum(m.replayed_duration_ms for m in self.metrics) / len(self.metrics)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'total_requests': self.total_requests,
            'successful_replays': self.successful_replays,
            'failed_replays': self.failed_replays,
            'status_matches': self.status_matches,
            'status_mismatches': self.status_mismatches,
            'total_duration_sec': round(self.total_duration_sec, 2),
            'success_rate': round(self.success_rate, 2),
            'status_match_rate': round(self.status_match_rate, 2),
            'avg_duration_ms': round(self.avg_duration_ms, 2),
            'metrics': [m.to_dict() for m in self.metrics]
        }


class TrafficReplayer:
    """
    Replay captured HTTP traffic with metrics tracking and response comparison.

    Features:
    - Load captures from TraceTap JSON logs
    - Replay requests with configurable target URL
    - Variable substitution (tokens, IDs, etc.)
    - Concurrent replay with thread pool
    - Response comparison (status codes, timing)
    - Detailed metrics tracking

    Example:
        replayer = TrafficReplayer('session.json')
        result = replayer.replay(target_base_url='http://localhost:3000')
        print(f"Success rate: {result.success_rate}%")
    """

    def __init__(
        self,
        log_file: str,
        timeout: int = 30,
        verify_ssl: bool = True,
        max_retries: int = 3
    ):
        """
        Initialize Traffic Replayer.

        Args:
            log_file: Path to TraceTap JSON log file
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retry attempts per request
        """
        self.log_file = Path(log_file)
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries

        # Load captures
        self.captures = self._load_captures()

        # Setup HTTP session with retry logic
        self.session = self._create_session()

    def _load_captures(self) -> List[Dict[str, Any]]:
        """Load captures from JSON log file using standardized loader."""
        loader = CaptureLoader(str(self.log_file))
        return loader.load()

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry configuration."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _replace_base_url(self, original_url: str, new_base_url: str) -> str:
        """
        Replace base URL while preserving path and query parameters.

        Args:
            original_url: Original URL from capture
            new_base_url: New base URL to use

        Returns:
            Modified URL with new base
        """
        from urllib.parse import urlparse, urlunparse

        original_parsed = urlparse(original_url)
        new_base_parsed = urlparse(new_base_url)

        # Combine new base with original path and query
        modified = urlunparse((
            new_base_parsed.scheme or original_parsed.scheme,
            new_base_parsed.netloc or original_parsed.netloc,
            original_parsed.path,
            original_parsed.params,
            original_parsed.query,
            original_parsed.fragment
        ))

        return modified

    def _replay_single(
        self,
        capture: Dict[str, Any],
        target_base_url: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None
    ) -> ReplayMetrics:
        """
        Replay a single captured request.

        Args:
            capture: Captured request/response data
            target_base_url: Optional base URL to override
            variables: Optional variable substitutions

        Returns:
            ReplayMetrics object with results
        """
        original_url = capture['url']
        original_status = capture.get('status', 0)
        original_duration = capture.get('duration_ms', 0)

        # Determine target URL
        if target_base_url:
            url = self._replace_base_url(original_url, target_base_url)
        else:
            url = original_url

        # Apply variable substitutions if provided
        if variables:
            for var_name, var_value in variables.items():
                url = url.replace(f"{{{var_name}}}", var_value)

        # Prepare request parameters
        method = capture.get('method', 'GET')
        headers = capture.get('req_headers', {})
        body = capture.get('req_body', '')

        # Remove headers that cause issues
        headers_to_remove = ['host', 'content-length', 'transfer-encoding']
        headers = {k: v for k, v in headers.items() if k.lower() not in headers_to_remove}

        # Track timing
        start_time = time.time()

        try:
            # Send request
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                data=body if body else None,
                timeout=self.timeout,
                verify=self.verify_ssl,
                allow_redirects=True
            )

            duration_ms = (time.time() - start_time) * 1000

            # Create metrics
            metrics = ReplayMetrics(
                original_url=original_url,
                replayed_url=url,
                original_status=original_status,
                replayed_status=response.status_code,
                original_duration_ms=original_duration,
                replayed_duration_ms=duration_ms,
                status_match=(response.status_code == original_status)
            )

            return metrics

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Create metrics with error
            metrics = ReplayMetrics(
                original_url=original_url,
                replayed_url=url,
                original_status=original_status,
                replayed_status=0,
                original_duration_ms=original_duration,
                replayed_duration_ms=duration_ms,
                status_match=False,
                error=str(e)
            )

            return metrics

    def replay(
        self,
        target_base_url: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        max_workers: int = 5,
        filter_fn: Optional[callable] = None,
        verbose: bool = False
    ) -> ReplayResult:
        """
        Replay all captured requests with optional filtering and concurrency.

        Args:
            target_base_url: Optional base URL to override (e.g., 'http://localhost:3000')
            variables: Optional variable substitutions (e.g., {'user_id': '123'})
            max_workers: Number of concurrent workers for replay
            filter_fn: Optional function to filter which requests to replay
            verbose: Print detailed progress information

        Returns:
            ReplayResult with metrics and summary
        """
        # Filter captures if filter function provided
        captures_to_replay = self.captures
        if filter_fn:
            captures_to_replay = [c for c in self.captures if filter_fn(c)]

        if verbose:
            print(f"Replaying {len(captures_to_replay)} requests...")
            if target_base_url:
                print(f"Target: {target_base_url}")
            if variables:
                print(f"Variables: {variables}")

        # Track results
        metrics_list = []
        successful = 0
        failed = 0
        status_matches = 0
        status_mismatches = 0

        start_time = time.time()

        # Replay with concurrency
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_capture = {
                executor.submit(
                    self._replay_single,
                    capture,
                    target_base_url,
                    variables
                ): capture
                for capture in captures_to_replay
            }

            # Process completed tasks
            for i, future in enumerate(as_completed(future_to_capture), 1):
                capture = future_to_capture[future]

                try:
                    metrics = future.result()
                    metrics_list.append(metrics)

                    if metrics.error:
                        failed += 1
                        if verbose:
                            print(f"[{i}/{len(captures_to_replay)}] ❌ {capture['method']} {capture['url']}: {metrics.error}")
                    else:
                        successful += 1
                        if metrics.status_match:
                            status_matches += 1
                        else:
                            status_mismatches += 1

                        if verbose:
                            status_icon = "✅" if metrics.status_match else "⚠️"
                            print(f"[{i}/{len(captures_to_replay)}] {status_icon} {capture['method']} {capture['url']} → {metrics.replayed_status} ({metrics.replayed_duration_ms:.0f}ms)")

                except Exception as e:
                    failed += 1
                    if verbose:
                        print(f"[{i}/{len(captures_to_replay)}] ❌ {capture['method']} {capture['url']}: Unexpected error: {e}")

        total_duration = time.time() - start_time

        # Build result
        result = ReplayResult(
            total_requests=len(captures_to_replay),
            successful_replays=successful,
            failed_replays=failed,
            status_matches=status_matches,
            status_mismatches=status_mismatches,
            total_duration_sec=total_duration,
            metrics=metrics_list
        )

        if verbose:
            print(f"\n📊 Replay Summary:")
            print(f"   Total: {result.total_requests}")
            print(f"   Successful: {result.successful_replays} ({result.success_rate:.1f}%)")
            print(f"   Failed: {result.failed_replays}")
            print(f"   Status matches: {result.status_matches} ({result.status_match_rate:.1f}%)")
            print(f"   Duration: {result.total_duration_sec:.2f}s")
            print(f"   Avg response time: {result.avg_duration_ms:.0f}ms")

        return result

    def save_result(self, result: ReplayResult, output_file: str):
        """
        Save replay results to JSON file.

        Args:
            result: ReplayResult to save
            output_file: Path to output JSON file
        """
        with open(output_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        print(f"✅ Saved replay results to {output_file}")
