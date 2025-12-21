"""
TraceTap Mock Server

FastAPI-based HTTP mock server that serves responses from captured traffic.

Features:
- Request matching (exact, fuzzy, pattern-based)
- Response serving from captures
- Chaos engineering (delays, errors, failures)
- Admin API for runtime configuration
- Metrics and logging
"""

from __future__ import annotations  # Enable forward references for type hints

import json
import re
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import logging

try:
    from fastapi import FastAPI, Request, Response, HTTPException
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from .matcher import RequestMatcher, MatchResult
from .generator import ResponseGenerator

# Import common utilities
from ..common import CaptureLoader


@dataclass
class MockConfig:
    """Configuration for mock server behavior."""

    # Matching strategy
    matching_strategy: str = "fuzzy"  # exact, fuzzy, pattern
    match_query_params: bool = True
    match_headers: bool = False
    match_body: bool = False

    # Response behavior
    add_delay_ms: int = 0  # Fixed delay in milliseconds
    random_delay_range: tuple = (0, 0)  # (min_ms, max_ms) for random delays
    response_mode: str = "static"  # static, template, transform, ai, intelligent

    # AI features
    ai_enabled: bool = False  # Enable AI-powered features
    ai_api_key: Optional[str] = None  # Anthropic API key for AI features

    # Request recording
    recording_enabled: bool = False  # Record incoming requests during mock operation
    recording_limit: int = 1000  # Maximum number of requests to record (0 = unlimited)

    # Request diff tracking
    diff_enabled: bool = False  # Track diffs for failed/low-score matches
    diff_threshold: float = 0.8  # Show diff if match score below this (0.0-1.0)
    diff_limit: int = 100  # Maximum number of diffs to store (0 = unlimited)

    # Match result caching
    cache_enabled: bool = True  # Enable match result caching for performance
    cache_max_size: int = 1000  # Maximum cache entries (FIFO eviction when full)

    # Chaos engineering
    chaos_enabled: bool = False
    chaos_failure_rate: float = 0.0  # 0.0 to 1.0
    chaos_error_status: int = 500

    # Fallback behavior
    fallback_status: int = 404
    fallback_body: str = '{"error": "No matching request found in captures"}'

    # Server options
    host: str = "127.0.0.1"
    port: int = 8080
    log_level: str = "info"
    verbose_mode: bool = False  # Show detailed request/match info in console

    # Admin API
    admin_enabled: bool = True
    admin_prefix: str = "/__admin__"


@dataclass
class MockMetrics:
    """Track mock server metrics."""

    total_requests: int = 0
    matched_requests: int = 0
    unmatched_requests: int = 0
    chaos_failures: int = 0
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        uptime_seconds = (datetime.now() - datetime.fromisoformat(self.start_time)).total_seconds()
        return {
            'total_requests': self.total_requests,
            'matched_requests': self.matched_requests,
            'unmatched_requests': self.unmatched_requests,
            'chaos_failures': self.chaos_failures,
            'match_rate': round((self.matched_requests / self.total_requests * 100) if self.total_requests > 0 else 0, 2),
            'uptime_seconds': round(uptime_seconds, 2),
            'start_time': self.start_time
        }


