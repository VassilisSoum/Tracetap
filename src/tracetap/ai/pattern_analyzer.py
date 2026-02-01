"""
AI Pattern Analyzer for Traffic Analysis

Analyzes captured HTTP traffic to identify testing gaps and patterns.
Detects always-present vs never-seen conditions, error paths, and boundary conditions.
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from ..common.ai_utils import create_anthropic_client


class Pattern:
    """Represents a detected pattern in traffic"""

    def __init__(
        self,
        pattern_type: str,
        severity: str,
        title: str,
        description: str,
        evidence: List[str],
        suggestion: str,
        confidence: float = 1.0
    ):
        self.pattern_type = pattern_type
        self.severity = severity  # HIGH, MEDIUM, LOW
        self.title = title
        self.description = description
        self.evidence = evidence
        self.suggestion = suggestion
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'type': self.pattern_type,
            'severity': self.severity,
            'title': self.title,
            'description': self.description,
            'evidence': self.evidence,
            'suggestion': self.suggestion,
            'confidence': self.confidence
        }


class PatternAnalyzer:
    """
    Analyzes HTTP traffic patterns to find testing gaps

    Detects:
    - Empty array scenarios (always returns data, never empty)
    - Error path coverage (missing 4xx, 5xx responses)
    - Concurrency patterns (simultaneous requests)
    - Boundary conditions (min/max values)
    - Success bias (only 2xx responses)
    """

    def __init__(self, use_ai: bool = True, verbose: bool = True):
        """
        Initialize pattern analyzer

        Args:
            use_ai: Whether to use AI enhancement (graceful degradation if unavailable)
            verbose: Print status messages
        """
        self.use_ai = use_ai
        self.verbose = verbose
        self.ai_client = None
        self.ai_available = False

        if use_ai:
            self.ai_client, self.ai_available, _ = create_anthropic_client(
                verbose=False  # Silent initialization
            )

    def analyze_traffic(self, requests: List[Dict]) -> Dict[str, Any]:
        """
        Analyze captured traffic for patterns

        Args:
            requests: List of captured HTTP requests

        Returns:
            Dictionary with analysis results:
            {
                'patterns': [Pattern objects],
                'stats': {...},
                'ai_enhanced': bool
            }
        """
        if not requests:
            return {
                'patterns': [],
                'stats': {},
                'ai_enhanced': False
            }

        if self.verbose:
            print(f"🔍 Analyzing {len(requests)} requests for patterns...")

        # Statistical analysis (no AI needed)
        patterns = []

        # 1. Detect empty array patterns
        patterns.extend(self._detect_empty_array_patterns(requests))

        # 2. Detect error path coverage gaps
        patterns.extend(self._detect_error_path_gaps(requests))

        # 3. Detect concurrency patterns
        patterns.extend(self._detect_concurrency_patterns(requests))

        # 4. Detect boundary conditions
        patterns.extend(self._detect_boundary_conditions(requests))

        # 5. Detect success bias
        patterns.extend(self._detect_success_bias(requests))

        # Compute statistics
        stats = self._compute_statistics(requests)

        # Optional AI enhancement
        ai_enhanced = False
        if self.ai_available and self.use_ai and len(patterns) > 0:
            try:
                patterns = self._enhance_with_ai(patterns, requests, stats)
                ai_enhanced = True
            except Exception as e:
                if self.verbose:
                    print(f"⚠ AI enhancement failed: {e}")

        if self.verbose:
            print(f"✓ Found {len(patterns)} patterns")

        return {
            'patterns': [p.to_dict() for p in patterns],
            'stats': stats,
            'ai_enhanced': ai_enhanced
        }

    def _detect_empty_array_patterns(self, requests: List[Dict]) -> List[Pattern]:
        """Detect endpoints that always return data, never empty arrays"""
        patterns = []

        # Group by endpoint
        endpoint_responses = defaultdict(list)
        for req in requests:
            if req.get('response_body'):
                endpoint = self._normalize_endpoint(req)
                try:
                    body = json.loads(req['response_body'])
                    endpoint_responses[endpoint].append(body)
                except (json.JSONDecodeError, TypeError):
                    pass

        # Check each endpoint
        for endpoint, responses in endpoint_responses.items():
            if len(responses) < 3:  # Need at least 3 samples
                continue

            # Check for array responses that are never empty
            array_responses = [r for r in responses if isinstance(r, list)]
            if len(array_responses) >= 3:
                non_empty = [r for r in array_responses if len(r) > 0]

                if len(non_empty) == len(array_responses):
                    # Always returns data, never empty
                    patterns.append(Pattern(
                        pattern_type='empty-array',
                        severity='MEDIUM',
                        title=f'Empty array never tested: {endpoint}',
                        description=f'Endpoint {endpoint} always returns data ({len(array_responses)} samples), but empty array case is never tested.',
                        evidence=[
                            f'Observed {len(array_responses)} responses, all non-empty',
                            f'Min size: {min(len(r) for r in array_responses)}',
                            f'Max size: {max(len(r) for r in array_responses)}'
                        ],
                        suggestion=f'Test {endpoint} with conditions that return empty array: no matching records, empty database, filtered to zero results.'
                    ))

        return patterns

    def _detect_error_path_gaps(self, requests: List[Dict]) -> List[Pattern]:
        """Detect missing error status codes"""
        patterns = []

        # Collect all status codes by endpoint
        endpoint_statuses = defaultdict(set)
        for req in requests:
            endpoint = self._normalize_endpoint(req)
            status = req.get('status_code', 200)
            endpoint_statuses[endpoint].add(status)

        # Common error codes to check for
        important_errors = {
            400: 'Bad Request (malformed input)',
            401: 'Unauthorized (missing/invalid auth)',
            403: 'Forbidden (insufficient permissions)',
            404: 'Not Found (invalid ID)',
            422: 'Unprocessable Entity (validation errors)',
            429: 'Rate Limited (too many requests)',
            500: 'Internal Server Error',
            503: 'Service Unavailable'
        }

        # Check each endpoint
        for endpoint, statuses in endpoint_statuses.items():
            # Only check endpoints with multiple requests
            if len([r for r in requests if self._normalize_endpoint(r) == endpoint]) < 2:
                continue

            # Check for missing error codes
            missing_errors = []
            for code, description in important_errors.items():
                if code not in statuses:
                    missing_errors.append(f'{code} ({description})')

            # If endpoint only has 2xx responses, flag it
            if all(200 <= s < 300 for s in statuses) and len(statuses) > 2:
                patterns.append(Pattern(
                    pattern_type='error-path',
                    severity='HIGH',
                    title=f'No error cases tested: {endpoint}',
                    description=f'Endpoint {endpoint} only shows success responses (2xx). Error handling is untested.',
                    evidence=[
                        f'Observed status codes: {sorted(statuses)}',
                        f'Missing error codes: {", ".join(missing_errors[:3])}'
                    ],
                    suggestion=f'Test error paths for {endpoint}: invalid IDs, malformed input, unauthorized access, rate limiting.'
                ))

        return patterns

    def _detect_concurrency_patterns(self, requests: List[Dict]) -> List[Pattern]:
        """Detect concurrent requests that might have race conditions"""
        patterns = []

        # Group requests by timestamp windows (within 100ms)
        concurrent_groups = []
        sorted_requests = sorted(
            [r for r in requests if r.get('timestamp')],
            key=lambda r: r['timestamp']
        )

        for i, req in enumerate(sorted_requests):
            if i == 0:
                concurrent_groups.append([req])
                continue

            # Parse timestamps
            curr_time = self._parse_timestamp(req.get('timestamp', ''))
            prev_time = self._parse_timestamp(sorted_requests[i-1].get('timestamp', ''))

            if curr_time and prev_time:
                time_diff = abs(curr_time - prev_time)

                # Within 100ms = concurrent
                if time_diff < 0.1:
                    concurrent_groups[-1].append(req)
                else:
                    concurrent_groups.append([req])

        # Find groups with 2+ requests to same endpoint
        for group in concurrent_groups:
            if len(group) < 2:
                continue

            # Group by endpoint within this concurrent window
            endpoint_requests = defaultdict(list)
            for req in group:
                endpoint = self._normalize_endpoint(req)
                endpoint_requests[endpoint].append(req)

            # Check for concurrent writes to same endpoint
            for endpoint, reqs in endpoint_requests.items():
                if len(reqs) >= 2:
                    methods = [r.get('method', 'GET') for r in reqs]
                    write_methods = [m for m in methods if m in ['POST', 'PUT', 'PATCH', 'DELETE']]

                    if len(write_methods) >= 2:
                        patterns.append(Pattern(
                            pattern_type='concurrency',
                            severity='HIGH',
                            title=f'Concurrent writes detected: {endpoint}',
                            description=f'Multiple write operations to {endpoint} occurred simultaneously. Potential race condition.',
                            evidence=[
                                f'{len(write_methods)} concurrent writes',
                                f'Methods: {", ".join(write_methods)}',
                                f'Within 100ms window'
                            ],
                            suggestion=f'Test {endpoint} with concurrent requests to ensure proper locking/isolation. Check for race conditions, duplicate processing, or lost updates.'
                        ))

        return patterns

    def _detect_boundary_conditions(self, requests: List[Dict]) -> List[Pattern]:
        """Detect missing boundary condition tests"""
        patterns = []

        # Look for numeric parameters in URLs and bodies
        numeric_params = defaultdict(list)

        for req in requests:
            endpoint = self._normalize_endpoint(req)

            # Check URL for numeric IDs
            url = req.get('url', '')
            numbers = re.findall(r'/(\d+)(?:/|$|\?)', url)
            for num in numbers:
                numeric_params[endpoint].append(int(num))

            # Check request body for numeric values
            if req.get('body'):
                try:
                    body = json.loads(req['body'])
                    numbers = self._extract_numbers_from_json(body)
                    numeric_params[endpoint].extend(numbers)
                except (json.JSONDecodeError, TypeError):
                    pass

        # Check for missing boundary tests
        for endpoint, numbers in numeric_params.items():
            if len(numbers) < 3:
                continue

            unique_numbers = set(numbers)

            # Check for missing zero/negative tests
            has_zero = 0 in unique_numbers
            has_negative = any(n < 0 for n in unique_numbers)
            has_small = any(0 < n < 10 for n in unique_numbers)
            has_large = any(n > 1000000 for n in unique_numbers)

            missing_boundaries = []
            if not has_zero:
                missing_boundaries.append('zero (0)')
            if not has_negative:
                missing_boundaries.append('negative values')
            if not has_large:
                missing_boundaries.append('large values (>1M)')

            if len(missing_boundaries) >= 2:
                patterns.append(Pattern(
                    pattern_type='boundary',
                    severity='MEDIUM',
                    title=f'Boundary conditions untested: {endpoint}',
                    description=f'Endpoint {endpoint} uses numeric parameters but boundary cases are missing.',
                    evidence=[
                        f'Values seen: {min(numbers)} to {max(numbers)}',
                        f'Missing: {", ".join(missing_boundaries)}'
                    ],
                    suggestion=f'Test {endpoint} with boundary values: zero, negative numbers, very large numbers, maximum int values.'
                ))

        return patterns

    def _detect_success_bias(self, requests: List[Dict]) -> List[Pattern]:
        """Detect overall success bias in testing"""
        patterns = []

        status_codes = [r.get('status_code', 200) for r in requests]

        if not status_codes:
            return patterns

        success_count = sum(1 for s in status_codes if 200 <= s < 300)
        error_count = sum(1 for s in status_codes if s >= 400)

        success_ratio = success_count / len(status_codes)

        # If 95%+ are successful, flag it
        if success_ratio >= 0.95 and len(requests) >= 10:
            patterns.append(Pattern(
                pattern_type='success-bias',
                severity='HIGH',
                title='Success bias: error scenarios undertested',
                description=f'{success_ratio*100:.1f}% of requests are successful (2xx). Error handling is undertested.',
                evidence=[
                    f'{success_count} success / {len(requests)} total requests',
                    f'Only {error_count} error responses observed',
                    f'Success ratio: {success_ratio*100:.1f}%'
                ],
                suggestion='Add tests for error scenarios: invalid input, missing resources, unauthorized access, rate limiting, server errors.'
            ))

        return patterns

    def _enhance_with_ai(
        self,
        patterns: List[Pattern],
        requests: List[Dict],
        stats: Dict
    ) -> List[Pattern]:
        """Enhance patterns with AI insights"""
        # Prepare summary for AI
        summary = self._prepare_summary_for_ai(patterns, requests, stats)

        # Ask AI for additional insights
        prompt = f"""Analyze this HTTP traffic pattern analysis and provide additional insights:

{summary}

Focus on:
1. Additional testing gaps not mentioned
2. Security implications
3. Performance testing opportunities
4. Data integrity concerns

Respond with 2-3 specific, actionable test suggestions."""

        try:
            message = self.ai_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            ai_insights = message.content[0].text

            # Parse AI response and add as patterns
            # For now, just add as a single insight pattern
            if ai_insights:
                patterns.append(Pattern(
                    pattern_type='ai-insight',
                    severity='MEDIUM',
                    title='AI-identified testing opportunities',
                    description=ai_insights,
                    evidence=['Claude AI analysis'],
                    suggestion='Review AI suggestions and incorporate into test plan.',
                    confidence=0.8
                ))

        except Exception as e:
            if self.verbose:
                print(f"⚠ AI enhancement failed: {e}")

        return patterns

    def _compute_statistics(self, requests: List[Dict]) -> Dict[str, Any]:
        """Compute traffic statistics"""
        if not requests:
            return {}

        status_codes = defaultdict(int)
        methods = defaultdict(int)
        endpoints = set()

        for req in requests:
            status_codes[req.get('status_code', 200)] += 1
            methods[req.get('method', 'GET')] += 1
            endpoints.add(self._normalize_endpoint(req))

        return {
            'total_requests': len(requests),
            'unique_endpoints': len(endpoints),
            'status_codes': dict(status_codes),
            'methods': dict(methods),
            'success_rate': sum(v for k, v in status_codes.items() if 200 <= k < 300) / len(requests)
        }

    def _normalize_endpoint(self, request: Dict) -> str:
        """Normalize endpoint by replacing IDs with placeholders"""
        url = request.get('url', '')
        method = request.get('method', 'GET')

        parsed = urlparse(url)
        path = parsed.path

        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{uuid}',
            path,
            flags=re.IGNORECASE
        )

        # Replace numeric IDs
        path = re.sub(r'/\d+(?:/|$)', '/{id}/', path)

        # Replace MongoDB IDs
        path = re.sub(r'/[0-9a-f]{24}(?:/|$)', '/{objectId}/', path)

        return f"{method} {path}".rstrip('/')

    def _parse_timestamp(self, timestamp: str) -> Optional[float]:
        """Parse ISO timestamp to seconds"""
        if not timestamp:
            return None

        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.timestamp()
        except (ValueError, AttributeError):
            return None

    def _extract_numbers_from_json(self, data: Any, numbers: Optional[List[int]] = None) -> List[int]:
        """Recursively extract numbers from JSON data"""
        if numbers is None:
            numbers = []

        if isinstance(data, dict):
            for value in data.values():
                self._extract_numbers_from_json(value, numbers)
        elif isinstance(data, list):
            for item in data:
                self._extract_numbers_from_json(item, numbers)
        elif isinstance(data, int):
            numbers.append(data)

        return numbers

    def _prepare_summary_for_ai(
        self,
        patterns: List[Pattern],
        requests: List[Dict],
        stats: Dict
    ) -> str:
        """Prepare traffic summary for AI analysis"""
        summary_lines = [
            f"Traffic Summary:",
            f"- Total requests: {stats.get('total_requests', 0)}",
            f"- Unique endpoints: {stats.get('unique_endpoints', 0)}",
            f"- Success rate: {stats.get('success_rate', 0)*100:.1f}%",
            "",
            "Detected Patterns:"
        ]

        for i, pattern in enumerate(patterns[:5], 1):  # Top 5 patterns
            summary_lines.append(f"{i}. [{pattern.severity}] {pattern.title}")
            summary_lines.append(f"   {pattern.description}")

        return "\n".join(summary_lines)


def analyze_traffic_file(
    json_file: str,
    use_ai: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to analyze traffic from JSON file

    Args:
        json_file: Path to captured traffic JSON
        use_ai: Whether to use AI enhancement
        verbose: Print status messages

    Returns:
        Analysis results dictionary
    """
    # Load traffic
    with open(json_file, 'r') as f:
        data = json.load(f)

    requests = data.get('requests', [])

    # Analyze
    analyzer = PatternAnalyzer(use_ai=use_ai, verbose=verbose)
    return analyzer.analyze_traffic(requests)