class MockServer:
    """
    FastAPI-based mock server for serving captured HTTP traffic.

    Loads captured requests/responses from TraceTap JSON logs and serves
    matching responses for incoming requests.

    Example:
        # Load captures and start server
        server = MockServer('session.json')
        server.start(host='0.0.0.0', port=8080)

        # With custom config
        config = MockConfig(
            matching_strategy='fuzzy',
            add_delay_ms=100,
            chaos_enabled=True,
            chaos_failure_rate=0.1
        )
        server = MockServer('session.json', config=config)
        server.start()
    """

    def __init__(
        self,
        log_file: str,
        config: Optional[MockConfig] = None,
        request_matcher: Optional[Any] = None,
        response_generator: Optional[Any] = None
    ):
        """
        Initialize mock server.

        Args:
            log_file: Path to TraceTap JSON log file with captures
            config: Optional MockConfig for server behavior
            request_matcher: Optional RequestMatcher instance (will create if None)
            response_generator: Optional ResponseGenerator instance (will create if None)
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI is required for mock server. Install with: pip install fastapi uvicorn")

        self.log_file = Path(log_file)
        self.config = config or MockConfig()
        self.metrics = MockMetrics()
        self.recorded_requests: List[Dict[str, Any]] = []  # Store recorded requests
        self.request_diffs: List[Dict[str, Any]] = []  # Store request diffs for debugging
        self.live_requests: List[Dict[str, Any]] = []  # Store recent requests for live dashboard
        self.live_requests_limit = 100  # Keep last 100 requests

        # Setup logging first (before loading captures)
        self.logger = logging.getLogger("tracetap.mock")
        self.logger.setLevel(getattr(logging, self.config.log_level.upper()))

        # Load captures
        self.captures = self._load_captures()

        # Initialize matcher and generator
        self.matcher = request_matcher or RequestMatcher(
            captures=self.captures,
            strategy=self.config.matching_strategy,
            min_score=0.7,
            api_key=self.config.ai_api_key if self.config.ai_enabled else None,
            cache_enabled=self.config.cache_enabled,
            cache_max_size=self.config.cache_max_size
        )
        self.generator = response_generator or ResponseGenerator(
            use_ai=self.config.ai_enabled,
            api_key=self.config.ai_api_key
        )

        # Setup FastAPI app
        self.app = self._create_app()

    def _load_captures(self) -> List[Dict[str, Any]]:
        """Load captures from JSON log file using standardized loader."""
        loader = CaptureLoader(str(self.log_file))
        captures = loader.load()
        self.logger.info(f"Loaded {len(captures)} captures from {self.log_file}")
        return captures

    def _create_app(self) -> FastAPI:
        """Create FastAPI application with routes."""
        app = FastAPI(
            title="TraceTap Mock Server",
            description="Mock HTTP server serving captured traffic responses",
            version="1.0.0"
        )

        # Admin API routes
        if self.config.admin_enabled:
            @app.get(f"{self.config.admin_prefix}/metrics")
            async def get_metrics():
                """Get server metrics."""
                return JSONResponse(content=self.metrics.to_dict())

            @app.get(f"{self.config.admin_prefix}/live")
            async def get_live_requests():
                """Get recent requests with match details for live debugging."""
                return JSONResponse(content={
                    'total': len(self.live_requests),
                    'limit': self.live_requests_limit,
                    'requests': list(reversed(self.live_requests))  # Most recent first
                })

            @app.get(f"{self.config.admin_prefix}/config")
            async def get_config():
                """Get current configuration."""
                return JSONResponse(content={
                    'matching_strategy': self.config.matching_strategy,
                    'add_delay_ms': self.config.add_delay_ms,
                    'chaos_enabled': self.config.chaos_enabled,
                    'chaos_failure_rate': self.config.chaos_failure_rate,
                    'total_captures': len(self.captures)
                })

            @app.post(f"{self.config.admin_prefix}/config")
            async def update_config(request: Request):
                """Update configuration at runtime."""
                body = await request.json()

                if 'matching_strategy' in body:
                    self.config.matching_strategy = body['matching_strategy']
                if 'add_delay_ms' in body:
                    self.config.add_delay_ms = int(body['add_delay_ms'])
                if 'chaos_enabled' in body:
                    self.config.chaos_enabled = bool(body['chaos_enabled'])
                if 'chaos_failure_rate' in body:
                    self.config.chaos_failure_rate = float(body['chaos_failure_rate'])

                return JSONResponse(content={'status': 'updated'})

            @app.get(f"{self.config.admin_prefix}/captures")
            async def list_captures():
                """List all captured requests."""
                captures_summary = [
                    {
                        'method': c.get('method'),
                        'url': c.get('url'),
                        'status': c.get('status'),
                        'timestamp': c.get('timestamp')
                    }
                    for c in self.captures
                ]
                return JSONResponse(content={
                    'total': len(captures_summary),
                    'captures': captures_summary
                })

            @app.post(f"{self.config.admin_prefix}/reset")
            async def reset_metrics():
                """Reset metrics."""
                self.metrics = MockMetrics()
                return JSONResponse(content={'status': 'reset'})

            @app.get(f"{self.config.admin_prefix}/recordings")
            async def get_recordings():
                """Get all recorded requests."""
                return JSONResponse(content={
                    'total': len(self.recorded_requests),
                    'limit': self.config.recording_limit,
                    'recording_enabled': self.config.recording_enabled,
                    'recordings': self.recorded_requests
                })

            @app.delete(f"{self.config.admin_prefix}/recordings")
            async def clear_recordings():
                """Clear all recorded requests."""
                count = len(self.recorded_requests)
                self.recorded_requests.clear()
                return JSONResponse(content={
                    'status': 'cleared',
                    'cleared_count': count
                })

            @app.get(f"{self.config.admin_prefix}/recordings/export")
            async def export_recordings():
                """Export recordings in TraceTap JSON format."""
                # Format recordings as TraceTap log format
                export_data = {
                    'session': 'mock-server-recording',
                    'timestamp': datetime.now().isoformat(),
                    'requests': [
                        {
                            'method': r['method'],
                            'url': r['url'],
                            'req_headers': r['headers'],
                            'req_body': r['body'],
                            'status': r['response_status'],
                            'resp_body': r['response_body'],
                            'timestamp': r['timestamp'],
                            'matched': r['matched'],
                            'matched_url': r['matched_url']
                        }
                        for r in self.recorded_requests
                    ]
                }
                return JSONResponse(content=export_data)

            @app.get(f"{self.config.admin_prefix}/diffs")
            async def get_diffs():
                """Get all tracked request diffs."""
                return JSONResponse(content={
                    'total': len(self.request_diffs),
                    'limit': self.config.diff_limit,
                    'threshold': self.config.diff_threshold,
                    'diff_enabled': self.config.diff_enabled,
                    'diffs': self.request_diffs
                })

            @app.delete(f"{self.config.admin_prefix}/diffs")
            async def clear_diffs():
                """Clear all tracked request diffs."""
                count = len(self.request_diffs)
                self.request_diffs.clear()
                return JSONResponse(content={
                    'status': 'cleared',
                    'cleared_count': count
                })

            @app.get(f"{self.config.admin_prefix}/diffs/latest")
            async def get_latest_diff():
                """Get the most recent diff."""
                if not self.request_diffs:
                    return JSONResponse(
                        content={'error': 'No diffs available'},
                        status_code=404
                    )
                return JSONResponse(content=self.request_diffs[-1])

            @app.post(f"{self.config.admin_prefix}/replay")
            async def replay_recordings(request: Request):
                """
                Replay recorded requests for regression testing.

                POST body can be:
                - {"indices": [0, 1, 2]} - Replay specific recordings by index
                - {"all": true} - Replay all recordings
                - Empty body - Replay all recordings

                Returns summary of replay results.
                """
                import httpx

                try:
                    body = await request.json()
                except:
                    body = {}

                # Determine which recordings to replay
                if 'indices' in body:
                    indices = body['indices']
                    to_replay = [self.recorded_requests[i] for i in indices if 0 <= i < len(self.recorded_requests)]
                else:
                    # Replay all
                    to_replay = self.recorded_requests

                if not to_replay:
                    return JSONResponse(content={
                        'error': 'No recordings to replay',
                        'total_recordings': len(self.recorded_requests)
                    }, status_code=400)

                # Replay each request
                results = []
                async with httpx.AsyncClient(timeout=30.0) as client:
                    for i, recording in enumerate(to_replay):
                        try:
                            # Reconstruct URL (use localhost for mock server)
                            url = f"http://{self.config.host}:{self.config.port}{recording['url'].split('/', 3)[3] if recording['url'].count('/') >= 3 else '/'}"

                            # Make request
                            response = await client.request(
                                method=recording['method'],
                                url=url,
                                headers={k: v for k, v in recording.get('headers', {}).items() if k.lower() not in ['host', 'content-length']},
                                content=recording.get('body', '').encode() if isinstance(recording.get('body'), str) else recording.get('body', b'')
                            )

                            # Compare with original
                            results.append({
                                'index': i,
                                'method': recording['method'],
                                'url': recording['url'],
                                'original_status': recording.get('response_status'),
                                'replay_status': response.status_code,
                                'status_match': recording.get('response_status') == response.status_code,
                                'success': True
                            })
                        except Exception as e:
                            results.append({
                                'index': i,
                                'method': recording.get('method'),
                                'url': recording.get('url'),
                                'success': False,
                                'error': str(e)
                            })

                # Generate summary
                successful = sum(1 for r in results if r.get('success'))
                status_matches = sum(1 for r in results if r.get('status_match'))

                return JSONResponse(content={
                    'total_replayed': len(results),
                    'successful': successful,
                    'failed': len(results) - successful,
                    'status_matches': status_matches,
                    'status_mismatches': successful - status_matches,
                    'results': results
                })

            @app.get(f"{self.config.admin_prefix}/cache")
            async def get_cache_stats():
                """Get cache statistics and configuration."""
                return JSONResponse(content={
                    'enabled': self.config.cache_enabled,
                    'max_size': self.config.cache_max_size,
                    'current_size': len(self.matcher.cache),
                    'hits': self.matcher.cache_hits,
                    'misses': self.matcher.cache_misses,
                    'hit_rate': self.matcher.cache_hits / (self.matcher.cache_hits + self.matcher.cache_misses) if (self.matcher.cache_hits + self.matcher.cache_misses) > 0 else 0.0
                })

            @app.delete(f"{self.config.admin_prefix}/cache")
            async def clear_cache():
                """Clear the match result cache."""
                size_before = len(self.matcher.cache)
                self.matcher.cache.clear()
                self.matcher.cache_hits = 0
                self.matcher.cache_misses = 0
                return JSONResponse(content={
                    'status': 'cleared',
                    'entries_cleared': size_before
                })

        # Main catch-all route for mocking
        @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
        async def mock_request(request: Request, path: str):
            """Handle incoming requests and serve mock responses."""
            return await self._handle_request(request, path)

        return app

    async def _handle_request(self, request: Request, path: str) -> Response:
        """
        Handle incoming request and serve mock response.

        Args:
            request: FastAPI Request object
            path: Request path

        Returns:
            FastAPI Response with mocked data
        """
        import time
        from datetime import datetime

        start_time = time.time()
        self.metrics.total_requests += 1

        # Extract request details
        method = request.method
        url = str(request.url)
        headers = dict(request.headers)
        body = await request.body()

        self.logger.debug(f"Incoming: {method} {url}")

        # Verbose logging - request start
        if self.config.verbose_mode:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {method} {url}")

        # Apply chaos engineering if enabled
        if self.config.chaos_enabled:
            if self._should_trigger_chaos():
                self.metrics.chaos_failures += 1
                self.logger.warning(f"Chaos failure triggered for {method} {url}")
                return Response(
                    content=json.dumps({"error": "Chaos engineering failure"}),
                    status_code=self.config.chaos_error_status,
                    media_type="application/json"
                )

        # Apply delay if configured
        await self._apply_delay()

        # Track cache state before matching to detect cache hits
        cache_hits_before = self.matcher.cache_hits if self.config.cache_enabled else 0

        # Find matching capture (get full match result for diff tracking)
        match_result = self.matcher.find_match(method, url, headers, body)
        matched_capture = match_result.capture if match_result.matched else None

        # Detect if this was a cache hit
        cache_hit = False
        if self.config.cache_enabled:
            cache_hit = self.matcher.cache_hits > cache_hits_before

        # Extract request context for template mode
        request_context = self._extract_request_context(url, body)

        # Verbose logging - match details
        if self.config.verbose_mode:
            if matched_capture:
                matched_url = matched_capture.get('url', 'unknown')
                score = match_result.score.total_score if match_result.score else 1.0
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Matched: {matched_url} (score: {score:.3f})")

                if match_result.score and score < 0.9:
                    # Show score breakdown for non-perfect matches
                    print(f"[{datetime.now().strftime('%H:%M:%S')}]     Path: {match_result.score.path_score:.2f} | Query: {match_result.score.query_score:.2f} | Headers: {match_result.score.header_score:.2f} | Body: {match_result.score.body_score:.2f}")

                if cache_hit:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}]   💾 Cache HIT")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ No match found")

        # Track diff if enabled and match quality is poor
        if self.config.diff_enabled:
            should_track_diff = False
            best_match_for_diff = None

            if not match_result.matched:
                # No match found - track diff against best candidate
                should_track_diff = True
                # Try to find best candidate even if below threshold
                best_match_for_diff = self._find_best_candidate(method, url, headers, body)
            elif match_result.score and match_result.score.total_score < self.config.diff_threshold:
                # Match found but score is low - track diff
                should_track_diff = True
                best_match_for_diff = matched_capture

            if should_track_diff and best_match_for_diff:
                self._track_diff(
                    incoming_method=method,
                    incoming_url=url,
                    incoming_headers=headers,
                    incoming_body=body,
                    matched_capture=best_match_for_diff,
                    match_score=match_result.score.total_score if match_result.score else 0.0,
                    match_reason=match_result.reason
                )

                # Real-time diff notification to console
                timestamp = datetime.now().strftime("%H:%M:%S")
                score = match_result.score.total_score if match_result.score else 0.0

                if not match_result.matched:
                    print(f"\n[{timestamp}] ⚠️  No match found for {method} {url}")
                    print(f"[{timestamp}]   Best candidate: {best_match_for_diff.get('url', 'unknown')}")
                    print(f"[{timestamp}]   See full diff: http://{self.config.host}:{self.config.port}{self.config.admin_prefix}/diffs/latest\n")
                else:
                    print(f"\n[{timestamp}] ⚠️  Low match score ({score:.2f}) for {method} {url}")
                    print(f"[{timestamp}]   Matched: {best_match_for_diff.get('url', 'unknown')}")
                    print(f"[{timestamp}]   Reason: {match_result.reason}")
                    print(f"[{timestamp}]   Threshold: {self.config.diff_threshold:.2f}")
                    print(f"[{timestamp}]   See full diff: http://{self.config.host}:{self.config.port}{self.config.admin_prefix}/diffs/latest\n")

        # Generate response
        if matched_capture:
            self.metrics.matched_requests += 1
            response = self._create_response(
                matched_capture,
                request_context=request_context,
                match_score=match_result.score.total_score if match_result.score else None,
                matched_url=matched_capture.get('url'),
                cache_hit=cache_hit
            )
            response_status = response.status_code
            response_body = response.body
        else:
            self.metrics.unmatched_requests += 1
            self.logger.warning(f"No match found for {method} {url}")

            # Generate helpful fallback response with debugging info
            fallback_content = self._create_enhanced_fallback(method, url, headers, body)

            response = Response(
                content=json.dumps(fallback_content) if isinstance(fallback_content, dict) else fallback_content,
                status_code=self.config.fallback_status,
                media_type="application/json",
                headers={
                    'X-TraceTap-Matched': 'false',
                    'X-TraceTap-Strategy': self.config.matching_strategy
                }
            )
            response_status = response.status_code
            response_body = response.body

        # Record request if recording is enabled
        if self.config.recording_enabled:
            self._record_request(
                method=method,
                url=url,
                headers=headers,
                body=body,
                matched=bool(matched_capture),
                matched_url=matched_capture.get('url') if matched_capture else None,
                response_status=response_status,
                response_body=response_body
            )

        # Calculate timing
        elapsed_ms = (time.time() - start_time) * 1000

        # Verbose logging - response details
        if self.config.verbose_mode:
            status_emoji = "✓" if 200 <= response_status < 300 else "✗"
            print(f"[{datetime.now().strftime('%H:%M:%S')}]   {status_emoji} Response: {response_status} ({elapsed_ms:.1f}ms)")

        # Track request for live dashboard (FIFO with limit)
        if len(self.live_requests) >= self.live_requests_limit:
            self.live_requests.pop(0)

        live_entry = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'url': url,
            'matched': bool(matched_capture),
            'response_status': response_status,
            'response_time_ms': round(elapsed_ms, 2),
            'cache_hit': cache_hit
        }

        if matched_capture and match_result.score:
            live_entry['match_score'] = round(match_result.score.total_score, 3)
            live_entry['match_breakdown'] = {
                'path': round(match_result.score.path_score, 2),
                'query': round(match_result.score.query_score, 2),
                'headers': round(match_result.score.header_score, 2),
                'body': round(match_result.score.body_score, 2)
            }
            live_entry['matched_url'] = matched_capture.get('url')

        self.live_requests.append(live_entry)

        return response

    def _create_response(
        self,
        capture: Dict[str, Any],
        request_context: Optional[Dict[str, Any]] = None,
        match_score: Optional[float] = None,
        matched_url: Optional[str] = None,
        cache_hit: bool = False
    ) -> Response:
        """
        Create FastAPI Response from captured response.

        Args:
            capture: Captured request/response data
            request_context: Context variables for template substitution
            match_score: Match score (0.0 to 1.0) for debugging
            matched_url: Original URL of the matched capture
            cache_hit: Whether this was served from cache

        Returns:
            FastAPI Response object with TraceTap debug headers
        """
        # Use generator to create response (uses configured mode: static, template, transform, ai, intelligent)
        generated = self.generator.generate(capture, request_context, mode=self.config.response_mode)

        # Extract response data
        status_code = generated.get('status', 200)
        response_headers = generated.get('resp_headers', {})
        response_body = generated.get('resp_body', '')

        # Filter headers that FastAPI shouldn't set manually
        headers_to_skip = {'content-length', 'transfer-encoding', 'connection'}
        filtered_headers = {
            k: v for k, v in response_headers.items()
            if k.lower() not in headers_to_skip
        }

        # Add TraceTap debug headers for developer visibility
        if match_score is not None:
            filtered_headers['X-TraceTap-Match-Score'] = f"{match_score:.3f}"

        if matched_url:
            filtered_headers['X-TraceTap-Matched-URL'] = matched_url

        filtered_headers['X-TraceTap-Cache-Hit'] = 'true' if cache_hit else 'false'
        filtered_headers['X-TraceTap-Strategy'] = self.config.matching_strategy

        # Determine media type
        content_type = response_headers.get('content-type',
                                           response_headers.get('Content-Type',
                                                               'application/json'))

        # Create response
        return Response(
            content=response_body if isinstance(response_body, (bytes, str)) else json.dumps(response_body),
            status_code=status_code,
            headers=filtered_headers,
            media_type=content_type
        )

    async def _apply_delay(self):
        """Apply configured delay to response."""
        # Apply random delay if configured, otherwise apply fixed delay
        if self.config.random_delay_range[1] > 0:
            import random
            delay_ms = random.randint(
                self.config.random_delay_range[0],
                self.config.random_delay_range[1]
            )
            await asyncio.sleep(delay_ms / 1000)
        elif self.config.add_delay_ms > 0:
            await asyncio.sleep(self.config.add_delay_ms / 1000)

    def _should_trigger_chaos(self) -> bool:
        """Determine if chaos engineering should trigger."""
        import random
        return random.random() < self.config.chaos_failure_rate

    def _extract_request_context(self, url: str, body: bytes) -> Dict[str, Any]:
        """
        Extract context from incoming request for template variable substitution.

        Extracts:
        - Query parameters from URL
        - Path parameters (numeric IDs, UUIDs) from URL path
        - JSON body fields (if valid JSON)

        Args:
            url: Full request URL
            body: Request body bytes

        Returns:
            Dictionary of context variables for template substitution
        """
        context = {}

        # Parse URL
        parsed = urlparse(url)

        # Extract query parameters
        query_params = parse_qs(parsed.query)
        for key, values in query_params.items():
            # Use first value if single, otherwise use list
            context[key] = values[0] if len(values) == 1 else values

        # Extract path parameters (numeric IDs and UUIDs)
        path_parts = [p for p in parsed.path.split('/') if p]
        for part in path_parts:
            # Detect numeric IDs
            if part.isdigit():
                context['id'] = part
            # Detect UUIDs (simple pattern match)
            elif re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', part, re.I):
                context['uuid'] = part

        # Parse JSON body and add fields to context
        if body:
            try:
                body_json = json.loads(body)
                if isinstance(body_json, dict):
                    # Add all body fields to context
                    context.update(body_json)
            except (json.JSONDecodeError, TypeError):
                # Not JSON or invalid, skip body parsing
                pass

        return context

    def _record_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: bytes,
        matched: bool,
        matched_url: Optional[str],
        response_status: int,
        response_body: Any
    ):
        """
        Record an incoming request for later analysis.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            matched: Whether a capture was matched
            matched_url: URL of matched capture (if any)
            response_status: Response status code
            response_body: Response body
        """
        # Apply recording limit
        if self.config.recording_limit > 0 and len(self.recorded_requests) >= self.config.recording_limit:
            # Remove oldest request (FIFO)
            self.recorded_requests.pop(0)

        # Decode body if bytes
        try:
            body_str = body.decode('utf-8') if isinstance(body, bytes) else str(body)
        except:
            body_str = "[binary data]"

        # Decode response body if bytes
        try:
            if isinstance(response_body, bytes):
                response_body_str = response_body.decode('utf-8')
            else:
                response_body_str = str(response_body) if response_body else ""
        except:
            response_body_str = "[binary data]"

        # Create recording
        recording = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'url': url,
            'headers': dict(headers),
            'body': body_str,
            'matched': matched,
            'matched_url': matched_url,
            'response_status': response_status,
            'response_body': response_body_str
        }

        self.recorded_requests.append(recording)
        self.logger.debug(f"Recorded request: {method} {url} (matched: {matched})")

    def _create_enhanced_fallback(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: bytes
    ) -> Dict[str, Any]:
        """
        Create enhanced fallback response with debugging information.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body

        Returns:
            Dict with error info, closest matches, and suggestions
        """
        from urllib.parse import urlparse

        parsed_url = urlparse(url)

        # Try to find closest matches for debugging
        closest_matches = []

        # Get captures with same method
        method_captures = [c for c in self.captures if c.get('method') == method]

        if method_captures:
            # Score each capture to find closest ones using simple path similarity
            scored_captures = []

            path_parts = [p for p in parsed_url.path.split('/') if p]

            for capture in method_captures[:50]:  # Limit for performance
                cap_url = capture.get('url', '')
                cap_parsed = urlparse(cap_url)
                cap_path_parts = [p for p in cap_parsed.path.split('/') if p]

                # Calculate simple path similarity
                if len(path_parts) == len(cap_path_parts) and path_parts:
                    matching_parts = sum(1 for p1, p2 in zip(path_parts, cap_path_parts) if p1 == p2 or self.matcher._is_likely_id(p1) and self.matcher._is_likely_id(p2))
                    score = matching_parts / len(path_parts)
                elif path_parts and cap_path_parts:
                    # Different lengths - use prefix matching
                    min_len = min(len(path_parts), len(cap_path_parts))
                    matching_parts = sum(1 for p1, p2 in zip(path_parts[:min_len], cap_path_parts[:min_len]) if p1 == p2 or self.matcher._is_likely_id(p1) and self.matcher._is_likely_id(p2))
                    score = matching_parts / max(len(path_parts), len(cap_path_parts))
                else:
                    score = 0.0

                # Determine main reason for low score
                reasons = []

                if score < 0.3:
                    reasons.append(f"Path structure differs ({parsed_url.path} vs {cap_parsed.path})")
                elif score < 0.7:
                    reasons.append(f"Path partially matches (score {score:.2f})")
                else:
                    reasons.append(f"Path similar but score {score:.2f} below threshold {self.matcher.min_score:.2f}")

                if parsed_url.query != cap_parsed.query:
                    reasons.append("Query parameters differ")

                scored_captures.append({
                    'url': cap_url,
                    'score': score,
                    'reason': reasons[0] if reasons else "Unknown"
                })

            # Sort by score and take top 3
            scored_captures.sort(key=lambda x: x['score'], reverse=True)
            closest_matches = scored_captures[:3]

        # Generate suggestions based on the situation
        suggestions = []

        if not self.captures:
            suggestions.append("No captures loaded - check your capture file path")
        elif not method_captures:
            available_methods = list(set(c.get('method', 'GET') for c in self.captures))
            suggestions.append(f"No captures with method {method}. Available methods: {', '.join(available_methods)}")
        else:
            # Analyze common issues
            if closest_matches and closest_matches[0]['score'] > 0.6:
                suggestions.append(f"Close match found (score {closest_matches[0]['score']:.2f}). Try lowering min_score threshold or use --strategy fuzzy")

            if self.config.matching_strategy == 'exact':
                suggestions.append("Using 'exact' matching - try --strategy fuzzy for flexible ID matching")
            elif self.config.matching_strategy == 'fuzzy' and not self.config.ai_enabled:
                suggestions.append("Try --strategy semantic --ai for AI-powered intent matching")

            if '/id' in parsed_url.path or any(c.isdigit() for c in parsed_url.path):
                suggestions.append("Path contains IDs/numbers - fuzzy/semantic matching works better with dynamic IDs")

            if not suggestions:
                suggestions.append("Check if request URL, method, and parameters match captured traffic")
                suggestions.append("Enable --record to capture this request for future matching")

        # Build response
        response = {
            "error": "No matching request found in captures",
            "request": {
                "method": method,
                "url": url,
                "path": parsed_url.path
            },
            "debug": {
                "total_captures": len(self.captures),
                "captures_with_method": len(method_captures),
                "matching_strategy": self.config.matching_strategy,
                "min_score_threshold": self.matcher.min_score
            }
        }

        if closest_matches:
            response["closest_matches"] = closest_matches

        if suggestions:
            response["suggestions"] = suggestions

        return response

    def _find_best_candidate(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Find best matching capture even if below threshold (for diff comparison).

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body

        Returns:
            Best matching capture or None
        """
        # Try to find captures with same method first
        method_matches = [c for c in self.captures if c.get('method') == method]

        if method_matches:
            # Use fuzzy matching on method_matches to find best
            from urllib.parse import urlparse
            parsed_url = urlparse(url)

            best_score = 0.0
            best_capture = None

            for capture in method_matches[:20]:  # Limit to first 20 for performance
                cap_url = capture.get('url', '')
                cap_parsed = urlparse(cap_url)

                # Simple path similarity
                path_parts = [p for p in parsed_url.path.split('/') if p]
                cap_path_parts = [p for p in cap_parsed.path.split('/') if p]

                if len(path_parts) == len(cap_path_parts):
                    # Same path length - good candidate
                    matching_parts = sum(1 for p1, p2 in zip(path_parts, cap_path_parts) if p1 == p2)
                    score = matching_parts / max(len(path_parts), 1)

                    if score > best_score:
                        best_score = score
                        best_capture = capture

            if best_capture:
                return best_capture

        # Fallback: return first capture with same method, or just first capture
        return method_matches[0] if method_matches else (self.captures[0] if self.captures else None)

    def _track_diff(
        self,
        incoming_method: str,
        incoming_url: str,
        incoming_headers: Dict[str, str],
        incoming_body: bytes,
        matched_capture: Dict[str, Any],
        match_score: float,
        match_reason: str
    ):
        """
        Calculate and track diff between incoming request and matched capture.

        Args:
            incoming_method: Incoming request method
            incoming_url: Incoming request URL
            incoming_headers: Incoming request headers
            incoming_body: Incoming request body
            matched_capture: Best matching capture
            match_score: Match score (0.0-1.0)
            match_reason: Reason for match/no-match
        """
        from urllib.parse import urlparse, parse_qs
        import difflib

        # Apply diff limit
        if self.config.diff_limit > 0 and len(self.request_diffs) >= self.config.diff_limit:
            # Remove oldest diff (FIFO)
            self.request_diffs.pop(0)

        # Parse URLs
        incoming_parsed = urlparse(incoming_url)
        matched_parsed = urlparse(matched_capture.get('url', ''))

        # Decode bodies
        try:
            incoming_body_str = incoming_body.decode('utf-8') if isinstance(incoming_body, bytes) else str(incoming_body)
        except:
            incoming_body_str = "[binary data]"

        matched_body = matched_capture.get('req_body', '')

        # Calculate path diff
        incoming_path = incoming_parsed.path or '/'
        matched_path = matched_parsed.path or '/'

        path_diff = {
            'incoming': incoming_path,
            'matched': matched_path,
            'differs': incoming_path != matched_path
        }

        if path_diff['differs']:
            # Show path component differences
            incoming_parts = [p for p in incoming_path.split('/') if p]
            matched_parts = [p for p in matched_path.split('/') if p]
            path_diff['incoming_parts'] = incoming_parts
            path_diff['matched_parts'] = matched_parts
            path_diff['part_diffs'] = [
                {'index': i, 'incoming': inc, 'matched': mat}
                for i, (inc, mat) in enumerate(zip(incoming_parts, matched_parts))
                if inc != mat
            ]

        # Calculate query param diff
        incoming_query = parse_qs(incoming_parsed.query or '')
        matched_query = parse_qs(matched_parsed.query or '')

        query_diff = {
            'incoming': dict(incoming_query),
            'matched': dict(matched_query),
            'added_params': list(set(incoming_query.keys()) - set(matched_query.keys())),
            'removed_params': list(set(matched_query.keys()) - set(incoming_query.keys())),
            'changed_params': [
                {'param': k, 'incoming': incoming_query[k], 'matched': matched_query[k]}
                for k in set(incoming_query.keys()) & set(matched_query.keys())
                if incoming_query[k] != matched_query[k]
            ]
        }

        # Calculate header diff (only interesting headers)
        interesting_headers = ['content-type', 'authorization', 'accept', 'x-api-key', 'x-auth-token']
        incoming_headers_filtered = {
            k.lower(): v for k, v in incoming_headers.items()
            if k.lower() in interesting_headers
        }
        matched_headers_filtered = {
            k.lower(): v for k, v in matched_capture.get('req_headers', {}).items()
            if k.lower() in interesting_headers
        }

        header_diff = {
            'incoming': incoming_headers_filtered,
            'matched': matched_headers_filtered,
            'added_headers': list(set(incoming_headers_filtered.keys()) - set(matched_headers_filtered.keys())),
            'removed_headers': list(set(matched_headers_filtered.keys()) - set(incoming_headers_filtered.keys())),
            'changed_headers': [
                {'header': k, 'incoming': incoming_headers_filtered[k], 'matched': matched_headers_filtered[k]}
                for k in set(incoming_headers_filtered.keys()) & set(matched_headers_filtered.keys())
                if incoming_headers_filtered[k] != matched_headers_filtered[k]
            ]
        }

        # Calculate body diff
        body_diff = {
            'incoming': incoming_body_str[:500] if incoming_body_str else '',
            'matched': matched_body[:500] if matched_body else '',
            'differs': incoming_body_str != matched_body
        }

        # Try to provide structured diff for JSON bodies
        if body_diff['differs']:
            try:
                incoming_json = json.loads(incoming_body_str) if incoming_body_str else {}
                matched_json = json.loads(matched_body) if matched_body else {}

                # Show key differences
                if isinstance(incoming_json, dict) and isinstance(matched_json, dict):
                    body_diff['added_keys'] = list(set(incoming_json.keys()) - set(matched_json.keys()))
                    body_diff['removed_keys'] = list(set(matched_json.keys()) - set(incoming_json.keys()))
                    body_diff['changed_keys'] = [
                        {'key': k, 'incoming': incoming_json[k], 'matched': matched_json[k]}
                        for k in set(incoming_json.keys()) & set(matched_json.keys())
                        if incoming_json[k] != matched_json[k]
                    ]
            except (json.JSONDecodeError, TypeError):
                # Not JSON or parsing failed - use line diff
                if incoming_body_str and matched_body:
                    incoming_lines = incoming_body_str.splitlines()
                    matched_lines = matched_body.splitlines()
                    diff_lines = list(difflib.unified_diff(
                        matched_lines,
                        incoming_lines,
                        fromfile='matched',
                        tofile='incoming',
                        lineterm=''
                    ))
                    body_diff['line_diff'] = diff_lines[:50]  # Limit to 50 lines

        # Create diff record
        diff_record = {
            'timestamp': datetime.now().isoformat(),
            'incoming_method': incoming_method,
            'incoming_url': incoming_url,
            'matched_url': matched_capture.get('url'),
            'match_score': match_score,
            'match_reason': match_reason,
            'method_differs': incoming_method != matched_capture.get('method'),
            'path_diff': path_diff,
            'query_diff': query_diff,
            'header_diff': header_diff,
            'body_diff': body_diff
        }

        self.request_diffs.append(diff_record)
        self.logger.debug(f"Tracked diff for: {incoming_method} {incoming_url} (score: {match_score:.2f})")

    def start(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        reload: bool = False,
        access_log: bool = True
    ):
        """
        Start the mock server.

        Args:
            host: Host to bind to (overrides config)
            port: Port to bind to (overrides config)
            reload: Enable auto-reload for development
            access_log: Enable access logging
        """
        actual_host = host or self.config.host
        actual_port = port or self.config.port

        print(f"🚀 TraceTap Mock Server starting...")
        print(f"   Host: {actual_host}:{actual_port}")
        print(f"   Captures loaded: {len(self.captures)}")
        print(f"   Matching strategy: {self.config.matching_strategy}")

        if self.config.admin_enabled:
            print(f"   Admin API: http://{actual_host}:{actual_port}{self.config.admin_prefix}/metrics")

        if self.config.chaos_enabled:
            print(f"   ⚠️  Chaos mode enabled ({self.config.chaos_failure_rate * 100}% failure rate)")

        print()

        uvicorn.run(
            self.app,
            host=actual_host,
            port=actual_port,
            log_level=self.config.log_level,
            access_log=access_log,
            reload=reload
        )

    def get_app(self) -> FastAPI:
        """
        Get the FastAPI app instance for testing or custom deployment.

        Returns:
            FastAPI application instance
        """
        return self.app


def create_mock_server(
    log_file: str,
    host: str = "127.0.0.1",
    port: int = 8080,
    matching_strategy: str = "fuzzy",
    add_delay_ms: int = 0,
    chaos_enabled: bool = False,
    chaos_failure_rate: float = 0.0,
    ai_enabled: bool = False,
    ai_api_key: Optional[str] = None,
    response_mode: str = "static",
    recording_enabled: bool = False,
    recording_limit: int = 1000,
    diff_enabled: bool = False,
    diff_threshold: float = 0.8,
    diff_limit: int = 100
) -> MockServer:
    """
    Convenience function to create and configure a mock server.

    Args:
        log_file: Path to TraceTap JSON log file
        host: Host to bind to
        port: Port to bind to
        matching_strategy: Matching strategy (exact, fuzzy, pattern, semantic)
        add_delay_ms: Fixed delay in milliseconds
        chaos_enabled: Enable chaos engineering
        chaos_failure_rate: Chaos failure rate (0.0 to 1.0)
        ai_enabled: Enable AI-powered features
        ai_api_key: Anthropic API key for AI features
        response_mode: Response generation mode (static, template, transform, ai, intelligent)
        recording_enabled: Enable request recording
        recording_limit: Maximum requests to record (0 = unlimited)
        diff_enabled: Enable request diff tracking
        diff_threshold: Track diffs when match score below this (0.0-1.0)
        diff_limit: Maximum diffs to store (0 = unlimited)

    Returns:
        Configured MockServer instance

    Example:
        server = create_mock_server(
            'session.json',
            port=8080,
            matching_strategy='fuzzy',
            add_delay_ms=50,
            ai_enabled=True,
            response_mode='intelligent',
            recording_enabled=True,
            diff_enabled=True
        )
        server.start()
    """
    config = MockConfig(
        host=host,
        port=port,
        matching_strategy=matching_strategy,
        add_delay_ms=add_delay_ms,
        chaos_enabled=chaos_enabled,
        chaos_failure_rate=chaos_failure_rate,
        ai_enabled=ai_enabled,
        ai_api_key=ai_api_key,
        response_mode=response_mode,
        recording_enabled=recording_enabled,
        recording_limit=recording_limit,
        diff_enabled=diff_enabled,
        diff_threshold=diff_threshold,
        diff_limit=diff_limit
    )

    return MockServer(log_file, config=config)
